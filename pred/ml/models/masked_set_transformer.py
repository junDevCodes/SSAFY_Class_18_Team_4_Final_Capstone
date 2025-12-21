# -*- coding: utf-8 -*-
"""
Masked Set Transformer 모델 (프로덕션용)

notebooks/utils/gap_filling/model.py 에서 추론에 필요한 부분만 추출

핵심 특징:
- Positional Encoding 제거 (재료는 순서 무관한 Set)
- BERT-style Masked Language Modeling
- 256차원 임베딩
"""

import math
from typing import Dict, Optional, Set, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from core.logging import get_logger

logger = get_logger(__name__)


class SetTransformerEncoder(nn.Module):
    """Set Transformer Encoder (Positional Encoding 제거)"""

    def __init__(
        self,
        d_model: int = 256,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 1024,
        dropout: float = 0.1,
        activation: str = 'gelu'
    ):
        super().__init__()

        self.d_model = d_model

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation=activation,
            batch_first=True,
            norm_first=True,
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_layers,
            enable_nested_tensor=False
        )

        self.layer_norm = nn.LayerNorm(d_model)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        if attention_mask is not None:
            src_key_padding_mask = (attention_mask == 0)
        else:
            src_key_padding_mask = None

        output = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        output = self.layer_norm(output)
        return output


class MaskedSetTransformer(nn.Module):
    """Masked Set Transformer (프로덕션용)"""

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 1024,
        dropout: float = 0.1,
        pad_id: int = 0
    ):
        super().__init__()

        self.vocab_size = vocab_size
        self.d_model = d_model
        self.pad_id = pad_id

        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
        self.embed_scale = math.sqrt(d_model)
        self.embed_dropout = nn.Dropout(dropout)

        self.encoder = SetTransformerEncoder(
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            d_ff=d_ff,
            dropout=dropout
        )

        self.mlm_head = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, vocab_size)
        )

        # Weight Tying
        self.mlm_head[-1].weight = self.embedding.weight

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        x = self.embedding(input_ids)
        x = x * self.embed_scale
        x = self.embed_dropout(x)

        hidden_states = self.encoder(x, attention_mask)
        logits = self.mlm_head(hidden_states)

        result = {
            'logits': logits,
            'hidden_states': hidden_states,
        }

        if labels is not None:
            loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
            loss = loss_fn(logits.view(-1, self.vocab_size), labels.view(-1))
            result['loss'] = loss

        return result


# ============================================================
# 비구매 재료 (Stop Words) 필터링
# ============================================================
NON_PURCHASABLE_INGREDIENTS: Set[str] = {
    # 기본 양념 (대부분 집에 보유)
    '물', '뜨거운물', '찬물', '끓는물', '냉수', '온수', '미지근한물',
    '소금', '천일염', '꽃소금', '소금물', '굵은소금',
    '설탕', '흑설탕', '백설탕', '황설탕',
    '후추', '흑후추', '백후추', '후춧가루', '통후추',
    '식용유', '포도씨유', '카놀라유', '해바라기유', '콩기름',
    '참기름', '들기름',
    '간장', '진간장', '국간장', '양조간장', '조선간장',
    '된장', '재래된장', '쌈장',
    '고추장',
    '식초', '현미식초', '사과식초', '발사믹식초',
    '맛술', '청주', '미림', '소주', '맛소금',
    '전분', '녹말', '감자전분', '옥수수전분',

    # 다진 양념
    '다진마늘', '다진생강', '다진파', '다진양파',
    '마늘', '통마늘', '마늘가루',
    '생강', '생강가루', '생강즙',

    # 깨 / 기타 저가 양념
    '통깨', '깨소금', '검은깨', '볶은깨', '참깨',
    '파슬리', '파슬리가루',
    '계피', '계피가루', '시나몬',

    # 육수 / 물 기반
    '육수', '멸치육수', '다시마물', '채소육수', '사골육수',
    '다시다', '치킨스톡', '비프스톡', '쇠고기다시다',

    # 기타 극저가 재료
    '밀가루', '부침가루', '튀김가루',
    '빵가루', '달걀물',
}


class RecipeGapFillingModelV2:
    """프로덕션용 레시피 Gap Filling 모델 래퍼 (v2)

    Pickle 딕셔너리로부터 모델을 복원하여 추론 수행

    Kaggle Top 전략 적용:
    - Stop Words 필터링: 비구매 재료 (물, 소금 등) 자동 제외
    - IDF 가중치: 희귀 재료 우선 추천
    """

    # 특수 토큰 ID
    PAD_ID = 0
    MASK_ID = 1
    UNK_ID = 2
    CLS_ID = 3
    SEP_ID = 4

    def __init__(
        self,
        model: MaskedSetTransformer,
        vocab: Dict[str, int],
        token_freq: Dict[str, int],
        token_idf: Optional[Dict[str, float]] = None,
        device: str = 'cpu',
        filter_non_purchasable: bool = True,
        use_idf_weighting: bool = True,
        idf_weight_strength: float = 0.3
    ):
        """초기화

        Args:
            model: MaskedSetTransformer 인스턴스
            vocab: 토큰 → ID 딕셔너리
            token_freq: 토큰 빈도 딕셔너리
            token_idf: 토큰 IDF 딕셔너리 (옵션)
            device: 추론 디바이스
            filter_non_purchasable: 비구매 재료 필터링 여부
            use_idf_weighting: IDF 가중 추천 사용 여부
            idf_weight_strength: IDF 가중치 강도
        """
        self.model = model.to(device)
        self.model.eval()
        self.device = device

        self.vocab = vocab
        self.id2token = {v: k for k, v in vocab.items()}
        self.token_freq = token_freq
        self.token_idf = token_idf or {}

        self.filter_non_purchasable = filter_non_purchasable
        self.use_idf_weighting = use_idf_weighting
        self.idf_weight_strength = idf_weight_strength

        # 비구매 재료 ID 캐싱
        self._non_purchasable_ids: Set[int] = set()
        if filter_non_purchasable:
            for ing_name in NON_PURCHASABLE_INGREDIENTS:
                ing_id = self.vocab.get(ing_name, self.UNK_ID)
                if ing_id != self.UNK_ID:
                    self._non_purchasable_ids.add(ing_id)

        # IDF 텐서 캐싱
        self._idf_tensor: Optional[torch.Tensor] = None
        if use_idf_weighting and token_idf:
            idf_weights = []
            for i in range(len(vocab)):
                token = self.id2token.get(i, '')
                idf = token_idf.get(token, 1.0)
                idf_weights.append(idf)
            self._idf_tensor = torch.tensor(idf_weights, dtype=torch.float32, device=device)

        logger.info(
            f"RecipeGapFillingModelV2 초기화: "
            f"vocab_size={len(vocab)}, device={device}, "
            f"filter_non_purchasable={filter_non_purchasable}"
        )

    def get_token_id(self, token: str) -> int:
        """토큰 → ID"""
        return self.vocab.get(token, self.UNK_ID)

    def get_token(self, token_id: int) -> str:
        """ID → 토큰"""
        return self.id2token.get(token_id, '[UNK]')

    def recommend(
        self,
        given_ingredients: List[str],
        top_k: int = 10,
        exclude_given: bool = True,
        max_len: int = 32
    ) -> List[str]:
        """주어진 재료를 기반으로 추천 재료 반환

        Args:
            given_ingredients: 주어진 재료명 리스트
            top_k: 반환할 추천 개수
            exclude_given: 주어진 재료 제외 여부
            max_len: 최대 시퀀스 길이

        Returns:
            추천 재료명 리스트
        """
        # 1. 토큰화
        ingredient_ids = [self.get_token_id(ing) for ing in given_ingredients]
        valid_ids = [ing_id for ing_id in ingredient_ids if ing_id != self.UNK_ID]

        if not valid_ids:
            logger.warning("유효한 재료가 없습니다")
            return []

        # 2. 시퀀스 구성: [CLS] + ingredients + [MASK] + [SEP]
        max_ingredients = max_len - 3
        truncated = valid_ids[:max_ingredients]

        input_ids = [self.CLS_ID] + truncated + [self.MASK_ID] + [self.SEP_ID]
        seq_len = len(input_ids)
        mask_position = len(truncated) + 1

        # 패딩
        pad_len = max_len - seq_len
        input_ids = input_ids + [self.PAD_ID] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len

        # 3. 텐서 변환
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        mask_tensor = torch.tensor([attention_mask], dtype=torch.long, device=self.device)

        # 4. 예측
        with torch.no_grad():
            output = self.model(input_tensor, mask_tensor)
            logits = output['logits'][0, mask_position]

            # 주어진 재료 제외
            if exclude_given:
                for ing_id in valid_ids:
                    logits[ing_id] = float('-inf')

            # 특수 토큰 제외
            for special_id in [self.PAD_ID, self.MASK_ID, self.UNK_ID, self.CLS_ID, self.SEP_ID]:
                logits[special_id] = float('-inf')

            # 비구매 재료 필터링
            if self.filter_non_purchasable:
                for non_purch_id in self._non_purchasable_ids:
                    logits[non_purch_id] = float('-inf')

            # IDF 가중치 적용
            if self.use_idf_weighting and self._idf_tensor is not None:
                idf_normalized = (self._idf_tensor - self._idf_tensor.min()) / \
                                (self._idf_tensor.max() - self._idf_tensor.min() + 1e-8)
                logits = logits + self.idf_weight_strength * idf_normalized

            # Top-K
            top_k_probs, top_k_ids = torch.topk(logits, k=min(top_k * 2, logits.size(-1)))

        # 5. 디코딩
        recommendations = []
        for idx in top_k_ids:
            token = self.get_token(idx.item())
            if token != '[UNK]':
                recommendations.append(token)
            if len(recommendations) >= top_k:
                break

        return recommendations

    @classmethod
    def from_pickle_dict(
        cls,
        pickle_data: Dict,
        device: str = 'cpu'
    ) -> 'RecipeGapFillingModelV2':
        """Pickle 딕셔너리로부터 모델 생성

        Args:
            pickle_data: model_loader가 로드한 딕셔너리
            device: 추론 디바이스

        Returns:
            RecipeGapFillingModelV2 인스턴스
        """
        # 모델 설정 추출
        model_config = pickle_data.get('model_config', {})
        vocab_size = model_config.get('vocab_size', 5000)
        d_model = model_config.get('d_model', 256)
        pad_id = model_config.get('pad_id', 0)

        # 모델 생성 및 가중치 로드
        model = MaskedSetTransformer(
            vocab_size=vocab_size,
            d_model=d_model,
            pad_id=pad_id
        )
        model.load_state_dict(pickle_data['model_state_dict'])

        # 토크나이저 정보
        vocab = pickle_data.get('tokenizer_vocab', {})
        token_freq = pickle_data.get('tokenizer_freq', {})
        token_idf = pickle_data.get('tokenizer_idf', {})

        logger.info(
            f"Pickle에서 v2 모델 로드: "
            f"vocab_size={vocab_size}, d_model={d_model}"
        )

        return cls(
            model=model,
            vocab=vocab,
            token_freq=token_freq,
            token_idf=token_idf,
            device=device
        )

    def __repr__(self) -> str:
        return f"RecipeGapFillingModelV2(vocab_size={len(self.vocab)}, device={self.device})"
