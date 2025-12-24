"""
AIRScout 텍스트 인코더

ko-sroberta-multitask 모델을 사용한 768D 임베딩 생성
- SentenceTransformer 우선 사용
- 실패 시 HuggingFace Transformers 폴백 (Mean Pooling)
- 배치 인코딩 지원
"""

import asyncio
from pathlib import Path
from typing import List, Optional

import numpy as np

from core.logging import get_logger

logger = get_logger(__name__)


class AIRScoutEncoder:
    """AIRScout 텍스트 인코더 (싱글톤)

    특징:
    - SentenceTransformer 우선 로드
    - 실패 시 HuggingFace Transformers 폴백 (_HFEncoder)
    - 배치 인코딩 지원
    - 임베딩 캐싱 (선택적)

    사용법:
        encoder = await AIRScoutEncoder.get_instance(model_dir)
        embeddings = encoder.encode(["텍스트1", "텍스트2"])
        similarity = encoder.compute_similarity(query_emb, candidate_embs)
    """

    _instance: Optional["AIRScoutEncoder"] = None
    _init_lock = asyncio.Lock()

    def __init__(self, model_dir: Path, batch_size: int = 32, max_length: int = 128):
        """
        Args:
            model_dir: HuggingFace 모델 디렉토리 경로
            batch_size: 배치 인코딩 크기
            max_length: 토큰 최대 길이
        """
        self.model_dir = model_dir
        self.batch_size = batch_size
        self.max_length = max_length
        self._model = None
        self._tokenizer = None
        self._hf_model = None
        self._device = None
        self._initialized = False
        self._use_hf_fallback = False
        self._embedding_dim = 768  # ko-sroberta-multitask 기본 차원

    @classmethod
    async def get_instance(cls, model_dir: Path) -> "AIRScoutEncoder":
        """싱글톤 인스턴스 반환 (Double-checked Locking)

        Args:
            model_dir: HuggingFace 모델 디렉토리 경로

        Returns:
            초기화된 AIRScoutEncoder 인스턴스
        """
        if cls._instance is not None and cls._instance._initialized:
            return cls._instance

        async with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls(model_dir)
                await cls._instance.initialize()

        return cls._instance

    async def initialize(self) -> None:
        """모델 초기화 (비동기 컨텍스트에서 실행)"""
        if self._initialized:
            return

        # 블로킹 모델 로드를 executor에서 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_sync)

        self._initialized = True
        logger.info(
            "AIRScoutEncoder 초기화 완료",
            extra={
                "model_dir": str(self.model_dir),
                "embedding_dim": self._embedding_dim,
                "use_hf_fallback": self._use_hf_fallback,
            }
        )

    def _load_model_sync(self) -> None:
        """동기 모델 로드 (executor에서 호출)"""
        # 1) SentenceTransformer 시도
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(str(self.model_dir))
            logger.info("SentenceTransformer 로드 성공")
            return
        except Exception as e:
            logger.warning(f"SentenceTransformer 로드 실패, HF 폴백 사용: {e}")

        # 2) HuggingFace Transformers 폴백
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            self._hf_model = AutoModel.from_pretrained(str(self.model_dir))
            self._hf_model.eval()
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._hf_model.to(self._device)
            self._use_hf_fallback = True

            logger.info(f"HuggingFace Transformers 로드 성공 (device={self._device})")
        except Exception as e:
            logger.error(f"모델 로드 완전 실패: {e}")
            raise RuntimeError(f"AIRScout 모델 로드 실패: {e}")

    def encode(
        self,
        texts: List[str],
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환

        Args:
            texts: 인코딩할 텍스트 목록
            convert_to_numpy: numpy 배열로 변환 여부
            show_progress_bar: 진행률 표시 여부

        Returns:
            (N, 768) 형태의 임베딩 배열
        """
        if not texts:
            return np.array([]).reshape(0, self._embedding_dim)

        if self._use_hf_fallback:
            return self._encode_with_hf(texts)

        return self._model.encode(
            texts,
            convert_to_numpy=convert_to_numpy,
            show_progress_bar=show_progress_bar,
            batch_size=self.batch_size,
        )

    def _encode_with_hf(self, texts: List[str]) -> np.ndarray:
        """HuggingFace Transformers로 인코딩 (Mean Pooling)"""
        import torch

        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._hf_model(**inputs)
                # Mean Pooling
                attention_mask = inputs["attention_mask"]
                token_embeddings = outputs.last_hidden_state
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(
                    token_embeddings.size()
                ).float()
                sum_embeddings = (token_embeddings * input_mask_expanded).sum(1)
                sum_mask = input_mask_expanded.sum(1).clamp(min=1e-9)
                embeddings = sum_embeddings / sum_mask

            all_embeddings.append(embeddings.detach().cpu().numpy())

        return np.vstack(all_embeddings)

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
    ) -> np.ndarray:
        """코사인 유사도 계산

        Args:
            query_embedding: (768,) 또는 (1, 768) 쿼리 임베딩
            candidate_embeddings: (N, 768) 후보 임베딩

        Returns:
            (N,) 유사도 배열 [0, 1] 범위로 정규화
        """
        if candidate_embeddings.size == 0:
            return np.array([])

        # 1D -> 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # 코사인 유사도
        query_norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        candidate_norms = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)

        # 0 방지
        query_norm = np.where(query_norm == 0, 1e-8, query_norm)
        candidate_norms = np.where(candidate_norms == 0, 1e-8, candidate_norms)

        query_normalized = query_embedding / query_norm
        candidates_normalized = candidate_embeddings / candidate_norms

        # [-1, 1] -> [0, 1] 정규화
        cosine_sim = np.dot(candidates_normalized, query_normalized.T).flatten()
        return (cosine_sim + 1.0) / 2.0

    @property
    def embedding_dim(self) -> int:
        """임베딩 차원"""
        return self._embedding_dim

    @property
    def is_initialized(self) -> bool:
        """초기화 완료 여부"""
        return self._initialized
