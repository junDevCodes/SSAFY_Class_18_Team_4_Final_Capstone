"""
추천 관련 API Views (REC-005)

최근 본 상품, 개인화 추천 등 추천 관련 API를 제공합니다.
"""
import logging

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProductStats, Product
from .serializers import ProductListSerializerV2
from . import pred_client

logger = logging.getLogger(__name__)


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


class HomeRecommendationsView(APIView):
    """홈 페이지 추천 API

    GET /api/recommendations/home/?limit=10

    ML 추천 서비스(pred)를 통한 개인화/비개인화 추천
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 10

        # 로그인 사용자면 user_id 전달
        user_id = request.user.id if request.user.is_authenticated else None

        # pred 서비스 호출
        result = pred_client.get_home_recommendations(user_id=user_id, limit=limit)

        if not result.get("success", True):
            # pred 실패 시 fallback: 인기 상품
            logger.warning("pred 서비스 호출 실패, fallback 사용")
            return self._fallback_products(limit)

        # pred 응답의 product_id로 실제 Product 조회
        product_ids = [r.get("product_id") for r in (result.get("recommendations") or [])]
        if not product_ids:
            return self._fallback_products(limit)

        products = Product.objects.filter(
            id__in=product_ids,
            status="active"
        ).select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related('images')

        # 추천 순서 유지
        product_dict = {p.id: p for p in products}
        ordered_products = [product_dict[pid] for pid in product_ids if pid in product_dict]

        serializer = ProductListSerializerV2(ordered_products, many=True)

        return Response({
            'products': serializer.data,
            'user_type': result.get('user_type', 'cold'),
            'model_name': result.get('model_results', [{}])[0].get('model_name', 'unknown') if result.get('model_results') else 'unknown',
        })

    def _fallback_products(self, limit):
        """pred 실패 시 인기 상품 반환"""
        products = Product.objects.filter(
            status="active"
        ).select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related(
            'images'
        ).order_by('-stats__order_event_count')[:limit]

        serializer = ProductListSerializerV2(products, many=True)
        return Response({
            'products': serializer.data,
            'user_type': 'cold',
            'model_name': 'fallback',
        })


class ProductRecommendationsView(APIView):
    """상품 상세 페이지 연관 상품 추천 API

    GET /api/recommendations/product/<product_id>/?limit=10
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 10

        user_id = request.user.id if request.user.is_authenticated else None

        # pred 서비스 호출
        result = pred_client.get_product_recommendations(
            product_id=product_id,
            user_id=user_id,
            limit=limit,
        )

        if not result.get("success", True):
            # pred 실패 시 fallback: 같은 카테고리 인기 상품
            return self._fallback_products(product_id, limit)

        # pred 응답의 product_id로 실제 Product 조회
        product_ids = [r.get("product_id") for r in (result.get("recommendations") or [])]
        if not product_ids:
            return self._fallback_products(product_id, limit)

        products = Product.objects.filter(
            id__in=product_ids,
            status="active"
        ).select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related('images')

        product_dict = {p.id: p for p in products}
        ordered_products = [product_dict[pid] for pid in product_ids if pid in product_dict]

        serializer = ProductListSerializerV2(ordered_products, many=True)

        return Response({
            'products': serializer.data,
        })

    def _fallback_products(self, product_id, limit):
        """같은 카테고리 인기 상품"""
        try:
            product = Product.objects.get(id=product_id)
            category_id = product.category_id
        except Product.DoesNotExist:
            category_id = None

        queryset = Product.objects.filter(status="active").exclude(id=product_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        products = queryset.select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related(
            'images'
        ).order_by('-stats__order_event_count')[:limit]

        serializer = ProductListSerializerV2(products, many=True)
        return Response({'products': serializer.data})


class DealRecommendationsView(APIView):
    """할인 상품 추천 API (TimeDeal용)

    GET /api/recommendations/deals/?limit=10
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 10

        category_id_raw = request.query_params.get('category_id')
        try:
            category_id = int(category_id_raw) if category_id_raw else None
        except (ValueError, TypeError):
            category_id = None
        user_id = request.user.id if request.user.is_authenticated else None

        # pred 서비스 호출
        result = pred_client.get_deal_recommendations(
            user_id=user_id,
            category_id=category_id,
            limit=limit,
        )

        if not result.get("success", True):
            # pred 실패 시 fallback: 할인율 높은 상품
            return self._fallback_deals(limit)

        product_ids = [r.get("product_id") for r in (result.get("recommendations") or [])]
        if not product_ids:
            return self._fallback_deals(limit)

        products = Product.objects.filter(
            id__in=product_ids,
            status="active"
        ).select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related('images')

        product_dict = {p.id: p for p in products}
        ordered_products = [product_dict[pid] for pid in product_ids if pid in product_dict]

        serializer = ProductListSerializerV2(ordered_products, many=True)

        return Response({
            'products': serializer.data,
        })

    def _fallback_deals(self, limit):
        """할인율 높은 상품"""
        products = Product.objects.filter(
            status="active",
            discount_rate__gt=0,
        ).select_related(
            'category', 'stats', 'inventory'
        ).prefetch_related(
            'images'
        ).order_by('-discount_rate')[:limit]

        serializer = ProductListSerializerV2(products, many=True)
        return Response({'products': serializer.data})


# ============================================================
# 장바구니 통합 추천 API (레시피 > 개인화 > Instacart)
# ============================================================


class CartUnifiedRecommendationsView(APIView):
    """장바구니 통합 추천 API

    POST /api/recommendations/cart/unified/
    {
        "user_id": 123,  // 선택사항
        "cart_product_ids": [1, 2, 3],
        "limit": 9
    }

    추천 우선순위:
    1. 레시피 기반 추천 (요리명 포함) - 장바구니 재료로 만들 수 있는 레시피의 부족 재료
    2. 개인화 추천 (로그인 사용자) - SVD 임베딩 기반
    3. Instacart 추천 (비로그인/신규) - 시간대별 인기 상품

    응답 필드:
    - source: 추천 출처 (recipe, personalized, instacart)
    - recipe_name: 레시피 기반 추천 시 요리명 (예: "된장찌개")
    - ingredient_name: 레시피 기반 추천 시 부족 재료명 (예: "두부")
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 요청 데이터 파싱
        cart_product_ids = request.data.get('cart_product_ids', [])
        user_id = request.data.get('user_id')

        # 로그인 사용자면 user_id 사용
        if user_id is None and request.user.is_authenticated:
            user_id = request.user.id

        try:
            limit = int(request.data.get('limit', 9))
            limit = max(1, min(limit, 30))
        except (ValueError, TypeError):
            limit = 9

        # pred 서비스 호출
        result = pred_client.get_cart_unified_recommendations(
            user_id=user_id,
            cart_product_ids=cart_product_ids,
            limit=limit,
        )

        # 응답 반환
        return Response({
            'success': result.get('success', False),
            'recommendations': result.get('recommendations', []),
            'total_count': result.get('total_count', 0),
            'recipe_count': result.get('recipe_count', 0),
            'personalized_count': result.get('personalized_count', 0),
            'instacart_count': result.get('instacart_count', 0),
            'user_type': result.get('user_type', 'cold'),
            'processing_time_ms': result.get('processing_time_ms', 0),
            'message': result.get('message'),
        })


# ============================================================
# 레시피 GapFilling 추천 API
# ============================================================


class CartRecipeRecommendationsView(APIView):
    """장바구니 기반 레시피 추천 API

    POST /api/recommendations/cart-recipes/
    {
        "cart_product_ids": [1, 2, 3],
        "limit": 3
    }

    장바구니에 담긴 상품을 분석하여:
    1. 만들 수 있는 레시피를 추천
    2. 부족한 재료(Gap)에 해당하는 상품 추천
    3. 재료 매칭률이 높은 순으로 정렬

    비로그인 사용자도 사용 가능 (장바구니 ID 기반)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 요청 데이터 파싱
        cart_product_ids = request.data.get('cart_product_ids', [])
        try:
            limit = int(request.data.get('limit', 3))
            limit = max(1, min(limit, 10))
        except (ValueError, TypeError):
            limit = 3

        # 빈 장바구니 체크
        if not cart_product_ids:
            return Response({
                'success': False,
                'recipes': [],
                'cart_ingredients': [],
                'total_gap_count': 0,
                'message': '장바구니가 비어있습니다',
            })

        # pred 서비스 호출
        result = pred_client.get_cart_recipe_recommendations(
            cart_product_ids=cart_product_ids,
            limit=limit,
        )

        # 레시피 추천 결과 반환
        # pred 서비스 응답 그대로 전달 (프론트엔드에서 활용)
        return Response({
            'success': result.get('success', False),
            'recipes': result.get('recipes', []),
            'cart_ingredients': result.get('cart_ingredients', []),
            'total_gap_count': result.get('total_gap_count', 0),
            'processing_time_ms': result.get('processing_time_ms', 0),
            'message': result.get('message'),
        })


class RecipeDetailView(APIView):
    """레시피 상세 정보 API

    GET /api/recommendations/recipe/<recipe_id>/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, recipe_id):
        # pred 서비스 호출
        result = pred_client.get_recipe_detail(recipe_id)

        if result.get('error'):
            return Response({
                'success': False,
                'recipe': None,
                'ingredients': [],
                'message': result.get('error'),
            }, status=404)

        return Response({
            'success': True,
            'recipe': result.get('recipe'),
            'ingredients': result.get('ingredients', []),
        })


class RecipeSearchView(APIView):
    """레시피 검색 API

    GET /api/recommendations/recipe/search/?query=김치찌개&limit=20
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('query', '')
        category = request.query_params.get('category')

        try:
            limit = int(request.query_params.get('limit', 20))
            limit = max(1, min(limit, 100))
        except (ValueError, TypeError):
            limit = 20

        if not query:
            return Response({
                'recipes': [],
                'total_count': 0,
                'message': '검색어를 입력해주세요',
            })

        # pred 서비스 호출
        result = pred_client.search_recipes(
            query=query,
            category=category,
            limit=limit,
        )

        return Response({
            'recipes': result.get('recipes', []),
            'total_count': result.get('total_count', 0),
            'query': query,
            'category': category,
        })
