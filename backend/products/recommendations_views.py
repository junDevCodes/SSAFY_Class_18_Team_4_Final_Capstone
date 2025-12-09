"""
추천 관련 API Views (REC-005)

최근 본 상품, 개인화 추천 등 추천 관련 API를 제공합니다.
"""
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import UserProductStats
from .serializers import ProductListSerializerV2


class RecentViewedProductsView(generics.GenericAPIView):
    """최근 본 상품 목록 조회 API (REC-005)

    GET /api/recommendations/recent/?limit=10

    사용자가 최근에 조회한 상품 목록을 last_interacted_at 기준 내림차순으로 반환.
    중복 제거는 UserProductStats의 unique_together로 보장됨.

    Parameters:
        limit (int, optional): 조회 개수 (기본: 10)

    Returns:
        200: { "products": ProductListDTO[] }
        401: { "detail": "자격 인증데이터가 제공되지 않았습니다." }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 쿼리 파라미터에서 limit 추출 (기본값: 10)
        try:
            limit = int(request.query_params.get('limit', 10))
            # 음수나 너무 큰 값 방지
            limit = max(1, min(limit, 100))
        except (ValueError, TypeError):
            limit = 10

        # 최근 본 상품 조회 (last_interacted_at 기준 내림차순)
        # view_count > 0: 실제로 조회한 상품만 (장바구니만 추가한 경우 제외)
        recent_stats = UserProductStats.objects.filter(
            user=request.user,
            view_count__gt=0
        ).select_related(
            'product__category',
            'product__stats',
            'product__inventory',
        ).prefetch_related(
            'product__images'
        ).order_by('-last_interacted_at')[:limit]

        # Product 객체 추출
        products = [stat.product for stat in recent_stats]

        # 시리얼라이즈
        serializer = ProductListSerializerV2(products, many=True)

        return Response({
            'products': serializer.data
        })
