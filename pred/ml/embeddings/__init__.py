"""
임베딩 패키지

BERT 기반 텍스트 임베딩 생성
"""

from ml.embeddings.text_embedding import ProductEmbedding, UserEmbedding

__all__ = [
    "ProductEmbedding",
    "UserEmbedding",
]
