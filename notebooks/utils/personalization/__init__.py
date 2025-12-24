"""
개인화 추천 시스템 모듈

Kaggle 최상위 랭커 수준의 식료품 이커머스 개인화 추천 시스템
ALS 32차원 + 하이브리드 가중치 (CBF 0.7 + CF 0.3)

학술적 근거:
- Hu, Y., Koren, Y., & Volinsky, C. (2008). IEEE ICDM
- Netflix Prize (2009)
- E-commerce Conversion Benchmarks (2024)

모듈 구조:
- weight_config: 상호작용 가중치 및 Confidence 설정
- data_processor: Instacart 데이터 로드 및 희소 행렬 생성
- instacart_mapper: Instacart → SelF 상품 매핑
- als_recommender: ALS 32차원 협업 필터링
- cbf_recommender: 콘텐츠 기반 필터링
- hybrid_recommender: 하이브리드 추천기
- evaluator: 오프라인 평가 (Recall, NDCG, Hit Rate, MRR)
"""

from .weight_config import (
    InteractionWeights,
    ConfidenceWeights,
    HybridWeights,
    TimeDecayWeights,
    UserType,
    INTERACTION_WEIGHTS,
    CONFIDENCE_WEIGHTS,
    HYBRID_WEIGHTS,
    TIME_DECAY_WEIGHTS,
    compute_interaction_score,
    compute_confidence,
    compute_hybrid_score,
    compute_final_score,
)

from .data_processor import (
    InstacartDataLoader,
    InteractionMatrixBuilder,
    FeatureEngineer,
)

from .instacart_mapper import (
    AisleCategoryMapper,
    ProductMatcher,
)

from .als_recommender import (
    OptimizedALSRecommender,
    ALSEvaluator,
    KAGGLE_PARAMS,
    create_optimized_pickle,
    load_optimized_pickle,
)

from .cbf_recommender import (
    ContentBasedRecommender,
    CategorySimilarity,
    create_cbf_from_dataframe,
)

from .hybrid_recommender import (
    HybridRecommender,
    HybridStrategy,
    DynamicWeightCalculator,
    create_hybrid_recommender,
)

from .evaluator import (
    RecommenderEvaluator,
    CrossValidator,
    EvaluationResult,
    compute_recall_at_k,
    compute_precision_at_k,
    compute_ndcg_at_k,
    compute_hit_rate,
    compute_mrr,
    compute_map_at_k,
    compute_f1_at_k,
    compute_coverage,
    compute_diversity,
    compute_novelty,
    benchmark_report,
    kaggle_target_check,
)

__all__ = [
    # weight_config
    'InteractionWeights',
    'ConfidenceWeights',
    'HybridWeights',
    'TimeDecayWeights',
    'UserType',
    'INTERACTION_WEIGHTS',
    'CONFIDENCE_WEIGHTS',
    'HYBRID_WEIGHTS',
    'TIME_DECAY_WEIGHTS',
    'compute_interaction_score',
    'compute_confidence',
    'compute_hybrid_score',
    'compute_final_score',
    # data_processor
    'InstacartDataLoader',
    'InteractionMatrixBuilder',
    'FeatureEngineer',
    # instacart_mapper
    'AisleCategoryMapper',
    'ProductMatcher',
    # als_recommender
    'OptimizedALSRecommender',
    'ALSEvaluator',
    'KAGGLE_PARAMS',
    'create_optimized_pickle',
    'load_optimized_pickle',
    # cbf_recommender
    'ContentBasedRecommender',
    'CategorySimilarity',
    'create_cbf_from_dataframe',
    # hybrid_recommender
    'HybridRecommender',
    'HybridStrategy',
    'DynamicWeightCalculator',
    'create_hybrid_recommender',
    # evaluator
    'RecommenderEvaluator',
    'CrossValidator',
    'EvaluationResult',
    'compute_recall_at_k',
    'compute_precision_at_k',
    'compute_ndcg_at_k',
    'compute_hit_rate',
    'compute_mrr',
    'compute_map_at_k',
    'compute_f1_at_k',
    'compute_coverage',
    'compute_diversity',
    'compute_novelty',
    'benchmark_report',
    'kaggle_target_check',
]

__version__ = '2.0.0'
__author__ = 'SelF Team - SSAFY Class 18 Team 4'
