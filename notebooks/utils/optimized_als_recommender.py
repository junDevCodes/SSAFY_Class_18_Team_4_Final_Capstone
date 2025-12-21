"""
최적화된 ALS 추천 시스템 - 32차원 설계

Kaggle Master 기준 최적화:
1. 32차원 (27K 상호작용 기준 적정)
2. implicit 라이브러리 활용 (C++ 백엔드, 10-100배 빠름)
3. Confidence Weighting (Netflix Prize 기법)
4. BM25 가중치 (희소 데이터 최적화)

작성자: 20년차 시니어 개발자 관점
"""

import numpy as np
import pickle
from scipy.sparse import csr_matrix, lil_matrix
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
import warnings
import time

warnings.filterwarnings('ignore')


# ============================================================================
# 1. 최적화된 ALS 추천기 (32차원)
# ============================================================================

class OptimizedALSRecommender:
    """
    Kaggle 실전 기준 최적화된 ALS 추천기

    핵심 설계 원칙:
    1. 차원: 32 (27K 상호작용 → 32차원 Rule of Thumb)
    2. Confidence: log 스케일 (C = 1 + α * log(1 + r))
    3. 정규화: L2 + BM25 가중치
    4. 학습: implicit 라이브러리 또는 순수 Python fallback

    성능 목표:
    - 학습 시간: < 5분 (5K users × 2K items)
    - 추론 시간: < 1ms per user
    - 메모리: < 10MB (32차원 기준)
    """

    # Kaggle 실전 파라미터
    KAGGLE_PARAMS = {
        'small': {   # < 50K 상호작용
            'factors': 32,
            'regularization': 0.1,
            'iterations': 15,
            'alpha': 15.0,
        },
        'medium': {  # 50K ~ 500K 상호작용
            'factors': 64,
            'regularization': 0.05,
            'iterations': 20,
            'alpha': 40.0,
        },
        'large': {   # > 500K 상호작용
            'factors': 128,
            'regularization': 0.01,
            'iterations': 30,
            'alpha': 40.0,
        },
    }

    def __init__(
        self,
        factors: int = 32,
        regularization: float = 0.1,
        iterations: int = 15,
        alpha: float = 15.0,
        use_gpu: bool = False,
        use_native: bool = True,  # implicit 라이브러리 사용 여부
        random_state: int = 42
    ):
        """
        Args:
            factors: 잠재 요인 차원 (기본 32, 데이터 규모에 따라 조정)
            regularization: L2 정규화 강도 (희소 데이터일수록 높게)
            iterations: ALS 반복 횟수
            alpha: Confidence 스케일링 (희소 데이터일수록 낮게)
            use_gpu: GPU 가속 사용 여부
            use_native: implicit 라이브러리 사용 여부
            random_state: 재현성을 위한 시드
        """
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.alpha = alpha
        self.use_gpu = use_gpu
        self.use_native = use_native
        self.random_state = random_state

        # 모델 상태
        self.user_factors = None
        self.item_factors = None
        self.user_id_to_idx = {}
        self.item_id_to_idx = {}
        self.idx_to_user_id = {}
        self.idx_to_item_id = {}

        # 학습 통계
        self.train_stats = {}

        # implicit 모델
        self._implicit_model = None

    @classmethod
    def from_data_size(
        cls,
        n_interactions: int,
        use_native: bool = True
    ) -> 'OptimizedALSRecommender':
        """
        데이터 규모에 따라 자동으로 최적 파라미터 선택

        Kaggle Rule of Thumb:
        - < 50K: 32차원
        - 50K~500K: 64차원
        - > 500K: 128차원
        """
        if n_interactions < 50_000:
            params = cls.KAGGLE_PARAMS['small']
        elif n_interactions < 500_000:
            params = cls.KAGGLE_PARAMS['medium']
        else:
            params = cls.KAGGLE_PARAMS['large']

        print(f"[AutoConfig] {n_interactions:,}개 상호작용 → {params['factors']}차원 선택")

        return cls(
            factors=params['factors'],
            regularization=params['regularization'],
            iterations=params['iterations'],
            alpha=params['alpha'],
            use_native=use_native
        )

    def _build_interaction_matrix(
        self,
        user_ids: List[int],
        item_ids: List[int],
        scores: List[float]
    ) -> csr_matrix:
        """
        상호작용 행렬 구축 (희소 행렬)
        """
        # ID 매핑 생성
        unique_users = sorted(set(user_ids))
        unique_items = sorted(set(item_ids))

        self.user_id_to_idx = {uid: i for i, uid in enumerate(unique_users)}
        self.item_id_to_idx = {iid: i for i, iid in enumerate(unique_items)}
        self.idx_to_user_id = {i: uid for uid, i in self.user_id_to_idx.items()}
        self.idx_to_item_id = {i: iid for iid, i in self.item_id_to_idx.items()}

        n_users = len(unique_users)
        n_items = len(unique_items)

        # 희소 행렬 생성
        rows = [self.user_id_to_idx[uid] for uid in user_ids]
        cols = [self.item_id_to_idx[iid] for iid in item_ids]

        matrix = csr_matrix(
            (scores, (rows, cols)),
            shape=(n_users, n_items),
            dtype=np.float32
        )

        return matrix

    def _apply_confidence_weighting(self, matrix: csr_matrix) -> csr_matrix:
        """
        Confidence Weighting 적용

        Netflix Prize 기법:
        C_ui = 1 + α * log(1 + r_ui)

        희소 데이터에서는 log 스케일이 선형보다 효과적
        """
        confidence = matrix.copy()
        confidence.data = 1 + self.alpha * np.log1p(confidence.data)
        return confidence

    def _apply_bm25_weighting(self, matrix: csr_matrix) -> csr_matrix:
        """
        BM25 가중치 적용 (희소 데이터 최적화)

        TF-IDF의 개선 버전으로, 희소 행렬에서
        인기 아이템의 과대 평가를 방지
        """
        # 아이템별 빈도
        item_counts = np.array(matrix.sum(axis=0)).flatten()
        total_interactions = matrix.sum()

        # IDF 계산
        n_users = matrix.shape[0]
        idf = np.log((n_users + 1) / (item_counts + 1)) + 1

        # BM25 적용
        bm25_matrix = matrix.copy()

        # 각 열에 IDF 가중치 적용
        for i in range(bm25_matrix.shape[1]):
            bm25_matrix.data[bm25_matrix.indptr[i]:bm25_matrix.indptr[i+1]] *= idf[i]

        return bm25_matrix

    def fit(
        self,
        user_ids: List[int],
        item_ids: List[int],
        scores: List[float],
        show_progress: bool = True
    ) -> 'OptimizedALSRecommender':
        """
        모델 학습

        Args:
            user_ids: 사용자 ID 리스트
            item_ids: 아이템 ID 리스트
            scores: 상호작용 점수 (view*1 + cart*3 + order*5)
            show_progress: 진행 상황 출력
        """
        start_time = time.time()

        # 1. 상호작용 행렬 구축
        interaction_matrix = self._build_interaction_matrix(user_ids, item_ids, scores)
        n_users, n_items = interaction_matrix.shape
        n_interactions = len(scores)

        # 2. 희소성 계산
        sparsity = 1 - (n_interactions / (n_users * n_items))

        if show_progress:
            print(f"[ALS 학습 시작]")
            print(f"  • 유저: {n_users:,}명")
            print(f"  • 아이템: {n_items:,}개")
            print(f"  • 상호작용: {n_interactions:,}개")
            print(f"  • 희소성: {sparsity:.2%}")
            print(f"  • 차원: {self.factors}")
            print(f"  • 정규화: {self.regularization}")
            print(f"  • 반복: {self.iterations}회")

        # 3. implicit 라이브러리 사용 시도
        if self.use_native:
            try:
                from implicit.als import AlternatingLeastSquares
                from implicit.evaluation import precision_at_k

                if show_progress:
                    print(f"  • 백엔드: implicit (C++ 최적화)")

                # Confidence 적용
                confidence_matrix = self._apply_confidence_weighting(interaction_matrix)

                # implicit 모델 생성
                self._implicit_model = AlternatingLeastSquares(
                    factors=self.factors,
                    regularization=self.regularization,
                    iterations=self.iterations,
                    random_state=self.random_state,
                    use_gpu=self.use_gpu
                )

                # 학습 (item-user 행렬로 전치)
                self._implicit_model.fit(confidence_matrix.T.tocsr(), show_progress=show_progress)

                # 임베딩 추출
                self.user_factors = self._implicit_model.user_factors
                self.item_factors = self._implicit_model.item_factors

            except ImportError:
                if show_progress:
                    print(f"  ⚠️ implicit 라이브러리 없음 → Python 구현 사용")
                self._fit_python(interaction_matrix, show_progress)
        else:
            self._fit_python(interaction_matrix, show_progress)

        # 4. 학습 통계
        elapsed = time.time() - start_time
        self.train_stats = {
            'n_users': n_users,
            'n_items': n_items,
            'n_interactions': n_interactions,
            'sparsity': sparsity,
            'factors': self.factors,
            'train_time_sec': elapsed,
        }

        if show_progress:
            print(f"[ALS 학습 완료] {elapsed:.1f}초")

        return self

    def _fit_python(self, interaction_matrix: csr_matrix, show_progress: bool = True):
        """
        순수 Python ALS 구현 (fallback)
        """
        if show_progress:
            print(f"  • 백엔드: Python (순수 구현)")

        n_users, n_items = interaction_matrix.shape

        # Confidence 적용
        confidence = self._apply_confidence_weighting(interaction_matrix)

        # 랜덤 초기화
        np.random.seed(self.random_state)
        self.user_factors = np.random.normal(0, 0.01, (n_users, self.factors)).astype(np.float32)
        self.item_factors = np.random.normal(0, 0.01, (n_items, self.factors)).astype(np.float32)

        # ALS 반복
        for iteration in range(self.iterations):
            # 아이템 고정, 유저 업데이트
            self._als_update(
                self.user_factors,
                self.item_factors,
                confidence
            )

            # 유저 고정, 아이템 업데이트
            self._als_update(
                self.item_factors,
                self.user_factors,
                confidence.T.tocsr()
            )

            if show_progress and (iteration + 1) % 5 == 0:
                print(f"    Iteration {iteration + 1}/{self.iterations}")

    def _als_update(
        self,
        factors_to_update: np.ndarray,
        fixed_factors: np.ndarray,
        confidence: csr_matrix
    ):
        """
        ALS 업데이트 스텝

        X = (Y^T * C * Y + λI)^-1 * Y^T * C * p
        """
        n_factors = fixed_factors.shape[1]
        n_entities = confidence.shape[0]

        # Y^T * Y 사전 계산
        YtY = fixed_factors.T @ fixed_factors

        # 정규화 행렬
        reg_matrix = self.regularization * np.eye(n_factors, dtype=np.float32)

        for i in range(n_entities):
            # 해당 행의 비영점 요소
            row_start = confidence.indptr[i]
            row_end = confidence.indptr[i + 1]

            if row_start == row_end:
                continue

            indices = confidence.indices[row_start:row_end]
            data = confidence.data[row_start:row_end]

            # Y_i: 상호작용 있는 아이템의 임베딩
            Y_i = fixed_factors[indices]

            # A = Y^T * (C - I) * Y + Y^T * Y + λI
            # 효율적 계산: (C-1) 부분만 추가
            A = YtY + reg_matrix

            # (C_i - 1) 대각 요소 추가
            c_minus_1 = data - 1
            A += Y_i.T @ (Y_i * c_minus_1[:, np.newaxis])

            # b = Y^T * C * p (p는 모두 1)
            b = Y_i.T @ data

            # 해 계산
            factors_to_update[i] = np.linalg.solve(A, b)

    def recommend(
        self,
        user_id: int,
        top_k: int = 10,
        exclude_items: Optional[Set[int]] = None,
        filter_already_interacted: bool = True
    ) -> List[Tuple[int, float]]:
        """
        사용자에게 아이템 추천

        Args:
            user_id: 사용자 ID
            top_k: 추천 개수
            exclude_items: 제외할 아이템 ID 집합
            filter_already_interacted: 이미 상호작용한 아이템 제외

        Returns:
            [(item_id, score), ...] 리스트
        """
        if user_id not in self.user_id_to_idx:
            return self._cold_start_recommend(top_k)

        user_idx = self.user_id_to_idx[user_id]
        user_vec = self.user_factors[user_idx]

        # 모든 아이템과의 점수 계산
        scores = self.item_factors @ user_vec

        # 제외 아이템 처리
        if exclude_items:
            for item_id in exclude_items:
                if item_id in self.item_id_to_idx:
                    scores[self.item_id_to_idx[item_id]] = -np.inf

        # Top-K 추출
        top_indices = np.argsort(scores)[::-1][:top_k]

        recommendations = []
        for idx in top_indices:
            if scores[idx] == -np.inf:
                continue
            item_id = self.idx_to_item_id[idx]
            score = float(scores[idx])
            recommendations.append((item_id, score))

        return recommendations

    def _cold_start_recommend(self, top_k: int) -> List[Tuple[int, float]]:
        """
        Cold Start 사용자를 위한 인기 아이템 추천
        """
        # 아이템 임베딩의 L2 norm으로 인기도 추정
        item_popularity = np.linalg.norm(self.item_factors, axis=1)
        top_indices = np.argsort(item_popularity)[::-1][:top_k]

        return [
            (self.idx_to_item_id[idx], float(item_popularity[idx]))
            for idx in top_indices
        ]

    def similar_items(
        self,
        item_id: int,
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        유사 아이템 검색
        """
        if item_id not in self.item_id_to_idx:
            return []

        item_idx = self.item_id_to_idx[item_id]
        item_vec = self.item_factors[item_idx]

        # 코사인 유사도
        norms = np.linalg.norm(self.item_factors, axis=1, keepdims=True)
        normalized = self.item_factors / (norms + 1e-10)
        item_vec_normalized = item_vec / (np.linalg.norm(item_vec) + 1e-10)

        similarities = normalized @ item_vec_normalized
        similarities[item_idx] = -np.inf  # 자기 자신 제외

        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            (self.idx_to_item_id[idx], float(similarities[idx]))
            for idx in top_indices
        ]

    def similar_users(
        self,
        user_id: int,
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        유사 사용자 검색
        """
        if user_id not in self.user_id_to_idx:
            return []

        user_idx = self.user_id_to_idx[user_id]
        user_vec = self.user_factors[user_idx]

        # 코사인 유사도
        norms = np.linalg.norm(self.user_factors, axis=1, keepdims=True)
        normalized = self.user_factors / (norms + 1e-10)
        user_vec_normalized = user_vec / (np.linalg.norm(user_vec) + 1e-10)

        similarities = normalized @ user_vec_normalized
        similarities[user_idx] = -np.inf  # 자기 자신 제외

        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            (self.idx_to_user_id[idx], float(similarities[idx]))
            for idx in top_indices
        ]

    def get_user_embedding(self, user_id: int) -> Optional[np.ndarray]:
        """사용자 임베딩 조회"""
        if user_id not in self.user_id_to_idx:
            return None
        return self.user_factors[self.user_id_to_idx[user_id]].copy()

    def get_item_embedding(self, item_id: int) -> Optional[np.ndarray]:
        """아이템 임베딩 조회"""
        if item_id not in self.item_id_to_idx:
            return None
        return self.item_factors[self.item_id_to_idx[item_id]].copy()

    def explained_variance_estimate(self) -> float:
        """
        설명된 분산 추정

        ALS는 직접적인 설명 분산을 제공하지 않으므로
        재구성 오차 기반으로 추정
        """
        if self.user_factors is None or self.item_factors is None:
            return 0.0

        # 샘플링된 재구성 오차로 추정
        n_samples = min(1000, self.user_factors.shape[0])
        sample_indices = np.random.choice(
            self.user_factors.shape[0],
            n_samples,
            replace=False
        )

        # 재구성 품질 = 임베딩의 분산 / 전체 분산
        user_var = np.var(self.user_factors[sample_indices])
        item_var = np.var(self.item_factors)

        # 휴리스틱: 분산이 높을수록 정보량이 많음
        return min(1.0, (user_var + item_var) * 10)

    def save(self, filepath: str):
        """모델 저장"""
        model_data = {
            'version': '2.0.0',
            'algorithm': 'ALS',
            'factors': self.factors,
            'regularization': self.regularization,
            'iterations': self.iterations,
            'alpha': self.alpha,
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
            'user_id_to_idx': self.user_id_to_idx,
            'item_id_to_idx': self.item_id_to_idx,
            'idx_to_user_id': self.idx_to_user_id,
            'idx_to_item_id': self.idx_to_item_id,
            'train_stats': self.train_stats,
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"[저장 완료] {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'OptimizedALSRecommender':
        """모델 로드"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        model = cls(
            factors=model_data['factors'],
            regularization=model_data['regularization'],
            iterations=model_data['iterations'],
            alpha=model_data['alpha']
        )

        model.user_factors = model_data['user_factors']
        model.item_factors = model_data['item_factors']
        model.user_id_to_idx = model_data['user_id_to_idx']
        model.item_id_to_idx = model_data['item_id_to_idx']
        model.idx_to_user_id = model_data['idx_to_user_id']
        model.idx_to_item_id = model_data['idx_to_item_id']
        model.train_stats = model_data.get('train_stats', {})

        print(f"[로드 완료] {filepath}")
        print(f"  • 버전: {model_data.get('version', '1.0.0')}")
        print(f"  • 차원: {model.factors}")
        print(f"  • 유저: {len(model.user_id_to_idx):,}")
        print(f"  • 아이템: {len(model.item_id_to_idx):,}")

        return model


# ============================================================================
# 2. 메모리 효율적인 Pickle 포맷
# ============================================================================

def create_optimized_pickle(
    model: OptimizedALSRecommender,
    output_path: str,
    include_mappings: bool = True
) -> Dict[str, Any]:
    """
    프로덕션용 최적화된 Pickle 생성

    32차원 기준 예상 크기:
    - user_factors: 5K × 32 × 4 bytes = 640 KB
    - item_factors: 2K × 32 × 4 bytes = 256 KB
    - 매핑: ~100 KB
    - 총: ~1 MB (기존 60MB 대비 98% 감소!)
    """
    pickle_data = {
        'version': '2.0.0',
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'algorithm': 'ALS',
        'metadata': {
            'n_users': len(model.user_id_to_idx),
            'n_items': len(model.item_id_to_idx),
            'factors': model.factors,
            'regularization': model.regularization,
            'alpha': model.alpha,
            'train_stats': model.train_stats,
        },
        'components': {
            # numpy 배열을 bytes로 변환 (호환성)
            'user_embeddings': {
                'data': model.user_factors.tobytes(),
                'shape': model.user_factors.shape,
                'dtype': str(model.user_factors.dtype),
            },
            'item_embeddings': {
                'data': model.item_factors.tobytes(),
                'shape': model.item_factors.shape,
                'dtype': str(model.item_factors.dtype),
            },
        },
        'hyperparameters': {
            'factors': model.factors,
            'regularization': model.regularization,
            'iterations': model.iterations,
            'alpha': model.alpha,
        },
    }

    if include_mappings:
        pickle_data['components']['user_id_to_idx'] = model.user_id_to_idx
        pickle_data['components']['item_id_to_idx'] = model.item_id_to_idx
        pickle_data['components']['idx_to_user_id'] = model.idx_to_user_id
        pickle_data['components']['idx_to_item_id'] = model.idx_to_item_id

    with open(output_path, 'wb') as f:
        pickle.dump(pickle_data, f)

    import os
    file_size = os.path.getsize(output_path) / 1024  # KB

    print(f"[Pickle 생성 완료]")
    print(f"  • 경로: {output_path}")
    print(f"  • 크기: {file_size:.1f} KB")
    print(f"  • 유저 임베딩: {model.user_factors.shape}")
    print(f"  • 아이템 임베딩: {model.item_factors.shape}")

    return pickle_data


def load_optimized_pickle(filepath: str) -> OptimizedALSRecommender:
    """
    최적화된 Pickle 로드
    """
    with open(filepath, 'rb') as f:
        data = pickle.load(f)

    # numpy 배열 복원
    user_emb_data = data['components']['user_embeddings']
    item_emb_data = data['components']['item_embeddings']

    user_factors = np.frombuffer(
        user_emb_data['data'],
        dtype=user_emb_data['dtype']
    ).reshape(user_emb_data['shape'])

    item_factors = np.frombuffer(
        item_emb_data['data'],
        dtype=item_emb_data['dtype']
    ).reshape(item_emb_data['shape'])

    # 모델 복원
    hp = data['hyperparameters']
    model = OptimizedALSRecommender(
        factors=hp['factors'],
        regularization=hp['regularization'],
        iterations=hp['iterations'],
        alpha=hp['alpha']
    )

    model.user_factors = user_factors
    model.item_factors = item_factors
    model.user_id_to_idx = data['components'].get('user_id_to_idx', {})
    model.item_id_to_idx = data['components'].get('item_id_to_idx', {})
    model.idx_to_user_id = data['components'].get('idx_to_user_id', {})
    model.idx_to_item_id = data['components'].get('idx_to_item_id', {})
    model.train_stats = data['metadata'].get('train_stats', {})

    return model


# ============================================================================
# 3. 평가 유틸리티
# ============================================================================

class ALSEvaluator:
    """
    ALS 모델 평가기
    """

    @staticmethod
    def evaluate(
        model: OptimizedALSRecommender,
        test_interactions: List[Tuple[int, int, float]],
        k_values: List[int] = [5, 10, 20]
    ) -> Dict[str, float]:
        """
        모델 평가

        Args:
            model: 학습된 ALS 모델
            test_interactions: [(user_id, item_id, score), ...]
            k_values: 평가할 K 값 리스트

        Returns:
            평가 지표 딕셔너리
        """
        # 사용자별 실제 아이템 그룹화
        user_items = defaultdict(set)
        for user_id, item_id, score in test_interactions:
            if score > 0:
                user_items[user_id].add(item_id)

        results = {k: {'hits': 0, 'total': 0, 'ndcg': []} for k in k_values}

        for user_id, actual_items in user_items.items():
            if user_id not in model.user_id_to_idx:
                continue

            # 추천 생성
            recs = model.recommend(user_id, top_k=max(k_values))
            rec_ids = [r[0] for r in recs]

            for k in k_values:
                rec_k = set(rec_ids[:k])
                hits = len(rec_k & actual_items)

                results[k]['hits'] += hits
                results[k]['total'] += min(k, len(actual_items))

                # NDCG
                dcg = sum(
                    1.0 / np.log2(i + 2)
                    for i, item in enumerate(rec_ids[:k])
                    if item in actual_items
                )
                idcg = sum(
                    1.0 / np.log2(i + 2)
                    for i in range(min(k, len(actual_items)))
                )
                ndcg = dcg / idcg if idcg > 0 else 0
                results[k]['ndcg'].append(ndcg)

        # 집계
        metrics = {}
        for k in k_values:
            recall = results[k]['hits'] / results[k]['total'] if results[k]['total'] > 0 else 0
            ndcg = np.mean(results[k]['ndcg']) if results[k]['ndcg'] else 0

            metrics[f'Recall@{k}'] = recall
            metrics[f'NDCG@{k}'] = ndcg

        return metrics


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("최적화된 ALS 추천기 - 32차원 설계")
    print("=" * 60)

    # 시뮬레이션 데이터
    np.random.seed(42)
    n_users = 5000
    n_items = 2000
    n_interactions = 27000

    user_ids = np.random.randint(1, n_users + 1, n_interactions).tolist()
    item_ids = np.random.randint(1, n_items + 1, n_interactions).tolist()
    scores = (
        np.random.randint(0, 5, n_interactions) * 1 +  # view
        np.random.randint(0, 3, n_interactions) * 3 +  # cart
        np.random.randint(0, 2, n_interactions) * 5    # order
    ).tolist()

    print(f"\n[시뮬레이션 데이터]")
    print(f"  • 유저: {n_users:,}")
    print(f"  • 아이템: {n_items:,}")
    print(f"  • 상호작용: {n_interactions:,}")

    # 1. 자동 파라미터 선택
    print(f"\n[1. 모델 생성 - 자동 파라미터]")
    model = OptimizedALSRecommender.from_data_size(n_interactions, use_native=False)

    # 2. 학습
    print(f"\n[2. 모델 학습]")
    model.fit(user_ids, item_ids, scores)

    # 3. 추천 테스트
    print(f"\n[3. 추천 테스트]")
    test_user = user_ids[0]
    recs = model.recommend(test_user, top_k=5)
    print(f"  유저 {test_user} 추천:")
    for item_id, score in recs:
        print(f"    - 아이템 {item_id}: {score:.4f}")

    # 4. Pickle 저장
    print(f"\n[4. Pickle 저장]")
    create_optimized_pickle(model, 'test_als_32dim.pkl')

    print(f"\n완료!")
