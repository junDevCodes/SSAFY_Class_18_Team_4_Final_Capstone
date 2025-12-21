"""
하이브리드 추천 시스템 모듈

CBF (Content-Based Filtering)와 CF (Collaborative Filtering)을 동적으로 결합.
사용자의 상호작용 히스토리에 따라 가중치를 자동 조정.

학술적 근거:
- Burke, R. (2002). "Hybrid Recommender Systems: Survey and Experiments."
- Ricci, F., Rokach, L., & Shapira, B. (2015).
  "Recommender Systems Handbook (2nd Edition)."
- Netflix Prize (2009): BellKor's Pragmatic Chaos 솔루션
  → 다수의 알고리즘 블렌딩이 단일 알고리즘보다 우수

하이브리드 전략:
1. Weighted Hybrid: 점수 가중 평균 (기본)
2. Switching Hybrid: 조건부 알고리즘 선택
3. Cascade Hybrid: 순차적 필터링
4. Feature Augmentation: CBF 특성을 CF에 통합

기본 설정 (Netflix Prize 기반):
- Cold Start (0-9 상호작용): CBF 0.8 + CF 0.2
- Warm (10-29): CBF 0.7 + CF 0.3
- Active (30-49): CBF 0.5 + CF 0.5
- Power (50+): CBF 0.3 + CF 0.7
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

import numpy as np

from .weight_config import (
    HybridWeights,
    HYBRID_WEIGHTS,
    UserType,
    compute_hybrid_score,
    TIME_DECAY_WEIGHTS,
)
from .als_recommender import OptimizedALSRecommender
from .cbf_recommender import ContentBasedRecommender


# ============================================================================
# 동적 가중치 계산기
# ============================================================================

class HybridStrategy(Enum):
    """하이브리드 전략 타입"""
    WEIGHTED = "weighted"       # 가중 평균 (기본)
    SWITCHING = "switching"     # 조건부 선택
    CASCADE = "cascade"         # 순차적 필터링
    MIXED = "mixed"             # 혼합 (결과 병합)


@dataclass
class DynamicWeightCalculator:
    """
    동적 가중치 계산기

    사용자 특성에 따라 CBF/CF 가중치를 자동 조정.

    고려 요소:
    1. 상호작용 수 (가장 중요)
    2. 상호작용 다양성 (카테고리 분포)
    3. 시간 경과 (최근 활동 여부)
    4. 상호작용 품질 (구매 vs 조회)

    학술 근거:
    - Adaptive Collaborative Filtering (Bell & Koren, 2007)
    - User Cold-Start Problem (Lam et al., 2008)
    """

    # 상호작용 수 → 가중치 매핑
    INTERACTION_THRESHOLDS: List[Tuple[int, float, float]] = field(
        default_factory=lambda: [
            # (min_interactions, cbf_weight, cf_weight)
            (0, 1.0, 0.0),    # 완전 Cold Start
            (1, 0.9, 0.1),    # 아주 적은 상호작용
            (5, 0.8, 0.2),    # Cold Start
            (10, 0.7, 0.3),   # Warm Start (기본 추천)
            (20, 0.6, 0.4),   # 일반 사용자
            (30, 0.5, 0.5),   # 활성 사용자
            (50, 0.4, 0.6),   # 고빈도 사용자
            (100, 0.3, 0.7),  # Power User
        ]
    )

    # 카테고리 다양성 보정 계수
    DIVERSITY_BONUS: float = 0.1  # 다양성 높으면 CF 가중치 증가

    # 최근 활동 보정 계수
    RECENCY_BONUS: float = 0.05  # 최근 활동 있으면 CF 가중치 증가

    def compute_weights(
        self,
        n_interactions: int,
        n_unique_categories: int = 0,
        days_since_last_interaction: int = 0,
        high_quality_ratio: float = 0.0,  # 구매/리뷰 비율
    ) -> Tuple[float, float]:
        """
        동적 가중치 계산

        Args:
            n_interactions: 총 상호작용 수
            n_unique_categories: 상호작용한 고유 카테고리 수
            days_since_last_interaction: 마지막 상호작용 후 경과일
            high_quality_ratio: 고품질 상호작용 비율 (구매, 리뷰)

        Returns:
            (cbf_weight, cf_weight): 합이 1.0인 가중치 튜플
        """
        # 1. 기본 가중치 (상호작용 수 기반)
        cbf_weight, cf_weight = 1.0, 0.0

        for min_count, cbf_w, cf_w in sorted(self.INTERACTION_THRESHOLDS, reverse=True):
            if n_interactions >= min_count:
                cbf_weight, cf_weight = cbf_w, cf_w
                break

        # 2. 카테고리 다양성 보정 (다양하면 CF 증가)
        if n_unique_categories >= 5:
            diversity_adjustment = min(self.DIVERSITY_BONUS, cf_weight * 0.5)
            cf_weight += diversity_adjustment
            cbf_weight -= diversity_adjustment

        # 3. 최근 활동 보정 (최근 활동 있으면 CF 증가)
        if days_since_last_interaction < 7:
            recency_adjustment = min(self.RECENCY_BONUS, cf_weight * 0.5)
            cf_weight += recency_adjustment
            cbf_weight -= recency_adjustment

        # 4. 고품질 상호작용 보정 (구매 많으면 CF 신뢰도 증가)
        if high_quality_ratio > 0.3:
            quality_adjustment = min(high_quality_ratio * 0.1, cf_weight * 0.3)
            cf_weight += quality_adjustment
            cbf_weight -= quality_adjustment

        # 정규화 (합이 1.0)
        total = cbf_weight + cf_weight
        if total > 0:
            cbf_weight /= total
            cf_weight /= total

        return cbf_weight, cf_weight

    def get_user_type(self, n_interactions: int) -> UserType:
        """상호작용 수 기반 사용자 유형 분류"""
        if n_interactions == 0:
            return UserType.COLD
        elif n_interactions < 10:
            return UserType.LUKEWARM
        elif n_interactions < 30:
            return UserType.WARM
        else:
            return UserType.HOT


# ============================================================================
# 하이브리드 추천기
# ============================================================================

class HybridRecommender:
    """
    하이브리드 추천 시스템

    CBF와 CF를 동적으로 결합하여 추천 제공.

    주요 기능:
    1. 동적 가중치: 사용자 특성에 따라 자동 조정
    2. Cold Start 처리: CBF + 인기도 기반 추천
    3. 다양성 보장: MMR (Maximal Marginal Relevance) 적용
    4. 식료품 특화: 재구매 허용 (filter_already_liked=False)

    학술 근거:
    - Netflix Prize: 앙상블 방법론
    - Burke (2002): 하이브리드 전략 분류
    - Carbonell & Goldstein (1998): MMR for 다양성
    """

    def __init__(
        self,
        cf_model: Optional[OptimizedALSRecommender] = None,
        cbf_model: Optional[ContentBasedRecommender] = None,
        strategy: HybridStrategy = HybridStrategy.WEIGHTED,
        default_cbf_weight: float = 0.7,
        default_cf_weight: float = 0.3,
        use_dynamic_weights: bool = True,
        diversity_lambda: float = 0.3,  # MMR 다양성 파라미터
    ):
        """
        Args:
            cf_model: 협업 필터링 모델 (ALS)
            cbf_model: 콘텐츠 기반 모델
            strategy: 하이브리드 전략
            default_cbf_weight: 기본 CBF 가중치 (0.7 = Netflix Prize 기반)
            default_cf_weight: 기본 CF 가중치 (0.3)
            use_dynamic_weights: 동적 가중치 사용 여부
            diversity_lambda: MMR 다양성 계수 (0=관련성만, 1=다양성만)
        """
        self.cf_model = cf_model
        self.cbf_model = cbf_model
        self.strategy = strategy
        self.default_cbf_weight = default_cbf_weight
        self.default_cf_weight = default_cf_weight
        self.use_dynamic_weights = use_dynamic_weights
        self.diversity_lambda = diversity_lambda

        # 동적 가중치 계산기
        self.weight_calculator = DynamicWeightCalculator()

        # 사용자별 상호작용 캐시 (동적 가중치용)
        self.user_interaction_counts: Dict[int, int] = {}
        self.user_category_counts: Dict[int, int] = {}

        # 성능 통계
        self.recommendation_stats: Dict[str, int] = {
            'total': 0,
            'cold_start': 0,
            'warm_start': 0,
            'cf_dominant': 0,
            'cbf_dominant': 0,
        }

    def set_cf_model(self, model: OptimizedALSRecommender) -> None:
        """CF 모델 설정"""
        self.cf_model = model

    def set_cbf_model(self, model: ContentBasedRecommender) -> None:
        """CBF 모델 설정"""
        self.cbf_model = model

    def update_user_stats(
        self,
        user_id: int,
        n_interactions: int,
        n_categories: int = 0
    ) -> None:
        """사용자 통계 업데이트 (동적 가중치용)"""
        self.user_interaction_counts[user_id] = n_interactions
        if n_categories > 0:
            self.user_category_counts[user_id] = n_categories

    def _get_user_weights(self, user_id: int) -> Tuple[float, float]:
        """사용자별 동적 가중치 조회"""
        if not self.use_dynamic_weights:
            return self.default_cbf_weight, self.default_cf_weight

        n_interactions = self.user_interaction_counts.get(user_id, 0)
        n_categories = self.user_category_counts.get(user_id, 0)

        return self.weight_calculator.compute_weights(
            n_interactions=n_interactions,
            n_unique_categories=n_categories,
        )

    def recommend(
        self,
        user_id: int,
        user_interactions: Optional[Dict[int, float]] = None,
        top_k: int = 10,
        filter_already_interacted: bool = False,  # 식료품: False 권장
        candidate_items: Optional[List[int]] = None,
        category_filter: Optional[str] = None,
        apply_diversity: bool = True,
    ) -> List[Tuple[int, float]]:
        """
        하이브리드 추천 생성

        Args:
            user_id: 사용자 ID
            user_interactions: {product_id: score} 상호작용 정보
            top_k: 추천 수
            filter_already_interacted: 상호작용 아이템 제외 (식료품은 False)
            candidate_items: 후보 아이템 제한 (None=전체)
            category_filter: 카테고리 필터
            apply_diversity: MMR 다양성 적용 여부

        Returns:
            [(product_id, score), ...]
        """
        self.recommendation_stats['total'] += 1

        # 상호작용 수 업데이트
        if user_interactions:
            self.user_interaction_counts[user_id] = len(user_interactions)

        # 가중치 계산
        cbf_weight, cf_weight = self._get_user_weights(user_id)

        # Cold Start 확인
        n_interactions = len(user_interactions) if user_interactions else 0
        is_cold_start = n_interactions < 5

        if is_cold_start:
            self.recommendation_stats['cold_start'] += 1
        else:
            self.recommendation_stats['warm_start'] += 1

        # 전략별 추천 생성
        if self.strategy == HybridStrategy.WEIGHTED:
            results = self._weighted_hybrid(
                user_id, user_interactions, top_k * 2,
                cbf_weight, cf_weight,
                filter_already_interacted, candidate_items
            )
        elif self.strategy == HybridStrategy.SWITCHING:
            results = self._switching_hybrid(
                user_id, user_interactions, top_k * 2,
                is_cold_start, filter_already_interacted, candidate_items
            )
        elif self.strategy == HybridStrategy.CASCADE:
            results = self._cascade_hybrid(
                user_id, user_interactions, top_k * 2,
                cbf_weight, filter_already_interacted, candidate_items
            )
        else:  # MIXED
            results = self._mixed_hybrid(
                user_id, user_interactions, top_k * 2,
                filter_already_interacted, candidate_items
            )

        # 카테고리 필터링
        if category_filter and self.cbf_model:
            # TODO: 카테고리 필터 구현
            pass

        # 다양성 적용 (MMR)
        if apply_diversity and len(results) > top_k:
            results = self._apply_mmr(results, top_k)
        else:
            results = results[:top_k]

        # 통계 업데이트
        if cf_weight > cbf_weight:
            self.recommendation_stats['cf_dominant'] += 1
        else:
            self.recommendation_stats['cbf_dominant'] += 1

        return results

    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        점수 Min-Max 정규화 (0~1 범위)

        문제 해결:
        - CBF 점수: 0~1 범위 (코사인 유사도)
        - CF 점수: 임의 범위 (내적 결과, 예: 0.8~1.5)
        - 해결: 두 점수를 동일한 0~1 범위로 정규화 후 가중 결합
        """
        if not scores:
            return {}

        values = list(scores.values())
        min_val = min(values)
        max_val = max(values)

        if max_val - min_val < 1e-8:
            # 모든 점수가 동일한 경우
            return {k: 0.5 for k in scores}

        return {
            k: (v - min_val) / (max_val - min_val)
            for k, v in scores.items()
        }

    def _weighted_hybrid(
        self,
        user_id: int,
        user_interactions: Optional[Dict[int, float]],
        top_k: int,
        cbf_weight: float,
        cf_weight: float,
        filter_already_interacted: bool,
        candidate_items: Optional[List[int]],
    ) -> List[Tuple[int, float]]:
        """
        가중 하이브리드: CBF와 CF 점수를 가중 평균

        S_hybrid = α × S_cbf_normalized + (1-α) × S_cf_normalized

        수정 사항:
        - CBF와 CF 점수를 각각 0~1로 정규화 후 결합
        - 이를 통해 가중치가 정확하게 작동
        """
        cbf_scores: Dict[int, float] = {}
        cf_scores: Dict[int, float] = {}

        # 1. CBF 점수 수집
        if self.cbf_model and cbf_weight > 0:
            cbf_results = self.cbf_model.recommend_for_user(
                user_interactions or {},
                top_k=top_k * 3,  # 더 많은 후보 수집
                exclude_interacted=filter_already_interacted,
            )
            for product_id, score in cbf_results:
                if candidate_items is None or product_id in candidate_items:
                    cbf_scores[product_id] = score

        # 2. CF 점수 수집
        if self.cf_model and cf_weight > 0:
            try:
                cf_results = self.cf_model.recommend(
                    user_id=user_id,
                    top_k=top_k * 3,  # 더 많은 후보 수집
                    filter_already_interacted=filter_already_interacted,
                )
                for product_id, score in cf_results:
                    if candidate_items is None or product_id in candidate_items:
                        cf_scores[product_id] = score
            except (KeyError, ValueError):
                # CF 모델에 사용자가 없는 경우
                pass

        # 3. 점수 정규화 (0~1 범위)
        cbf_scores_normalized = self._normalize_scores(cbf_scores)
        cf_scores_normalized = self._normalize_scores(cf_scores)

        # 4. 가중 결합
        all_products = set(cbf_scores_normalized.keys()) | set(cf_scores_normalized.keys())
        final_scores: Dict[int, float] = {}

        for product_id in all_products:
            cbf_score = cbf_scores_normalized.get(product_id, 0.0)
            cf_score = cf_scores_normalized.get(product_id, 0.0)
            final_scores[product_id] = cbf_weight * cbf_score + cf_weight * cf_score

        # 정렬
        sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]

    def _switching_hybrid(
        self,
        user_id: int,
        user_interactions: Optional[Dict[int, float]],
        top_k: int,
        is_cold_start: bool,
        filter_already_interacted: bool,
        candidate_items: Optional[List[int]],
    ) -> List[Tuple[int, float]]:
        """
        스위칭 하이브리드: 조건에 따라 알고리즘 선택

        Cold Start → CBF만 사용
        Warm Start → CF만 사용
        """
        if is_cold_start or self.cf_model is None:
            # CBF 사용
            if self.cbf_model:
                results = self.cbf_model.recommend_for_user(
                    user_interactions or {},
                    top_k=top_k,
                    exclude_interacted=filter_already_interacted,
                )
            else:
                results = []
        else:
            # CF 사용
            try:
                results = self.cf_model.recommend(
                    user_id=user_id,
                    top_k=top_k,
                    filter_already_interacted=filter_already_interacted,
                )
            except (KeyError, ValueError):
                # CF 실패시 CBF fallback
                if self.cbf_model:
                    results = self.cbf_model.recommend_for_user(
                        user_interactions or {},
                        top_k=top_k,
                        exclude_interacted=filter_already_interacted,
                    )
                else:
                    results = []

        # 후보 필터링
        if candidate_items:
            candidate_set = set(candidate_items)
            results = [(pid, score) for pid, score in results if pid in candidate_set]

        return results

    def _cascade_hybrid(
        self,
        user_id: int,
        user_interactions: Optional[Dict[int, float]],
        top_k: int,
        cbf_weight: float,
        filter_already_interacted: bool,
        candidate_items: Optional[List[int]],
    ) -> List[Tuple[int, float]]:
        """
        캐스케이드 하이브리드: CBF로 후보 생성 → CF로 재순위

        단계:
        1. CBF로 top_k * 3 후보 생성
        2. CF로 후보들 점수 계산
        3. 최종 점수 = CBF 순위 + CF 점수
        """
        # 1. CBF 후보 생성
        cbf_candidates = []
        if self.cbf_model:
            cbf_results = self.cbf_model.recommend_for_user(
                user_interactions or {},
                top_k=top_k * 3,
                exclude_interacted=filter_already_interacted,
            )
            cbf_candidates = [pid for pid, _ in cbf_results]

        if not cbf_candidates:
            # CBF 실패시 CF만 사용
            if self.cf_model:
                try:
                    return list(self.cf_model.recommend(
                        user_id=user_id,
                        top_k=top_k,
                        filter_already_interacted=filter_already_interacted,
                    ))
                except (KeyError, ValueError):
                    return []
            return []

        # 2. CF로 재순위
        if self.cf_model:
            try:
                cf_results = self.cf_model.recommend(
                    user_id=user_id,
                    top_k=top_k * 5,
                    filter_already_interacted=filter_already_interacted,
                )
                cf_scores = {pid: score for pid, score in cf_results}
            except (KeyError, ValueError):
                cf_scores = {}
        else:
            cf_scores = {}

        # 3. 최종 점수 계산
        final_scores: Dict[int, float] = {}
        for rank, pid in enumerate(cbf_candidates):
            if candidate_items and pid not in candidate_items:
                continue

            cbf_rank_score = 1.0 - (rank / len(cbf_candidates))
            cf_score = cf_scores.get(pid, 0.0)

            # 가중 결합
            final_scores[pid] = cbf_weight * cbf_rank_score + (1 - cbf_weight) * cf_score

        sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]

    def _mixed_hybrid(
        self,
        user_id: int,
        user_interactions: Optional[Dict[int, float]],
        top_k: int,
        filter_already_interacted: bool,
        candidate_items: Optional[List[int]],
    ) -> List[Tuple[int, float]]:
        """
        혼합 하이브리드: CBF와 CF 결과를 인터리빙

        순서: CBF1, CF1, CBF2, CF2, ...
        중복 제거
        """
        cbf_results = []
        cf_results = []

        # CBF 결과
        if self.cbf_model:
            cbf_results = list(self.cbf_model.recommend_for_user(
                user_interactions or {},
                top_k=top_k,
                exclude_interacted=filter_already_interacted,
            ))

        # CF 결과
        if self.cf_model:
            try:
                cf_results = list(self.cf_model.recommend(
                    user_id=user_id,
                    top_k=top_k,
                    filter_already_interacted=filter_already_interacted,
                ))
            except (KeyError, ValueError):
                pass

        # 인터리빙
        results = []
        seen: Set[int] = set()
        cbf_idx, cf_idx = 0, 0

        while len(results) < top_k and (cbf_idx < len(cbf_results) or cf_idx < len(cf_results)):
            # CBF에서 하나
            while cbf_idx < len(cbf_results):
                pid, score = cbf_results[cbf_idx]
                cbf_idx += 1
                if pid not in seen and (candidate_items is None or pid in candidate_items):
                    results.append((pid, score))
                    seen.add(pid)
                    break

            if len(results) >= top_k:
                break

            # CF에서 하나
            while cf_idx < len(cf_results):
                pid, score = cf_results[cf_idx]
                cf_idx += 1
                if pid not in seen and (candidate_items is None or pid in candidate_items):
                    results.append((pid, score))
                    seen.add(pid)
                    break

        return results

    def _apply_mmr(
        self,
        candidates: List[Tuple[int, float]],
        top_k: int
    ) -> List[Tuple[int, float]]:
        """
        Maximal Marginal Relevance (MMR) 적용

        다양성과 관련성의 균형을 맞춤.

        MMR = λ × Relevance - (1-λ) × max(Similarity to selected)

        학술 근거:
        - Carbonell & Goldstein (1998): MMR 정의
        - 추천 시스템에서 다양성 확보의 중요성
        """
        if not candidates or not self.cbf_model:
            return candidates[:top_k]

        selected: List[Tuple[int, float]] = []
        remaining = list(candidates)

        # 첫 번째는 최고 관련성 아이템
        if remaining:
            selected.append(remaining.pop(0))

        while len(selected) < top_k and remaining:
            best_mmr = float('-inf')
            best_idx = 0

            for i, (pid, relevance) in enumerate(remaining):
                # 선택된 아이템들과의 최대 유사도
                max_sim = 0.0

                pid_features = self.cbf_model.get_item_features(pid)
                if pid_features is not None:
                    for selected_pid, _ in selected:
                        sel_features = self.cbf_model.get_item_features(selected_pid)
                        if sel_features is not None:
                            sim = float(np.dot(pid_features, sel_features))
                            max_sim = max(max_sim, sim)

                # MMR 점수
                mmr = self.diversity_lambda * relevance - (1 - self.diversity_lambda) * max_sim

                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def recommend_cold_start(
        self,
        preferred_categories: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """Cold Start 사용자 추천 (CBF 전용)"""
        if self.cbf_model:
            return self.cbf_model.recommend_cold_start(
                preferred_categories=preferred_categories,
                top_k=top_k,
            )
        return []

    def get_similar_items(
        self,
        product_id: int,
        top_k: int = 10,
        method: str = 'hybrid'
    ) -> List[Tuple[int, float]]:
        """
        유사 아이템 추천

        Args:
            product_id: 기준 상품
            top_k: 반환 수
            method: 'cbf', 'cf', 'hybrid'
        """
        if method == 'cbf' and self.cbf_model:
            return self.cbf_model.get_similar_items(product_id, top_k)
        elif method == 'cf' and self.cf_model:
            return self.cf_model.similar_items(product_id, top_k)
        else:
            # Hybrid: 두 결과 결합
            cbf_results = []
            cf_results = []

            if self.cbf_model:
                cbf_results = self.cbf_model.get_similar_items(product_id, top_k)
            if self.cf_model:
                cf_results = self.cf_model.similar_items(product_id, top_k)

            # 점수 결합
            scores: Dict[int, float] = {}
            for pid, score in cbf_results:
                scores[pid] = self.default_cbf_weight * score
            for pid, score in cf_results:
                if pid in scores:
                    scores[pid] += self.default_cf_weight * score
                else:
                    scores[pid] = self.default_cf_weight * score

            return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """추천 통계 조회"""
        total = self.recommendation_stats['total']
        if total == 0:
            return self.recommendation_stats

        stats = dict(self.recommendation_stats)
        stats['cold_start_ratio'] = stats['cold_start'] / total
        stats['cf_dominant_ratio'] = stats['cf_dominant'] / total
        stats['cbf_dominant_ratio'] = stats['cbf_dominant'] / total

        return stats

    def save(self, filepath: str) -> None:
        """하이브리드 모델 저장 (메타데이터만)"""
        data = {
            'version': '1.0.0',
            'strategy': self.strategy.value,
            'default_cbf_weight': self.default_cbf_weight,
            'default_cf_weight': self.default_cf_weight,
            'use_dynamic_weights': self.use_dynamic_weights,
            'diversity_lambda': self.diversity_lambda,
            'user_interaction_counts': self.user_interaction_counts,
            'user_category_counts': self.user_category_counts,
            'recommendation_stats': self.recommendation_stats,
        }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(
        cls,
        filepath: str,
        cf_model: Optional[OptimizedALSRecommender] = None,
        cbf_model: Optional[ContentBasedRecommender] = None,
    ) -> 'HybridRecommender':
        """하이브리드 모델 로드"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        recommender = cls(
            cf_model=cf_model,
            cbf_model=cbf_model,
            strategy=HybridStrategy(data['strategy']),
            default_cbf_weight=data['default_cbf_weight'],
            default_cf_weight=data['default_cf_weight'],
            use_dynamic_weights=data['use_dynamic_weights'],
            diversity_lambda=data['diversity_lambda'],
        )
        recommender.user_interaction_counts = data.get('user_interaction_counts', {})
        recommender.user_category_counts = data.get('user_category_counts', {})
        recommender.recommendation_stats = data.get('recommendation_stats', {})

        return recommender


# ============================================================================
# 팩토리 함수
# ============================================================================

def create_hybrid_recommender(
    cf_model: Optional[OptimizedALSRecommender] = None,
    cbf_model: Optional[ContentBasedRecommender] = None,
    strategy: str = 'weighted',
    cbf_weight: float = 0.7,
    use_dynamic_weights: bool = True,
) -> HybridRecommender:
    """
    하이브리드 추천기 생성 헬퍼

    Args:
        cf_model: ALS 모델
        cbf_model: CBF 모델
        strategy: 'weighted', 'switching', 'cascade', 'mixed'
        cbf_weight: CBF 기본 가중치
        use_dynamic_weights: 동적 가중치 사용 여부

    Returns:
        HybridRecommender 인스턴스
    """
    strategy_enum = HybridStrategy(strategy)

    return HybridRecommender(
        cf_model=cf_model,
        cbf_model=cbf_model,
        strategy=strategy_enum,
        default_cbf_weight=cbf_weight,
        default_cf_weight=1.0 - cbf_weight,
        use_dynamic_weights=use_dynamic_weights,
    )


__all__ = [
    'HybridStrategy',
    'DynamicWeightCalculator',
    'HybridRecommender',
    'create_hybrid_recommender',
]
