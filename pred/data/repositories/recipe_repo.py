"""
레시피 데이터 Repository

RecipeGapFilling 추천 모델을 위한 레시피/재료 데이터 접근
"""

from typing import Any, Dict, List, Optional, Set

from data.repositories.base import ReadOnlyRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class RecipeRepository(ReadOnlyRepository):
    """레시피 Repository

    레시피 검색 및 조회
    """

    @property
    def table_name(self) -> str:
        return "pred_recipes"

    async def get_recipe_by_id(
        self,
        recipe_id: int,
    ) -> Optional[Dict[str, Any]]:
        """레시피 상세 조회

        Args:
            recipe_id: 레시피 ID

        Returns:
            레시피 정보
        """
        query = """
            SELECT r.id, r.name, r.description, r.cooking_time_minutes,
                   r.difficulty, r.servings, r.image_url,
                   r.cuisine_type, r.meal_type, r.source_url,
                   r.created_at
            FROM pred_recipes r
            WHERE r.id = $1
        """

        record = await self.db.fetch_one(query, recipe_id)
        return self._record_to_dict(record) if record else None

    async def search_recipes(
        self,
        query_text: str,
        meal_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_cooking_time: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """레시피 검색

        Args:
            query_text: 검색어
            meal_type: 식사 유형 ('breakfast', 'lunch', 'dinner', 'snack')
            difficulty: 난이도 ('easy', 'medium', 'hard')
            max_cooking_time: 최대 조리 시간 (분)
            limit: 조회 개수

        Returns:
            레시피 목록
        """
        query = """
            SELECT r.id, r.name, r.description, r.cooking_time_minutes,
                   r.difficulty, r.servings, r.image_url,
                   r.cuisine_type, r.meal_type
            FROM pred_recipes r
            WHERE r.name ILIKE $1 OR r.description ILIKE $1
        """
        params = [f"%{query_text}%"]

        if meal_type:
            query += f" AND r.meal_type = ${len(params)+1}"
            params.append(meal_type)

        if difficulty:
            query += f" AND r.difficulty = ${len(params)+1}"
            params.append(difficulty)

        if max_cooking_time:
            query += f" AND r.cooking_time_minutes <= ${len(params)+1}"
            params.append(max_cooking_time)

        query += f" ORDER BY r.name LIMIT ${len(params)+1}"
        params.append(limit)

        records = await self.db.fetch_all(query, *params)
        return self._records_to_list(records)

    async def get_recipes_by_meal_type(
        self,
        meal_type: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """식사 유형별 레시피 조회

        Args:
            meal_type: 식사 유형
            limit: 조회 개수

        Returns:
            레시피 목록
        """
        query = """
            SELECT r.id, r.name, r.description, r.cooking_time_minutes,
                   r.difficulty, r.servings, r.image_url,
                   r.cuisine_type, r.meal_type
            FROM pred_recipes r
            WHERE r.meal_type = $1
            ORDER BY r.created_at DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, meal_type, limit)
        return self._records_to_list(records)


class RecipeIngredientRepository(ReadOnlyRepository):
    """레시피 재료 Repository

    레시피의 필요 재료 조회
    """

    @property
    def table_name(self) -> str:
        return "pred_recipe_ingredients"

    async def get_recipe_ingredients(
        self,
        recipe_id: int,
    ) -> List[Dict[str, Any]]:
        """레시피의 재료 목록 조회

        Args:
            recipe_id: 레시피 ID

        Returns:
            재료 목록
        """
        query = """
            SELECT ri.ingredient_id, i.name AS ingredient_name,
                   ri.quantity, ri.unit, ri.is_optional,
                   i.category AS ingredient_category
            FROM pred_recipe_ingredients ri
            JOIN pred_ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = $1
            ORDER BY ri.is_optional ASC, i.name ASC
        """

        records = await self.db.fetch_all(query, recipe_id)
        return self._records_to_list(records)

    async def get_recipes_by_ingredients(
        self,
        ingredient_ids: List[int],
        min_match_ratio: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """보유 재료로 만들 수 있는 레시피 조회

        Args:
            ingredient_ids: 보유 재료 ID 목록
            min_match_ratio: 최소 재료 매칭 비율
            limit: 조회 개수

        Returns:
            레시피 목록 (매칭률 순)
        """
        if not ingredient_ids:
            return []

        query = """
            WITH recipe_matches AS (
                SELECT ri.recipe_id,
                       COUNT(*) FILTER (WHERE ri.ingredient_id = ANY($1)) AS matched_count,
                       COUNT(*) FILTER (WHERE NOT ri.is_optional) AS required_count,
                       COUNT(*) AS total_count
                FROM pred_recipe_ingredients ri
                GROUP BY ri.recipe_id
            )
            SELECT rm.recipe_id, rm.matched_count, rm.required_count, rm.total_count,
                   ROUND(rm.matched_count::DECIMAL / NULLIF(rm.required_count, 0), 2) AS match_ratio,
                   r.name, r.description, r.cooking_time_minutes,
                   r.difficulty, r.image_url, r.meal_type
            FROM recipe_matches rm
            JOIN pred_recipes r ON rm.recipe_id = r.id
            WHERE rm.matched_count::DECIMAL / NULLIF(rm.required_count, 0) >= $2
            ORDER BY match_ratio DESC, rm.matched_count DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(
            query, ingredient_ids, min_match_ratio, limit
        )
        return self._records_to_list(records)


class IngredientProductRepository(ReadOnlyRepository):
    """재료-상품 매핑 Repository

    레시피 재료와 SelF 상품 간 매핑
    """

    @property
    def table_name(self) -> str:
        return "pred_ingredient_products"

    async def get_products_for_ingredient(
        self,
        ingredient_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """재료에 매핑된 상품 조회

        Args:
            ingredient_id: 재료 ID
            limit: 조회 개수

        Returns:
            매핑된 상품 목록
        """
        query = """
            SELECT ip.product_id, ip.match_score,
                   p.name, p.price, p.category_id, p.seller_id,
                   ps.order_event_count, ps.average_rating
            FROM pred_ingredient_products ip
            JOIN products p ON ip.product_id = p.id
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE ip.ingredient_id = $1
              AND p.status = 'active'
            ORDER BY ip.match_score DESC, ps.order_event_count DESC
            LIMIT $2
        """

        records = await self.db.fetch_all(query, ingredient_id, limit)
        return self._records_to_list(records)

    async def get_missing_ingredients_products(
        self,
        recipe_id: int,
        owned_ingredient_ids: List[int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """레시피에서 부족한 재료의 상품 추천

        RecipeGapFilling 핵심 기능

        Args:
            recipe_id: 레시피 ID
            owned_ingredient_ids: 보유 재료 ID 목록
            limit: 조회 개수

        Returns:
            부족한 재료에 해당하는 상품 목록
        """
        owned_set = owned_ingredient_ids if owned_ingredient_ids else []

        query = """
            WITH missing_ingredients AS (
                SELECT ri.ingredient_id, i.name AS ingredient_name,
                       ri.quantity, ri.unit, ri.is_optional
                FROM pred_recipe_ingredients ri
                JOIN pred_ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = $1
                  AND ri.ingredient_id != ALL($2)
                ORDER BY ri.is_optional ASC
            )
            SELECT mi.ingredient_id, mi.ingredient_name, mi.quantity, mi.unit,
                   mi.is_optional,
                   ip.product_id, ip.match_score,
                   p.name AS product_name, p.price, p.category_id,
                   ps.order_event_count, ps.average_rating
            FROM missing_ingredients mi
            JOIN pred_ingredient_products ip ON mi.ingredient_id = ip.ingredient_id
            JOIN products p ON ip.product_id = p.id
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE p.status = 'active'
            ORDER BY mi.is_optional ASC, ip.match_score DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(query, recipe_id, owned_set, limit)
        return self._records_to_list(records)

    async def get_recipe_shopping_list(
        self,
        recipe_id: int,
        owned_ingredient_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """레시피 장보기 목록 생성

        Args:
            recipe_id: 레시피 ID
            owned_ingredient_ids: 보유 재료 ID 목록

        Returns:
            장보기 목록 (재료별 추천 상품 포함)
        """
        owned_set = owned_ingredient_ids or []

        # 레시피 기본 정보
        recipe_query = """
            SELECT id, name, description, servings
            FROM pred_recipes WHERE id = $1
        """
        recipe = await self.db.fetch_one(recipe_query, recipe_id)

        if not recipe:
            return {"error": "레시피를 찾을 수 없습니다"}

        # 필요 재료와 상품 매핑
        ingredients_query = """
            SELECT ri.ingredient_id, i.name AS ingredient_name,
                   ri.quantity, ri.unit, ri.is_optional,
                   ri.ingredient_id = ANY($2) AS is_owned
            FROM pred_recipe_ingredients ri
            JOIN pred_ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = $1
            ORDER BY ri.is_optional ASC, i.name ASC
        """
        ingredients = await self.db.fetch_all(
            ingredients_query, recipe_id, owned_set
        )

        # 부족한 재료의 추천 상품
        missing_ids = [
            r["ingredient_id"] for r in ingredients
            if not r["is_owned"]
        ]

        products_by_ingredient = {}
        if missing_ids:
            products_query = """
                SELECT ip.ingredient_id, ip.product_id, ip.match_score,
                       p.name AS product_name, p.price, p.category_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY ip.ingredient_id
                           ORDER BY ip.match_score DESC
                       ) AS rank
                FROM pred_ingredient_products ip
                JOIN products p ON ip.product_id = p.id
                WHERE ip.ingredient_id = ANY($1)
                  AND p.status = 'active'
            """
            products = await self.db.fetch_all(products_query, missing_ids)

            for p in products:
                if p["rank"] <= 3:  # 재료당 최대 3개 상품
                    ing_id = p["ingredient_id"]
                    if ing_id not in products_by_ingredient:
                        products_by_ingredient[ing_id] = []
                    products_by_ingredient[ing_id].append(dict(p))

        return {
            "recipe": dict(recipe),
            "ingredients": self._records_to_list(ingredients),
            "recommended_products": products_by_ingredient,
            "owned_count": len(owned_set),
            "missing_count": len(missing_ids),
        }


class RecipeGapFillingRepository(ReadOnlyRepository):
    """RecipeGapFilling 전용 Repository

    장바구니/구매 이력 기반 레시피 Gap 분석
    """

    @property
    def table_name(self) -> str:
        return "pred_recipes"

    async def find_recipes_with_gap(
        self,
        cart_product_ids: List[int],
        max_gap_count: int = 3,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """장바구니 상품으로 거의 만들 수 있는 레시피 찾기

        핵심 로직: 장바구니 상품 → 재료 역매핑 → 레시피 Gap 분석

        Args:
            cart_product_ids: 장바구니 상품 ID 목록
            max_gap_count: 부족한 재료 최대 개수
            limit: 조회 개수

        Returns:
            레시피 목록 (부족한 재료 정보 포함)
        """
        if not cart_product_ids:
            return []

        query = """
            WITH cart_ingredients AS (
                -- 장바구니 상품 → 재료 역매핑
                SELECT DISTINCT ip.ingredient_id
                FROM pred_ingredient_products ip
                WHERE ip.product_id = ANY($1)
            ),
            recipe_gaps AS (
                -- 레시피별 Gap 분석
                SELECT ri.recipe_id,
                       COUNT(*) FILTER (WHERE ri.ingredient_id NOT IN (SELECT ingredient_id FROM cart_ingredients) AND NOT ri.is_optional) AS gap_count,
                       COUNT(*) FILTER (WHERE ri.ingredient_id IN (SELECT ingredient_id FROM cart_ingredients)) AS matched_count,
                       COUNT(*) FILTER (WHERE NOT ri.is_optional) AS required_count,
                       ARRAY_AGG(ri.ingredient_id) FILTER (WHERE ri.ingredient_id NOT IN (SELECT ingredient_id FROM cart_ingredients) AND NOT ri.is_optional) AS missing_ingredient_ids
                FROM pred_recipe_ingredients ri
                GROUP BY ri.recipe_id
            )
            SELECT rg.recipe_id, rg.gap_count, rg.matched_count, rg.required_count,
                   rg.missing_ingredient_ids,
                   ROUND(rg.matched_count::DECIMAL / NULLIF(rg.required_count, 0) * 100, 1) AS match_percentage,
                   r.name, r.description, r.cooking_time_minutes,
                   r.difficulty, r.image_url, r.meal_type
            FROM recipe_gaps rg
            JOIN pred_recipes r ON rg.recipe_id = r.id
            WHERE rg.gap_count > 0
              AND rg.gap_count <= $2
              AND rg.matched_count > 0
            ORDER BY rg.gap_count ASC, rg.match_percentage DESC
            LIMIT $3
        """

        records = await self.db.fetch_all(
            query, cart_product_ids, max_gap_count, limit
        )
        return self._records_to_list(records)

    async def get_gap_filling_products(
        self,
        missing_ingredient_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """부족한 재료에 대한 상품 추천

        Args:
            missing_ingredient_ids: 부족한 재료 ID 목록

        Returns:
            재료별 추천 상품 목록
        """
        if not missing_ingredient_ids:
            return []

        query = """
            SELECT i.id AS ingredient_id, i.name AS ingredient_name,
                   ip.product_id, ip.match_score,
                   p.name AS product_name, p.price, p.category_id,
                   ps.order_event_count, ps.average_rating,
                   ROW_NUMBER() OVER (
                       PARTITION BY i.id
                       ORDER BY ip.match_score DESC, ps.order_event_count DESC
                   ) AS rank
            FROM pred_ingredients i
            JOIN pred_ingredient_products ip ON i.id = ip.ingredient_id
            JOIN products p ON ip.product_id = p.id
            LEFT JOIN product_stats ps ON p.id = ps.product_id
            WHERE i.id = ANY($1)
              AND p.status = 'active'
        """

        all_records = await self.db.fetch_all(query, missing_ingredient_ids)

        # 재료당 상위 2개 상품만 선택
        return [
            dict(r) for r in all_records
            if r["rank"] <= 2
        ]
