"""
추천 관련 API Views (REC-005)

최근 본 상품, 개인화 추천, 장바구니 기반 추천 등 추천 관련 API를 제공합니다.
"""
import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import F

from .models import UserProductStats, Product, Category, ProductStatus
from .serializers import ProductListSerializerV2
from .constants import CATEGORY_FIELD_TO_NAME
from .pred_client import (
    request_cart_recommendations,
    request_personalized_recommendations,
    request_time_deal_products,
    request_price_history,
)

logger = logging.getLogger(__name__)


class CartRecommendationsView(APIView):
    """장바구니 기반 상품 추천 API

    POST /api/recommendations/cart/

    장바구니에 담긴 상품들의 재료를 분석하여
    ML 모델(레시피 Gap Filling)로 추천 상품을 반환합니다.

    - **비회원 허용**: 인증 없이 사용 가능
    - **parsed_ingredients 활용**: 상품의 main_ingredient 필드 우선 사용

    Request Body:
        {
            "product_ids": [1, 2, 3],  # 장바구니 상품 ID 목록
            "limit": 20                # 추천 상품 개수 (기본 20, 최대 50)
        }

    Returns:
        200: {
            "products": [...],          # 추천 상품 목록
            "cart_ingredients": [...],  # 인식된 재료
            "model_version": "v2",      # 모델 버전
            "total_count": 15           # 추천 상품 개수
        }
        503: { "error": "추천 서비스 오류" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        limit = request.data.get('limit', 20)

        # 유효성 검사
        if not isinstance(product_ids, list):
            return Response(
                {'error': 'product_ids는 배열이어야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 정수만 필터링
        product_ids = [
            int(pid) for pid in product_ids
            if isinstance(pid, (int, str)) and str(pid).isdigit()
        ]

        # limit 범위 제한
        try:
            limit = int(limit)
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 20

        # 빈 장바구니 처리
        if not product_ids:
            return Response({
                'products': [],
                'cart_ingredients': [],
                'model_version': 'v2',
                'total_count': 0,
            })

        try:
            result = request_cart_recommendations(
                product_ids=product_ids,
                limit=limit,
            )
            return Response(result)

        except Exception as e:
            logger.error(f"장바구니 추천 API 호출 실패: {e}", exc_info=True)
            return Response(
                {'error': f'추천 서비스에 연결할 수 없습니다: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


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


class PersonalizedRecommendationsView(APIView):
    """개인화 추천 API

    GET /api/recommendations/personalized/

    회원/비회원 모두를 위한 개인화 추천을 제공합니다.
    메인 페이지 MD's Pick 섹션에서 사용됩니다.

    - **비회원 허용**: 비회원은 AIRScout 100% 기반 추천
    - **회원**: user_type(cold/lukewarm/warm)에 따라 AIRScout 가중치 적용
    - **장바구니 제외**: 현재 장바구니에 있는 상품은 추천에서 제외
    - **가중치 적용**: order > cart + 시간 감쇠
    - **항상 8개 반환**: 부족하면 인기 상품으로 채움

    Query Parameters:
        limit (int, optional): 추천 상품 개수 (기본: 8, 최대: 50)
        page_type (str, optional): 페이지 타입 (기본: home)
            - home: 메인 페이지
            - category: 카테고리 페이지
            - product_detail: 상품 상세 페이지
        category_id (int, optional): 카테고리 ID

    Returns:
        200: {
            "products": [...],          # 추천 상품 목록
            "user_type": "warm",        # 사용자 유형 (cold/lukewarm/warm/guest)
            "model_version": "v2",      # 모델 버전
            "total_count": 8,           # 추천 상품 개수
            "metadata": {...}           # 추가 메타데이터
        }
        503: { "error": "추천 서비스 오류" }
    """
    permission_classes = [permissions.AllowAny]  # 비회원도 허용

    def get(self, request):
        # 쿼리 파라미터 추출
        try:
            limit = int(request.query_params.get('limit', 8))
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 8

        page_type = request.query_params.get('page_type', 'home')
        if page_type not in ['home', 'category', 'product_detail']:
            page_type = 'home'

        category_id = request.query_params.get('category_id')
        if category_id:
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                category_id = None
        else:
            category_id = None

        # 비회원/회원 분기 처리
        if request.user.is_authenticated:
            user_id = request.user.id
            cart_product_ids = self._get_user_cart_product_ids(request.user)
        else:
            # 비회원: user_id=0으로 전달 → pred에서 is_guest=True 처리
            user_id = 0
            cart_product_ids = []

        try:
            result = request_personalized_recommendations(
                user_id=user_id,
                limit=limit,
                page_type=page_type,
                category_id=category_id,
                cart_product_ids=cart_product_ids,
            )
            return Response(result)

        except Exception as e:
            logger.error(f"개인화 추천 API 호출 실패: {e}", exc_info=True)
            return Response(
                {'error': f'추천 서비스에 연결할 수 없습니다: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    def _get_user_cart_product_ids(self, user) -> list:
        """사용자 장바구니 상품 ID 목록 조회

        Args:
            user: 현재 로그인한 사용자

        Returns:
            장바구니 상품 ID 목록
        """
        try:
            from orders.models import Cart
            cart_items = Cart.objects.filter(user=user).values_list('product_id', flat=True)
            return list(cart_items)
        except Exception as e:
            logger.warning(f"장바구니 조회 실패: {e}")
            return []


class TimeDealProductsView(APIView):
    """타임세일 가성비 상품 API

    GET /api/recommendations/time-deal/

    self_price_analyzer_v1.pkl 모델과 PriceScout 점수 기반으로
    가성비 상품을 추천합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **정렬 기준**: PriceScout 점수 내림차순
    - **필터링**: 가격 하락 상품만, ABNORMAL 상품 제외
    - **폴백**: 가격 하락 상품 부족 시 할인 상품으로 대체

    가격 상태 분류:
    - SUPER_SALE (< -10%): 특가 할인
    - DISCOUNT (-10% ~ -2%): 일반 할인
    - STABLE (-2% ~ +2%): 안정적
    - INCREASE (+2% ~ +20%): 소폭 상승

    Query Parameters:
        limit (int, optional): 조회할 상품 수 (기본: 10, 최대: 50)
        category_id (int, optional): 카테고리 ID 필터

    Returns:
        200: {
            "products": [...],          # 가성비 상품 목록
            "model_version": "v1",      # 모델 버전
            "total_count": 10           # 상품 개수
        }
        503: { "error": "추천 서비스 오류" }
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # 쿼리 파라미터 추출
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = max(1, min(limit, 50))
        except (ValueError, TypeError):
            limit = 10

        category_id = request.query_params.get('category_id')
        if category_id:
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                category_id = None
        else:
            category_id = None

        try:
            result = request_time_deal_products(
                limit=limit,
                category_id=category_id,
            )
            return Response(result)

        except Exception as e:
            logger.error(f"타임세일 상품 API 호출 실패: {e}", exc_info=True)
            return Response(
                {'error': f'타임세일 서비스에 연결할 수 없습니다: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class PriceHistoryView(APIView):
    """상품 가격 히스토리 API

    GET /api/recommendations/price-history/{product_id}/

    상품의 가격 변동 이력을 조회합니다.
    폴센트(Pollcent) 스타일의 가격 추적 그래프용 데이터를 제공합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **기간 설정**: 7일 ~ 365일 (기본 30일)

    Path Parameters:
        product_id (int): 상품 ID

    Query Parameters:
        days (int, optional): 조회 기간 (기본: 30, 범위: 7~365)

    Returns:
        200: {
            "product_id": int,
            "product_name": str,
            "history": [...],
            "statistics": {...}
        }
        404: { "error": "상품을 찾을 수 없습니다" }
        503: { "error": "서비스 오류" }
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        # 쿼리 파라미터 추출
        try:
            days = int(request.query_params.get('days', 30))
            days = max(7, min(days, 365))
        except (ValueError, TypeError):
            days = 30

        try:
            result = request_price_history(
                product_id=product_id,
                days=days,
            )
            return Response(result)

        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                return Response(
                    {'error': f'상품을 찾을 수 없습니다: {product_id}'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            logger.error(f"가격 히스토리 API 호출 실패: {e}", exc_info=True)
            return Response(
                {'error': f'가격 히스토리 서비스에 연결할 수 없습니다: {error_msg}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class OnboardingRecommendationsView(APIView):
    """온보딩 기반 추천 API

    GET /api/recommendations/onboarding/

    사용자의 온보딩 선호도를 기반으로 추천 상품을 반환합니다.
    - 가중치 높은 카테고리에서 인기 상품 우선
    - 제외(-1) 카테고리는 완전 배제
    - 온보딩 미완료 시 빈 배열 반환

    Query Parameters:
        limit (int): 추천 개수 (기본: 8, 최대: 20)

    Returns:
        200: {
            "products": [...],
            "total_count": 8,
            "source": "onboarding"
        }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 쿼리 파라미터 추출
        try:
            limit = int(request.query_params.get('limit', 8))
            limit = max(1, min(limit, 20))
        except (ValueError, TypeError):
            limit = 8

        # 온보딩 선호도 조회
        try:
            preference = request.user.category_preference
        except Exception:
            # 온보딩 미완료
            return Response({
                'products': [],
                'total_count': 0,
                'source': 'onboarding',
                'message': '온보딩을 완료해주세요.'
            })

        # 카테고리별 가중치 추출 (양수만, 내림차순)
        weighted_categories = preference.get_weighted_categories()
        excluded_categories = preference.get_excluded_categories()

        if not weighted_categories:
            return Response({
                'products': [],
                'total_count': 0,
                'source': 'onboarding',
                'message': '선호하는 카테고리가 없습니다.'
            })

        # DB 카테고리 이름 → ID 매핑
        category_name_to_id = self._get_category_name_to_id_map()

        # 제외 카테고리 ID 목록
        excluded_category_ids = []
        for field_name in excluded_categories:
            category_name = CATEGORY_FIELD_TO_NAME.get(field_name)
            if category_name and category_name in category_name_to_id:
                excluded_category_ids.append(category_name_to_id[category_name])

        # 가중치 기반 상품 조회
        products = self._fetch_weighted_products(
            weighted_categories,
            category_name_to_id,
            excluded_category_ids,
            limit
        )

        serializer = ProductListSerializerV2(products, many=True)
        return Response({
            'products': serializer.data,
            'total_count': len(products),
            'source': 'onboarding'
        })

    def _get_category_name_to_id_map(self) -> dict:
        """카테고리 이름 → ID 매핑 딕셔너리 반환"""
        categories = Category.objects.filter(parent__isnull=True).values('id', 'name')
        return {cat['name']: cat['id'] for cat in categories}

    def _fetch_weighted_products(
        self,
        weighted_categories: list,
        category_name_to_id: dict,
        excluded_category_ids: list,
        limit: int
    ) -> list:
        """가중치 비례로 각 카테고리에서 인기 상품 조회

        Args:
            weighted_categories: [(필드명, 점수), ...] 내림차순 정렬된 리스트
            category_name_to_id: 카테고리 이름 → ID 매핑
            excluded_category_ids: 제외할 카테고리 ID 목록
            limit: 총 상품 개수

        Returns:
            상품 리스트
        """
        # 총 가중치 합계 계산
        total_weight = sum(score for _, score in weighted_categories)
        if total_weight == 0:
            return []

        products = []
        remaining = limit

        for field_name, score in weighted_categories:
            if remaining <= 0:
                break

            # 이 카테고리에서 가져올 상품 수 계산
            category_name = CATEGORY_FIELD_TO_NAME.get(field_name)
            if not category_name or category_name not in category_name_to_id:
                continue

            category_id = category_name_to_id[category_name]

            # 비율 계산 (최소 1개)
            count = max(1, round(score / total_weight * limit))
            count = min(count, remaining)

            # 해당 카테고리에서 인기 상품 조회
            category_products = Product.objects.filter(
                category_id=category_id,
                status=ProductStatus.ACTIVE,
            ).exclude(
                category_id__in=excluded_category_ids
            ).select_related(
                'category',
                'stats',
                'inventory',
            ).prefetch_related(
                'images'
            ).annotate(
                popularity_score=F('stats__view_count') + F('stats__wishlist_count') * 2
            ).order_by('-popularity_score')[:count]

            products.extend(list(category_products))
            remaining -= len(category_products)

        # 부족하면 가중치 순서대로 추가 상품 가져오기
        if len(products) < limit:
            existing_ids = [p.id for p in products]
            additional_needed = limit - len(products)

            # 가중치 카테고리들에서 추가 상품
            for field_name, _ in weighted_categories:
                if additional_needed <= 0:
                    break

                category_name = CATEGORY_FIELD_TO_NAME.get(field_name)
                if not category_name or category_name not in category_name_to_id:
                    continue

                category_id = category_name_to_id[category_name]

                additional_products = Product.objects.filter(
                    category_id=category_id,
                    status=ProductStatus.ACTIVE,
                ).exclude(
                    id__in=existing_ids
                ).exclude(
                    category_id__in=excluded_category_ids
                ).select_related(
                    'category',
                    'stats',
                    'inventory',
                ).prefetch_related(
                    'images'
                ).annotate(
                    popularity_score=F('stats__view_count') + F('stats__wishlist_count') * 2
                ).order_by('-popularity_score')[:additional_needed]

                for p in additional_products:
                    if p.id not in existing_ids:
                        products.append(p)
                        existing_ids.append(p.id)
                        additional_needed -= 1

        return products[:limit]
