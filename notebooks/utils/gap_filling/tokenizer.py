# -*- coding: utf-8 -*-
"""
재료 Tokenizer 모듈

BERT 스타일의 재료 토크나이저
- 특수 토큰: [PAD], [MASK], [UNK], [CLS], [SEP]
- 빈도 기반 ID 할당 (빈번한 재료 = 낮은 ID)
- IDF (Inverse Document Frequency) 가중치 지원

Kaggle Top 전략:
- IDF를 활용하여 고빈도 재료(마늘, 파 등)의 영향력 감소
- 참고: https://towardsdatascience.com/building-a-recipe-recommendation-system-297c229dda7b/
"""

import json
import math
from collections import Counter
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class IngredientTokenizer:
    """재료 Tokenizer (BERT 스타일)

    특수 토큰:
        [PAD]: 패딩 토큰 (ID=0)
        [MASK]: 마스킹 토큰 (ID=1)
        [UNK]: 미등록 토큰 (ID=2)
        [CLS]: 시퀀스 시작 토큰 (ID=3)
        [SEP]: 시퀀스 종료 토큰 (ID=4)

    Attributes:
        vocab (Dict[str, int]): 재료 → ID 매핑
        id2token (Dict[int, str]): ID → 재료 매핑
        token_freq (Dict[str, int]): 재료별 빈도

    Example:
        >>> tokenizer = IngredientTokenizer()
        >>> recipes = [['돼지고기', '양파', '마늘'], ['닭고기', '양파', '간장']]
        >>> tokenizer.build_vocab(recipes, min_freq=1)
        >>> ids = tokenizer.encode(['돼지고기', '양파'])
        >>> print(ids)  # [3, 5, 6, 4] with [CLS] and [SEP]
    """

    # 특수 토큰 정의
    PAD_TOKEN = '[PAD]'
    MASK_TOKEN = '[MASK]'
    UNK_TOKEN = '[UNK]'
    CLS_TOKEN = '[CLS]'
    SEP_TOKEN = '[SEP]'

    # 특수 토큰 ID (고정)
    PAD_ID = 0
    MASK_ID = 1
    UNK_ID = 2
    CLS_ID = 3
    SEP_ID = 4

    def __init__(self):
        """토크나이저 초기화"""
        self.vocab: Dict[str, int] = {}
        self.id2token: Dict[int, str] = {}
        self.token_freq: Dict[str, int] = {}
        self.token_idf: Dict[str, float] = {}  # IDF 가중치
        self.token_doc_freq: Dict[str, int] = {}  # 문서 빈도 (레시피 수)
        self._total_docs: int = 0  # 전체 레시피 수
        self._init_special_tokens()

    def _init_special_tokens(self) -> None:
        """특수 토큰 초기화"""
        special_tokens = [
            (self.PAD_TOKEN, self.PAD_ID),
            (self.MASK_TOKEN, self.MASK_ID),
            (self.UNK_TOKEN, self.UNK_ID),
            (self.CLS_TOKEN, self.CLS_ID),
            (self.SEP_TOKEN, self.SEP_ID),
        ]
        for token, token_id in special_tokens:
            self.vocab[token] = token_id
            self.id2token[token_id] = token

    def build_vocab(
        self,
        recipes: List[List[str]],
        min_freq: int = 5,
        max_vocab_size: Optional[int] = None,
        compute_idf: bool = True
    ) -> None:
        """레시피 데이터로부터 어휘 사전 구축

        빈도 기반으로 ID를 할당하여 빈번한 재료가 낮은 ID를 갖도록 함
        IDF(Inverse Document Frequency) 가중치도 함께 계산

        Args:
            recipes: 레시피 리스트. 각 레시피는 재료명 리스트
            min_freq: 최소 등장 빈도. 이 빈도 미만인 재료는 UNK 처리
            max_vocab_size: 최대 어휘 크기. None이면 제한 없음
            compute_idf: IDF 가중치 계산 여부 (기본: True)

        Example:
            >>> tokenizer.build_vocab(recipes, min_freq=5, max_vocab_size=5000)
        """
        # 재료 빈도 계산
        counter = Counter()
        doc_counter = Counter()  # 문서(레시피) 빈도

        self._total_docs = len(recipes)

        for recipe in recipes:
            counter.update(recipe)
            # 문서 빈도: 각 레시피에서 고유 재료만 카운트
            doc_counter.update(set(recipe))

        self.token_freq = dict(counter)
        self.token_doc_freq = dict(doc_counter)

        # IDF 계산: log(전체 레시피 수 / 해당 재료 포함 레시피 수)
        if compute_idf and self._total_docs > 0:
            for token, doc_freq in doc_counter.items():
                # smoothed IDF: log((N + 1) / (df + 1)) + 1
                idf = math.log((self._total_docs + 1) / (doc_freq + 1)) + 1
                self.token_idf[token] = idf

        # 빈도순 정렬 (높은 빈도 → 낮은 ID)
        sorted_items = sorted(
            counter.items(),
            key=lambda x: (-x[1], x[0])  # 빈도 내림차순, 동률 시 알파벳순
        )

        # 빈도 필터링
        filtered_items = [
            (token, freq) for token, freq in sorted_items
            if freq >= min_freq
        ]

        # 최대 크기 제한
        if max_vocab_size is not None:
            # 특수 토큰 개수 고려
            available_size = max_vocab_size - len(self.vocab)
            filtered_items = filtered_items[:available_size]

        # 어휘 사전 구축 (특수 토큰 ID 이후부터 시작)
        next_id = len(self.vocab)
        for token, _ in filtered_items:
            if token not in self.vocab:  # 특수 토큰과 중복 방지
                self.vocab[token] = next_id
                self.id2token[next_id] = token
                next_id += 1

        # IDF 통계 로깅
        if self.token_idf:
            idf_values = list(self.token_idf.values())
            logger.info(
                f"IDF 가중치 계산 완료: "
                f"min={min(idf_values):.2f}, max={max(idf_values):.2f}, "
                f"mean={np.mean(idf_values):.2f}"
            )

        logger.info(
            f"어휘 사전 구축 완료: "
            f"총 {len(self.vocab)}개 토큰 "
            f"(특수 토큰 5개 + 재료 {len(self.vocab) - 5}개), "
            f"min_freq={min_freq}로 {len(counter) - len(filtered_items)}개 필터링됨"
        )

    def encode(
        self,
        ingredients: List[str],
        max_len: int = 32,
        add_special_tokens: bool = True,
        padding: bool = True,
        return_attention_mask: bool = False
    ) -> Dict[str, List[int]]:
        """재료 리스트를 토큰 ID 리스트로 인코딩

        Args:
            ingredients: 재료명 리스트
            max_len: 최대 시퀀스 길이 (패딩 포함)
            add_special_tokens: [CLS], [SEP] 토큰 추가 여부
            padding: 패딩 적용 여부
            return_attention_mask: attention mask 반환 여부

        Returns:
            Dict with:
                - input_ids: 토큰 ID 리스트
                - attention_mask: (optional) 어텐션 마스크

        Example:
            >>> result = tokenizer.encode(['돼지고기', '양파'], max_len=10)
            >>> print(result['input_ids'])  # [3, 5, 6, 4, 0, 0, 0, 0, 0, 0]
        """
        # 재료 → ID 변환
        ids = [
            self.vocab.get(ing, self.UNK_ID)
            for ing in ingredients
        ]

        # 특수 토큰 추가
        if add_special_tokens:
            # max_len에서 [CLS], [SEP] 자리 확보
            max_ingredients = max_len - 2
            ids = ids[:max_ingredients]
            ids = [self.CLS_ID] + ids + [self.SEP_ID]
        else:
            ids = ids[:max_len]

        # attention mask 생성 (패딩 전)
        attention_mask = [1] * len(ids)

        # 패딩
        if padding:
            pad_len = max_len - len(ids)
            ids = ids + [self.PAD_ID] * pad_len
            attention_mask = attention_mask + [0] * pad_len

        result = {'input_ids': ids}
        if return_attention_mask:
            result['attention_mask'] = attention_mask

        return result

    def encode_batch(
        self,
        recipes: List[List[str]],
        max_len: int = 32,
        add_special_tokens: bool = True
    ) -> Dict[str, List[List[int]]]:
        """여러 레시피를 일괄 인코딩

        Args:
            recipes: 레시피 리스트
            max_len: 최대 시퀀스 길이
            add_special_tokens: 특수 토큰 추가 여부

        Returns:
            Dict with:
                - input_ids: 2D 토큰 ID 리스트
                - attention_mask: 2D 어텐션 마스크
        """
        all_input_ids = []
        all_attention_masks = []

        for recipe in recipes:
            encoded = self.encode(
                recipe,
                max_len=max_len,
                add_special_tokens=add_special_tokens,
                padding=True,
                return_attention_mask=True
            )
            all_input_ids.append(encoded['input_ids'])
            all_attention_masks.append(encoded['attention_mask'])

        return {
            'input_ids': all_input_ids,
            'attention_mask': all_attention_masks
        }

    def decode(
        self,
        ids: List[int],
        skip_special_tokens: bool = True
    ) -> List[str]:
        """토큰 ID 리스트를 재료명 리스트로 디코딩

        Args:
            ids: 토큰 ID 리스트
            skip_special_tokens: 특수 토큰 제외 여부

        Returns:
            재료명 리스트

        Example:
            >>> ingredients = tokenizer.decode([3, 5, 6, 4, 0, 0])
            >>> print(ingredients)  # ['돼지고기', '양파']
        """
        special_ids = {self.PAD_ID, self.MASK_ID, self.UNK_ID,
                       self.CLS_ID, self.SEP_ID}

        tokens = []
        for token_id in ids:
            if skip_special_tokens and token_id in special_ids:
                continue
            token = self.id2token.get(token_id, self.UNK_TOKEN)
            if not skip_special_tokens or token not in [
                self.PAD_TOKEN, self.MASK_TOKEN, self.UNK_TOKEN,
                self.CLS_TOKEN, self.SEP_TOKEN
            ]:
                tokens.append(token)

        return tokens

    def get_token_id(self, token: str) -> int:
        """토큰의 ID 반환

        Args:
            token: 재료명

        Returns:
            토큰 ID (미등록 시 UNK_ID)
        """
        return self.vocab.get(token, self.UNK_ID)

    def get_token(self, token_id: int) -> str:
        """ID의 토큰 반환

        Args:
            token_id: 토큰 ID

        Returns:
            재료명 (미등록 시 UNK_TOKEN)
        """
        return self.id2token.get(token_id, self.UNK_TOKEN)

    @property
    def vocab_size(self) -> int:
        """어휘 사전 크기 반환"""
        return len(self.vocab)

    @property
    def num_ingredients(self) -> int:
        """재료 개수 반환 (특수 토큰 제외)"""
        return len(self.vocab) - 5

    def get_frequency(self, token: str) -> int:
        """토큰의 원본 빈도 반환

        Args:
            token: 재료명

        Returns:
            빈도 (미등록 시 0)
        """
        return self.token_freq.get(token, 0)

    def get_idf(self, token: str) -> float:
        """토큰의 IDF 가중치 반환

        IDF = log((전체 레시피 수 + 1) / (해당 재료 포함 레시피 수 + 1)) + 1

        고빈도 재료(마늘, 파 등): 낮은 IDF (1.x)
        희귀 재료(트러플오일 등): 높은 IDF (5.x~10.x)

        Args:
            token: 재료명

        Returns:
            IDF 가중치 (미등록 시 1.0)
        """
        return self.token_idf.get(token, 1.0)

    def get_idf_by_id(self, token_id: int) -> float:
        """토큰 ID로 IDF 가중치 반환

        Args:
            token_id: 토큰 ID

        Returns:
            IDF 가중치 (미등록 시 1.0)
        """
        token = self.get_token(token_id)
        return self.get_idf(token)

    def get_idf_tensor(self, device: str = 'cpu') -> 'torch.Tensor':
        """전체 어휘에 대한 IDF 텐서 반환 (학습용)

        Args:
            device: 텐서 디바이스

        Returns:
            IDF 가중치 텐서 [vocab_size]
        """
        import torch
        idf_weights = []
        for i in range(self.vocab_size):
            token = self.get_token(i)
            idf = self.get_idf(token)
            idf_weights.append(idf)
        return torch.tensor(idf_weights, dtype=torch.float32, device=device)

    def get_lowest_idf_tokens(self, n: int = 20) -> List[Tuple[str, float]]:
        """IDF가 가장 낮은 (가장 흔한) 재료 n개 반환

        Args:
            n: 반환할 재료 개수

        Returns:
            (재료명, IDF) 튜플 리스트
        """
        sorted_items = sorted(
            self.token_idf.items(),
            key=lambda x: x[1]
        )
        return sorted_items[:n]

    def get_highest_idf_tokens(self, n: int = 20) -> List[Tuple[str, float]]:
        """IDF가 가장 높은 (가장 희귀한) 재료 n개 반환

        Args:
            n: 반환할 재료 개수

        Returns:
            (재료명, IDF) 튜플 리스트
        """
        sorted_items = sorted(
            self.token_idf.items(),
            key=lambda x: -x[1]
        )
        return sorted_items[:n]

    def get_most_common(self, n: int = 20) -> List[Tuple[str, int]]:
        """가장 빈번한 재료 n개 반환

        Args:
            n: 반환할 재료 개수

        Returns:
            (재료명, 빈도) 튜플 리스트
        """
        sorted_items = sorted(
            self.token_freq.items(),
            key=lambda x: -x[1]
        )
        return sorted_items[:n]

    def save(self, path: str) -> None:
        """토크나이저를 JSON 파일로 저장

        Args:
            path: 저장 경로 (.json)

        Example:
            >>> tokenizer.save('data/processed/recipe_v3/tokenizer.json')
        """
        data = {
            'vocab': self.vocab,
            'token_freq': self.token_freq,
            'token_idf': self.token_idf,
            'token_doc_freq': self.token_doc_freq,
            'total_docs': self._total_docs,
            'version': '2.1.0',  # IDF 지원 버전
            'special_tokens': {
                'pad': self.PAD_TOKEN,
                'mask': self.MASK_TOKEN,
                'unk': self.UNK_TOKEN,
                'cls': self.CLS_TOKEN,
                'sep': self.SEP_TOKEN,
            }
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"토크나이저 저장 완료: {path} (vocab_size={self.vocab_size}, IDF 포함)")

    @classmethod
    def load(cls, path: str) -> 'IngredientTokenizer':
        """JSON 파일에서 토크나이저 로드

        Args:
            path: 로드 경로 (.json)

        Returns:
            로드된 IngredientTokenizer 인스턴스

        Example:
            >>> tokenizer = IngredientTokenizer.load('data/processed/recipe_v3/tokenizer.json')
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tokenizer = cls()
        tokenizer.vocab = {k: int(v) for k, v in data['vocab'].items()}
        tokenizer.id2token = {int(v): k for k, v in data['vocab'].items()}
        tokenizer.token_freq = data.get('token_freq', {})

        # IDF 관련 데이터 로드 (v2.1.0+)
        tokenizer.token_idf = data.get('token_idf', {})
        tokenizer.token_doc_freq = data.get('token_doc_freq', {})
        tokenizer._total_docs = data.get('total_docs', 0)

        version = data.get('version', 'unknown')
        has_idf = bool(tokenizer.token_idf)
        logger.info(
            f"토크나이저 로드 완료: {path} "
            f"(vocab_size={tokenizer.vocab_size}, version={version}, IDF={'포함' if has_idf else '없음'})"
        )
        return tokenizer

    def __len__(self) -> int:
        """어휘 사전 크기 반환"""
        return self.vocab_size

    def __contains__(self, token: str) -> bool:
        """토큰이 어휘 사전에 있는지 확인"""
        return token in self.vocab

    def __repr__(self) -> str:
        return (
            f"IngredientTokenizer("
            f"vocab_size={self.vocab_size}, "
            f"num_ingredients={self.num_ingredients})"
        )
