"""
텍스트 임베딩 모듈

BERT 기반 한국어 텍스트 임베딩 생성
"""

from typing import Dict, List, Optional, Union
import numpy as np

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


class ProductEmbedding:
    """상품 텍스트 임베딩

    BERT 기반 한국어 임베딩:
    - 모델: klue/bert-base
    - 차원: 768
    - 입력: 상품명 + 카테고리명 + 짧은 설명
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Args:
            model_name: 사용할 BERT 모델명 (기본: klue/bert-base)
        """
        self.model_name = model_name or settings.bert_model_name
        self.dimension = settings.embedding_dimension
        self.tokenizer = None
        self.model = None
        self._initialized = False

    async def initialize(self) -> None:
        """모델 초기화 (지연 로딩)"""
        if self._initialized:
            return

        try:
            from transformers import AutoTokenizer, AutoModel

            logger.info("BERT 모델 로딩 시작", model_name=self.model_name)

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self._initialized = True

            logger.info("BERT 모델 로딩 완료", model_name=self.model_name)

        except ImportError:
            logger.warning(
                "transformers 라이브러리가 설치되지 않음, 더미 임베딩 사용"
            )
            self._initialized = True

        except Exception as e:
            logger.error("BERT 모델 로딩 실패", error=str(e))
            raise

    def encode(self, product: Dict) -> np.ndarray:
        """상품 → 임베딩 벡터

        입력 텍스트 구성:
        "[CLS] {카테고리명} [SEP] {상품명} [SEP] {짧은설명}"

        Args:
            product: 상품 정보 딕셔너리

        Returns:
            768차원 임베딩 벡터
        """
        if not self._initialized:
            raise RuntimeError("모델이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")

        # 텍스트 구성
        text = self._build_product_text(product)

        # BERT 모델이 로드되지 않은 경우 더미 임베딩 반환
        if self.tokenizer is None or self.model is None:
            return self._generate_dummy_embedding(text)

        try:
            import torch

            # 토큰화
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=128,
                truncation=True,
                padding=True,
            )

            # 추론
            with torch.no_grad():
                outputs = self.model(**inputs)

            # [CLS] 토큰 임베딩 추출
            embedding = outputs.last_hidden_state[:, 0, :].numpy()
            return embedding.squeeze()

        except Exception as e:
            logger.warning("임베딩 생성 실패, 더미 임베딩 반환", error=str(e))
            return self._generate_dummy_embedding(text)

    def encode_batch(self, products: List[Dict]) -> List[np.ndarray]:
        """여러 상품 일괄 임베딩

        Args:
            products: 상품 정보 딕셔너리 목록

        Returns:
            임베딩 벡터 목록
        """
        if not self._initialized:
            raise RuntimeError("모델이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")

        if self.tokenizer is None or self.model is None:
            return [
                self._generate_dummy_embedding(self._build_product_text(p))
                for p in products
            ]

        try:
            import torch

            texts = [self._build_product_text(p) for p in products]

            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                max_length=128,
                truncation=True,
                padding=True,
            )

            with torch.no_grad():
                outputs = self.model(**inputs)

            embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            return [embeddings[i] for i in range(len(products))]

        except Exception as e:
            logger.warning("배치 임베딩 생성 실패", error=str(e))
            return [
                self._generate_dummy_embedding(self._build_product_text(p))
                for p in products
            ]

    def _build_product_text(self, product: Dict) -> str:
        """상품 정보에서 임베딩용 텍스트 생성

        Args:
            product: 상품 정보 딕셔너리

        Returns:
            임베딩용 텍스트
        """
        parts = []

        # 카테고리명
        if product.get("category_name"):
            parts.append(product["category_name"])

        # 상품명
        if product.get("name"):
            parts.append(product["name"])

        # 짧은 설명
        if product.get("short_description"):
            parts.append(product["short_description"])

        return " ".join(parts) if parts else "상품"

    def _generate_dummy_embedding(self, text: str) -> np.ndarray:
        """더미 임베딩 생성 (개발/테스트용)

        텍스트 해시 기반 결정론적 임베딩 생성

        Args:
            text: 입력 텍스트

        Returns:
            768차원 더미 임베딩 벡터
        """
        import hashlib

        # 텍스트 해시 기반 시드 생성
        hash_value = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_value % (2**32))

        # 정규화된 랜덤 벡터 생성
        embedding = np.random.randn(self.dimension)
        embedding = embedding / np.linalg.norm(embedding)

        return embedding.astype(np.float32)


class UserEmbedding:
    """사용자 임베딩

    사용자의 상호작용 이력 기반 임베딩 생성
    - 상품 임베딩의 가중 평균으로 계산
    """

    def __init__(self, product_embedding: Optional[ProductEmbedding] = None):
        """
        Args:
            product_embedding: ProductEmbedding 인스턴스
        """
        self.product_embedding = product_embedding or ProductEmbedding()
        self.dimension = settings.embedding_dimension

    def compute_user_embedding(
        self,
        product_embeddings: List[np.ndarray],
        weights: List[float],
    ) -> np.ndarray:
        """사용자 임베딩 계산

        상품 임베딩의 가중 평균으로 사용자 임베딩 생성

        Args:
            product_embeddings: 상품 임베딩 벡터 목록
            weights: 상품별 가중치 (상호작용 강도 기반)

        Returns:
            사용자 임베딩 벡터
        """
        if not product_embeddings:
            # 상호작용 없는 경우 영벡터 반환
            return np.zeros(self.dimension, dtype=np.float32)

        # 가중 평균 계산
        total_weight = sum(weights)
        if total_weight == 0:
            # 가중치 합이 0인 경우 단순 평균
            user_embedding = np.mean(product_embeddings, axis=0)
        else:
            weighted_sum = np.zeros(self.dimension, dtype=np.float32)
            for emb, w in zip(product_embeddings, weights):
                weighted_sum += emb * (w / total_weight)
            user_embedding = weighted_sum

        # 정규화
        norm = np.linalg.norm(user_embedding)
        if norm > 0:
            user_embedding = user_embedding / norm

        return user_embedding

    def calculate_interaction_weight(self, interaction: Dict) -> float:
        """상호작용 기반 가중치 계산

        Args:
            interaction: 상호작용 정보
                - order_event_count: 구매 횟수
                - cart_event_count: 장바구니 횟수
                - view_count: 조회 횟수

        Returns:
            가중치 값
        """
        order_count = interaction.get("order_event_count", 0) or 0
        cart_count = interaction.get("cart_event_count", 0) or 0
        view_count = interaction.get("view_count", 0) or 0

        # 가중치 공식: 구매 5 + 장바구니 3 + 조회 1
        weight = (
            order_count * 5 +
            cart_count * 3 +
            view_count * 1
        )

        return float(weight)
