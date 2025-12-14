"""
Recipe Gap Filling 추천 모델

장바구니/구매 이력 기반 레시피 Gap 분석 및 부족 재료 추천
"이 재료들이면 OO 요리를 만들 수 있어요!" 형태의 추천
"""

from typing import Any, Dict, List, Optional

from ml.base import HybridModel, RecommendationContext
from data.repositories.recipe_repo import (
    RecipeRepository,
    RecipeIngredientRepository,
    IngredientProductRepository,
    RecipeGapFillingRepository,
)
from data.repositories.user_repo import UserInteractionRepository
from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class RecipeGapFillingModel(HybridModel):
    """레시피 Gap Filling 추천 모델

    핵심 특징:
    - 장바구니 상품 → 재료 역매핑 → 레시피 Gap 분석
    - "N개만 더 사면 OO를 만들 수 있어요" 형태의 추천
    - 부족한 재료에 해당하는 상품 자동 추천
    - 시간대별 식사 유형 기반 레시피 필터링
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        super().__init__(db, cache)
        self.recipe_repo = RecipeRepository(db)
        self.recipe_ingredient_repo = RecipeIngredientRepository(db)
        self.ingredient_product_repo = IngredientProductRepository(db)
        self.gap_filling_repo = RecipeGapFillingRepository(db)
        self.user_repo = UserInteractionRepository(db)

        # Gap 탐지 설정
        self.max_gap_count = 3  # 최대 부족 재료 개수
        self.min_match_ratio = 0.5  # 최소 재료 매칭 비율

    @property
    def model_name(self) -> str:
        return "recipe_gap_filling"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """레시피 Gap Filling 추천 로직

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록 (부족 재료 상품)
        """
        # 장바구니 상품이 없으면 시간대 기반 레시피 추천
        if not context.cart_product_ids:
            return await self._get_time_based_recipe_recommendations(
                context, limit
            )

        # 장바구니 기반 레시피 Gap 분석
        gap_analysis = await self._analyze_recipe_gaps(
            context.cart_product_ids,
            context.time_context,
        )

        if not gap_analysis:
            return []

        # 부족 재료에 해당하는 상품 추천
        products = await self._get_gap_filling_products(gap_analysis, limit)

        return products

    async def _analyze_recipe_gaps(
        self,
        cart_product_ids: List[int],
        time_context: str,
    ) -> List[Dict[str, Any]]:
        """장바구니 기반 레시피 Gap 분석

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            time_context: 시간 컨텍스트

        Returns:
            Gap 분석 결과 (레시피 + 부족 재료)
        """
        # 시간대별 식사 유형 매핑
        meal_type_mapping = {
            "morning": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
            "night": "snack",
            "default": None,
        }
        meal_type = meal_type_mapping.get(time_context)

        # Gap이 있는 레시피 찾기
        recipes_with_gap = await self.gap_filling_repo.find_recipes_with_gap(
            cart_product_ids=cart_product_ids,
            max_gap_count=self.max_gap_count,
            limit=5,
        )

        # 식사 유형 필터링 (선택적)
        if meal_type:
            recipes_with_gap = [
                r for r in recipes_with_gap
                if r.get("meal_type") == meal_type or r.get("meal_type") is None
            ] or recipes_with_gap  # 필터 결과가 없으면 원본 유지

        return recipes_with_gap

    async def _get_gap_filling_products(
        self,
        gap_analysis: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """부족 재료에 해당하는 상품 추천

        Args:
            gap_analysis: Gap 분석 결과
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        all_products = []

        for recipe in gap_analysis[:3]:  # 상위 3개 레시피만 처리
            missing_ingredient_ids = recipe.get("missing_ingredient_ids", [])

            if not missing_ingredient_ids:
                continue

            # 부족 재료의 상품 추천
            products = await self.gap_filling_repo.get_gap_filling_products(
                missing_ingredient_ids=missing_ingredient_ids
            )

            for product in products:
                product["_recipe_id"] = recipe.get("recipe_id")
                product["_recipe_name"] = recipe.get("name")
                product["_gap_count"] = recipe.get("gap_count")
                product["_match_percentage"] = recipe.get("match_percentage")

                # 점수 계산: Gap이 적을수록, 매칭률 높을수록 높은 점수
                gap_count = recipe.get("gap_count", 3)
                match_pct = recipe.get("match_percentage", 50) or 50
                product["_score"] = (100 - gap_count * 20) + float(match_pct) / 2

            all_products.extend(products)

        # 중복 제거 및 정렬
        return self._deduplicate_and_format(all_products, limit)

    async def _get_time_based_recipe_recommendations(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """시간대 기반 레시피 추천

        장바구니가 비어있을 때 시간대에 맞는 레시피의 재료 추천

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        # 시간대별 식사 유형 결정
        meal_type_mapping = {
            "morning": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
            "night": "snack",
            "default": "lunch",
        }
        meal_type = meal_type_mapping.get(context.time_context, "lunch")

        # 식사 유형별 인기 레시피 조회
        recipes = await self.recipe_repo.get_recipes_by_meal_type(
            meal_type=meal_type,
            limit=3,
        )

        if not recipes:
            return []

        # 레시피 재료 상품 추천
        all_products = []
        for recipe in recipes[:2]:
            recipe_id = recipe.get("id")

            # 레시피 재료와 상품 조회
            shopping_list = await self.ingredient_product_repo.get_recipe_shopping_list(
                recipe_id=recipe_id,
                owned_ingredient_ids=[],  # 빈 장바구니
            )

            recommended_products = shopping_list.get("recommended_products", {})

            for ingredient_id, products in recommended_products.items():
                for product in products[:1]:  # 재료당 1개 상품만
                    product["_recipe_id"] = recipe_id
                    product["_recipe_name"] = recipe.get("name")
                    product["_score"] = 50  # 기본 점수

                    all_products.append(product)

        return self._deduplicate_and_format(all_products, limit)

    async def get_recipe_suggestions(
        self,
        cart_product_ids: List[int],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """레시피 제안

        장바구니로 만들 수 있거나 거의 만들 수 있는 레시피 제안

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            limit: 제안 개수

        Returns:
            레시피 제안 목록
        """
        if not cart_product_ids:
            return []

        recipes = await self.gap_filling_repo.find_recipes_with_gap(
            cart_product_ids=cart_product_ids,
            max_gap_count=self.max_gap_count,
            limit=limit,
        )

        suggestions = []
        for recipe in recipes:
            recipe_id = recipe.get("recipe_id")
            missing_ids = recipe.get("missing_ingredient_ids", [])

            # 부족 재료 상품 조회
            missing_products = []
            if missing_ids:
                products = await self.gap_filling_repo.get_gap_filling_products(
                    missing_ingredient_ids=missing_ids
                )
                missing_products = products

            suggestions.append({
                "recipe_id": recipe_id,
                "recipe_name": recipe.get("name"),
                "description": recipe.get("description"),
                "cooking_time": recipe.get("cooking_time_minutes"),
                "difficulty": recipe.get("difficulty"),
                "image_url": recipe.get("image_url"),
                "match_percentage": recipe.get("match_percentage"),
                "gap_count": recipe.get("gap_count"),
                "missing_ingredients": missing_products,
                "total_missing_cost": sum(
                    p.get("price", 0) for p in missing_products
                    if p.get("rank") == 1  # 각 재료의 최상위 상품만
                ),
            })

        return suggestions

    async def get_shopping_list(
        self,
        recipe_id: int,
        owned_ingredient_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """레시피 장보기 목록 생성

        Args:
            recipe_id: 레시피 ID
            owned_ingredient_ids: 보유 재료 ID 목록

        Returns:
            장보기 목록
        """
        return await self.ingredient_product_repo.get_recipe_shopping_list(
            recipe_id=recipe_id,
            owned_ingredient_ids=owned_ingredient_ids,
        )

    def _deduplicate_and_format(
        self,
        products: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """중복 제거 및 포맷팅

        Args:
            products: 상품 목록
            limit: 최대 개수

        Returns:
            정리된 상품 목록
        """
        seen_ids = set()
        unique_products = []

        # 점수 기반 정렬
        products.sort(key=lambda x: x.get("_score", 0), reverse=True)

        for product in products:
            product_id = product.get("product_id") or product.get("id")
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)

                # 메타데이터 추출 후 정리
                recipe_info = {
                    "recipe_id": product.pop("_recipe_id", None),
                    "recipe_name": product.pop("_recipe_name", None),
                    "gap_count": product.pop("_gap_count", None),
                    "match_percentage": product.pop("_match_percentage", None),
                }
                product.pop("_score", None)
                product.pop("rank", None)

                product["recipe_context"] = recipe_info
                unique_products.append(product)

                if len(unique_products) >= limit:
                    break

        return unique_products

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """신뢰도 계산

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        # 장바구니가 있으면 신뢰도 증가
        base_confidence = 0.6
        if context.cart_product_ids:
            base_confidence = 0.8

        # 레시피 컨텍스트가 있는 상품 비율
        with_recipe = sum(
            1 for p in products
            if p.get("recipe_context", {}).get("recipe_id")
        )
        recipe_ratio = with_recipe / len(products) if products else 0

        return min(1.0, base_confidence * (0.5 + recipe_ratio * 0.5))
