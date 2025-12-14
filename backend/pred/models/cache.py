"""
캐시 데이터 모델

추천 결과 및 가격 이상치 분석 캐시를 저장합니다.
Redis 장애 시 백업용으로 사용됩니다.
"""

from django.db import models
from django.conf import settings
from products.models import Product, Category


class PageTypeChoices(models.TextChoices):
    """페이지 타입"""
    HOME = 'home', '메인 홈'
    CATEGORY = 'category', '카테고리'
    PRODUCT_DETAIL = 'product_detail', '상품 상세'
    CART = 'cart', '장바구니'
    SEARCH = 'search', '검색 결과'
    TIMEDEAL = 'timedeal', '타임딜'


class PredRecommendationCache(models.Model):
    """추천 결과 캐시

    Redis 백업용 DB 캐시
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recommendation_caches',
        verbose_name='사용자',
        help_text='NULL이면 비로그인 사용자'
    )
    page_type = models.CharField(
        max_length=30,
        choices=PageTypeChoices.choices,
        verbose_name='페이지 타입'
    )
    context_hash = models.CharField(
        max_length=64,
        verbose_name='컨텍스트 해시',
        help_text='SHA256(category_id + product_id + cart_items + time_slot)'
    )

    # 캐시 값
    recommendations = models.JSONField(
        verbose_name='추천 결과',
        help_text='[{product_id, score, reason}, ...]'
    )
    model_used = models.CharField(
        max_length=100,
        verbose_name='사용된 모델들'
    )

    # TTL
    expires_at = models.DateTimeField(
        verbose_name='만료 일시'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'pred_recommendation_cache'
        verbose_name = '추천 캐시'
        verbose_name_plural = '추천 캐시들'
        unique_together = [['user', 'page_type', 'context_hash']]
        indexes = [
            models.Index(
                fields=['user'],
                name='ix_rec_cache_user'
            ),
            models.Index(
                fields=['user', 'page_type', 'context_hash', 'expires_at'],
                name='ix_rec_cache_lookup'
            ),
            models.Index(
                fields=['expires_at'],
                name='ix_rec_cache_expires'
            ),
        ]

    def __str__(self):
        user_part = self.user.username if self.user else 'anonymous'
        return f"Cache: {user_part}/{self.page_type}"

    @property
    def is_expired(self) -> bool:
        """만료 여부"""
        from django.utils import timezone
        return self.expires_at < timezone.now()


class PredPriceAnomalyCache(models.Model):
    """가격 이상치 분석 캐시

    배치로 1시간마다 갱신
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='anomaly_cache',
        verbose_name='상품'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomaly_caches',
        verbose_name='카테고리'
    )

    # 가격 정보
    current_price = models.IntegerField(
        verbose_name='현재 가격'
    )
    previous_price = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='이전 가격'
    )
    price_change_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='가격 변동률 (%)'
    )

    # 탐지 점수
    anomaly_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name='이상치 점수',
        help_text='0.0000~1.0000'
    )
    detection_methods = models.CharField(
        max_length=100,
        verbose_name='탐지 방법들',
        help_text='zscore,iqr,ma (쉼표 구분)'
    )

    # 분석 상세 (선택적)
    zscore_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Z-Score 값'
    )
    iqr_lower_bound = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='IQR 하한'
    )
    ma_7day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='7일 이동평균'
    )

    # TTL
    analyzed_at = models.DateTimeField(
        auto_now=True,
        verbose_name='분석 일시'
    )
    expires_at = models.DateTimeField(
        verbose_name='만료 일시'
    )

    class Meta:
        db_table = 'pred_price_anomaly_cache'
        verbose_name = '가격 이상치 캐시'
        verbose_name_plural = '가격 이상치 캐시들'
        indexes = [
            models.Index(
                fields=['-anomaly_score'],
                name='ix_anomaly_score'
            ),
            models.Index(
                fields=['category'],
                name='ix_anomaly_category'
            ),
            models.Index(
                fields=['expires_at'],
                name='ix_anomaly_expires'
            ),
        ]

    def __str__(self):
        return f"Anomaly: {self.product.name} ({self.anomaly_score})"

    @property
    def is_expired(self) -> bool:
        """만료 여부"""
        from django.utils import timezone
        return self.expires_at < timezone.now()

    @property
    def detection_methods_list(self) -> list:
        """탐지 방법 목록"""
        return [m.strip() for m in self.detection_methods.split(',') if m.strip()]
