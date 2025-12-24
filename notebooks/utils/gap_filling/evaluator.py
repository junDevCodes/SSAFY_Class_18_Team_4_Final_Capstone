# -*- coding: utf-8 -*-
"""
Leave-One-Out 평가기 및 프로덕션 래퍼 모듈

평가 전략:
- Leave-One-Out: 각 레시피의 각 재료를 순회하며 평가
- Hit@K, MRR, Coverage 메트릭
- Head/Torso/Tail 별 성능 분석
- Stop Words 필터링 (비구매 재료 제외)
- IDF 가중치 적용
"""

import pickle
from typing import Dict, List, Optional, Tuple, Union, Set
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

# ============================================================
# Kaggle Top Solution: 비구매 재료 (Stop Words) 필터링
# 참고: https://towardsdatascience.com/building-a-recipe-recommendation-system-297c229dda7b/
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

    # 다진 양념 (이미 준비된 재료)
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


class LeaveOneOutEvaluator:
    """Leave-One-Out 평가기

    각 레시피의 각 재료를 한 번씩 마스킹하고 예측하여 평가

    평가 메트릭:
        - Hit@K: 상위 K개 예측에 정답이 포함된 비율
        - MRR (Mean Reciprocal Rank): 정답 순위의 역수 평균
        - Coverage: 예측된 고유 재료 수 / 전체 재료 수

    Args:
        model: MaskedSetTransformer 모델
        tokenizer: IngredientTokenizer 인스턴스
        device: 평가 디바이스

    Example:
        >>> evaluator = LeaveOneOutEvaluator(model, tokenizer, device='cuda')
        >>> metrics = evaluator.evaluate_dataset(recipes, k_values=[1, 5, 10])
        >>> print(f"Hit@5: {metrics['hit_at_5']:.2f}%")
    """

    def __init__(
        self,
        model,
        tokenizer,
        device: str = 'cuda'
    ):
        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.device = device

        # 특수 토큰 ID
        self.mask_id = tokenizer.MASK_ID
        self.pad_id = tokenizer.PAD_ID
        self.cls_id = tokenizer.CLS_ID
        self.sep_id = tokenizer.SEP_ID

    def evaluate_single(
        self,
        recipe: List[int],
        masked_idx: int,
        max_len: int = 32,
        top_k: int = 10
    ) -> Tuple[int, List[int]]:
        """단일 마스킹 샘플 평가

        Args:
            recipe: 재료 ID 리스트 (특수 토큰 제외)
            masked_idx: 마스킹할 재료 인덱스
            max_len: 최대 시퀀스 길이
            top_k: 예측할 상위 K개

        Returns:
            (타겟 ID, Top-K 예측 ID 리스트)
        """
        self.model.eval()

        # 타겟 저장
        target_id = recipe[masked_idx]

        # 마스킹된 시퀀스 생성
        masked_recipe = recipe.copy()
        masked_recipe[masked_idx] = self.mask_id

        # 시퀀스 구성: [CLS] + ingredients + [SEP]
        max_ingredients = max_len - 2
        truncated = masked_recipe[:max_ingredients]

        input_ids = [self.cls_id] + truncated + [self.sep_id]
        seq_len = len(input_ids)

        # 마스킹 위치 (CLS 이후)
        masked_position = min(masked_idx, len(truncated) - 1) + 1

        # 패딩
        pad_len = max_len - seq_len
        input_ids = input_ids + [self.pad_id] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len

        # 텐서 변환
        input_ids = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        attention_mask = torch.tensor([attention_mask], dtype=torch.long, device=self.device)

        # 예측
        with torch.no_grad():
            output = self.model(input_ids, attention_mask)
            logits = output['logits'][0, masked_position]  # [vocab_size]

            # Top-K 예측
            top_k_probs, top_k_ids = torch.topk(logits, k=top_k)
            predictions = top_k_ids.cpu().tolist()

        return target_id, predictions

    def evaluate_dataset(
        self,
        recipes: List[List[int]],
        k_values: List[int] = [1, 5, 10],
        max_len: int = 32,
        show_progress: bool = True
    ) -> Dict[str, float]:
        """전체 데이터셋 Leave-One-Out 평가

        Args:
            recipes: 레시피 리스트 (각 레시피는 재료 ID 리스트)
            k_values: 평가할 K 값들
            max_len: 최대 시퀀스 길이
            show_progress: 진행률 표시 여부

        Returns:
            평가 메트릭 딕셔너리
        """
        self.model.eval()

        # 메트릭 초기화
        max_k = max(k_values)
        hits = {k: 0 for k in k_values}
        reciprocal_ranks = []
        all_predictions = set()
        total_samples = 0

        # (recipe_idx, ingredient_idx) 쌍 생성
        samples = []
        for recipe_idx, recipe in enumerate(recipes):
            for ing_idx in range(len(recipe)):
                samples.append((recipe_idx, ing_idx))

        # 진행률 표시
        iterator = tqdm(samples, desc="Leave-One-Out 평가") if show_progress else samples

        for recipe_idx, ing_idx in iterator:
            recipe = recipes[recipe_idx]
            target_id, predictions = self.evaluate_single(
                recipe, ing_idx, max_len, max_k
            )

            # Hit@K 계산
            for k in k_values:
                if target_id in predictions[:k]:
                    hits[k] += 1

            # MRR 계산
            if target_id in predictions:
                rank = predictions.index(target_id) + 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

            # Coverage 계산용
            all_predictions.update(predictions[:5])
            total_samples += 1

        # 메트릭 계산
        metrics = {}
        for k in k_values:
            metrics[f'hit_at_{k}'] = hits[k] / total_samples * 100

        metrics['mrr'] = np.mean(reciprocal_ranks)
        metrics['coverage'] = len(all_predictions) / self.tokenizer.num_ingredients * 100
        metrics['total_samples'] = total_samples

        logger.info(
            f"Leave-One-Out 평가 완료: "
            f"Hit@1={metrics['hit_at_1']:.2f}%, "
            f"Hit@5={metrics['hit_at_5']:.2f}%, "
            f"Hit@10={metrics['hit_at_10']:.2f}%, "
            f"MRR={metrics['mrr']:.4f}"
        )

        return metrics

    def evaluate_by_frequency(
        self,
        recipes: List[List[int]],
        freq_bins: Dict[str, Tuple[int, int]] = None,
        k: int = 5,
        max_len: int = 32
    ) -> Dict[str, Dict[str, float]]:
        """빈도 구간별 성능 분석 (Head/Torso/Tail)

        Args:
            recipes: 레시피 리스트
            freq_bins: 빈도 구간 정의 {'head': (1000, inf), 'torso': (100, 1000), 'tail': (0, 100)}
            k: 평가할 K 값
            max_len: 최대 시퀀스 길이

        Returns:
            구간별 메트릭
        """
        if freq_bins is None:
            freq_bins = {
                'head': (1000, float('inf')),
                'torso': (100, 1000),
                'tail': (0, 100)
            }

        # 구간별 카운터 초기화
        bin_hits = {bin_name: 0 for bin_name in freq_bins}
        bin_totals = {bin_name: 0 for bin_name in freq_bins}

        for recipe in tqdm(recipes, desc="빈도별 평가"):
            for ing_idx, ing_id in enumerate(recipe):
                # 재료 빈도 확인
                ing_token = self.tokenizer.get_token(ing_id)
                freq = self.tokenizer.get_frequency(ing_token)

                # 해당 구간 찾기
                for bin_name, (min_freq, max_freq) in freq_bins.items():
                    if min_freq <= freq < max_freq:
                        target_id, predictions = self.evaluate_single(
                            recipe, ing_idx, max_len, k
                        )
                        if target_id in predictions:
                            bin_hits[bin_name] += 1
                        bin_totals[bin_name] += 1
                        break

        # 결과 계산
        results = {}
        for bin_name in freq_bins:
            if bin_totals[bin_name] > 0:
                hit_rate = bin_hits[bin_name] / bin_totals[bin_name] * 100
            else:
                hit_rate = 0.0
            results[bin_name] = {
                f'hit_at_{k}': hit_rate,
                'total': bin_totals[bin_name]
            }

        logger.info(f"빈도별 성능: {results}")
        return results


class RecipeGapFillingModel:
    """프로덕션용 레시피 Gap Filling 모델 래퍼

    pred/ 서비스와 호환되는 인터페이스 제공

    Kaggle Top 전략 적용:
    - Stop Words 필터링: 비구매 재료 (물, 소금 등) 자동 제외
    - IDF 가중치: 희귀 재료 우선 추천

    참고: https://towardsdatascience.com/building-a-recipe-recommendation-system-297c229dda7b/

    Methods:
        recommend(given_ingredients, top_k=10) -> List[str]

    Example:
        >>> model = RecipeGapFillingModel.load('pred/models/recipe_gapfilling_v2.pkl')
        >>> recommendations = model.recommend(['돼지고기', '양파'], top_k=5)
        >>> print(recommendations)  # ['대파', '고추', '청양고추', '깻잎', '버섯']
        >>> # 참고: '간장', '소금', '마늘' 등 비구매 재료는 자동 제외됨
    """

    def __init__(
        self,
        model,
        tokenizer,
        normalizer=None,
        device: str = 'cuda',
        filter_non_purchasable: bool = True,
        use_idf_weighting: bool = True,
        idf_weight_strength: float = 0.3
    ):
        """초기화

        Args:
            model: 학습된 MaskedSetTransformer
            tokenizer: IngredientTokenizer
            normalizer: MultiStageNormalizer (선택)
            device: 추론 디바이스
            filter_non_purchasable: 비구매 재료 필터링 여부 (기본: True)
            use_idf_weighting: IDF 가중 추천 사용 여부 (기본: True)
            idf_weight_strength: IDF 가중치 강도 (0.0~1.0, 기본: 0.3)
        """
        self.model = model
        self.tokenizer = tokenizer
        self.normalizer = normalizer
        self.device = device
        self.filter_non_purchasable = filter_non_purchasable
        self.use_idf_weighting = use_idf_weighting
        self.idf_weight_strength = idf_weight_strength

        # 모델을 디바이스로 이동 및 평가 모드
        if hasattr(model, 'to'):
            self.model = model.to(device)
        if hasattr(model, 'eval'):
            self.model.eval()

        # 특수 토큰 ID
        self.mask_id = tokenizer.MASK_ID
        self.pad_id = tokenizer.PAD_ID
        self.cls_id = tokenizer.CLS_ID
        self.sep_id = tokenizer.SEP_ID

        # 비구매 재료 ID 캐싱 (성능 최적화)
        self._non_purchasable_ids: Set[int] = set()
        if filter_non_purchasable:
            for ing_name in NON_PURCHASABLE_INGREDIENTS:
                ing_id = tokenizer.get_token_id(ing_name)
                if ing_id != tokenizer.UNK_ID:
                    self._non_purchasable_ids.add(ing_id)
            logger.info(f"비구매 재료 필터링 활성화: {len(self._non_purchasable_ids)}개 재료 제외")

        # IDF 가중치 텐서 캐싱
        self._idf_tensor = None
        if use_idf_weighting and tokenizer.token_idf:
            self._idf_tensor = tokenizer.get_idf_tensor(device=device)
            logger.info(f"IDF 가중 추천 활성화: strength={idf_weight_strength}")

        logger.info(f"RecipeGapFillingModel 초기화: device={device}")

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

        Example:
            >>> recommendations = model.recommend(['돼지고기', '양파', '마늘'], top_k=5)
        """
        # 1. 정규화 (normalizer가 있는 경우)
        if self.normalizer:
            normalized = self.normalizer.normalize_list(given_ingredients)
        else:
            normalized = given_ingredients

        # 2. 토큰화
        ingredient_ids = [
            self.tokenizer.get_token_id(ing)
            for ing in normalized
        ]

        # UNK 필터링 (옵션)
        valid_ids = [
            ing_id for ing_id in ingredient_ids
            if ing_id != self.tokenizer.UNK_ID
        ]

        if not valid_ids:
            logger.warning("유효한 재료가 없습니다")
            return []

        # 3. 시퀀스 구성: [CLS] + ingredients + [MASK] + [SEP]
        # 마스크 위치에서 예측
        max_ingredients = max_len - 3  # CLS, MASK, SEP
        truncated = valid_ids[:max_ingredients]

        input_ids = [self.cls_id] + truncated + [self.mask_id] + [self.sep_id]
        seq_len = len(input_ids)
        mask_position = len(truncated) + 1  # MASK 위치

        # 패딩
        pad_len = max_len - seq_len
        input_ids = input_ids + [self.pad_id] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len

        # 4. 텐서 변환
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        mask_tensor = torch.tensor([attention_mask], dtype=torch.long, device=self.device)

        # 5. 예측
        with torch.no_grad():
            output = self.model(input_tensor, mask_tensor)
            logits = output['logits'][0, mask_position]  # [vocab_size]

            # 주어진 재료 제외
            if exclude_given:
                for ing_id in valid_ids:
                    logits[ing_id] = float('-inf')

            # 특수 토큰 제외
            for special_id in [self.pad_id, self.mask_id, self.tokenizer.UNK_ID,
                               self.cls_id, self.sep_id]:
                logits[special_id] = float('-inf')

            # Kaggle Top 전략: 비구매 재료 필터링
            if self.filter_non_purchasable:
                for non_purch_id in self._non_purchasable_ids:
                    logits[non_purch_id] = float('-inf')

            # Kaggle Top 전략: IDF 가중치 적용
            # 희귀 재료에 약간의 보너스를 줘서 다양성 증가
            if self.use_idf_weighting and self._idf_tensor is not None:
                # IDF 정규화 (0~1 범위로)
                idf_normalized = (self._idf_tensor - self._idf_tensor.min()) / \
                                (self._idf_tensor.max() - self._idf_tensor.min() + 1e-8)
                # 가중치 적용: logits = logits + strength * normalized_idf
                logits = logits + self.idf_weight_strength * idf_normalized

            # Top-K (필터링으로 인해 더 많이 가져온 후 유효한 것만 반환)
            top_k_probs, top_k_ids = torch.topk(logits, k=min(top_k * 2, logits.size(-1)))

        # 6. 디코딩
        recommendations = []
        for idx in top_k_ids:
            token = self.tokenizer.get_token(idx.item())
            if token != self.tokenizer.UNK_TOKEN:
                recommendations.append(token)
            if len(recommendations) >= top_k:
                break

        return recommendations

    def recommend_with_scores(
        self,
        given_ingredients: List[str],
        top_k: int = 10,
        exclude_given: bool = True
    ) -> List[Tuple[str, float]]:
        """추천 재료와 신뢰도 점수 반환

        Args:
            given_ingredients: 주어진 재료명 리스트
            top_k: 반환할 추천 개수
            exclude_given: 주어진 재료 제외 여부

        Returns:
            (재료명, 확률) 튜플 리스트
        """
        # recommend 메서드와 유사하지만 점수도 반환
        if self.normalizer:
            normalized = self.normalizer.normalize_list(given_ingredients)
        else:
            normalized = given_ingredients

        ingredient_ids = [
            self.tokenizer.get_token_id(ing)
            for ing in normalized
        ]
        valid_ids = [
            ing_id for ing_id in ingredient_ids
            if ing_id != self.tokenizer.UNK_ID
        ]

        if not valid_ids:
            return []

        max_len = 32
        max_ingredients = max_len - 3
        truncated = valid_ids[:max_ingredients]

        input_ids = [self.cls_id] + truncated + [self.mask_id] + [self.sep_id]
        seq_len = len(input_ids)
        mask_position = len(truncated) + 1

        pad_len = max_len - seq_len
        input_ids = input_ids + [self.pad_id] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len

        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        mask_tensor = torch.tensor([attention_mask], dtype=torch.long, device=self.device)

        with torch.no_grad():
            output = self.model(input_tensor, mask_tensor)
            logits = output['logits'][0, mask_position]

            if exclude_given:
                for ing_id in valid_ids:
                    logits[ing_id] = float('-inf')

            for special_id in [self.pad_id, self.mask_id, self.tokenizer.UNK_ID,
                               self.cls_id, self.sep_id]:
                logits[special_id] = float('-inf')

            # Kaggle Top 전략: 비구매 재료 필터링
            if self.filter_non_purchasable:
                for non_purch_id in self._non_purchasable_ids:
                    logits[non_purch_id] = float('-inf')

            # Kaggle Top 전략: IDF 가중치 적용
            if self.use_idf_weighting and self._idf_tensor is not None:
                idf_normalized = (self._idf_tensor - self._idf_tensor.min()) / \
                                (self._idf_tensor.max() - self._idf_tensor.min() + 1e-8)
                logits = logits + self.idf_weight_strength * idf_normalized

            # Softmax로 확률 변환
            probs = F.softmax(logits, dim=-1)
            top_k_probs, top_k_ids = torch.topk(probs, k=min(top_k * 2, probs.size(-1)))

        results = []
        for idx, prob in zip(top_k_ids, top_k_probs):
            token = self.tokenizer.get_token(idx.item())
            if token != self.tokenizer.UNK_TOKEN:
                results.append((token, prob.item()))
            if len(results) >= top_k:
                break

        return results

    def batch_recommend(
        self,
        recipes: List[List[str]],
        top_k: int = 10,
        exclude_given: bool = True
    ) -> List[List[str]]:
        """여러 레시피에 대해 일괄 추천

        Args:
            recipes: 레시피 리스트 (각 레시피는 재료명 리스트)
            top_k: 각 레시피당 추천 개수
            exclude_given: 주어진 재료 제외 여부

        Returns:
            추천 결과 리스트
        """
        return [
            self.recommend(recipe, top_k, exclude_given)
            for recipe in recipes
        ]

    def save(self, path: str) -> None:
        """모델을 pickle 파일로 저장

        Args:
            path: 저장 경로 (.pkl)
        """
        # CPU로 이동하여 저장 (GPU 메모리 문제 방지)
        model_cpu = self.model.cpu()

        save_data = {
            'model_state_dict': model_cpu.state_dict(),
            'model_config': {
                'vocab_size': model_cpu.vocab_size,
                'd_model': model_cpu.d_model,
                'pad_id': model_cpu.pad_id,
            },
            'tokenizer_vocab': self.tokenizer.vocab,
            'tokenizer_freq': self.tokenizer.token_freq,
            'normalizer': self.normalizer,
            'version': '2.0.0',
        }

        with open(path, 'wb') as f:
            pickle.dump(save_data, f)

        # 다시 원래 디바이스로 이동
        self.model = model_cpu.to(self.device)

        logger.info(f"모델 저장 완료: {path}")

    @classmethod
    def load(
        cls,
        path: str,
        device: str = 'cuda'
    ) -> 'RecipeGapFillingModel':
        """저장된 모델 로드

        Args:
            path: 모델 경로 (.pkl)
            device: 추론 디바이스

        Returns:
            RecipeGapFillingModel 인스턴스
        """
        from .model import MaskedSetTransformer
        from .tokenizer import IngredientTokenizer

        with open(path, 'rb') as f:
            save_data = pickle.load(f)

        # 토크나이저 복원
        tokenizer = IngredientTokenizer()
        tokenizer.vocab = save_data['tokenizer_vocab']
        tokenizer.id2token = {v: k for k, v in tokenizer.vocab.items()}
        tokenizer.token_freq = save_data.get('tokenizer_freq', {})

        # 모델 복원
        model_config = save_data['model_config']
        model = MaskedSetTransformer(**model_config)
        model.load_state_dict(save_data['model_state_dict'])

        # Normalizer 복원
        normalizer = save_data.get('normalizer')

        logger.info(f"모델 로드 완료: {path} (version={save_data.get('version', 'unknown')})")

        return cls(
            model=model,
            tokenizer=tokenizer,
            normalizer=normalizer,
            device=device
        )

    def __repr__(self) -> str:
        return (
            f"RecipeGapFillingModel("
            f"vocab_size={self.tokenizer.vocab_size}, "
            f"device={self.device})"
        )
