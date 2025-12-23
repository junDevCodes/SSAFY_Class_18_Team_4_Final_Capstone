"""
SelF Pred API - ML 기반 추천 서버

장바구니 상품 기반 레시피 추천 및 상품 추천 API를 제공합니다.
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.database import db
from core.logging import get_logger
from ml.model_loader import model_loader

logger = get_logger(__name__)

# 전역 모델 인스턴스
_recipe_model = None


async def get_recipe_model():
    """RecipePickleModel 싱글톤 인스턴스 반환"""
    global _recipe_model
    if _recipe_model is None:
        from ml.models.recipe_pickle_model import RecipePickleModel
        _recipe_model = RecipePickleModel(db=db)
        await _recipe_model.initialize()
        logger.info("RecipePickleModel 초기화 완료")
    return _recipe_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리

    Startup: DB 연결, 모델 로드
    Shutdown: DB 연결 종료
    """
    # Startup
    logger.info("서버 시작 - DB 연결 및 모델 로드 중...")
    try:
        await db.connect()
        await model_loader.load_all_models()
        # 레시피 모델 미리 초기화
        await get_recipe_model()
        logger.info("서버 시작 완료")
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        raise

    yield

    # Shutdown
    logger.info("서버 종료 - DB 연결 해제 중...")
    await db.disconnect()
    logger.info("서버 종료 완료")


app = FastAPI(
    title="SelF Pred API",
    version="1.0.0",
    description="장바구니 기반 레시피 추천 및 상품 추천 API",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic 모델 ====================

class CartRecommendationRequest(BaseModel):
    """장바구니 추천 요청"""
    product_ids: List[int] = Field(..., description="장바구니 상품 ID 목록")
    limit: int = Field(default=20, ge=1, le=50, description="추천 상품 개수 (최대 50)")


class RecommendedProduct(BaseModel):
    """추천 상품 정보"""
    product_id: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품명")
    slug: str = Field(..., description="상품 slug")
    price: int = Field(..., description="가격")
    original_price: Optional[int] = Field(None, description="원가")
    main_image: Optional[str] = Field(None, description="대표 이미지 URL")
    order_count: int = Field(default=0, description="주문 수")
    ingredient: str = Field(default="", description="이 상품이 커버하는 재료")


class CartRecommendationResponse(BaseModel):
    """장바구니 추천 응답"""
    products: List[RecommendedProduct] = Field(default_factory=list, description="추천 상품 목록")
    cart_ingredients: List[str] = Field(default_factory=list, description="장바구니에서 인식된 재료")
    model_version: str = Field(default="v2", description="사용된 모델 버전")
    total_count: int = Field(default=0, description="추천 상품 개수")


# ==================== API 엔드포인트 ====================

@app.get("/")
async def read_root():
    """루트 경로 응답"""
    return {
        "message": "SelF Pred API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # DB 연결 상태 확인
    db_healthy = await db.health_check()
    model_loaded = model_loader.is_loaded

    status = "healthy" if db_healthy and model_loaded else "degraded"

    return {
        "status": status,
        "db": "connected" if db_healthy else "disconnected",
        "models": "loaded" if model_loaded else "not_loaded",
        "loaded_models": model_loader.loaded_models,
    }


@app.post("/api/cart-recommendations", response_model=CartRecommendationResponse)
async def cart_recommendations(request: CartRecommendationRequest):
    """장바구니 기반 상품 추천 API

    장바구니에 담긴 상품들의 재료를 분석하여
    레시피 Gap Filling 모델로 추천 상품을 반환합니다.

    - **인증 불필요**: 회원/비회원 모두 사용 가능
    - **parsed_ingredients 활용**: 상품의 main_ingredient 필드 우선 사용

    Args:
        request: 장바구니 상품 ID 목록 및 추천 개수

    Returns:
        추천 상품 목록, 인식된 재료, 모델 버전
    """
    # 빈 장바구니 처리
    if not request.product_ids:
        return CartRecommendationResponse(
            products=[],
            cart_ingredients=[],
            model_version="v2",
            total_count=0,
        )

    try:
        model = await get_recipe_model()
        result = await model.get_simple_cart_recommendations(
            cart_product_ids=request.product_ids,
            limit=request.limit,
        )

        # 응답 변환
        products = [
            RecommendedProduct(
                product_id=p.get("product_id"),
                name=p.get("name", ""),
                slug=p.get("slug", ""),
                price=p.get("price", 0),
                original_price=p.get("original_price"),
                main_image=p.get("main_image"),
                order_count=p.get("order_count", 0),
                ingredient=p.get("ingredient", ""),
            )
            for p in result.get("products", [])
        ]

        return CartRecommendationResponse(
            products=products,
            cart_ingredients=result.get("cart_ingredients", []),
            model_version=result.get("model_version", "v2"),
            total_count=len(products),
        )

    except Exception as e:
        logger.error(f"장바구니 추천 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 처리 중 오류가 발생했습니다: {str(e)}",
        )


@app.post("/api/recommend")
async def recommend_products():
    """추천 로직 자리 - 추후 구현"""
    # TODO: 개인화 추천 로직 추가
    return {"status": "pending"}


@app.post("/api/predict-price")
async def predict_price_legacy():
    """가격 예측 API (레거시)"""
    return {
        "status": "deprecated",
        "message": "이 엔드포인트는 deprecated됩니다. /api/v1/recommendations/deals를 사용하세요.",
    }


# ============================================================================
# 직접 실행 시
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
