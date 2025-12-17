"""
임베딩 데이터 모델

상품/사용자 임베딩 벡터를 저장합니다.
개인화 추천에 활용됩니다.
"""

from django.db import models
from django.conf import settings
from products.models import Product


class UserTypeChoices(models.TextChoices):
    """사용자 타입"""
    COLD = 'cold', '콜드 유저 (데이터 부족)'
    LUKEWARM = 'lukewarm', '루크웜 유저 (제한적 개인화)'
    WARM = 'warm', '웜 유저 (완전 개인화)'


class PredProductEmbedding(models.Model):
    """상품 임베딩 벡터

    BERT 768차원 임베딩
    상품 텍스트(이름 + 카테고리 + 설명) 기반
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='embedding',
        verbose_name='상품'
    )

    # BERT 텍스트 임베딩 (768차원)
    bert_vector = models.JSONField(
        null=True,
        blank=True,
        verbose_name='BERT 임베딩 벡터',
        help_text='768차원 float 배열'
    )
    bert_version = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='BERT 모델 버전'
    )
    bert_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='BERT 임베딩 갱신 일시'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_product_embeddings'
        verbose_name = '상품 임베딩'
        verbose_name_plural = '상품 임베딩들'

    def __str__(self):
        return f"Embedding: {self.product.name}"

    @property
    def has_embedding(self) -> bool:
        """임베딩 벡터 존재 여부"""
        return self.bert_vector is not None


class PredUserEmbedding(models.Model):
    """사용자 임베딩 벡터

    사용자 선호도 벡터 (구매/조회 이력 기반)
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='recommendation_embedding',
        verbose_name='사용자'
    )

    # 사용자 선호 임베딩 (구매/조회 이력 기반)
    preference_vector = models.JSONField(
        null=True,
        blank=True,
        verbose_name='선호도 벡터',
        help_text='768차원 float 배열'
    )

    # 사용자 타입
    user_type = models.CharField(
        max_length=20,
        choices=UserTypeChoices.choices,
        default=UserTypeChoices.COLD,
        verbose_name='사용자 타입'
    )

    # 메타데이터
    interaction_count = models.IntegerField(
        default=0,
        verbose_name='총 상호작용 수'
    )
    last_interaction_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='마지막 상호작용 일시'
    )

    # 버전
    version = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='임베딩 버전'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'pred_user_embeddings'
        verbose_name = '사용자 임베딩'
        verbose_name_plural = '사용자 임베딩들'
        indexes = [
            models.Index(
                fields=['user_type'],
                name='ix_user_emb_type'
            ),
            models.Index(
                fields=['updated_at'],
                name='ix_user_emb_updated'
            ),
        ]

    def __str__(self):
        return f"UserEmbed: {self.user.username} ({self.user_type})"

    @property
    def has_embedding(self) -> bool:
        """임베딩 벡터 존재 여부"""
        return self.preference_vector is not None
