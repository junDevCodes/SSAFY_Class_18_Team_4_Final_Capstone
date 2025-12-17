"""
추천 API 라우터

추천 시스템의 메인 API 엔드포인트
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecipeSuggestionRequest,
    RecipeSuggestionResponse,
    ShoppingListRequest,
    PriceAnalysisRequest,
    PriceAnalysisResponse,
    ProductRecommendation,
    ModelResult,
    ErrorResponse,
    PageType,
    UserType,
    TimeContext,
    CartRecommendationRequest,
    CartRecommendationResponse,
    CartProductRecommendation,
    CartRecommendationSource,
)
from api.dependencies import (
    get_orchestrator,
    get_db,
    get_cache,
    get_time_context,
)
from core.orchestrator import RecommendationOrchestrator
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger
from ml.base import RecommendationContext

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "/",
    response_model=RecommendationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 오류"},
    },
    summary="추천 요청",
    description="사용자/페이지 컨텍스트 기반 상품 추천",
)
async def get_recommendations(
    request: RecommendationRequest,
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """추천 요청 처리

    페이지 타입과 사용자 컨텍스트에 따라 적절한 모델을 선택하여 추천 생성
    """
    start_time = datetime.now()

    try:
        # 추천 컨텍스트 생성
        context = RecommendationContext(
            user_id=request.user_id,
            page_type=request.page_type.value,
            category_id=request.category_id,
            product_id=request.product_id,
            cart_product_ids=request.cart_product_ids,
            search_query=request.search_query,
            time_context=time_context.value,
        )

        # 오케스트레이터를 통한 추천 실행
        result = await orchestrator.recommend(
            user_id=request.user_id,
            page_type=request.page_type.value,
            category_id=request.category_id,
            product_id=request.product_id,
            cart_items=request.cart_product_ids,
            limit=request.limit,
        )

        # 실행 시간 계산
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # 응답 구성
        recommendations = [
            ProductRecommendation(
                product_id=p.get("product_id") or p.get("id"),
                name=p.get("name", ""),
                price=p.get("price", 0),
                category_id=p.get("category_id"),
                seller_id=p.get("seller_id"),
                image_url=p.get("image_url"),
                recommendation_score=p.get("recommendation_score"),
                recommendation_source=p.get("recommendation_source"),
                original_price=p.get("original_price"),
                discount_rate=p.get("discount_rate"),
                average_rating=p.get("average_rating"),
                order_count=p.get("order_event_count"),
            )
            for p in result.get("recommendations", [])
        ]

        model_results = [
            ModelResult(
                model_name=mr.get("model_name", "unknown"),
                model_version=mr.get("version", "1.0.0"),
                execution_time_ms=mr.get("execution_time_ms", 0),
                product_count=mr.get("product_count", 0),
                confidence=mr.get("confidence", 0),
                error=mr.get("error"),
            )
            for mr in result.get("model_results", [])
        ]

        return RecommendationResponse(
            success=True,
            user_id=request.user_id,
            user_type=UserType(result.get("user_type", "cold")),
            page_type=request.page_type,
            recommendations=recommendations,
            total_count=len(recommendations),
            model_results=model_results,
            total_execution_time_ms=total_time,
            time_context=time_context,
            cached=result.get("cached", False),
        )

    except Exception as e:
        logger.error(
            "추천 요청 처리 실패",
            error=str(e),
            user_id=request.user_id,
            page_type=request.page_type.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "RECOMMENDATION_ERROR", "error_message": str(e)},
        )


@router.get(
    "/home",
    response_model=RecommendationResponse,
    summary="홈 페이지 추천",
    description="홈 페이지용 추천 (간편 API). user_id 없으면 Cold Start 추천",
)
async def get_home_recommendations(
    user_id: Optional[int] = Query(None, description="사용자 ID (없으면 Cold Start)"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """홈 페이지 추천 (비로그인 사용자도 지원)"""
    request = RecommendationRequest(
        user_id=user_id,
        page_type=PageType.HOME,
        limit=limit,
    )
    return await get_recommendations(request, orchestrator, time_context)


@router.get(
    "/category/{category_id}",
    response_model=RecommendationResponse,
    summary="카테고리 페이지 추천",
    description="특정 카테고리 페이지용 추천. user_id 없으면 Cold Start 추천",
)
async def get_category_recommendations(
    category_id: int,
    user_id: Optional[int] = Query(None, description="사용자 ID (없으면 Cold Start)"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """카테고리 페이지 추천 (비로그인 사용자도 지원)"""
    request = RecommendationRequest(
        user_id=user_id,
        page_type=PageType.CATEGORY,
        category_id=category_id,
        limit=limit,
    )
    return await get_recommendations(request, orchestrator, time_context)


@router.get(
    "/product/{product_id}",
    response_model=RecommendationResponse,
    summary="상품 상세 페이지 추천",
    description="특정 상품 페이지용 관련 상품 추천. user_id 없으면 Cold Start 추천",
)
async def get_product_recommendations(
    product_id: int,
    user_id: Optional[int] = Query(None, description="사용자 ID (없으면 Cold Start)"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """상품 상세 페이지 추천 (비로그인 사용자도 지원)"""
    request = RecommendationRequest(
        user_id=user_id,
        page_type=PageType.PRODUCT_DETAIL,
        product_id=product_id,
        limit=limit,
    )
    return await get_recommendations(request, orchestrator, time_context)


@router.post(
    "/cart",
    response_model=RecommendationResponse,
    summary="장바구니 페이지 추천",
    description="장바구니 상품 기반 추천. user_id 없으면 Cold Start 추천",
)
async def get_cart_recommendations(
    user_id: Optional[int] = Query(None, description="사용자 ID (없으면 Cold Start)"),
    cart_product_ids: list[int] = Query(..., description="장바구니 상품 ID 목록"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """장바구니 페이지 추천 (비로그인 사용자도 지원)"""
    request = RecommendationRequest(
        user_id=user_id,
        page_type=PageType.CART,
        cart_product_ids=cart_product_ids,
        limit=limit,
    )
    return await get_recommendations(request, orchestrator, time_context)


@router.get(
    "/deals",
    response_model=RecommendationResponse,
    summary="할인 상품 추천",
    description="가격 이상치 기반 할인 상품 추천. user_id 없으면 Cold Start 추천",
)
async def get_deal_recommendations(
    user_id: Optional[int] = Query(None, description="사용자 ID (없으면 Cold Start)"),
    category_id: Optional[int] = Query(None, description="카테고리 ID (선택적)"),
    limit: int = Query(10, ge=1, le=50, description="추천 개수"),
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    time_context: TimeContext = Depends(get_time_context),
):
    """할인 상품 추천 (PriceAnomaly 모델 기반, 비로그인 사용자도 지원)"""
    # 할인 추천은 별도 처리 필요 - 오케스트레이터 확장 시 구현
    request = RecommendationRequest(
        user_id=user_id,
        page_type=PageType.HOME,  # 임시
        category_id=category_id,
        limit=limit,
    )
    return await get_recommendations(request, orchestrator, time_context)


# ============================================================================
# 장바구니 통합 추천 API (레시피 > 개인화 > Instacart 우선순위)
# ============================================================================

@router.post(
    "/cart/unified",
    response_model=CartRecommendationResponse,
    summary="장바구니 통합 추천",
    description="""
    장바구니 상품 기반 통합 추천 API.

    **추천 우선순위:**
    1. **레시피 기반 추천** (최우선): 장바구니 재료로 만들 수 있는 레시피의 부족 재료 추천
       - 각 상품에 추천 레시피 요리명(recipe_name)과 재료명(ingredient_name) 포함
    2. **개인화 추천** (로그인 사용자): SVD 임베딩 기반 사용자 맞춤 추천
    3. **Instacart 추천** (비로그인/신규): 시간대별 인기 상품 추천

    **응답 필드 설명:**
    - `source`: 추천 출처 (recipe, personalized, instacart)
    - `recipe_name`: 레시피 기반 추천 시 해당 요리명 (예: "된장찌개")
    - `ingredient_name`: 레시피 기반 추천 시 부족 재료명 (예: "두부")
    """,
)
async def get_cart_unified_recommendations(
    request: CartRecommendationRequest,
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
    db: Database = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """장바구니 통합 추천

    레시피 > 개인화 > Instacart 우선순위로 추천 상품 반환
    """
    start_time = datetime.now()

    try:
        recommendations = []
        seen_product_ids = set()
        recipe_count = 0
        personalized_count = 0
        instacart_count = 0

        # 1. 레시피 기반 추천 (최우선 - 장바구니가 있을 때만)
        if request.cart_product_ids:
            recipe_recs = await _get_recipe_recommendations(
                cart_product_ids=request.cart_product_ids,
                limit=request.limit,
                db=db,
                cache=cache,
            )
            for rec in recipe_recs:
                if rec.product_id not in seen_product_ids:
                    seen_product_ids.add(rec.product_id)
                    recommendations.append(rec)
                    recipe_count += 1

        # 2. 개인화 추천 (로그인 사용자)
        remaining_slots = request.limit - len(recommendations)
        if remaining_slots > 0 and request.user_id:
            personalized_recs = await _get_personalized_recommendations(
                user_id=request.user_id,
                cart_product_ids=request.cart_product_ids,
                limit=remaining_slots * 2,  # 중복 제거 고려하여 더 많이 요청
                orchestrator=orchestrator,
            )
            for rec in personalized_recs:
                if rec.product_id not in seen_product_ids and len(recommendations) < request.limit:
                    seen_product_ids.add(rec.product_id)
                    recommendations.append(rec)
                    personalized_count += 1

        # 3. Instacart Cold Start 추천 (부족한 슬롯 채우기)
        remaining_slots = request.limit - len(recommendations)
        if remaining_slots > 0:
            instacart_recs = await _get_instacart_recommendations(
                cart_product_ids=request.cart_product_ids,
                limit=remaining_slots * 2,
                orchestrator=orchestrator,
            )
            for rec in instacart_recs:
                if rec.product_id not in seen_product_ids and len(recommendations) < request.limit:
                    seen_product_ids.add(rec.product_id)
                    recommendations.append(rec)
                    instacart_count += 1

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # 사용자 타입 결정
        user_type = UserType.COLD
        if request.user_id:
            # 오케스트레이터에서 사용자 타입 조회
            try:
                user_type_str = await orchestrator.determine_user_type(request.user_id)
                user_type = UserType(user_type_str)
            except Exception:
                user_type = UserType.COLD

        return CartRecommendationResponse(
            success=True,
            recommendations=recommendations,
            total_count=len(recommendations),
            recipe_count=recipe_count,
            personalized_count=personalized_count,
            instacart_count=instacart_count,
            user_type=user_type,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"장바구니 통합 추천 실패: {e}", exc_info=True)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return CartRecommendationResponse(
            success=False,
            recommendations=[],
            total_count=0,
            processing_time_ms=processing_time,
            message=f"추천 처리 중 오류: {str(e)}",
        )


async def _get_recipe_recommendations(
    cart_product_ids: list[int],
    limit: int,
    db: Database,
    cache: CacheManager,
) -> list[CartProductRecommendation]:
    """레시피 기반 추천 (부족 재료 상품 + 요리명)"""
    try:
        from ml.models.recipe_pickle_model import RecipePickleModel

        # RecipePickleModel 인스턴스 생성 및 초기화
        recipe_model = RecipePickleModel(db, cache)
        await recipe_model.initialize()

        if not recipe_model._use_pickle:
            logger.warning("레시피 Pickle 모델이 로드되지 않음")
            return []

        # 레시피 추천 조회
        result = await recipe_model.get_cart_recipe_recommendations(
            cart_product_ids=cart_product_ids,
            limit=3,  # 상위 3개 레시피만
        )

        recommendations = []
        recipes = result.get("recipes", [])

        for recipe in recipes:
            recipe_name = recipe.get("name", "")  # 요리명 (예: 된장찌개)
            gap_products = recipe.get("recommended_products", [])

            for product in gap_products:
                if len(recommendations) >= limit:
                    break

                recommendations.append(CartProductRecommendation(
                    product_id=product.get("product_id"),
                    name=product.get("name", ""),
                    price=product.get("price", 0),
                    original_price=product.get("original_price"),
                    image_url=product.get("main_image"),
                    category_id=product.get("category_id"),
                    source=CartRecommendationSource.RECIPE,
                    recommendation_score=recipe.get("match_ratio", 0),
                    recipe_name=recipe_name,  # 레시피 요리명
                    ingredient_name=product.get("ingredient", ""),  # 부족 재료명
                ))

            if len(recommendations) >= limit:
                break

        return recommendations

    except Exception as e:
        logger.warning(f"레시피 추천 조회 실패: {e}")
        return []


async def _get_personalized_recommendations(
    user_id: int,
    cart_product_ids: list[int],
    limit: int,
    orchestrator: RecommendationOrchestrator,
) -> list[CartProductRecommendation]:
    """개인화 기반 추천"""
    try:
        # self 모델만 사용하여 개인화 추천
        self_model = orchestrator.models.get("self")
        if not self_model:
            logger.warning("self 모델이 오케스트레이터에 등록되지 않음")
            return []

        from ml.base import RecommendationContext

        context = RecommendationContext(
            user_id=user_id,
            page_type="cart",
            cart_product_ids=cart_product_ids,
            user_type="warm",  # 개인화 추천은 warm 사용자 대상
        )

        result = await self_model.recommend(context, limit)

        # RecommendationResult 객체에서 products 추출
        products = result.products if hasattr(result, 'products') else []
        logger.info(f"개인화 추천 결과: {len(products)}개 상품")

        recommendations = []
        for product in products:
            recommendations.append(CartProductRecommendation(
                product_id=product.get("product_id") or product.get("id"),
                name=product.get("name", ""),
                price=product.get("price", 0),
                original_price=product.get("original_price"),
                discount_rate=product.get("discount_rate"),
                image_url=product.get("image_url") or product.get("main_image"),
                category_id=product.get("category_id"),
                source=CartRecommendationSource.PERSONALIZED,
                recommendation_score=product.get("recommendation_score"),
            ))

        return recommendations

    except Exception as e:
        logger.warning(f"개인화 추천 조회 실패: {e}")
        return []


async def _get_instacart_recommendations(
    cart_product_ids: list[int],
    limit: int,
    orchestrator: RecommendationOrchestrator,
) -> list[CartProductRecommendation]:
    """Instacart Cold Start 추천"""
    try:
        instacart_model = orchestrator.models.get("instacart")
        if not instacart_model:
            logger.warning("instacart 모델이 오케스트레이터에 등록되지 않음")
            return []

        from ml.base import RecommendationContext
        from datetime import datetime

        now = datetime.now()
        context = RecommendationContext(
            user_id=0,  # Cold Start이므로 0
            page_type="cart",
            cart_product_ids=cart_product_ids,
            user_type="cold",
            day_of_week=now.weekday(),
            hour_of_day=now.hour,
            is_weekend=now.weekday() >= 5,
        )

        result = await instacart_model.recommend(context, limit)

        # RecommendationResult 객체에서 products 추출
        products = result.products if hasattr(result, 'products') else []
        logger.info(f"Instacart 추천 결과: {len(products)}개 상품")

        recommendations = []
        for product in products:
            recommendations.append(CartProductRecommendation(
                product_id=product.get("product_id") or product.get("id"),
                name=product.get("name", ""),
                price=product.get("price", 0),
                original_price=product.get("original_price"),
                discount_rate=product.get("discount_rate"),
                image_url=product.get("image_url") or product.get("main_image"),
                category_id=product.get("category_id"),
                source=CartRecommendationSource.INSTACART,
                recommendation_score=product.get("recommendation_score"),
            ))

        return recommendations

    except Exception as e:
        logger.warning(f"Instacart 추천 조회 실패: {e}")
        return []
