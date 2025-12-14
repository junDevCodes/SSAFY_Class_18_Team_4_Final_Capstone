"""
레시피 API 라우터

레시피 갭필링 및 관련 엔드포인트
- 장바구니 기반 레시피 추천
- 부족한 재료(Gap) 상품 추천
- Pickle 모델 기반 빠른 추천
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import get_db, get_cache
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger
from data.repositories import (
    RecipeRepository,
    RecipeIngredientRepository,
    RecipeGapFillingRepository,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/recipe", tags=["recipe"])


# ============================================================
# Pydantic 스키마 정의
# ============================================================

class CartRecipeRequest(BaseModel):
    """장바구니 레시피 추천 요청"""
    cart_product_ids: List[int] = Field(..., description="장바구니 상품 ID 목록", min_items=1)
    limit: int = Field(3, ge=1, le=10, description="추천 레시피 개수")


class GapProduct(BaseModel):
    """Gap 재료 상품"""
    product_id: int
    name: str
    price: int
    original_price: Optional[int] = None
    main_image: Optional[str] = None
    ingredient: str = Field(..., description="해당 재료명")


class RecipeRecommendation(BaseModel):
    """추천 레시피"""
    recipe_id: int
    name: str = Field(..., description="요리명 (CKG_NM)")
    title: Optional[str] = Field(None, description="레시피 제목")
    match_ratio: float = Field(..., description="재료 매칭률 (0-1)")
    gap_count: int = Field(..., description="부족한 재료 수")
    gap_ingredients: List[str] = Field(default_factory=list, description="부족한 재료 목록")
    matched_ingredients: List[str] = Field(default_factory=list, description="매칭된 재료 목록")
    recommended_products: List[GapProduct] = Field(default_factory=list, description="추천 상품 목록")
    view_count: int = Field(0, description="레시피 조회수")
    matched_dish: Optional[str] = Field(None, description="상품명에서 검출된 요리명 (예: 삼계탕)")
    is_dish_matched: bool = Field(False, description="요리명 기반 매칭 여부")


class CartRecipeResponse(BaseModel):
    """장바구니 레시피 추천 응답"""
    success: bool = True
    recipes: List[RecipeRecommendation] = Field(default_factory=list)
    cart_ingredients: List[str] = Field(default_factory=list, description="인식된 재료 목록")
    detected_dishes: List[str] = Field(default_factory=list, description="상품명에서 검출된 요리명 목록")
    total_gap_count: int = Field(0, description="전체 부족 재료 수")
    processing_time_ms: float = Field(0, description="처리 시간 (ms)")
    message: Optional[str] = None


# ============================================================
# 전역 모델 인스턴스 (지연 로딩)
# ============================================================

_recipe_pickle_model = None


async def get_recipe_pickle_model(
    db: Database = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """레시피 Pickle 모델 의존성 주입"""
    global _recipe_pickle_model

    if _recipe_pickle_model is None:
        from ml.models.recipe_pickle_model import RecipePickleModel
        _recipe_pickle_model = RecipePickleModel(db, cache)
        await _recipe_pickle_model.initialize()

    return _recipe_pickle_model


# ============================================================
# 장바구니 레시피 추천 API (신규)
# ============================================================

@router.post(
    "/cart-recommendations",
    response_model=CartRecipeResponse,
    summary="장바구니 기반 레시피 추천",
    description="""
    장바구니 상품을 분석하여 만들 수 있는 레시피를 추천합니다.

    기능:
    - 상품명 → 재료명 퍼지 매칭
    - 레시피 Gap 분석 (부족한 재료 식별)
    - 부족한 재료에 해당하는 상품 추천
    - 메인 재료 우선 추천

    사용 예시:
    ```
    POST /api/v1/recipe/cart-recommendations
    {
        "cart_product_ids": [123, 456, 789],
        "limit": 3
    }
    ```
    """,
)
async def get_cart_recipe_recommendations(
    request: CartRecipeRequest,
    model=Depends(get_recipe_pickle_model),
    db: Database = Depends(get_db),
):
    """장바구니 기반 레시피 추천

    프로세스:
    1. 장바구니 상품명 조회
    2. 상품명 → 재료명 퍼지 매칭
    3. Pickle 모델로 레시피 Gap 분석
    4. 부족한 재료 → 상품 검색
    """
    start_time = datetime.now()

    try:
        result = await model.get_cart_recipe_recommendations(
            cart_product_ids=request.cart_product_ids,
            limit=request.limit,
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # 응답 변환
        recipes = []
        for r in result.get('recipes', []):
            recommended_products = []
            for p in r.get('recommended_products', []):
                recommended_products.append(GapProduct(
                    product_id=p.get('product_id'),
                    name=p.get('name', ''),
                    price=p.get('price', 0),
                    original_price=p.get('original_price'),
                    main_image=p.get('main_image'),
                    ingredient=p.get('ingredient', ''),
                ))

            recipes.append(RecipeRecommendation(
                recipe_id=r.get('recipe_id', 0),
                name=r.get('name', ''),
                title=r.get('title'),
                match_ratio=r.get('match_ratio', 0),
                gap_count=r.get('gap_count', 0),
                gap_ingredients=r.get('gap_ingredients', []),
                matched_ingredients=r.get('matched_ingredients', []),
                recommended_products=recommended_products,
                view_count=r.get('view_count', 0),
                matched_dish=r.get('matched_dish'),  # 신규: 검출된 요리명
                is_dish_matched=r.get('is_dish_matched', False),  # 신규: 요리명 매칭 여부
            ))

        return CartRecipeResponse(
            success=True,
            recipes=recipes,
            cart_ingredients=result.get('cart_ingredients', []),
            detected_dishes=result.get('detected_dishes', []),  # 신규: 검출된 요리명 목록
            total_gap_count=result.get('total_gap_count', 0),
            processing_time_ms=processing_time,
            message=result.get('message'),
        )

    except Exception as e:
        logger.error(f"장바구니 레시피 추천 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return CartRecipeResponse(
            success=False,
            recipes=[],
            cart_ingredients=[],
            processing_time_ms=processing_time,
            message=f"추천 처리 중 오류: {str(e)}",
        )


@router.get(
    "/cart-recommendations",
    response_model=CartRecipeResponse,
    summary="장바구니 기반 레시피 추천 (GET)",
    description="GET 방식 장바구니 레시피 추천 (쿼리 파라미터 사용)",
)
async def get_cart_recipe_recommendations_get(
    cart_product_ids: List[int] = Query(..., description="장바구니 상품 ID 목록"),
    limit: int = Query(3, ge=1, le=10, description="추천 레시피 개수"),
    model=Depends(get_recipe_pickle_model),
    db: Database = Depends(get_db),
):
    """GET 방식 장바구니 레시피 추천"""
    request = CartRecipeRequest(cart_product_ids=cart_product_ids, limit=limit)
    return await get_cart_recipe_recommendations(request, model, db)


# ============================================================
# 기존 API (하위 호환성)
# ============================================================


@router.post(
    "/gap-fill",
    summary="레시피 갭필링",
    description="장바구니 상품 기반 레시피 매칭 및 부족 재료 추천",
)
async def gap_fill_recipes(
    cart_product_ids: List[int] = Query(..., description="장바구니 상품 ID 목록"),
    max_gap_count: int = Query(3, ge=1, le=10, description="최대 부족 재료 수"),
    limit: int = Query(5, ge=1, le=20, description="추천 레시피 수"),
    db: Database = Depends(get_db),
):
    """레시피 갭필링

    프로세스:
    1. 장바구니 상품 → 재료 추출
    2. 재료 → 매칭 레시피 탐색
    3. 레시피 → 부족 재료 → 상품 추천
    """
    start_time = datetime.now()

    if not cart_product_ids:
        return {
            "matched_recipes": [],
            "gap_products": [],
            "message": "장바구니가 비어있습니다",
        }

    gap_repo = RecipeGapFillingRepository(db)

    # 갭필링 레시피 찾기
    recipes_with_gap = await gap_repo.find_recipes_with_gap(
        cart_product_ids=cart_product_ids,
        max_gap_count=max_gap_count,
        limit=limit,
    )

    if not recipes_with_gap:
        return {
            "matched_recipes": [],
            "gap_products": [],
            "message": "매칭되는 레시피가 없습니다",
        }

    # 부족 재료에 해당하는 상품 찾기
    all_missing_ingredient_ids = []
    for recipe in recipes_with_gap:
        missing_ids = recipe.get("missing_ingredient_ids", [])
        all_missing_ingredient_ids.extend(missing_ids)

    gap_products = []
    if all_missing_ingredient_ids:
        gap_products = await gap_repo.get_gap_filling_products(
            missing_ingredient_ids=list(set(all_missing_ingredient_ids))
        )

    processing_time = (datetime.now() - start_time).total_seconds() * 1000

    return {
        "matched_recipes": recipes_with_gap,
        "gap_products": gap_products,
        "cart_product_count": len(cart_product_ids),
        "processing_time_ms": processing_time,
    }


@router.get(
    "/search",
    summary="레시피 검색",
    description="레시피명 또는 재료로 레시피 검색",
)
async def search_recipes(
    query: str = Query(..., min_length=1, description="검색어"),
    category: Optional[str] = Query(None, description="카테고리"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수"),
    db: Database = Depends(get_db),
):
    """레시피 검색"""
    recipe_repo = RecipeRepository(db)

    recipes = await recipe_repo.search_recipes(
        query=query,
        category=category,
        limit=limit,
    )

    return {
        "recipes": recipes,
        "total_count": len(recipes),
        "query": query,
        "category": category,
    }


@router.get(
    "/{recipe_id}",
    summary="레시피 상세 조회",
    description="레시피 상세 정보 및 재료 목록 조회",
)
async def get_recipe_detail(
    recipe_id: int,
    db: Database = Depends(get_db),
):
    """레시피 상세 조회"""
    recipe_repo = RecipeRepository(db)
    ing_repo = RecipeIngredientRepository(db)

    # 레시피 정보 조회
    recipe = await recipe_repo.get_by_id(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"레시피 {recipe_id}을(를) 찾을 수 없습니다",
        )

    # 재료 목록 조회
    ingredients = await ing_repo.get_recipe_ingredients(recipe_id)

    return {
        "recipe": recipe,
        "ingredients": ingredients,
    }


@router.get(
    "/{recipe_id}/products",
    summary="레시피 재료 상품 조회",
    description="레시피 재료에 해당하는 상품 목록 조회",
)
async def get_recipe_products(
    recipe_id: int,
    db: Database = Depends(get_db),
):
    """레시피 재료에 매핑된 상품 조회"""
    gap_repo = RecipeGapFillingRepository(db)

    products = await gap_repo.get_recipe_products(recipe_id)

    return {
        "recipe_id": recipe_id,
        "products": products,
        "total_count": len(products),
    }


@router.get(
    "/popular",
    summary="인기 레시피 조회",
    description="평점 및 좋아요 기반 인기 레시피",
)
async def get_popular_recipes(
    category: Optional[str] = Query(None, description="카테고리"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수"),
    db: Database = Depends(get_db),
):
    """인기 레시피 조회"""
    recipe_repo = RecipeRepository(db)

    recipes = await recipe_repo.get_popular_recipes(
        category=category,
        limit=limit,
    )

    return {
        "recipes": recipes,
        "total_count": len(recipes),
        "category": category,
    }


@router.get(
    "/by-ingredients",
    summary="재료 기반 레시피 검색",
    description="보유한 재료로 만들 수 있는 레시피 검색",
)
async def get_recipes_by_ingredients(
    ingredient_ids: List[int] = Query(..., description="재료 ID 목록"),
    min_match_ratio: float = Query(0.3, ge=0, le=1.0, description="최소 매칭 비율"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수"),
    db: Database = Depends(get_db),
):
    """재료 기반 레시피 검색"""
    ing_repo = RecipeIngredientRepository(db)

    recipes = await ing_repo.find_recipes_by_ingredients(
        ingredient_ids=ingredient_ids,
        min_match_ratio=min_match_ratio,
        limit=limit,
    )

    return {
        "recipes": recipes,
        "total_count": len(recipes),
        "ingredient_count": len(ingredient_ids),
        "min_match_ratio": min_match_ratio,
    }
