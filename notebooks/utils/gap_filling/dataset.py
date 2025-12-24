# -*- coding: utf-8 -*-
"""
동적 마스킹 데이터셋 모듈

Kaggle Top 전략 적용:
- Dynamic Masking: 20%~80% 랜덤 마스킹
- Shuffling: 매 epoch 순서 무작위화
- BERT-style: 80% MASK / 10% 랜덤 / 10% 유지
- Negative Sampling: Contrastive Learning
"""

import random
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset
import logging

logger = logging.getLogger(__name__)


class DynamicMaskingDataset(Dataset):
    """동적 마스킹 데이터셋

    Kaggle Top 전략:
        1. Dynamic Masking: 각 샘플마다 20%~80% 랜덤 마스킹
        2. Shuffling: 재료 순서 무작위화 (Set 특성 반영)
        3. BERT-style Masking:
           - 80%: [MASK] 토큰으로 대체
           - 10%: 랜덤 재료로 대체
           - 10%: 원본 유지

    Args:
        recipes: 레시피 리스트 (각 레시피는 토큰 ID 리스트)
        tokenizer: IngredientTokenizer 인스턴스
        max_len: 최대 시퀀스 길이
        mask_ratio_range: 마스킹 비율 범위 (min, max)
        shuffle_ingredients: 재료 순서 셔플 여부
        bert_style_masking: BERT 스타일 마스킹 적용 여부

    Example:
        >>> dataset = DynamicMaskingDataset(
        ...     recipes=encoded_recipes,
        ...     tokenizer=tokenizer,
        ...     mask_ratio_range=(0.2, 0.8)
        ... )
        >>> batch = dataset[0]
        >>> print(batch.keys())  # ['input_ids', 'attention_mask', 'labels', 'masked_positions']
    """

    def __init__(
        self,
        recipes: List[List[int]],
        tokenizer,
        max_len: int = 32,
        mask_ratio_range: Tuple[float, float] = (0.2, 0.8),
        shuffle_ingredients: bool = True,
        bert_style_masking: bool = True
    ):
        self.recipes = recipes
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.mask_ratio_range = mask_ratio_range
        self.shuffle_ingredients = shuffle_ingredients
        self.bert_style_masking = bert_style_masking

        # 특수 토큰 ID 캐싱
        self.pad_id = tokenizer.PAD_ID
        self.mask_id = tokenizer.MASK_ID
        self.cls_id = tokenizer.CLS_ID
        self.sep_id = tokenizer.SEP_ID
        self.unk_id = tokenizer.UNK_ID

        # 유효한 재료 ID 범위 (특수 토큰 제외)
        self.min_ingredient_id = 5  # 특수 토큰 이후
        self.max_ingredient_id = tokenizer.vocab_size - 1

        logger.info(
            f"DynamicMaskingDataset 초기화: "
            f"{len(recipes)}개 레시피, "
            f"mask_ratio={mask_ratio_range}, "
            f"shuffle={shuffle_ingredients}"
        )

    def __len__(self) -> int:
        return len(self.recipes)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """단일 샘플 반환

        Returns:
            Dict with:
                - input_ids: 마스킹된 입력 시퀀스 [max_len]
                - attention_mask: 어텐션 마스크 [max_len]
                - labels: 원본 토큰 ID (마스크 위치만, 나머지 -100) [max_len]
                - masked_positions: 마스킹된 위치 인덱스 [num_masked]
        """
        # 원본 레시피 복사 (특수 토큰 제외된 재료 ID 리스트)
        original_ids = self.recipes[idx].copy()

        # 1. 셔플링 (Set 특성: 순서 무관)
        if self.shuffle_ingredients:
            random.shuffle(original_ids)

        # 2. 시퀀스 구성: [CLS] + ingredients + [SEP] + [PAD]...
        max_ingredients = self.max_len - 2  # [CLS], [SEP] 자리 확보
        truncated_ids = original_ids[:max_ingredients]

        input_ids = [self.cls_id] + truncated_ids + [self.sep_id]
        seq_len = len(input_ids)

        # 패딩
        pad_len = self.max_len - seq_len
        input_ids = input_ids + [self.pad_id] * pad_len

        # 어텐션 마스크 (패딩 위치 = 0)
        attention_mask = [1] * seq_len + [0] * pad_len

        # 3. Dynamic Masking
        # 마스킹 비율 랜덤 선택
        mask_ratio = random.uniform(*self.mask_ratio_range)

        # 마스킹 대상: [CLS], [SEP], [PAD] 제외한 재료 토큰들
        # 인덱스 1 ~ seq_len-2 (0은 CLS, seq_len-1은 SEP)
        ingredient_positions = list(range(1, seq_len - 1))
        num_to_mask = max(1, int(len(ingredient_positions) * mask_ratio))
        masked_positions = sorted(random.sample(ingredient_positions, num_to_mask))

        # 라벨 초기화 (-100은 loss 계산에서 제외)
        labels = [-100] * self.max_len

        # 4. 마스킹 적용
        for pos in masked_positions:
            labels[pos] = input_ids[pos]  # 원본 저장

            if self.bert_style_masking:
                # BERT-style: 80% MASK, 10% random, 10% keep
                prob = random.random()
                if prob < 0.8:
                    input_ids[pos] = self.mask_id
                elif prob < 0.9:
                    # 랜덤 재료로 대체
                    input_ids[pos] = random.randint(
                        self.min_ingredient_id,
                        self.max_ingredient_id
                    )
                # else: 10% 원본 유지
            else:
                # 단순 마스킹
                input_ids[pos] = self.mask_id

        return {
            'input_ids': torch.tensor(input_ids, dtype=torch.long),
            'attention_mask': torch.tensor(attention_mask, dtype=torch.long),
            'labels': torch.tensor(labels, dtype=torch.long),
            'masked_positions': torch.tensor(masked_positions, dtype=torch.long),
        }

    def get_sample_info(self, idx: int) -> Dict:
        """디버깅용: 샘플 정보 반환"""
        original = self.recipes[idx]
        sample = self[idx]

        return {
            'original_ingredients': self.tokenizer.decode(original),
            'num_ingredients': len(original),
            'masked_input': self.tokenizer.decode(sample['input_ids'].tolist()),
            'num_masked': len(sample['masked_positions']),
            'mask_ratio': len(sample['masked_positions']) / max(1, len(original)),
        }


class NegativeSamplingDataset(Dataset):
    """Negative Sampling 데이터셋

    Contrastive Learning을 위한 데이터셋
    - Positive: 원본 레시피
    - Negative: 잘못된 재료가 포함된 레시피

    전략:
        1. In-batch Negatives: 다른 레시피의 재료 삽입
        2. Random Negatives: 랜덤 재료 삽입
        3. Hard Negatives: 동일 카테고리 내 다른 재료 (선택적)

    Args:
        recipes: 레시피 리스트 (각 레시피는 토큰 ID 리스트)
        tokenizer: IngredientTokenizer 인스턴스
        max_len: 최대 시퀀스 길이
        num_negatives: 각 positive당 negative 샘플 수
        negative_ratio: 교체할 재료 비율

    Example:
        >>> dataset = NegativeSamplingDataset(
        ...     recipes=encoded_recipes,
        ...     tokenizer=tokenizer,
        ...     num_negatives=3
        ... )
    """

    def __init__(
        self,
        recipes: List[List[int]],
        tokenizer,
        max_len: int = 32,
        num_negatives: int = 3,
        negative_ratio: float = 0.3
    ):
        self.recipes = recipes
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.num_negatives = num_negatives
        self.negative_ratio = negative_ratio

        # 특수 토큰 ID
        self.pad_id = tokenizer.PAD_ID
        self.cls_id = tokenizer.CLS_ID
        self.sep_id = tokenizer.SEP_ID

        # 전체 재료 풀 구축 (negative 샘플링용)
        self.all_ingredients = set()
        for recipe in recipes:
            self.all_ingredients.update(recipe)
        self.all_ingredients = list(self.all_ingredients)

        logger.info(
            f"NegativeSamplingDataset 초기화: "
            f"{len(recipes)}개 레시피, "
            f"{len(self.all_ingredients)}개 재료, "
            f"num_negatives={num_negatives}"
        )

    def __len__(self) -> int:
        return len(self.recipes)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """Positive 및 Negative 샘플 반환

        Returns:
            Dict with:
                - positive_ids: 원본 레시피 [max_len]
                - positive_mask: 어텐션 마스크 [max_len]
                - negative_ids: Negative 레시피들 [num_negatives, max_len]
                - negative_mask: 어텐션 마스크 [num_negatives, max_len]
                - labels: Binary 라벨 (1=positive, 0=negative) [1 + num_negatives]
        """
        original = self.recipes[idx].copy()

        # Positive 샘플 인코딩
        positive_ids, positive_mask = self._encode_recipe(original)

        # Negative 샘플 생성
        negative_ids_list = []
        negative_mask_list = []

        for _ in range(self.num_negatives):
            negative = self._create_negative_sample(original, idx)
            neg_ids, neg_mask = self._encode_recipe(negative)
            negative_ids_list.append(neg_ids)
            negative_mask_list.append(neg_mask)

        # 라벨: positive=1, negatives=0
        labels = [1] + [0] * self.num_negatives

        return {
            'positive_ids': torch.tensor(positive_ids, dtype=torch.long),
            'positive_mask': torch.tensor(positive_mask, dtype=torch.long),
            'negative_ids': torch.tensor(negative_ids_list, dtype=torch.long),
            'negative_mask': torch.tensor(negative_mask_list, dtype=torch.long),
            'labels': torch.tensor(labels, dtype=torch.float),
        }

    def _encode_recipe(self, ingredients: List[int]) -> Tuple[List[int], List[int]]:
        """레시피를 시퀀스로 인코딩"""
        max_ingredients = self.max_len - 2
        truncated = ingredients[:max_ingredients]

        ids = [self.cls_id] + truncated + [self.sep_id]
        seq_len = len(ids)

        pad_len = self.max_len - seq_len
        ids = ids + [self.pad_id] * pad_len
        mask = [1] * seq_len + [0] * pad_len

        return ids, mask

    def _create_negative_sample(
        self,
        original: List[int],
        original_idx: int
    ) -> List[int]:
        """Negative 샘플 생성

        전략:
            1. 50%: 다른 레시피에서 재료 가져오기 (In-batch)
            2. 50%: 랜덤 재료로 교체 (Random)
        """
        negative = original.copy()

        # 교체할 재료 수
        num_to_replace = max(1, int(len(negative) * self.negative_ratio))
        positions_to_replace = random.sample(range(len(negative)), num_to_replace)

        for pos in positions_to_replace:
            if random.random() < 0.5:
                # In-batch Negative: 다른 레시피에서 가져오기
                other_idx = random.randint(0, len(self.recipes) - 1)
                if other_idx != original_idx and self.recipes[other_idx]:
                    other_recipe = self.recipes[other_idx]
                    negative[pos] = random.choice(other_recipe)
            else:
                # Random Negative: 현재 레시피에 없는 재료로 교체
                candidates = [
                    ing for ing in self.all_ingredients
                    if ing not in original
                ]
                if candidates:
                    negative[pos] = random.choice(candidates)

        return negative

    def create_contrastive_batch(
        self,
        batch_size: int
    ) -> Dict[str, torch.Tensor]:
        """Contrastive Learning 배치 생성

        모든 샘플 쌍에 대해 positive/negative 관계 정의
        """
        indices = random.sample(range(len(self)), min(batch_size, len(self)))

        all_ids = []
        all_masks = []

        for idx in indices:
            sample = self[idx]
            all_ids.append(sample['positive_ids'])
            all_masks.append(sample['positive_mask'])

        # N x N 유사도 행렬에서 대각선이 positive
        ids_tensor = torch.stack(all_ids)
        mask_tensor = torch.stack(all_masks)

        # 라벨: 대각선 = 1, 나머지 = 0
        n = len(indices)
        labels = torch.eye(n)

        return {
            'input_ids': ids_tensor,
            'attention_mask': mask_tensor,
            'labels': labels,
        }


class LeaveOneOutDataset(Dataset):
    """Leave-One-Out 평가용 데이터셋

    각 레시피의 각 재료를 한 번씩 마스킹하여 평가

    Args:
        recipes: 레시피 리스트 (각 레시피는 토큰 ID 리스트)
        tokenizer: IngredientTokenizer 인스턴스
        max_len: 최대 시퀀스 길이

    Example:
        >>> dataset = LeaveOneOutDataset(recipes, tokenizer)
        >>> # 총 샘플 수 = sum(len(recipe) for recipe in recipes)
    """

    def __init__(
        self,
        recipes: List[List[int]],
        tokenizer,
        max_len: int = 32
    ):
        self.recipes = recipes
        self.tokenizer = tokenizer
        self.max_len = max_len

        # 특수 토큰 ID
        self.pad_id = tokenizer.PAD_ID
        self.mask_id = tokenizer.MASK_ID
        self.cls_id = tokenizer.CLS_ID
        self.sep_id = tokenizer.SEP_ID

        # (recipe_idx, ingredient_idx) 쌍 생성
        self.samples = []
        for recipe_idx, recipe in enumerate(recipes):
            for ing_idx in range(len(recipe)):
                self.samples.append((recipe_idx, ing_idx))

        logger.info(
            f"LeaveOneOutDataset 초기화: "
            f"{len(recipes)}개 레시피, "
            f"{len(self.samples)}개 평가 샘플"
        )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """단일 평가 샘플 반환

        Returns:
            Dict with:
                - input_ids: 1개 재료가 마스킹된 시퀀스 [max_len]
                - attention_mask: 어텐션 마스크 [max_len]
                - target_id: 마스킹된 재료의 실제 ID [1]
                - masked_position: 마스킹된 위치 [1]
                - recipe_idx: 원본 레시피 인덱스
        """
        recipe_idx, ing_idx = self.samples[idx]
        original = self.recipes[recipe_idx].copy()

        # 타겟 저장
        target_id = original[ing_idx]

        # 시퀀스 구성
        max_ingredients = self.max_len - 2
        truncated = original[:max_ingredients]

        # 마스킹 위치 조정 (truncation 고려)
        if ing_idx >= len(truncated):
            # truncation으로 인해 타겟이 잘린 경우
            # 마지막 재료를 마스킹
            ing_idx = len(truncated) - 1
            target_id = truncated[ing_idx]

        # 마스킹 적용
        truncated[ing_idx] = self.mask_id

        # [CLS] + ingredients + [SEP]
        input_ids = [self.cls_id] + truncated + [self.sep_id]
        seq_len = len(input_ids)

        # 마스킹 위치 (CLS 이후이므로 +1)
        masked_position = ing_idx + 1

        # 패딩
        pad_len = self.max_len - seq_len
        input_ids = input_ids + [self.pad_id] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len

        return {
            'input_ids': torch.tensor(input_ids, dtype=torch.long),
            'attention_mask': torch.tensor(attention_mask, dtype=torch.long),
            'target_id': torch.tensor(target_id, dtype=torch.long),
            'masked_position': torch.tensor(masked_position, dtype=torch.long),
            'recipe_idx': torch.tensor(recipe_idx, dtype=torch.long),
        }


def collate_fn(batch: List[Dict]) -> Dict[str, torch.Tensor]:
    """DataLoader용 collate 함수

    Args:
        batch: __getitem__에서 반환된 딕셔너리 리스트

    Returns:
        배치된 텐서 딕셔너리
    """
    result = {}
    # 가변 길이 필드 (스택 불가)
    variable_length_keys = {'masked_positions'}

    for key in batch[0].keys():
        if isinstance(batch[0][key], torch.Tensor):
            if key in variable_length_keys:
                # 가변 길이 텐서는 리스트로 유지
                result[key] = [item[key] for item in batch]
            else:
                # 고정 길이 텐서는 스택
                result[key] = torch.stack([item[key] for item in batch])
        else:
            result[key] = [item[key] for item in batch]
    return result
