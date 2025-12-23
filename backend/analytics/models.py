"""
Admin 분석용 집계 테이블 정의

일 단위로 비즈니스/추천 지표를 집계하여
대시보드 API에서 빠르게 조회할 수 있도록 한다.
"""

from django.db import models


class UserSegment(models.TextChoices):
    """유저 세그먼트 구분값"""

    ALL = "all", "전체"
    CONSUMER = "consumer", "일반회원"
    SELLER = "seller", "판매자"


class AdminBizDaily(models.Model):
    """
    일 단위 비즈니스 요약 지표

    - GMV / 주문 수 / 유니크 구매자 수 / 장바구니 담기 수 등을 저장
    - user_segment별로 동일 날짜에 여러 레코드가 존재할 수 있다.
    """

    date = models.DateField(verbose_name="집계 날짜")
    user_segment = models.CharField(
        max_length=20,
        choices=UserSegment.choices,
        default=UserSegment.ALL,
        verbose_name="유저 세그먼트",
    )

    sessions = models.BigIntegerField(
        default=0,
        verbose_name="세션 수",
        help_text="세션 로그 도입 후 채워질 값 (초기에는 0 유지)",
    )
    unique_buyers = models.BigIntegerField(
        default=0,
        verbose_name="구매 유저 수",
    )
    orders = models.BigIntegerField(
        default=0,
        verbose_name="주문 수",
    )
    gmv = models.BigIntegerField(
        default=0,
        verbose_name="총 매출(GMV)",
    )
    cart_adds = models.BigIntegerField(
        default=0,
        verbose_name="장바구니 담기 수",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "admin_analytics_biz_daily"
        verbose_name = "Admin 비즈니스 일간 집계"
        verbose_name_plural = "Admin 비즈니스 일간 집계"
        unique_together = [["date", "user_segment"]]
        indexes = [
            models.Index(
                fields=["date"],
                name="ix_abd_date",
            ),
            models.Index(
                fields=["date", "user_segment"],
                name="ix_abd_date_seg",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(sessions__gte=0),
                name="chk_admin_biz_daily_sessions_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(unique_buyers__gte=0),
                name="chk_admin_biz_daily_unique_buyers_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(orders__gte=0),
                name="chk_admin_biz_daily_orders_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(gmv__gte=0),
                name="chk_admin_biz_daily_gmv_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(cart_adds__gte=0),
                name="chk_admin_biz_daily_cart_adds_non_negative",
            ),
        ]

    def __str__(self) -> str:
        """관리자 화면에서 읽기 쉬운 문자열 표현"""
        return f"{self.date} / {self.user_segment} / 주문 {self.orders}건, GMV {self.gmv}"


class AdminCategoryDaily(models.Model):
    """
    일 단위 카테고리별 비즈니스 집계

    - 상위 카테고리 단위로 주문 수/매출을 집계하여
      Top Line 대시보드에서 카테고리별 성과 분해용으로 사용한다.
    """

    date = models.DateField(verbose_name="집계 날짜")
    user_segment = models.CharField(
        max_length=20,
        choices=UserSegment.choices,
        default=UserSegment.ALL,
        verbose_name="유저 세그먼트",
    )
    category_name = models.CharField(
        max_length=100,
        verbose_name="카테고리명",
    )

    sessions = models.BigIntegerField(
        default=0,
        verbose_name="세션 수",
    )
    orders = models.BigIntegerField(
        default=0,
        verbose_name="주문 수",
    )
    gmv = models.BigIntegerField(
        default=0,
        verbose_name="카테고리 매출(GMV)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "admin_analytics_category_daily"
        verbose_name = "Admin 카테고리 일간 집계"
        verbose_name_plural = "Admin 카테고리 일간 집계"
        unique_together = [["date", "user_segment", "category_name"]]
        indexes = [
            models.Index(fields=["date"], name="ix_acd_date"),
            models.Index(fields=["date", "user_segment"], name="ix_acd_date_seg"),
            models.Index(
                fields=["date", "user_segment", "category_name"],
                name="ix_acd_date_seg_cat",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(sessions__gte=0),
                name="chk_admin_cat_daily_sessions_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(orders__gte=0),
                name="chk_admin_cat_daily_orders_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(gmv__gte=0),
                name="chk_admin_cat_daily_gmv_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.date} / {self.user_segment} / {self.category_name} "
            f"/ 주문 {self.orders}건, GMV {self.gmv}"
        )


class AdminRecoDaily(models.Model):
    """
    일 단위 추천 성과 지표

    - placement(예: home) 단위로 노출/클릭/구매 기여를 집계
    """

    date = models.DateField(verbose_name="집계 날짜")
    placement = models.CharField(
        max_length=50,
        verbose_name="추천 위치",
        help_text="home, detail_similar, cart_gapfill 등 추천 위치 식별자",
    )
    user_segment = models.CharField(
        max_length=20,
        choices=UserSegment.choices,
        default=UserSegment.ALL,
        verbose_name="유저 세그먼트",
    )

    reco_impressions = models.BigIntegerField(
        default=0,
        verbose_name="추천 노출 수",
    )
    reco_clicks = models.BigIntegerField(
        default=0,
        verbose_name="추천 클릭 수",
    )
    reco_attributed_orders = models.BigIntegerField(
        default=0,
        verbose_name="추천 기여 주문 수",
    )
    reco_attributed_gmv = models.BigIntegerField(
        default=0,
        verbose_name="추천 기여 매출(GMV)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        db_table = "admin_analytics_reco_daily"
        verbose_name = "Admin 추천 일간 집계"
        verbose_name_plural = "Admin 추천 일간 집계"
        unique_together = [["date", "placement", "user_segment"]]
        indexes = [
            models.Index(
                fields=["date"],
                name="ix_ard_date",
            ),
            models.Index(
                fields=["date", "placement"],
                name="ix_ard_date_place",
            ),
            models.Index(
                fields=["date", "placement", "user_segment"],
                name="ix_ard_date_place_seg",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(reco_impressions__gte=0),
                name="chk_admin_reco_daily_impr_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(reco_clicks__gte=0),
                name="chk_admin_reco_daily_clicks_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(reco_attributed_orders__gte=0),
                name="chk_admin_reco_daily_orders_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(reco_attributed_gmv__gte=0),
                name="chk_admin_reco_daily_gmv_non_negative",
            ),
        ]

    def __str__(self) -> str:
        """관리자 화면에서 읽기 쉬운 문자열 표현"""
        return (
            f"{self.date} / {self.placement} / CTR={self.reco_clicks}/{self.reco_impressions}"
        )


