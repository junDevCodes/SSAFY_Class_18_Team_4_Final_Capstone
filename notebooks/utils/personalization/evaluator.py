"""
추천 시스템 평가 모듈

오프라인 평가 지표 및 교차 검증 프레임워크.

학술적 근거:
- Herlocker, J. L., et al. (2004).
  "Evaluating Collaborative Filtering Recommender Systems."
- Shani, G., & Gunawardana, A. (2011).
  "Evaluating Recommendation Systems."
- Cremonesi, P., et al. (2010).
  "Performance of Recommender Algorithms on Top-N Recommendation Tasks."

주요 평가 지표:
1. Recall@K: 실제 구매 중 추천에 포함된 비율
2. Precision@K: 추천 중 실제 구매 비율
3. NDCG@K: 순위 가중 정확도 (Normalized Discounted Cumulative Gain)
4. Hit Rate@K: 최소 1개 적중한 사용자 비율
5. MRR: Mean Reciprocal Rank (첫 적중 순위 역수 평균)
6. Coverage: 추천 커버리지 (추천된 고유 아이템 비율)
7. Diversity: 추천 다양성 (평균 아이템 간 비유사도)
8. Novelty: 추천 신규성 (인기도 역비례)

Kaggle 최상위 목표:
- Recall@10 ≥ 0.15
- NDCG@10 ≥ 0.20
- Hit Rate@10 ≥ 0.70
- MRR ≥ 0.25
- Coverage ≥ 0.50
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

import numpy as np

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


# ============================================================================
# 기본 평가 지표 함수
# ============================================================================

def compute_recall_at_k(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    Recall@K 계산

    Recall@K = |추천 ∩ 실제| / |실제|

    의미: 사용자가 실제로 좋아할 아이템 중 추천에 포함된 비율

    Args:
        recommended: 추천 아이템 리스트 (순서대로)
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        Recall@K 값 (0.0 ~ 1.0)
    """
    if not ground_truth:
        return 0.0

    recommended_k = set(recommended[:k])
    hits = len(recommended_k & ground_truth)

    return hits / len(ground_truth)


def compute_precision_at_k(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    Precision@K 계산

    Precision@K = |추천 ∩ 실제| / K

    의미: 추천 아이템 중 실제로 관련 있는 비율

    Args:
        recommended: 추천 아이템 리스트
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        Precision@K 값 (0.0 ~ 1.0)
    """
    if k == 0:
        return 0.0

    recommended_k = set(recommended[:k])
    hits = len(recommended_k & ground_truth)

    return hits / k


def compute_ndcg_at_k(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10,
    relevance_scores: Optional[Dict[int, float]] = None
) -> float:
    """
    NDCG@K (Normalized Discounted Cumulative Gain) 계산

    DCG@K = Σ (rel_i / log2(i+1)) for i=1..K
    NDCG@K = DCG@K / IDCG@K

    의미: 순위가 높을수록 가중치를 더 주는 정확도 지표

    Args:
        recommended: 추천 아이템 리스트 (순서대로)
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려
        relevance_scores: 아이템별 관련성 점수 (없으면 binary)

    Returns:
        NDCG@K 값 (0.0 ~ 1.0)
    """
    if not ground_truth:
        return 0.0

    # DCG 계산
    dcg = 0.0
    for i, item in enumerate(recommended[:k]):
        if item in ground_truth:
            # 관련성 점수 (기본 1.0)
            rel = relevance_scores.get(item, 1.0) if relevance_scores else 1.0
            # 순위 할인 (log2(rank+1))
            dcg += rel / np.log2(i + 2)  # i+2 because log2(1)=0

    # IDCG 계산 (이상적인 순서)
    ideal_relevances = []
    for item in ground_truth:
        rel = relevance_scores.get(item, 1.0) if relevance_scores else 1.0
        ideal_relevances.append(rel)

    ideal_relevances.sort(reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_relevances[:k]):
        idcg += rel / np.log2(i + 2)

    if idcg == 0:
        return 0.0

    return dcg / idcg


def compute_hit_rate(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    Hit Rate (Binary) 계산

    Hit = 1 if |추천@K ∩ 실제| > 0 else 0

    의미: 추천 중 최소 1개라도 맞았는지 여부

    Args:
        recommended: 추천 아이템 리스트
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        1.0 if hit, 0.0 otherwise
    """
    if not ground_truth:
        return 0.0

    recommended_k = set(recommended[:k])
    return 1.0 if (recommended_k & ground_truth) else 0.0


def compute_mrr(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    MRR (Mean Reciprocal Rank) 계산

    RR = 1 / rank_of_first_hit

    의미: 첫 번째 적중의 순위 역수 (높을수록 좋음)

    Args:
        recommended: 추천 아이템 리스트
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        RR 값 (0.0 ~ 1.0)
    """
    if not ground_truth:
        return 0.0

    for i, item in enumerate(recommended[:k]):
        if item in ground_truth:
            return 1.0 / (i + 1)

    return 0.0


def compute_map_at_k(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    MAP@K (Mean Average Precision) 계산

    AP@K = (1/|실제|) × Σ (Precision@i × rel_i) for i=1..K

    의미: 적중 시점마다 Precision을 계산하여 평균

    Args:
        recommended: 추천 아이템 리스트
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        AP@K 값 (0.0 ~ 1.0)
    """
    if not ground_truth:
        return 0.0

    hits = 0
    sum_precision = 0.0

    for i, item in enumerate(recommended[:k]):
        if item in ground_truth:
            hits += 1
            precision_at_i = hits / (i + 1)
            sum_precision += precision_at_i

    if len(ground_truth) == 0:
        return 0.0

    return sum_precision / min(len(ground_truth), k)


def compute_f1_at_k(
    recommended: List[int],
    ground_truth: Set[int],
    k: int = 10
) -> float:
    """
    F1@K 계산

    F1@K = 2 × (Precision@K × Recall@K) / (Precision@K + Recall@K)

    Args:
        recommended: 추천 아이템 리스트
        ground_truth: 실제 관심 아이템 집합
        k: 상위 K개만 고려

    Returns:
        F1@K 값 (0.0 ~ 1.0)
    """
    precision = compute_precision_at_k(recommended, ground_truth, k)
    recall = compute_recall_at_k(recommended, ground_truth, k)

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


# ============================================================================
# 다양성/커버리지 지표
# ============================================================================

def compute_coverage(
    all_recommendations: List[List[int]],
    total_items: int,
) -> float:
    """
    추천 커버리지 계산

    Coverage = |추천된 고유 아이템| / |전체 아이템|

    의미: 전체 카탈로그 중 추천에 등장한 아이템 비율

    Args:
        all_recommendations: 모든 사용자의 추천 리스트
        total_items: 전체 아이템 수

    Returns:
        Coverage 값 (0.0 ~ 1.0)
    """
    if total_items == 0:
        return 0.0

    unique_items: Set[int] = set()
    for recommendations in all_recommendations:
        unique_items.update(recommendations)

    return len(unique_items) / total_items


def compute_diversity(
    recommended: List[int],
    similarity_matrix: np.ndarray,
    item_to_idx: Dict[int, int],
) -> float:
    """
    추천 다양성 계산 (Intra-List Diversity)

    Diversity = 1 - (평균 아이템 간 유사도)

    의미: 추천 리스트 내 아이템들이 얼마나 다양한지

    Args:
        recommended: 추천 아이템 리스트
        similarity_matrix: (n_items, n_items) 유사도 행렬
        item_to_idx: 아이템 ID → 인덱스 매핑

    Returns:
        Diversity 값 (0.0 ~ 1.0)
    """
    if len(recommended) < 2:
        return 1.0

    total_similarity = 0.0
    count = 0

    for i, item1 in enumerate(recommended):
        for item2 in recommended[i + 1:]:
            idx1 = item_to_idx.get(item1)
            idx2 = item_to_idx.get(item2)

            if idx1 is not None and idx2 is not None:
                total_similarity += similarity_matrix[idx1, idx2]
                count += 1

    if count == 0:
        return 1.0

    avg_similarity = total_similarity / count
    return 1.0 - avg_similarity


def compute_novelty(
    recommended: List[int],
    item_popularity: Dict[int, float],
) -> float:
    """
    추천 신규성 계산

    Novelty = 평균(-log2(popularity))

    의미: 인기 없는(신규) 아이템을 추천할수록 높은 점수

    Args:
        recommended: 추천 아이템 리스트
        item_popularity: 아이템별 인기도 (0.0 ~ 1.0)

    Returns:
        Novelty 값 (높을수록 신규)
    """
    if not recommended:
        return 0.0

    novelty_scores = []
    for item in recommended:
        pop = item_popularity.get(item, 0.01)  # 최소값 0.01
        # Self-information: -log2(p)
        novelty_scores.append(-np.log2(max(pop, 1e-10)))

    return float(np.mean(novelty_scores))


# ============================================================================
# 추천기 평가자 클래스
# ============================================================================

@dataclass
class EvaluationResult:
    """평가 결과 데이터 클래스"""
    metrics: Dict[str, float]
    per_user_metrics: Dict[int, Dict[str, float]]
    k_values: List[int]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model_name: str = ""
    n_users: int = 0
    n_items: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'metrics': self.metrics,
            'k_values': self.k_values,
            'timestamp': self.timestamp,
            'model_name': self.model_name,
            'n_users': self.n_users,
            'n_items': self.n_items,
        }

    def to_json(self, filepath: str) -> None:
        """JSON 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def summary(self) -> str:
        """평가 결과 요약 문자열"""
        lines = [
            f"=== 평가 결과 ({self.model_name}) ===",
            f"평가 시간: {self.timestamp}",
            f"사용자 수: {self.n_users:,}",
            f"아이템 수: {self.n_items:,}",
            "",
            "--- 주요 지표 ---",
        ]

        for k in self.k_values:
            lines.append(f"\n[K={k}]")
            for metric_name in ['Recall', 'Precision', 'NDCG', 'HitRate', 'MRR', 'MAP']:
                key = f'{metric_name}@{k}'
                if key in self.metrics:
                    lines.append(f"  {metric_name}@{k}: {self.metrics[key]:.4f}")

        if 'Coverage' in self.metrics:
            lines.append(f"\nCoverage: {self.metrics['Coverage']:.4f}")
        if 'Novelty' in self.metrics:
            lines.append(f"Novelty: {self.metrics['Novelty']:.4f}")

        return '\n'.join(lines)


class RecommenderEvaluator:
    """
    추천 시스템 평가기

    다양한 평가 지표를 계산하고 결과를 저장.

    사용법:
    ```python
    evaluator = RecommenderEvaluator()
    results = evaluator.evaluate(
        recommender=model,
        test_data=test_interactions,
        k_values=[5, 10, 20],
    )
    print(results.summary())
    ```
    """

    def __init__(
        self,
        k_values: List[int] = None,
        compute_coverage: bool = True,
        compute_novelty: bool = True,
        compute_diversity: bool = False,  # 계산 비용 높음
        verbose: bool = True,
    ):
        """
        Args:
            k_values: 평가할 K 값 리스트 (기본: [5, 10, 20])
            compute_coverage: 커버리지 계산 여부
            compute_novelty: 신규성 계산 여부
            compute_diversity: 다양성 계산 여부 (느림)
            verbose: 진행 상황 출력 여부
        """
        self.k_values = k_values or [5, 10, 20]
        self.compute_coverage_flag = compute_coverage
        self.compute_novelty_flag = compute_novelty
        self.compute_diversity_flag = compute_diversity
        self.verbose = verbose

    def evaluate(
        self,
        recommender: Any,
        test_data: Dict[int, Set[int]],
        train_data: Optional[Dict[int, Set[int]]] = None,
        item_popularity: Optional[Dict[int, float]] = None,
        total_items: int = 0,
        model_name: str = "Unknown",
    ) -> EvaluationResult:
        """
        추천 모델 평가

        Args:
            recommender: 추천 모델 (recommend() 메서드 필요)
            test_data: {user_id: set(item_ids)} 테스트 상호작용
            train_data: {user_id: set(item_ids)} 학습 상호작용 (필터링용)
            item_popularity: 아이템 인기도 (신규성 계산용)
            total_items: 전체 아이템 수 (커버리지 계산용)
            model_name: 모델 이름

        Returns:
            EvaluationResult 객체
        """
        max_k = max(self.k_values)

        # 지표 누적 변수
        metrics_sum: Dict[str, float] = {}
        per_user_metrics: Dict[int, Dict[str, float]] = {}
        all_recommendations: List[List[int]] = []

        # 사용자별 평가
        users = list(test_data.keys())

        if self.verbose and TQDM_AVAILABLE:
            iterator = tqdm(users, desc=f"평가 중 ({model_name})")
        else:
            iterator = users

        evaluated_users = 0

        for user_id in iterator:
            ground_truth = test_data[user_id]

            if not ground_truth:
                continue

            # 추천 생성
            try:
                # 학습 데이터에서의 상호작용 (있는 경우)
                user_train = train_data.get(user_id, set()) if train_data else set()

                # recommender.recommend() 호출
                recommendations = recommender.recommend(
                    user_id=user_id,
                    top_k=max_k,
                    filter_already_interacted=False,  # 식료품: 재구매 허용
                )

                # 결과 형식 처리: [(item, score), ...] 또는 [item, ...]
                if recommendations and isinstance(recommendations[0], tuple):
                    rec_items = [item for item, _ in recommendations]
                else:
                    rec_items = list(recommendations)

            except (KeyError, ValueError, AttributeError, IndexError) as e:
                # 사용자가 모델에 없는 경우 등
                continue

            if not rec_items:
                continue

            # 사용자별 지표 계산
            user_metrics: Dict[str, float] = {}

            for k in self.k_values:
                user_metrics[f'Recall@{k}'] = compute_recall_at_k(rec_items, ground_truth, k)
                user_metrics[f'Precision@{k}'] = compute_precision_at_k(rec_items, ground_truth, k)
                user_metrics[f'NDCG@{k}'] = compute_ndcg_at_k(rec_items, ground_truth, k)
                user_metrics[f'HitRate@{k}'] = compute_hit_rate(rec_items, ground_truth, k)
                user_metrics[f'MRR@{k}'] = compute_mrr(rec_items, ground_truth, k)
                user_metrics[f'MAP@{k}'] = compute_map_at_k(rec_items, ground_truth, k)
                user_metrics[f'F1@{k}'] = compute_f1_at_k(rec_items, ground_truth, k)

            # 누적
            for metric, value in user_metrics.items():
                if metric not in metrics_sum:
                    metrics_sum[metric] = 0.0
                metrics_sum[metric] += value

            per_user_metrics[user_id] = user_metrics
            all_recommendations.append(rec_items)
            evaluated_users += 1

        # 평균 계산
        if evaluated_users == 0:
            raise ValueError("평가할 사용자가 없습니다.")

        final_metrics = {
            k: v / evaluated_users for k, v in metrics_sum.items()
        }

        # 커버리지 계산
        if self.compute_coverage_flag and total_items > 0:
            final_metrics['Coverage'] = compute_coverage(all_recommendations, total_items)

        # 신규성 계산
        if self.compute_novelty_flag and item_popularity:
            novelty_scores = []
            for rec_items in all_recommendations:
                novelty_scores.append(compute_novelty(rec_items, item_popularity))
            final_metrics['Novelty'] = float(np.mean(novelty_scores))

        return EvaluationResult(
            metrics=final_metrics,
            per_user_metrics=per_user_metrics,
            k_values=self.k_values,
            model_name=model_name,
            n_users=evaluated_users,
            n_items=total_items,
        )

    def compare_models(
        self,
        models: Dict[str, Any],
        test_data: Dict[int, Set[int]],
        train_data: Optional[Dict[int, Set[int]]] = None,
        **kwargs
    ) -> Dict[str, EvaluationResult]:
        """
        여러 모델 비교 평가

        Args:
            models: {model_name: model} 딕셔너리
            test_data: 테스트 데이터
            train_data: 학습 데이터
            **kwargs: evaluate()에 전달할 추가 인자

        Returns:
            {model_name: EvaluationResult} 딕셔너리
        """
        results = {}

        for model_name, model in models.items():
            if self.verbose:
                print(f"\n>>> {model_name} 평가 중...")

            results[model_name] = self.evaluate(
                recommender=model,
                test_data=test_data,
                train_data=train_data,
                model_name=model_name,
                **kwargs
            )

        return results


# ============================================================================
# 교차 검증
# ============================================================================

class CrossValidator:
    """
    추천 시스템 교차 검증

    시간 기반 분할 또는 랜덤 분할로 K-Fold 교차 검증 수행.

    학술 근거:
    - Time-based split이 추천 시스템에서 더 현실적 (Campos et al., 2014)
    - Leave-One-Out은 계산 비용이 높지만 정확
    """

    def __init__(
        self,
        n_folds: int = 5,
        test_ratio: float = 0.2,
        time_based: bool = True,
        random_state: int = 42,
    ):
        """
        Args:
            n_folds: 교차 검증 Fold 수
            test_ratio: 테스트 비율 (시간 기반시 마지막 N%)
            time_based: 시간 기반 분할 사용 여부
            random_state: 랜덤 시드
        """
        self.n_folds = n_folds
        self.test_ratio = test_ratio
        self.time_based = time_based
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)

    def split_user_interactions(
        self,
        interactions: Dict[int, List[Tuple[int, float, Any]]],
    ) -> List[Tuple[Dict[int, Set[int]], Dict[int, Set[int]]]]:
        """
        사용자별 상호작용을 학습/테스트로 분할

        Args:
            interactions: {user_id: [(item_id, score, timestamp), ...]}

        Returns:
            [(train_dict, test_dict), ...] for each fold
        """
        folds = []

        for fold in range(self.n_folds):
            train_data: Dict[int, Set[int]] = {}
            test_data: Dict[int, Set[int]] = {}

            for user_id, user_items in interactions.items():
                if len(user_items) < 2:
                    # 상호작용이 너무 적으면 전부 학습에
                    train_data[user_id] = {item for item, _, _ in user_items}
                    continue

                if self.time_based:
                    # 시간순 정렬 (timestamp 기준)
                    sorted_items = sorted(user_items, key=lambda x: x[2])
                    split_idx = int(len(sorted_items) * (1 - self.test_ratio))
                else:
                    # 랜덤 분할
                    indices = list(range(len(user_items)))
                    self.rng.shuffle(indices)
                    split_idx = int(len(indices) * (1 - self.test_ratio))
                    sorted_items = [user_items[i] for i in indices]

                train_items = sorted_items[:split_idx]
                test_items = sorted_items[split_idx:]

                train_data[user_id] = {item for item, _, _ in train_items}
                test_data[user_id] = {item for item, _, _ in test_items}

            folds.append((train_data, test_data))

        return folds

    def cross_validate(
        self,
        model_factory: Callable[[], Any],
        interactions: Dict[int, List[Tuple[int, float, Any]]],
        evaluator: RecommenderEvaluator,
        **kwargs
    ) -> Dict[str, float]:
        """
        교차 검증 수행

        Args:
            model_factory: 모델 생성 팩토리 함수
            interactions: 상호작용 데이터
            evaluator: 평가기
            **kwargs: 평가에 전달할 추가 인자

        Returns:
            {metric: mean_value} 평균 지표
        """
        folds = self.split_user_interactions(interactions)
        all_results: List[Dict[str, float]] = []

        for fold_idx, (train_data, test_data) in enumerate(folds):
            print(f"\n=== Fold {fold_idx + 1}/{self.n_folds} ===")

            # 모델 학습 (팩토리로 새 모델 생성)
            model = model_factory()

            # 학습 (model.fit 또는 유사 메서드 필요)
            # TODO: 모델별 학습 로직 구현 필요

            # 평가
            result = evaluator.evaluate(
                recommender=model,
                test_data=test_data,
                train_data=train_data,
                model_name=f"Fold_{fold_idx + 1}",
                **kwargs
            )

            all_results.append(result.metrics)
            print(f"Recall@10: {result.metrics.get('Recall@10', 0):.4f}")

        # 평균 계산
        mean_metrics = {}
        for metric in all_results[0].keys():
            values = [r[metric] for r in all_results if metric in r]
            mean_metrics[metric] = float(np.mean(values))
            mean_metrics[f'{metric}_std'] = float(np.std(values))

        return mean_metrics


# ============================================================================
# 벤치마크 유틸리티
# ============================================================================

def benchmark_report(
    results: Dict[str, EvaluationResult],
    output_path: Optional[str] = None,
) -> str:
    """
    벤치마크 리포트 생성

    Args:
        results: {model_name: EvaluationResult}
        output_path: 저장 경로 (없으면 반환만)

    Returns:
        마크다운 형식 리포트 문자열
    """
    lines = [
        "# 추천 시스템 벤치마크 리포트",
        "",
        f"생성 시간: {datetime.now().isoformat()}",
        "",
        "## 모델 비교",
        "",
        "| 모델 | Recall@10 | NDCG@10 | HitRate@10 | MRR@10 | Coverage |",
        "|------|-----------|---------|------------|--------|----------|",
    ]

    for model_name, result in results.items():
        m = result.metrics
        lines.append(
            f"| {model_name} | "
            f"{m.get('Recall@10', 0):.4f} | "
            f"{m.get('NDCG@10', 0):.4f} | "
            f"{m.get('HitRate@10', 0):.4f} | "
            f"{m.get('MRR@10', 0):.4f} | "
            f"{m.get('Coverage', 0):.4f} |"
        )

    lines.extend([
        "",
        "## 상세 결과",
        "",
    ])

    for model_name, result in results.items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append(result.summary())
        lines.append("")

    report = '\n'.join(lines)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

    return report


def kaggle_target_check(metrics: Dict[str, float]) -> Dict[str, bool]:
    """
    Kaggle 최상위 목표 달성 여부 확인

    목표:
    - Recall@10 ≥ 0.15
    - NDCG@10 ≥ 0.20
    - HitRate@10 ≥ 0.70
    - MRR@10 ≥ 0.25
    - Coverage ≥ 0.50
    """
    targets = {
        'Recall@10': 0.15,
        'NDCG@10': 0.20,
        'HitRate@10': 0.70,
        'MRR@10': 0.25,
        'Coverage': 0.50,
    }

    results = {}
    for metric, target in targets.items():
        actual = metrics.get(metric, 0.0)
        results[metric] = actual >= target
        print(f"{metric}: {actual:.4f} {'✓' if results[metric] else '✗'} (목표: {target})")

    return results


__all__ = [
    # 기본 지표 함수
    'compute_recall_at_k',
    'compute_precision_at_k',
    'compute_ndcg_at_k',
    'compute_hit_rate',
    'compute_mrr',
    'compute_map_at_k',
    'compute_f1_at_k',
    # 다양성/커버리지 지표
    'compute_coverage',
    'compute_diversity',
    'compute_novelty',
    # 클래스
    'EvaluationResult',
    'RecommenderEvaluator',
    'CrossValidator',
    # 유틸리티
    'benchmark_report',
    'kaggle_target_check',
]
