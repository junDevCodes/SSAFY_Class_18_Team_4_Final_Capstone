"""
모델 학습 모듈

user_product_stats 기반 ALS 모델 학습
- 서버 시작 시 모델 없으면 자동 학습
- 매일 새벽 3시 배치 학습
- 백그라운드 비동기 학습 지원
"""

import asyncio
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix

from core.database import Database
from core.logging import get_logger
from ml.model_loader import model_loader

logger = get_logger(__name__)


class ALSTrainer:
    """ALS (Alternating Least Squares) 모델 학습기

    Implicit feedback 기반 협업 필터링 모델 학습
    - user_product_stats 테이블 데이터 사용
    - Confidence Weighting: α * interaction_score
    - 32차원 latent factor

    참조:
    - Hu, Y., Koren, Y., & Volinsky, C. (2008). IEEE ICDM
    """

    def __init__(
        self,
        db: Database,
        factors: int = 32,
        regularization: float = 0.01,
        alpha: float = 15.0,
        iterations: int = 15,
    ):
        """
        Args:
            db: 데이터베이스 인스턴스
            factors: Latent factor 차원 수
            regularization: L2 정규화 계수
            alpha: Confidence weighting 계수
            iterations: ALS 반복 횟수
        """
        self.db = db
        self.factors = factors
        self.regularization = regularization
        self.alpha = alpha
        self.iterations = iterations

        # 학습 상태
        self._is_training = False
        self._last_trained_at: Optional[datetime] = None
        self._training_task: Optional[asyncio.Task] = None

    async def fetch_interaction_data(self) -> Tuple[
        Dict[int, int],  # user_id_to_idx
        Dict[int, int],  # product_id_to_idx
        Dict[int, int],  # idx_to_product_id
        List[Tuple[int, int, float]],  # (user_idx, product_idx, score)
    ]:
        """DB에서 상호작용 데이터 조회

        Returns:
            user_id_to_idx: 사용자 ID → 인덱스 매핑
            product_id_to_idx: 상품 ID → 인덱스 매핑
            idx_to_product_id: 인덱스 → 상품 ID 매핑
            interactions: (user_idx, product_idx, score) 튜플 리스트
        """
        # 상호작용 데이터 조회 (가중치 적용)
        query = """
            SELECT
                ups.user_id,
                ups.product_id,
                (ups.order_event_count * 10.0 +
                 ups.cart_event_count * 2.0 +
                 ups.view_count * 0.1) AS score
            FROM user_product_stats ups
            JOIN products p ON ups.product_id = p.id
            WHERE p.status = 'active'
              AND (ups.order_event_count > 0 OR
                   ups.cart_event_count > 0 OR
                   ups.view_count > 0)
        """

        records = await self.db.fetch_all(query)

        if not records:
            logger.warning("학습할 상호작용 데이터가 없습니다")
            return {}, {}, {}, []

        # ID → 인덱스 매핑 생성
        user_ids = sorted(set(r["user_id"] for r in records))
        product_ids = sorted(set(r["product_id"] for r in records))

        user_id_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        product_id_to_idx = {pid: idx for idx, pid in enumerate(product_ids)}
        idx_to_product_id = {idx: pid for pid, idx in product_id_to_idx.items()}

        # 상호작용 리스트 생성
        interactions = [
            (
                user_id_to_idx[r["user_id"]],
                product_id_to_idx[r["product_id"]],
                float(r["score"]),
            )
            for r in records
        ]

        logger.info(
            "상호작용 데이터 로드 완료",
            extra={
                "n_users": len(user_ids),
                "n_products": len(product_ids),
                "n_interactions": len(interactions),
            }
        )

        return user_id_to_idx, product_id_to_idx, idx_to_product_id, interactions

    def build_interaction_matrix(
        self,
        n_users: int,
        n_products: int,
        interactions: List[Tuple[int, int, float]],
    ) -> csr_matrix:
        """상호작용 행렬 생성

        Args:
            n_users: 사용자 수
            n_products: 상품 수
            interactions: (user_idx, product_idx, score) 리스트

        Returns:
            CSR 형식 희소 행렬
        """
        rows = [i[0] for i in interactions]
        cols = [i[1] for i in interactions]
        data = [i[2] for i in interactions]

        return csr_matrix(
            (data, (rows, cols)),
            shape=(n_users, n_products),
            dtype=np.float32,
        )

    def train_als(
        self,
        interaction_matrix: csr_matrix,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """ALS 알고리즘으로 학습

        Implicit ALS 구현 (Hu et al., 2008)

        Args:
            interaction_matrix: 사용자-상품 상호작용 행렬

        Returns:
            (user_factors, item_factors) 튜플
        """
        n_users, n_items = interaction_matrix.shape

        # 랜덤 초기화
        np.random.seed(42)
        user_factors = np.random.randn(n_users, self.factors).astype(np.float32) * 0.01
        item_factors = np.random.randn(n_items, self.factors).astype(np.float32) * 0.01

        # Confidence matrix: C = 1 + α * R
        confidence = interaction_matrix.copy()
        confidence.data = 1 + self.alpha * confidence.data

        # Preference matrix: P = (R > 0)
        preference = interaction_matrix.copy()
        preference.data = np.ones_like(preference.data)

        # 정규화 행렬
        reg_matrix = self.regularization * np.eye(self.factors, dtype=np.float32)

        logger.info(f"ALS 학습 시작: {self.iterations}회 반복")

        for iteration in range(self.iterations):
            # User factors 업데이트
            user_factors = self._als_step(
                confidence, preference, item_factors, reg_matrix, is_user=True
            )

            # Item factors 업데이트
            item_factors = self._als_step(
                confidence.T.tocsr(), preference.T.tocsr(),
                user_factors, reg_matrix, is_user=False
            )

            if (iteration + 1) % 5 == 0:
                logger.info(f"ALS 반복 {iteration + 1}/{self.iterations} 완료")

        logger.info("ALS 학습 완료")
        return user_factors, item_factors

    def _als_step(
        self,
        confidence: csr_matrix,
        preference: csr_matrix,
        fixed_factors: np.ndarray,
        reg_matrix: np.ndarray,
        is_user: bool,
    ) -> np.ndarray:
        """ALS 단일 스텝 (User 또는 Item factor 업데이트)

        Args:
            confidence: Confidence 행렬
            preference: Preference 행렬
            fixed_factors: 고정된 factor (반대편)
            reg_matrix: 정규화 행렬
            is_user: User factor 업데이트 여부

        Returns:
            업데이트된 factors
        """
        n_entities = confidence.shape[0]
        n_factors = fixed_factors.shape[1]

        # Y^T Y 사전 계산
        YtY = fixed_factors.T @ fixed_factors

        new_factors = np.zeros((n_entities, n_factors), dtype=np.float32)

        for i in range(n_entities):
            # 해당 entity의 confidence와 preference
            conf_row = confidence.getrow(i).toarray().flatten()
            pref_row = preference.getrow(i).toarray().flatten()

            # Confidence weight 적용
            # A = Y^T C_u Y + λI
            Cu_minus_I = np.diag(conf_row - 1)  # C_u - I
            A = YtY + fixed_factors.T @ Cu_minus_I @ fixed_factors + reg_matrix

            # b = Y^T C_u p_u
            b = fixed_factors.T @ (conf_row * pref_row)

            # Solve: x = A^-1 b
            try:
                new_factors[i] = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                # 특이 행렬인 경우 pseudo-inverse 사용
                new_factors[i] = np.linalg.lstsq(A, b, rcond=None)[0]

        return new_factors

    async def fetch_popular_products(self) -> Tuple[List[int], Dict[int, List[int]]]:
        """인기 상품 조회

        Returns:
            global_popular: 전체 인기 상품 ID 리스트
            category_popular: 카테고리별 인기 상품 딕셔너리
        """
        # 전체 인기 상품
        global_query = """
            SELECT p.id
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
            ORDER BY COALESCE(ps.order_event_count, 0) DESC,
                     COALESCE(ps.view_count, 0) DESC
            LIMIT 100
        """
        global_records = await self.db.fetch_all(global_query)
        global_popular = [r["id"] for r in global_records]

        # 카테고리별 인기 상품
        category_query = """
            SELECT p.category_id, p.id
            FROM products p
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
              AND p.category_id IS NOT NULL
            ORDER BY p.category_id,
                     COALESCE(ps.order_event_count, 0) DESC,
                     COALESCE(ps.view_count, 0) DESC
        """
        category_records = await self.db.fetch_all(category_query)

        category_popular: Dict[int, List[int]] = {}
        for r in category_records:
            cat_id = r["category_id"]
            if cat_id not in category_popular:
                category_popular[cat_id] = []
            if len(category_popular[cat_id]) < 20:  # 카테고리당 최대 20개
                category_popular[cat_id].append(r["id"])

        logger.info(
            "인기 상품 조회 완료",
            extra={
                "global_count": len(global_popular),
                "category_count": len(category_popular),
            }
        )

        return global_popular, category_popular

    async def train_and_save(self, model_name: str = "self_personalized_v2") -> bool:
        """모델 학습 및 저장

        Args:
            model_name: 저장할 모델 이름

        Returns:
            학습 성공 여부
        """
        if self._is_training:
            logger.warning("이미 학습이 진행 중입니다")
            return False

        self._is_training = True
        start_time = datetime.now()

        try:
            logger.info("모델 학습 시작")

            # 1. 기존 모델 백업
            model_loader.backup_model(model_name)

            # 2. 데이터 로드
            (
                user_id_to_idx,
                product_id_to_idx,
                idx_to_product_id,
                interactions,
            ) = await self.fetch_interaction_data()

            if not interactions:
                logger.error("학습 데이터 없음 - 학습 중단")
                return False

            n_users = len(user_id_to_idx)
            n_products = len(product_id_to_idx)

            # 3. 상호작용 행렬 생성
            interaction_matrix = self.build_interaction_matrix(
                n_users, n_products, interactions
            )

            # 4. ALS 학습 (CPU 집약적이므로 별도 스레드에서 실행)
            loop = asyncio.get_event_loop()
            user_factors, item_factors = await loop.run_in_executor(
                None, self.train_als, interaction_matrix
            )

            # 5. 인기 상품 조회
            global_popular, category_popular = await self.fetch_popular_products()

            # 6. 모델 저장
            model_data = {
                "version": "2.0.0",
                "algorithm": "ALS",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "n_users": n_users,
                    "n_items": n_products,
                    "factors": self.factors,
                    "dtype": str(user_factors.dtype),
                },
                "hyperparameters": {
                    "factors": self.factors,
                    "regularization": self.regularization,
                    "alpha": self.alpha,
                    "iterations": self.iterations,
                    "cbf_weight": 0.7,
                    "cf_weight": 0.3,
                    "filter_already_liked_items": False,
                },
                "components": {
                    "user_embeddings": user_factors.tobytes(),
                    "product_embeddings": item_factors.tobytes(),
                    "user_id_to_idx": user_id_to_idx,
                    "idx_to_product_id": idx_to_product_id,
                    "global_popular_products": global_popular,
                    "category_popular_products": category_popular,
                },
                "metrics": {
                    "training_time_seconds": (datetime.now() - start_time).total_seconds(),
                },
            }

            # 저장 (런타임 모델은 runtime 디렉토리에 저장)
            model_path = model_loader.runtime_dir / f"{model_name}.pkl"
            model_loader.runtime_dir.mkdir(parents=True, exist_ok=True)

            with open(model_path, "wb") as f:
                pickle.dump(model_data, f)

            training_time = (datetime.now() - start_time).total_seconds()
            self._last_trained_at = datetime.now()

            logger.info(
                "모델 학습 및 저장 완료",
                extra={
                    "model_name": model_name,
                    "model_path": str(model_path),
                    "n_users": n_users,
                    "n_products": n_products,
                    "training_time_seconds": round(training_time, 2),
                }
            )

            return True

        except Exception as e:
            logger.error(f"모델 학습 실패: {e}", exc_info=True)
            return False

        finally:
            self._is_training = False

    async def train_in_background(self, model_name: str = "self_personalized_v2") -> None:
        """백그라운드에서 비동기 학습 실행

        Args:
            model_name: 모델 이름
        """
        if self._training_task is not None and not self._training_task.done():
            logger.warning("이미 백그라운드 학습이 진행 중입니다")
            return

        async def _train():
            await self.train_and_save(model_name)

        self._training_task = asyncio.create_task(_train())
        logger.info(f"백그라운드 학습 시작: {model_name}")

    @property
    def is_training(self) -> bool:
        """학습 진행 중 여부"""
        return self._is_training

    @property
    def last_trained_at(self) -> Optional[datetime]:
        """마지막 학습 시간"""
        return self._last_trained_at

    def get_status(self) -> Dict[str, Any]:
        """학습기 상태 조회"""
        return {
            "is_training": self._is_training,
            "last_trained_at": self._last_trained_at.isoformat() if self._last_trained_at else None,
            "hyperparameters": {
                "factors": self.factors,
                "regularization": self.regularization,
                "alpha": self.alpha,
                "iterations": self.iterations,
            },
        }


# 전역 학습기 인스턴스 (lazy init)
_trainer: Optional[ALSTrainer] = None


def get_trainer(db: Database) -> ALSTrainer:
    """ALSTrainer 싱글톤 인스턴스 반환"""
    global _trainer
    if _trainer is None:
        _trainer = ALSTrainer(db=db)
    return _trainer
