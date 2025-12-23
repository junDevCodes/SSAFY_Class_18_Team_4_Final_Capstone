"""
Instacart 데이터 처리 및 희소 행렬 생성 모듈

Kaggle 최상위 랭커 수준의 메모리 효율적 데이터 처리
- 청크 단위 로드 (대용량 CSV 처리)
- 데이터 타입 최적화 (int64 → int32)
- CSR 희소 행렬 생성
- Confidence Weighting 적용

============================================================================
Instacart 데이터셋 구조
============================================================================

1. orders.csv (3.4M 레코드)
   - order_id, user_id, eval_set, order_number
   - order_dow (요일), order_hour_of_day (시간)
   - days_since_prior_order (이전 주문 이후 일수)

2. order_products__prior.csv (32M 레코드)
   - order_id, product_id, add_to_cart_order, reordered

3. order_products__train.csv (1.4M 레코드)
   - order_id, product_id, add_to_cart_order, reordered

4. products.csv (50K 레코드)
   - product_id, product_name, aisle_id, department_id

5. aisles.csv (134 레코드)
   - aisle_id, aisle

6. departments.csv (21 레코드)
   - department_id, department
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix, save_npz, load_npz
from typing import List, Dict, Tuple, Optional, Generator, Any
from pathlib import Path
import pickle
import gc
import logging
import time

from .weight_config import (
    INTERACTION_WEIGHTS,
    CONFIDENCE_WEIGHTS,
    TIME_DECAY_WEIGHTS,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. Instacart 데이터 로더
# ============================================================================

class InstacartDataLoader:
    """
    Instacart Kaggle 데이터셋 로더

    메모리 효율성을 위한 설계:
    - 청크 단위 로드 (대용량 CSV)
    - 데이터 타입 최적화
    - 불필요한 컬럼 제거
    """

    # 데이터 타입 최적화 (메모리 50%+ 절감)
    DTYPE_OPTIMIZATIONS = {
        'orders': {
            'order_id': 'int32',
            'user_id': 'int32',
            'order_number': 'int16',
            'order_dow': 'int8',
            'order_hour_of_day': 'int8',
            'days_since_prior_order': 'float32',  # NaN 가능 (일부 Pandas 버전에서 float16 파싱 이슈 회피)
        },
        'order_products': {
            'order_id': 'int32',
            'product_id': 'int32',
            'add_to_cart_order': 'int8',
            'reordered': 'int8',
        },
        'products': {
            'product_id': 'int32',
            'aisle_id': 'int16',
            'department_id': 'int8',
        },
    }

    def __init__(
        self,
        data_dir: Optional[str] = None,
        *,
        data_path: Optional[str] = None,
        chunk_size: int = 1_000_000,
    ):
        """
        Args:
            data_dir: Instacart 데이터 디렉토리 경로
            data_path: data_dir 별칭(노트북 호환용)
            chunk_size: 기본 청크 크기(대용량 CSV 처리용)
        """
        if data_dir is None and data_path is None:
            raise ValueError("data_dir 또는 data_path는 필수입니다.")

        if data_dir is not None and data_path is not None:
            if Path(data_dir) != Path(data_path):
                raise ValueError("data_dir과 data_path가 서로 다릅니다.")

        resolved_data_dir = data_dir or data_path
        if resolved_data_dir is None:
            raise ValueError("data_dir 또는 data_path는 필수입니다.")

        self.data_dir = Path(resolved_data_dir)
        self.chunk_size = chunk_size

        # 캐시된 데이터
        self._orders = None
        self._order_products_prior = None
        self._order_products_train = None
        self._products = None
        self._aisles = None
        self._departments = None

    def load_orders(
        self,
        chunksize: Optional[int] = None,
        usecols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        orders.csv 로드

        Args:
            chunksize: 청크 크기 (None이면 전체 로드)
            usecols: 로드할 컬럼 리스트

        Returns:
            주문 DataFrame
        """
        filepath = self.data_dir / 'orders.csv'

        if not filepath.exists():
            raise FileNotFoundError(f"파일 없음: {filepath}")

        logger.info(f"orders.csv 로드 중... ({filepath})")
        start_time = time.time()

        dtype = self.DTYPE_OPTIMIZATIONS['orders']

        if chunksize:
            # 청크 단위 로드
            chunks = []
            for chunk in pd.read_csv(
                filepath,
                chunksize=chunksize,
                dtype=dtype,
                usecols=usecols
            ):
                chunks.append(chunk)
            df = pd.concat(chunks, ignore_index=True)
        else:
            df = pd.read_csv(filepath, dtype=dtype, usecols=usecols)

        elapsed = time.time() - start_time
        logger.info(f"  로드 완료: {len(df):,}개 레코드 ({elapsed:.1f}초)")

        self._orders = df
        return df

    def load_order_products_prior(
        self,
        chunksize: int = 1_000_000,
        usecols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        order_products__prior.csv 로드 (32M 레코드, 청크 필수)

        Args:
            chunksize: 청크 크기 (기본 100만)
            usecols: 로드할 컬럼 리스트

        Returns:
            주문-상품 DataFrame
        """
        filepath = self.data_dir / 'order_products__prior.csv'

        if not filepath.exists():
            raise FileNotFoundError(f"파일 없음: {filepath}")

        logger.info(f"order_products__prior.csv 로드 중... ({filepath})")
        start_time = time.time()

        dtype = self.DTYPE_OPTIMIZATIONS['order_products']

        chunks = []
        total_rows = 0

        for i, chunk in enumerate(pd.read_csv(
            filepath,
            chunksize=chunksize,
            dtype=dtype,
            usecols=usecols
        )):
            chunks.append(chunk)
            total_rows += len(chunk)
            if (i + 1) % 10 == 0:
                logger.info(f"  진행: {total_rows:,}개 레코드...")

        df = pd.concat(chunks, ignore_index=True)

        elapsed = time.time() - start_time
        logger.info(f"  로드 완료: {len(df):,}개 레코드 ({elapsed:.1f}초)")

        self._order_products_prior = df
        return df

    def load_order_products(
        self,
        split: str,
        chunksize: Optional[int] = None,
        usecols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        order_products 데이터 로드 (prior/train 통합 API)

        Args:
            split: 'prior' 또는 'train'
            chunksize: 청크 크기 (prior는 기본으로 self.chunk_size 사용)
            usecols: 로드할 컬럼 리스트

        Returns:
            주문-상품 DataFrame
        """
        if split not in {"prior", "train"}:
            raise ValueError("split은 'prior' 또는 'train'이어야 합니다.")

        if split == "prior":
            return self.load_order_products_prior(
                chunksize=chunksize or self.chunk_size,
                usecols=usecols,
            )

        if chunksize:
            filepath = self.data_dir / "order_products__train.csv"

            if not filepath.exists():
                raise FileNotFoundError(f"파일 없음: {filepath}")

            logger.info(f"order_products__train.csv 로드 중... (청크: {chunksize:,})")
            start_time = time.time()

            dtype = self.DTYPE_OPTIMIZATIONS["order_products"]
            chunks = []
            total_rows = 0

            for i, chunk in enumerate(
                pd.read_csv(
                    filepath,
                    chunksize=chunksize,
                    dtype=dtype,
                    usecols=usecols,
                )
            ):
                chunks.append(chunk)
                total_rows += len(chunk)
                if (i + 1) % 10 == 0:
                    logger.info(f"  진행: {total_rows:,}개 레코드...")

            df = pd.concat(chunks, ignore_index=True)

            elapsed = time.time() - start_time
            logger.info(f"  로드 완료: {len(df):,}개 레코드 ({elapsed:.1f}초)")

            self._order_products_train = df
            return df

        return self.load_order_products_train(usecols=usecols)

    def load_order_products_train(
        self,
        usecols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        order_products__train.csv 로드

        Args:
            usecols: 로드할 컬럼 리스트

        Returns:
            주문-상품 DataFrame
        """
        filepath = self.data_dir / 'order_products__train.csv'

        if not filepath.exists():
            raise FileNotFoundError(f"파일 없음: {filepath}")

        logger.info(f"order_products__train.csv 로드 중...")
        start_time = time.time()

        dtype = self.DTYPE_OPTIMIZATIONS['order_products']
        df = pd.read_csv(filepath, dtype=dtype, usecols=usecols)

        elapsed = time.time() - start_time
        logger.info(f"  로드 완료: {len(df):,}개 레코드 ({elapsed:.1f}초)")

        self._order_products_train = df
        return df

    def load_products(self) -> pd.DataFrame:
        """
        products.csv 로드

        Returns:
            상품 DataFrame
        """
        filepath = self.data_dir / 'products.csv'

        if not filepath.exists():
            raise FileNotFoundError(f"파일 없음: {filepath}")

        logger.info(f"products.csv 로드 중...")
        dtype = self.DTYPE_OPTIMIZATIONS['products']

        df = pd.read_csv(filepath, dtype=dtype)
        logger.info(f"  로드 완료: {len(df):,}개 상품")

        self._products = df
        return df

    def load_aisles(self) -> pd.DataFrame:
        """aisles.csv 로드"""
        filepath = self.data_dir / 'aisles.csv'
        df = pd.read_csv(filepath)
        logger.info(f"aisles.csv 로드 완료: {len(df)}개 통로")
        self._aisles = df
        return df

    def load_departments(self) -> pd.DataFrame:
        """departments.csv 로드"""
        filepath = self.data_dir / 'departments.csv'
        df = pd.read_csv(filepath)
        logger.info(f"departments.csv 로드 완료: {len(df)}개 부서")
        self._departments = df
        return df

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """
        모든 데이터셋 로드

        Returns:
            데이터셋 딕셔너리
        """
        return {
            'orders': self.load_orders(),
            'order_products_prior': self.load_order_products('prior'),
            'order_products_train': self.load_order_products('train'),
            'products': self.load_products(),
            'aisles': self.load_aisles(),
            'departments': self.load_departments(),
        }

    def build_user_product_interactions(
        self,
        orders_df: Optional[pd.DataFrame] = None,
        order_products_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        사용자-상품 상호작용 DataFrame 생성

        Args:
            orders_df: 주문 DataFrame (None이면 캐시 사용)
            order_products_df: 주문-상품 DataFrame (None이면 캐시 사용)

        Returns:
            사용자-상품 상호작용 DataFrame
            컬럼: user_id, product_id, order_count, reorder_count, days_since_first
        """
        if orders_df is None:
            orders_df = self._orders
        if order_products_df is None:
            order_products_df = self._order_products_prior

        if orders_df is None or order_products_df is None:
            raise ValueError("데이터가 로드되지 않음. load_orders(), load_order_products_prior() 먼저 호출")

        logger.info("사용자-상품 상호작용 구축 중...")
        start_time = time.time()

        # 주문-상품 조인
        merged = order_products_df.merge(
            orders_df[['order_id', 'user_id', 'days_since_prior_order']],
            on='order_id',
            how='left'
        )

        # 사용자-상품별 집계
        interactions = merged.groupby(['user_id', 'product_id']).agg({
            'order_id': 'count',  # 주문 횟수
            'reordered': 'sum',   # 재주문 횟수
            'days_since_prior_order': 'mean',  # 평균 재구매 주기
        }).reset_index()

        interactions.columns = [
            'user_id', 'product_id', 'order_count', 'reorder_count', 'avg_days_between'
        ]

        elapsed = time.time() - start_time
        logger.info(f"  상호작용 구축 완료: {len(interactions):,}개 ({elapsed:.1f}초)")

        return interactions

    def save_to_parquet(
        self,
        df: pd.DataFrame,
        filename: str,
        output_dir: Optional[str] = None
    ) -> Path:
        """
        Parquet 포맷으로 저장 (압축, 빠른 로드)

        Args:
            df: 저장할 DataFrame
            filename: 파일명
            output_dir: 출력 디렉토리 (None이면 data_dir)

        Returns:
            저장된 파일 경로
        """
        if output_dir is None:
            output_dir = self.data_dir

        output_path = Path(output_dir) / filename
        df.to_parquet(output_path, engine='pyarrow', index=False)
        logger.info(f"Parquet 저장 완료: {output_path}")

        return output_path


# ============================================================================
# 2. 상호작용 행렬 빌더
# ============================================================================

class InteractionMatrixBuilder:
    """
    희소 상호작용 행렬 생성기

    Kaggle 최적화:
    - CSR 포맷 (행 기반 연산 최적화)
    - float32 (메모리 50% 절감)
    - ID 매핑 완전 저장 (재현성)
    """

    def __init__(self):
        # ID 매핑
        self.user_id_to_idx: Dict[int, int] = {}
        self.idx_to_user_id: Dict[int, int] = {}
        self.item_id_to_idx: Dict[int, int] = {}
        self.idx_to_item_id: Dict[int, int] = {}

        # 통계
        self.n_users: int = 0
        self.n_items: int = 0
        self.n_interactions: int = 0

    def build_matrix(
        self,
        user_ids: List[int],
        item_ids: List[int],
        values: List[float]
    ) -> csr_matrix:
        """
        희소 상호작용 행렬 생성

        Args:
            user_ids: 사용자 ID 리스트
            item_ids: 아이템 ID 리스트
            values: 상호작용 값 리스트

        Returns:
            CSR 희소 행렬 (user × item)
        """
        logger.info("상호작용 행렬 생성 중...")
        start_time = time.time()

        # 1. ID 매핑 생성
        unique_users = sorted(set(user_ids))
        unique_items = sorted(set(item_ids))

        self.user_id_to_idx = {uid: i for i, uid in enumerate(unique_users)}
        self.idx_to_user_id = {i: uid for uid, i in self.user_id_to_idx.items()}
        self.item_id_to_idx = {iid: i for i, iid in enumerate(unique_items)}
        self.idx_to_item_id = {i: iid for iid, i in self.item_id_to_idx.items()}

        self.n_users = len(unique_users)
        self.n_items = len(unique_items)
        self.n_interactions = len(values)

        # 2. 인덱스 변환
        rows = [self.user_id_to_idx[uid] for uid in user_ids]
        cols = [self.item_id_to_idx[iid] for iid in item_ids]

        # 3. CSR 행렬 생성
        matrix = csr_matrix(
            (values, (rows, cols)),
            shape=(self.n_users, self.n_items),
            dtype=np.float32
        )

        # 4. 희소성 계산
        density = self.n_interactions / (self.n_users * self.n_items)
        sparsity = 1 - density

        elapsed = time.time() - start_time
        logger.info(f"  행렬 크기: {self.n_users:,} × {self.n_items:,}")
        logger.info(f"  상호작용: {self.n_interactions:,}개")
        logger.info(f"  희소성: {sparsity:.2%}")
        logger.info(f"  완료: {elapsed:.1f}초")

        return matrix

    def build_from_dataframe(
        self,
        df: pd.DataFrame,
        user_col: str = 'user_id',
        item_col: str = 'product_id',
        value_col: str = 'score'
    ) -> csr_matrix:
        """
        DataFrame에서 희소 행렬 생성

        Args:
            df: 상호작용 DataFrame
            user_col: 사용자 ID 컬럼명
            item_col: 아이템 ID 컬럼명
            value_col: 값 컬럼명

        Returns:
            CSR 희소 행렬
        """
        return self.build_matrix(
            user_ids=df[user_col].tolist(),
            item_ids=df[item_col].tolist(),
            values=df[value_col].tolist()
        )

    def apply_confidence_weighting(
        self,
        matrix: csr_matrix,
        alpha: float = 15.0
    ) -> csr_matrix:
        """
        Confidence Weighting 적용 (Hu et al., 2008)

        공식: C_ui = 1 + α × log(1 + r_ui)

        Args:
            matrix: 원본 상호작용 행렬
            alpha: 스케일링 팩터

        Returns:
            Confidence 가중 행렬
        """
        logger.info(f"Confidence Weighting 적용 (α={alpha})...")

        confidence = matrix.copy()
        confidence.data = 1 + alpha * np.log1p(confidence.data)

        return confidence

    def apply_time_decay(
        self,
        matrix: csr_matrix,
        days_matrix: csr_matrix,
        decay_rate: float = 0.05
    ) -> csr_matrix:
        """
        시간 감쇠 가중치 적용

        공식: weight = r_ui × exp(-λ × days)

        Args:
            matrix: 원본 상호작용 행렬
            days_matrix: 경과 일수 행렬 (동일 형태)
            decay_rate: 감쇠율 (λ)

        Returns:
            시간 감쇠 적용 행렬
        """
        logger.info(f"시간 감쇠 적용 (λ={decay_rate})...")

        decayed = matrix.copy()
        time_weights = np.exp(-decay_rate * days_matrix.data)
        decayed.data = decayed.data * time_weights

        return decayed

    def get_mappings(self) -> Dict[str, Dict]:
        """
        ID 매핑 반환 (Pickle 저장용)

        Returns:
            매핑 딕셔너리
        """
        return {
            'user_id_to_idx': self.user_id_to_idx,
            'idx_to_user_id': self.idx_to_user_id,
            'item_id_to_idx': self.item_id_to_idx,
            'idx_to_item_id': self.idx_to_item_id,
            'n_users': self.n_users,
            'n_items': self.n_items,
            'n_interactions': self.n_interactions,
        }

    def set_mappings(self, mappings: Dict[str, Dict]):
        """
        ID 매핑 설정 (Pickle 로드용)

        Args:
            mappings: 매핑 딕셔너리
        """
        self.user_id_to_idx = mappings['user_id_to_idx']
        self.idx_to_user_id = mappings['idx_to_user_id']
        self.item_id_to_idx = mappings['item_id_to_idx']
        self.idx_to_item_id = mappings['idx_to_item_id']
        self.n_users = mappings['n_users']
        self.n_items = mappings['n_items']
        self.n_interactions = mappings['n_interactions']

    def save(self, filepath: str, matrix: csr_matrix):
        """
        행렬 및 매핑 저장

        Args:
            filepath: 저장 경로 (확장자 제외)
            matrix: 저장할 희소 행렬
        """
        # 희소 행렬 저장
        save_npz(f"{filepath}_matrix.npz", matrix)

        # 매핑 저장
        with open(f"{filepath}_mappings.pkl", 'wb') as f:
            pickle.dump(self.get_mappings(), f)

        logger.info(f"저장 완료: {filepath}_matrix.npz, {filepath}_mappings.pkl")

    def load(self, filepath: str) -> csr_matrix:
        """
        행렬 및 매핑 로드

        Args:
            filepath: 저장 경로 (확장자 제외)

        Returns:
            로드된 희소 행렬
        """
        # 희소 행렬 로드
        matrix = load_npz(f"{filepath}_matrix.npz")

        # 매핑 로드
        with open(f"{filepath}_mappings.pkl", 'rb') as f:
            mappings = pickle.load(f)
        self.set_mappings(mappings)

        logger.info(f"로드 완료: {self.n_users:,}×{self.n_items:,} 행렬")

        return matrix


# ============================================================================
# 3. 피처 엔지니어링
# ============================================================================

class FeatureEngineer:
    """
    피처 엔지니어링 모듈

    Kaggle 최상위 전략:
    - 상호작용 가중치 적용 (전환율 역산)
    - 사용자 프로파일 생성
    - 상품 프로파일 생성
    - 시간 패턴 피처
    """

    def __init__(self, weights=None):
        """
        Args:
            weights: 상호작용 가중치 (None이면 기본값)
        """
        self.weights = weights or INTERACTION_WEIGHTS

    def compute_interaction_scores(
        self,
        df: pd.DataFrame,
        view_col: str = 'view_count',
        cart_col: str = 'cart_count',
        order_col: str = 'order_count',
        wishlist_col: str = 'wishlist_count',
        review_col: str = 'review_count'
    ) -> pd.Series:
        """
        상호작용 점수 계산 (가중 합산)

        Args:
            df: 상호작용 DataFrame
            *_col: 각 행동 유형 컬럼명

        Returns:
            점수 Series
        """
        score = pd.Series(0.0, index=df.index)

        if view_col in df.columns:
            score += self.weights.view * df[view_col]
        if cart_col in df.columns:
            score += self.weights.cart * df[cart_col]
        if order_col in df.columns:
            score += self.weights.order * df[order_col]
        if wishlist_col in df.columns:
            score += self.weights.wishlist * df[wishlist_col]
        if review_col in df.columns:
            score += self.weights.review * df[review_col]

        return score

    def compute_user_profiles(
        self,
        interactions_df: pd.DataFrame,
        products_df: pd.DataFrame,
        user_col: str = 'user_id',
        product_col: str = 'product_id',
        score_col: str = 'score'
    ) -> Dict[int, Dict]:
        """
        사용자 프로파일 생성

        Args:
            interactions_df: 상호작용 DataFrame
            products_df: 상품 DataFrame (aisle_id, department_id 포함)
            user_col: 사용자 ID 컬럼
            product_col: 상품 ID 컬럼
            score_col: 점수 컬럼

        Returns:
            사용자별 프로파일 딕셔너리
        """
        logger.info("사용자 프로파일 생성 중...")

        # 상품 정보 조인
        merged = interactions_df.merge(
            products_df[['product_id', 'aisle_id', 'department_id']],
            left_on=product_col,
            right_on='product_id',
            how='left'
        )

        profiles = {}

        for user_id, group in merged.groupby(user_col):
            # 선호 카테고리 (점수 기반)
            aisle_scores = group.groupby('aisle_id')[score_col].sum().to_dict()
            dept_scores = group.groupby('department_id')[score_col].sum().to_dict()

            # 총 상호작용
            total_interactions = len(group)
            total_score = group[score_col].sum()

            profiles[user_id] = {
                'aisle_preferences': aisle_scores,
                'department_preferences': dept_scores,
                'total_interactions': total_interactions,
                'total_score': total_score,
                'avg_score': total_score / total_interactions if total_interactions > 0 else 0,
            }

        logger.info(f"  {len(profiles):,}명 프로파일 생성 완료")

        return profiles

    def compute_item_profiles(
        self,
        interactions_df: pd.DataFrame,
        products_df: pd.DataFrame,
        product_col: str = 'product_id',
        score_col: str = 'score'
    ) -> Dict[int, Dict]:
        """
        상품 프로파일 생성

        Args:
            interactions_df: 상호작용 DataFrame
            products_df: 상품 DataFrame
            product_col: 상품 ID 컬럼
            score_col: 점수 컬럼

        Returns:
            상품별 프로파일 딕셔너리
        """
        logger.info("상품 프로파일 생성 중...")

        # 상품별 집계
        item_stats = interactions_df.groupby(product_col).agg({
            'user_id': 'nunique',  # 구매 사용자 수
            score_col: ['sum', 'mean', 'count'],  # 점수 통계
        }).reset_index()

        item_stats.columns = [
            'product_id', 'unique_users', 'total_score', 'avg_score', 'interaction_count'
        ]

        # 상품 정보 조인
        item_stats = item_stats.merge(
            products_df[['product_id', 'aisle_id', 'department_id', 'product_name']],
            on='product_id',
            how='left'
        )

        # 인기도 랭킹 (정규화)
        max_score = item_stats['total_score'].max()
        item_stats['popularity'] = item_stats['total_score'] / max_score if max_score > 0 else 0

        profiles = {}
        for _, row in item_stats.iterrows():
            profiles[row['product_id']] = {
                'aisle_id': row.get('aisle_id'),
                'department_id': row.get('department_id'),
                'product_name': row.get('product_name'),
                'unique_users': row['unique_users'],
                'total_score': row['total_score'],
                'avg_score': row['avg_score'],
                'interaction_count': row['interaction_count'],
                'popularity': row['popularity'],
            }

        logger.info(f"  {len(profiles):,}개 상품 프로파일 생성 완료")

        return profiles

    def compute_time_features(
        self,
        orders_df: pd.DataFrame,
        order_col: str = 'order_id',
        dow_col: str = 'order_dow',
        hour_col: str = 'order_hour_of_day'
    ) -> pd.DataFrame:
        """
        시간 패턴 피처 생성

        Args:
            orders_df: 주문 DataFrame
            dow_col: 요일 컬럼 (0=일요일, 6=토요일)
            hour_col: 시간 컬럼 (0-23)

        Returns:
            시간 피처가 추가된 DataFrame
        """
        df = orders_df.copy()

        # 시간대 분류
        def get_time_slot(hour: int) -> str:
            if 6 <= hour < 10:
                return 'morning'
            elif 10 <= hour < 14:
                return 'lunch'
            elif 14 <= hour < 18:
                return 'afternoon'
            elif 18 <= hour < 22:
                return 'dinner'
            else:
                return 'night'

        df['time_slot'] = df[hour_col].apply(get_time_slot)

        # 주말 여부
        df['is_weekend'] = df[dow_col].isin([0, 6]).astype(int)

        # 시간 인덱스 (168시간 = 7일 × 24시간)
        df['hour_index'] = df[dow_col] * 24 + df[hour_col]

        return df


# ============================================================================
# 테스트
# ============================================================================

def test_data_processor():
    """데이터 처리 모듈 테스트"""

    print("\n[데이터 처리 모듈 테스트]")

    # 1. 시뮬레이션 데이터 생성
    np.random.seed(42)
    n_users = 100
    n_items = 50
    n_interactions = 500

    user_ids = np.random.randint(1, n_users + 1, n_interactions).tolist()
    item_ids = np.random.randint(1, n_items + 1, n_interactions).tolist()
    values = np.random.randint(1, 10, n_interactions).astype(float).tolist()

    # 2. 행렬 빌더 테스트
    builder = InteractionMatrixBuilder()
    matrix = builder.build_matrix(user_ids, item_ids, values)

    print(f"  ✅ 행렬 생성: {matrix.shape}")
    assert matrix.shape == (n_users, n_items), "행렬 크기 오류"

    # 3. Confidence Weighting 테스트
    confidence = builder.apply_confidence_weighting(matrix, alpha=15.0)
    print(f"  ✅ Confidence Weighting 적용")
    assert confidence.data.min() >= 1.0, "Confidence는 1 이상"

    # 4. 매핑 저장/로드 테스트
    mappings = builder.get_mappings()
    assert len(mappings['user_id_to_idx']) == n_users, "사용자 매핑 오류"
    print(f"  ✅ 매핑 생성: {n_users}명 사용자, {n_items}개 상품")

    # 5. 피처 엔지니어링 테스트
    fe = FeatureEngineer()
    df = pd.DataFrame({
        'view_count': [5, 10, 2],
        'cart_count': [1, 0, 2],
        'order_count': [1, 0, 1],
    })
    scores = fe.compute_interaction_scores(df)
    expected = [5*0.1 + 1*2.0 + 1*5.0, 10*0.1, 2*0.1 + 2*2.0 + 1*5.0]
    assert abs(scores[0] - expected[0]) < 0.001, f"점수 오류: {scores[0]} != {expected[0]}"
    print(f"  ✅ 상호작용 점수 계산: {scores.tolist()}")

    print("\n✅ 모든 데이터 처리 테스트 통과!")


if __name__ == '__main__':
    test_data_processor()
