"""
추천 API 스키마

추천 API의 요청/응답 Pydantic 모델
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class PageType(str, Enum):
    """페이지 타입"""
    HOME = "home"
    CATEGORY = "category"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    SEARCH = "search"


class UserType(str, Enum):
    """사용자 유형"""
    COLD = "cold"
    LUKEWARM = "lukewarm"
    WARM = "warm"


class TimeContext(str, Enum):
    """시간 컨텍스트"""
    MORNING = "morning"  # 06:00-11:00
    LUNCH = "lunch"  # 11:00-14:00
    DINNER = "dinner"  # 17:00-21:00
    NIGHT = "night"  # 21:00-06:00
    DEFAULT = "default"


# ============================================================================
# 요청 스키마
# ============================================================================

class RecommendationRequest(BaseModel):
    """추천 요청"""

    user_id: Optional[int] = Field(None, description="사용자 ID (없으면 Cold Start)")
    page_type: PageType = Field(..., description="페이지 타입")
    category_id: Optional[int] = Field(None, description="카테고리 ID (category 페이지용)")
    product_id: Optional[int] = Field(None, description="상품 ID (product_detail 페이지용)")
    cart_product_ids: List[int] = Field(default_factory=list, description="장바구니 상품 ID 목록")
    search_query: Optional[str] = Field(None, description="검색어 (search 페이지용)")
    limit: int = Field(10, ge=1, le=50, description="추천 개수")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "page_type": "home",
                "cart_product_ids": [1, 2, 3],
                "limit": 10,
            }
        }


class RecipeSuggestionRequest(BaseModel):
    """레시피 제안 요청"""

    cart_product_ids: List[int] = Field(..., description="장바구니 상품 ID 목록")
    limit: int = Field(3, ge=1, le=10, description="제안 개수")


class ShoppingListRequest(BaseModel):
    """장보기 목록 요청"""

    recipe_id: int = Field(..., description="레시피 ID")
    owned_ingredient_ids: List[int] = Field(
        default_factory=list, description="보유 재료 ID 목록"
    )


class PriceAnalysisRequest(BaseModel):
    """가격 분석 요청"""

    product_id: int = Field(..., description="상품 ID")


# ============================================================================
# 응답 스키마
# ============================================================================

class ProductRecommendation(BaseModel):
    """추천 상품 정보"""

    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    price: int = Field(..., description="가격")
    category_id: Optional[int] = Field(None, description="카테고리 ID")
    seller_id: Optional[int] = Field(None, description="판매자 ID")
    image_url: Optional[str] = Field(None, description="이미지 URL")

    # 추천 관련 메타데이터
    recommendation_score: Optional[float] = Field(None, description="추천 점수")
    recommendation_source: Optional[str] = Field(None, description="추천 출처")

    # 선택적 추가 정보
    original_price: Optional[int] = Field(None, description="원가")
    discount_rate: Optional[float] = Field(None, description="할인율")
    average_rating: Optional[float] = Field(None, description="평균 평점")
    order_count: Optional[int] = Field(None, description="주문 수")


class ModelResult(BaseModel):
    """개별 모델 결과"""

    model_name: str = Field(..., description="모델 이름")
    model_version: str = Field(..., description="모델 버전")
    execution_time_ms: float = Field(..., description="실행 시간 (ms)")
    product_count: int = Field(..., description="추천 상품 수")
    confidence: float = Field(..., description="신뢰도")
    error: Optional[str] = Field(None, description="에러 메시지")


class RecommendationResponse(BaseModel):
    """추천 응답"""

    success: bool = Field(..., description="성공 여부")
    user_id: Optional[int] = Field(None, description="사용자 ID (비로그인 시 None)")
    user_type: UserType = Field(..., description="사용자 유형")
    page_type: PageType = Field(..., description="페이지 타입")

    recommendations: List[ProductRecommendation] = Field(
        ..., description="추천 상품 목록"
    )
    total_count: int = Field(..., description="총 추천 수")

    # 모델별 결과 메타데이터
    model_results: List[ModelResult] = Field(
        default_factory=list, description="모델별 결과"
    )
    total_execution_time_ms: float = Field(..., description="총 실행 시간 (ms)")

    # 컨텍스트 정보
    time_context: TimeContext = Field(TimeContext.DEFAULT, description="시간 컨텍스트")
    cached: bool = Field(False, description="캐시 히트 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_id": 123,
                "user_type": "warm",
                "page_type": "home",
                "recommendations": [
                    {
                        "product_id": 1,
                        "name": "유기농 사과",
                        "price": 5900,
                        "category_id": 10,
                        "recommendation_score": 0.95,
                    }
                ],
                "total_count": 10,
                "model_results": [
                    {
                        "model_name": "self_personalized",
                        "model_version": "1.0.0",
                        "execution_time_ms": 45.2,
                        "product_count": 10,
                        "confidence": 0.85,
                    }
                ],
                "total_execution_time_ms": 150.5,
                "time_context": "morning",
                "cached": False,
            }
        }


# ============================================================================
# 레시피/가격 분석 응답 스키마
# ============================================================================

class RecipeInfo(BaseModel):
    """레시피 정보"""

    recipe_id: int = Field(..., description="레시피 ID")
    recipe_name: str = Field(..., description="레시피명")
    description: Optional[str] = Field(None, description="설명")
    cooking_time: Optional[int] = Field(None, description="조리 시간 (분)")
    difficulty: Optional[str] = Field(None, description="난이도")
    image_url: Optional[str] = Field(None, description="이미지 URL")
    match_percentage: Optional[float] = Field(None, description="재료 매칭률")
    gap_count: Optional[int] = Field(None, description="부족 재료 수")


class MissingIngredient(BaseModel):
    """부족 재료 정보"""

    ingredient_id: int = Field(..., description="재료 ID")
    ingredient_name: str = Field(..., description="재료명")
    recommended_product: Optional[ProductRecommendation] = Field(
        None, description="추천 상품"
    )


class RecipeSuggestion(BaseModel):
    """레시피 제안"""

    recipe: RecipeInfo = Field(..., description="레시피 정보")
    missing_ingredients: List[MissingIngredient] = Field(
        default_factory=list, description="부족 재료 목록"
    )
    total_missing_cost: int = Field(0, description="부족 재료 총 비용")


class RecipeSuggestionResponse(BaseModel):
    """레시피 제안 응답"""

    success: bool = Field(..., description="성공 여부")
    suggestions: List[RecipeSuggestion] = Field(
        default_factory=list, description="레시피 제안 목록"
    )
    cart_product_count: int = Field(..., description="장바구니 상품 수")


class PriceAnalysisResponse(BaseModel):
    """가격 분석 응답"""

    success: bool = Field(..., description="성공 여부")
    product_id: int = Field(..., description="상품 ID")
    current_price: int = Field(..., description="현재 가격")
    avg_price_90d: Optional[float] = Field(None, description="90일 평균 가격")
    min_price_90d: Optional[int] = Field(None, description="90일 최저 가격")
    max_price_90d: Optional[int] = Field(None, description="90일 최고 가격")
    z_score: float = Field(..., description="Z-score")
    is_anomaly: bool = Field(..., description="이상치 여부")
    anomaly_type: Optional[str] = Field(None, description="이상치 유형")
    recent_change: Optional[int] = Field(None, description="최근 변동액")
    recent_change_rate: Optional[float] = Field(None, description="최근 변동률")


# ============================================================================
# 장바구니 통합 추천 스키마
# ============================================================================

class CartRecommendationSource(str, Enum):
    """추천 출처"""
    RECIPE = "recipe"  # 레시피 기반 추천 (요리명 포함)
    PERSONALIZED = "personalized"  # 개인화 추천
    INSTACART = "instacart"  # Instacart Cold Start 추천


class CartProductRecommendation(BaseModel):
    """장바구니 추천 상품 (레시피 요리명 포함)"""

    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    price: int = Field(..., description="가격")
    original_price: Optional[int] = Field(None, description="원가")
    discount_rate: Optional[float] = Field(None, description="할인율")
    image_url: Optional[str] = Field(None, description="이미지 URL")
    category_id: Optional[int] = Field(None, description="카테고리 ID")

    # 추천 출처 정보
    source: CartRecommendationSource = Field(..., description="추천 출처")
    recommendation_score: Optional[float] = Field(None, description="추천 점수")

    # 레시피 기반 추천인 경우만 사용
    recipe_name: Optional[str] = Field(None, description="추천 레시피 요리명 (레시피 추천 시)")
    ingredient_name: Optional[str] = Field(None, description="부족 재료명 (레시피 추천 시)")


class CartRecommendationRequest(BaseModel):
    """장바구니 통합 추천 요청"""

    user_id: Optional[int] = Field(None, description="사용자 ID (없으면 Cold Start)")
    cart_product_ids: List[int] = Field(..., description="장바구니 상품 ID 목록", min_length=0)
    limit: int = Field(9, ge=1, le=30, description="추천 개수")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "cart_product_ids": [1, 2, 3],
                "limit": 9,
            }
        }


class CartRecommendationResponse(BaseModel):
    """장바구니 통합 추천 응답"""

    success: bool = Field(True, description="성공 여부")
    recommendations: List[CartProductRecommendation] = Field(
        default_factory=list, description="추천 상품 목록"
    )
    total_count: int = Field(0, description="추천 상품 수")

    # 추천 출처별 개수
    recipe_count: int = Field(0, description="레시피 기반 추천 수")
    personalized_count: int = Field(0, description="개인화 추천 수")
    instacart_count: int = Field(0, description="Instacart 추천 수")

    # 메타데이터
    user_type: UserType = Field(UserType.COLD, description="사용자 유형")
    processing_time_ms: float = Field(0, description="처리 시간 (ms)")
    message: Optional[str] = Field(None, description="추가 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "recommendations": [
                    {
                        "product_id": 1,
                        "name": "대파 300g",
                        "price": 1500,
                        "image_url": "/images/product.jpg",
                        "source": "recipe",
                        "recipe_name": "된장찌개",
                        "ingredient_name": "대파",
                    },
                    {
                        "product_id": 2,
                        "name": "유기농 양파",
                        "price": 3900,
                        "image_url": "/images/onion.jpg",
                        "source": "personalized",
                    },
                ],
                "total_count": 9,
                "recipe_count": 3,
                "personalized_count": 4,
                "instacart_count": 2,
                "user_type": "warm",
                "processing_time_ms": 120.5,
            }
        }


# ============================================================================
# 에러 응답 스키마
# ============================================================================

class ErrorResponse(BaseModel):
    """에러 응답"""

    success: bool = Field(False, description="성공 여부")
    error_code: str = Field(..., description="에러 코드")
    error_message: str = Field(..., description="에러 메시지")
    detail: Optional[Dict[str, Any]] = Field(None, description="상세 정보")


class HealthResponse(BaseModel):
    """헬스 체크 응답"""

    status: str = Field(..., description="상태")
    version: str = Field(..., description="버전")
    database: str = Field(..., description="데이터베이스 상태")
    cache: str = Field(..., description="캐시 상태")
    timestamp: datetime = Field(..., description="타임스탬프")
