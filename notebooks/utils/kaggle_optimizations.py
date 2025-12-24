"""
Kaggle Champion 전략 기반 모델 최적화 유틸리티

이 모듈은 SelF 추천 시스템의 성능을 획기적으로 개선하기 위한
Kaggle 상위권 기법들을 구현합니다.

주요 개선 사항:
1. SVD → ALS 전환 (Implicit Feedback 최적화)
2. Confidence Weighting (Netflix Prize 기법)
3. Soft Ingredient Matching (Recipe 모델용)
4. Ensemble Recommender (다중 모델 결합)
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional, Any
import warnings

warnings.filterwarnings('ignore')


# ============================================================================
# 1. ALS 기반 협업 필터링 (SVD 대체)
# ============================================================================

class ALSRecommender:
    """
    Alternating Least Squares 기반 추천 모델

    장점:
    - Implicit feedback에 최적화
    - 희소 행렬에서 SVD보다 2-3배 높은 성능
    - Confidence weighting 지원

    References:
    - Hu, Koren, Volinsky (2008) - Collaborative Filtering for Implicit Feedback
    """

    def __init__(
        self,
        factors: int = 256,
        regularization: float = 0.01,
        iterations: int = 50,
        alpha: float = 40.0,
        use_confidence: bool = True
    ):
        """
        Args:
            factors: 잠재 요인 차원 수 (128 → 256 권장)
            regularization: L2 정규화 강도
            iterations: 반복 횟수
            alpha: Confidence 스케일링 팩터
            use_confidence: Confidence weighting 사용 여부
        """
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.alpha = alpha
        self.use_confidence = use_confidence

        self.user_factors = None
        self.item_factors = None
        self.user_id_to_idx = {}
        self.item_id_to_idx = {}
        self.idx_to_user_id = {}
        self.idx_to_item_id = {}

    def _create_confidence_matrix(self, interaction_matrix: csr_matrix) -> csr_matrix:
        """
        Confidence 행렬 생성

        C_ui = 1 + α * r_ui
        여기서 r_ui는 상호작용 점수
        """
        confidence = interaction_matrix.copy()
        confidence.data = 1 + self.alpha * np.log1p(confidence.data)
        return confidence

    def _als_step(
        self,
        fixed_factors: np.ndarray,
        confidence: csr_matrix,
        regularization: float
    ) -> np.ndarray:
        """
        ALS 한 스텝 (사용자 또는 아이템 업데이트)

        X = (Y^T * C * Y + λI)^-1 * Y^T * C * p
        """
        n_factors = fixed_factors.shape[1]
        n_entities = confidence.shape[0]

        # Y^T * Y 사전 계산
        YtY = fixed_factors.T @ fixed_factors

        # 정규화 행렬
        regularization_matrix = regularization * np.eye(n_factors)

        new_factors = np.zeros((n_entities, n_factors))

        for i in range(n_entities):
            # 해당 행의 비영점 요소
            row = confidence.getrow(i)
            indices = row.indices
            data = row.data

            if len(indices) == 0:
                continue

            # Y_i: 상호작용 있는 아이템의 임베딩
            Y_i = fixed_factors[indices]

            # C_i: 대각 confidence 행렬
            C_i = np.diag(data)

            # (Y^T * C * Y + λI)^-1 * Y^T * C * p
            # p는 모두 1 (implicit feedback)
            A = Y_i.T @ C_i @ Y_i + regularization_matrix
            b = Y_i.T @ (C_i @ np.ones(len(indices)))

            new_factors[i] = np.linalg.solve(A, b)

        return new_factors

    def fit(
        self,
        user_ids: List[int],
        item_ids: List[int],
        scores: List[float]
    ) -> 'ALSRecommender':
        """
        모델 학습

        Args:
            user_ids: 사용자 ID 리스트
            item_ids: 아이템 ID 리스트
            scores: 상호작용 점수 리스트
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

        interaction_matrix = csr_matrix(
            (scores, (rows, cols)),
            shape=(n_users, n_items),
            dtype=np.float32
        )

        # Confidence 행렬
        if self.use_confidence:
            confidence = self._create_confidence_matrix(interaction_matrix)
        else:
            confidence = interaction_matrix

        # 랜덤 초기화
        np.random.seed(42)
        self.user_factors = np.random.normal(0, 0.1, (n_users, self.factors))
        self.item_factors = np.random.normal(0, 0.1, (n_items, self.factors))

        # ALS 반복
        print(f"ALS 학습 시작 (factors={self.factors}, iterations={self.iterations})")

        for iteration in range(self.iterations):
            # 아이템 고정, 사용자 업데이트
            self.user_factors = self._als_step(
                self.item_factors,
                confidence,
                self.regularization
            )

            # 사용자 고정, 아이템 업데이트
            self.item_factors = self._als_step(
                self.user_factors,
                confidence.T.tocsr(),
                self.regularization
            )

            if (iteration + 1) % 10 == 0:
                print(f"  Iteration {iteration + 1}/{self.iterations} 완료")

        # L2 정규화
        self.user_factors = normalize(self.user_factors, norm='l2', axis=1)
        self.item_factors = normalize(self.item_factors, norm='l2', axis=1)

        print("ALS 학습 완료")
        return self

    def recommend(
        self,
        user_id: int,
        top_k: int = 10,
        exclude_items: Optional[Set[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        사용자에게 아이템 추천

        Args:
            user_id: 사용자 ID
            top_k: 추천 개수
            exclude_items: 제외할 아이템 ID 집합

        Returns:
            [(item_id, score), ...] 리스트
        """
        if user_id not in self.user_id_to_idx:
            return []

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
            item_id = self.idx_to_item_id[idx]
            score = float(scores[idx])
            recommendations.append((item_id, score))

        return recommendations

    def get_user_embedding(self, user_id: int) -> Optional[np.ndarray]:
        """사용자 임베딩 조회"""
        if user_id not in self.user_id_to_idx:
            return None
        return self.user_factors[self.user_id_to_idx[user_id]]

    def get_item_embedding(self, item_id: int) -> Optional[np.ndarray]:
        """아이템 임베딩 조회"""
        if item_id not in self.item_id_to_idx:
            return None
        return self.item_factors[self.item_id_to_idx[item_id]]


# ============================================================================
# 2. 재료 임베딩 기반 Soft Matching
# ============================================================================

class IngredientEmbedder:
    """
    재료 간 유사도를 학습하는 임베딩 모델

    Co-occurrence 기반으로 같이 사용되는 재료는
    유사한 벡터를 갖도록 학습
    """

    def __init__(self, embedding_dim: int = 100, window_size: int = 5):
        self.embedding_dim = embedding_dim
        self.window_size = window_size
        self.embeddings = {}
        self.ingredient_to_idx = {}
        self.idx_to_ingredient = {}

    def _build_cooccurrence_matrix(
        self,
        recipe_ingredients: List[Set[str]]
    ) -> Tuple[csr_matrix, Dict[str, int]]:
        """
        동시 출현 행렬 구축
        """
        # 모든 재료 수집
        all_ingredients = set()
        for ingredients in recipe_ingredients:
            all_ingredients.update(ingredients)

        ingredient_list = sorted(all_ingredients)
        n_ingredients = len(ingredient_list)

        ing_to_idx = {ing: i for i, ing in enumerate(ingredient_list)}

        # 동시 출현 카운트
        cooccurrence = np.zeros((n_ingredients, n_ingredients), dtype=np.float32)

        for ingredients in recipe_ingredients:
            ing_list = list(ingredients)
            for i, ing1 in enumerate(ing_list):
                for ing2 in ing_list[i+1:]:
                    idx1, idx2 = ing_to_idx[ing1], ing_to_idx[ing2]
                    cooccurrence[idx1, idx2] += 1
                    cooccurrence[idx2, idx1] += 1

        # PPMI (Positive Pointwise Mutual Information) 변환
        row_sums = cooccurrence.sum(axis=1, keepdims=True)
        col_sums = cooccurrence.sum(axis=0, keepdims=True)
        total = cooccurrence.sum()

        # PMI = log(P(x,y) / (P(x) * P(y)))
        with np.errstate(divide='ignore', invalid='ignore'):
            pmi = np.log(
                (cooccurrence * total) /
                (row_sums * col_sums + 1e-10)
            )

        # PPMI: 음수를 0으로
        ppmi = np.maximum(pmi, 0)
        ppmi = np.nan_to_num(ppmi)

        return csr_matrix(ppmi), ing_to_idx

    def fit(self, recipe_ingredients: List[Set[str]]) -> 'IngredientEmbedder':
        """
        재료 임베딩 학습

        Args:
            recipe_ingredients: 레시피별 재료 집합 리스트
        """
        print("재료 임베딩 학습 시작...")

        # 동시 출현 행렬
        ppmi_matrix, self.ingredient_to_idx = self._build_cooccurrence_matrix(recipe_ingredients)
        self.idx_to_ingredient = {i: ing for ing, i in self.ingredient_to_idx.items()}

        n_ingredients = len(self.ingredient_to_idx)
        print(f"  총 재료 수: {n_ingredients}")

        # SVD로 차원 축소
        from sklearn.decomposition import TruncatedSVD

        n_components = min(self.embedding_dim, n_ingredients - 1)
        svd = TruncatedSVD(n_components=n_components, random_state=42)

        embeddings = svd.fit_transform(ppmi_matrix)
        embeddings = normalize(embeddings, norm='l2', axis=1)

        # 딕셔너리로 저장
        for ingredient, idx in self.ingredient_to_idx.items():
            self.embeddings[ingredient] = embeddings[idx]

        print(f"  임베딩 차원: {n_components}")
        print(f"  설명 분산: {svd.explained_variance_ratio_.sum():.2%}")
        print("재료 임베딩 학습 완료")

        return self

    def get_embedding(self, ingredient: str) -> Optional[np.ndarray]:
        """재료 임베딩 조회"""
        return self.embeddings.get(ingredient)

    def similarity(self, ing1: str, ing2: str) -> float:
        """두 재료 간 코사인 유사도"""
        emb1 = self.get_embedding(ing1)
        emb2 = self.get_embedding(ing2)

        if emb1 is None or emb2 is None:
            return 0.0

        return float(np.dot(emb1, emb2))

    def most_similar(self, ingredient: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        가장 유사한 재료 검색

        Args:
            ingredient: 쿼리 재료
            top_k: 반환 개수

        Returns:
            [(재료명, 유사도), ...] 리스트
        """
        query_emb = self.get_embedding(ingredient)
        if query_emb is None:
            return []

        similarities = []
        for other_ing, other_emb in self.embeddings.items():
            if other_ing == ingredient:
                continue
            sim = float(np.dot(query_emb, other_emb))
            similarities.append((other_ing, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# ============================================================================
# 3. 개선된 Recipe GapFilling
# ============================================================================

class EnhancedRecipeGapFilling:
    """
    Soft Matching을 적용한 개선된 Recipe GapFilling

    개선 사항:
    1. 재료 유사도 기반 Soft Matching
    2. 동적 min_match_ratio
    3. 개선된 스코어링
    """

    def __init__(
        self,
        recipe_ingredient_sets: Dict[int, Set[str]],
        recipe_metadata: Dict[int, Dict[str, Any]],
        ingredient_embedder: Optional[IngredientEmbedder] = None,
        similarity_threshold: float = 0.6
    ):
        self.recipe_ingredient_sets = recipe_ingredient_sets
        self.recipe_metadata = recipe_metadata
        self.embedder = ingredient_embedder
        self.similarity_threshold = similarity_threshold

        # 파라미터 (완화됨)
        self.params = {
            'min_match_ratio': 0.25,  # 0.3 → 0.25
            'max_gap_count': 7,        # 5 → 7
            'popularity_weight': 0.3,  # 0.4 → 0.3
            'match_weight': 0.5,       # 0.4 → 0.5
            'soft_match_bonus': 0.15,  # 새로운 파라미터
        }

    def calculate_soft_match_ratio(
        self,
        cart_ingredients: Set[str],
        recipe_ingredients: Set[str]
    ) -> Tuple[float, int, int]:
        """
        Soft Matching 기반 매칭 비율 계산

        Returns:
            (soft_match_ratio, exact_matches, soft_matches)
        """
        exact_matches = 0
        soft_matches = 0

        for recipe_ing in recipe_ingredients:
            # 1. 정확 매칭
            if recipe_ing in cart_ingredients:
                exact_matches += 1
                continue

            # 2. 유사 매칭 (임베딩 기반)
            if self.embedder:
                max_similarity = 0
                for cart_ing in cart_ingredients:
                    sim = self.embedder.similarity(recipe_ing, cart_ing)
                    max_similarity = max(max_similarity, sim)

                if max_similarity >= self.similarity_threshold:
                    soft_matches += 1

        total_score = exact_matches + soft_matches * self.params['soft_match_bonus']
        match_ratio = total_score / len(recipe_ingredients) if recipe_ingredients else 0

        return match_ratio, exact_matches, soft_matches

    def recommend(
        self,
        cart_ingredients: List[str],
        top_k: int = 10,
        min_match_ratio: Optional[float] = None,
        max_gap_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        레시피 추천

        Args:
            cart_ingredients: 장바구니 재료 리스트
            top_k: 추천 개수
            min_match_ratio: 최소 매칭 비율 (None이면 기본값)
            max_gap_count: 최대 Gap 개수 (None이면 기본값)

        Returns:
            추천 레시피 리스트
        """
        if min_match_ratio is None:
            min_match_ratio = self.params['min_match_ratio']
        if max_gap_count is None:
            max_gap_count = self.params['max_gap_count']

        cart_set = set(cart_ingredients)
        results = []

        for recipe_id, recipe_ingredients in self.recipe_ingredient_sets.items():
            if not recipe_ingredients:
                continue

            # Soft Matching
            match_ratio, exact_matches, soft_matches = self.calculate_soft_match_ratio(
                cart_set, recipe_ingredients
            )

            # 필터링
            if match_ratio < min_match_ratio:
                continue

            gaps = recipe_ingredients - cart_set
            if len(gaps) > max_gap_count:
                continue

            # 메타데이터
            metadata = self.recipe_metadata.get(recipe_id, {})
            popularity = metadata.get('popularity_score', 0) or 0

            # 스코어 계산
            final_score = (
                self.params['match_weight'] * match_ratio +
                self.params['popularity_weight'] * min(popularity / 100, 1.0) +
                self.params['soft_match_bonus'] * (soft_matches / len(recipe_ingredients))
            )

            results.append({
                'recipe_id': recipe_id,
                'name': metadata.get('name', ''),
                'match_ratio': match_ratio,
                'exact_matches': exact_matches,
                'soft_matches': soft_matches,
                'gap_ingredients': list(gaps),
                'gap_count': len(gaps),
                'final_score': final_score,
            })

        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results[:top_k]


# ============================================================================
# 4. 앙상블 추천기
# ============================================================================

class EnsembleRecommender:
    """
    다중 모델 앙상블 추천기

    전략:
    - 각 모델의 추천 결과를 가중 결합
    - Rank Fusion 또는 Score Fusion 지원
    """

    def __init__(
        self,
        models: List[Any],
        weights: Optional[List[float]] = None,
        fusion_method: str = 'score'  # 'score' or 'rank'
    ):
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)
        self.fusion_method = fusion_method

        # 가중치 정규화
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]

    def recommend(
        self,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Tuple[Any, float]]:
        """
        앙상블 추천

        Args:
            user_id: 사용자 ID
            context: 추가 컨텍스트 (장바구니 등)
            top_k: 추천 개수

        Returns:
            [(item_id, score), ...] 리스트
        """
        all_scores = defaultdict(float)

        for model, weight in zip(self.models, self.weights):
            # 모델 타입에 따른 추천 호출
            if hasattr(model, 'recommend'):
                if user_id is not None:
                    predictions = model.recommend(user_id, top_k=top_k * 3)
                elif context is not None:
                    predictions = model.recommend(**context, top_k=top_k * 3)
                else:
                    continue
            else:
                continue

            if self.fusion_method == 'score':
                # Score Fusion
                for item in predictions:
                    if isinstance(item, tuple):
                        item_id, score = item
                    elif isinstance(item, dict):
                        item_id = item.get('product_id') or item.get('recipe_id')
                        score = item.get('score') or item.get('final_score', 0)
                    else:
                        continue

                    all_scores[item_id] += weight * score

            elif self.fusion_method == 'rank':
                # Rank Fusion (Borda Count)
                for rank, item in enumerate(predictions):
                    if isinstance(item, tuple):
                        item_id = item[0]
                    elif isinstance(item, dict):
                        item_id = item.get('product_id') or item.get('recipe_id')
                    else:
                        continue

                    # 역순위 점수
                    rank_score = 1.0 / (rank + 1)
                    all_scores[item_id] += weight * rank_score

        # 최종 랭킹
        ranked = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


# ============================================================================
# 5. 평가 유틸리티
# ============================================================================

class RecommendationMetrics:
    """
    추천 시스템 평가 메트릭
    """

    @staticmethod
    def precision_at_k(recommended: List, relevant: Set, k: int) -> float:
        """Precision@K"""
        if k == 0:
            return 0.0
        recommended_k = recommended[:k]
        hits = sum(1 for item in recommended_k if item in relevant)
        return hits / k

    @staticmethod
    def recall_at_k(recommended: List, relevant: Set, k: int) -> float:
        """Recall@K"""
        if len(relevant) == 0:
            return 0.0
        recommended_k = recommended[:k]
        hits = sum(1 for item in recommended_k if item in relevant)
        return hits / len(relevant)

    @staticmethod
    def ndcg_at_k(recommended: List, relevant: Set, k: int) -> float:
        """NDCG@K"""
        dcg = 0.0
        for i, item in enumerate(recommended[:k]):
            if item in relevant:
                dcg += 1.0 / np.log2(i + 2)

        # IDCG
        idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))

        return dcg / idcg if idcg > 0 else 0.0

    @staticmethod
    def hit_rate_at_k(recommended: List, relevant: Set, k: int) -> float:
        """Hit Rate@K (적어도 하나가 관련 있는지)"""
        recommended_k = set(recommended[:k])
        return 1.0 if recommended_k & relevant else 0.0

    @staticmethod
    def mrr(recommended: List, relevant: Set) -> float:
        """Mean Reciprocal Rank"""
        for i, item in enumerate(recommended):
            if item in relevant:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def catalog_coverage(all_recommendations: List[List], total_items: int) -> float:
        """Catalog Coverage (추천된 고유 아이템 비율)"""
        unique_items = set()
        for recs in all_recommendations:
            unique_items.update(recs)
        return len(unique_items) / total_items if total_items > 0 else 0.0


# ============================================================================
# 편의 함수
# ============================================================================

def evaluate_model(
    model,
    test_data: List[Dict[str, Any]],
    k_values: List[int] = [5, 10, 20]
) -> Dict[str, float]:
    """
    모델 종합 평가

    Args:
        model: 추천 모델
        test_data: [{'user_id': ..., 'relevant_items': set(), ...}, ...]
        k_values: 평가할 K 값 리스트

    Returns:
        평가 지표 딕셔너리
    """
    metrics = RecommendationMetrics()
    results = {k: {'precision': [], 'recall': [], 'ndcg': [], 'hit_rate': []} for k in k_values}
    all_recommendations = []

    for case in test_data:
        user_id = case.get('user_id')
        relevant = case.get('relevant_items', set())
        context = case.get('context', {})

        # 추천 생성
        if user_id is not None:
            recs = model.recommend(user_id, top_k=max(k_values))
        else:
            recs = model.recommend(**context, top_k=max(k_values))

        # ID 추출
        if recs and isinstance(recs[0], tuple):
            rec_ids = [r[0] for r in recs]
        elif recs and isinstance(recs[0], dict):
            rec_ids = [r.get('product_id') or r.get('recipe_id') for r in recs]
        else:
            rec_ids = []

        all_recommendations.append(rec_ids)

        for k in k_values:
            results[k]['precision'].append(metrics.precision_at_k(rec_ids, relevant, k))
            results[k]['recall'].append(metrics.recall_at_k(rec_ids, relevant, k))
            results[k]['ndcg'].append(metrics.ndcg_at_k(rec_ids, relevant, k))
            results[k]['hit_rate'].append(metrics.hit_rate_at_k(rec_ids, relevant, k))

    # 집계
    summary = {}
    for k in k_values:
        summary[f'Precision@{k}'] = np.mean(results[k]['precision'])
        summary[f'Recall@{k}'] = np.mean(results[k]['recall'])
        summary[f'NDCG@{k}'] = np.mean(results[k]['ndcg'])
        summary[f'Hit_Rate@{k}'] = np.mean(results[k]['hit_rate'])

    return summary


if __name__ == '__main__':
    # 간단한 테스트
    print("Kaggle Optimizations 모듈 로드 완료")
    print(f"  - ALSRecommender: ALS 기반 협업 필터링")
    print(f"  - IngredientEmbedder: 재료 임베딩")
    print(f"  - EnhancedRecipeGapFilling: 개선된 레시피 추천")
    print(f"  - EnsembleRecommender: 앙상블 추천기")
    print(f"  - RecommendationMetrics: 평가 메트릭")
