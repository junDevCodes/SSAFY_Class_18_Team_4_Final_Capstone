# -*- coding: utf-8 -*-
"""
레시피 Gap Filling 모듈

Masked Set Transformer 기반 레시피 재료 추천 시스템

주요 컴포넌트:
- normalizer: 재료 정규화 및 파싱
- tokenizer: 재료 토크나이저
- dataset: 동적 마스킹 데이터셋
- model: Masked Set Transformer 모델
- trainer: 학습 트레이너
- evaluator: Leave-One-Out 평가기
"""

from .normalizer import IngredientParser, MultiStageNormalizer
from .tokenizer import IngredientTokenizer
from .dataset import DynamicMaskingDataset, NegativeSamplingDataset, LeaveOneOutDataset, collate_fn
from .model import MaskedSetTransformer, SetTransformerEncoder, ContrastiveSetTransformer
from .trainer import Trainer
from .evaluator import LeaveOneOutEvaluator, RecipeGapFillingModel, NON_PURCHASABLE_INGREDIENTS

__all__ = [
    # 정규화
    'IngredientParser',
    'MultiStageNormalizer',
    # 토크나이저
    'IngredientTokenizer',
    # 데이터셋
    'DynamicMaskingDataset',
    'NegativeSamplingDataset',
    'LeaveOneOutDataset',
    'collate_fn',
    # 모델
    'MaskedSetTransformer',
    'SetTransformerEncoder',
    'ContrastiveSetTransformer',
    # 학습
    'Trainer',
    # 평가
    'LeaveOneOutEvaluator',
    'RecipeGapFillingModel',
    # Kaggle Top 전략: 비구매 재료 필터링
    'NON_PURCHASABLE_INGREDIENTS',
]

__version__ = '2.1.0'  # Stop Words 필터링 추가
