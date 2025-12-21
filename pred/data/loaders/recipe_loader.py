"""
레시피 데이터 로더

만개의레시피 크롤링 데이터를 DB에 적재
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.database import Database
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


class RecipeDataLoader:
    """레시피 데이터 로더

    만개의레시피 크롤링 JSON 데이터를 읽어 DB에 적재합니다.

    필요한 파일 형식:
    - recipes.json: 레시피 목록
    - ingredients.json: 재료 사전 (선택적)
    """

    def __init__(self, db: Database, data_dir: str):
        """
        Args:
            db: 데이터베이스 인스턴스
            data_dir: 레시피 데이터 디렉토리 경로
        """
        self.db = db
        self.data_dir = Path(data_dir)
        self.batch_size = settings.batch_chunk_size

        # 재료명 정규화 캐시
        self._ingredient_cache: Dict[str, int] = {}

    async def load_all(self) -> Dict[str, int]:
        """모든 레시피 데이터 로드

        Returns:
            테이블별 적재 건수
        """
        logger.info("레시피 데이터 로드 시작", data_dir=str(self.data_dir))

        results = {}

        # 1. 재료 사전 로드 (있으면)
        results["ingredients"] = await self.load_ingredients()

        # 2. 레시피 및 재료 관계 로드
        recipe_count, relation_count = await self.load_recipes()
        results["recipes"] = recipe_count
        results["recipe_ingredients"] = relation_count

        # 3. 재료-상품 매핑 생성
        results["ingredient_products"] = await self.generate_ingredient_product_mapping()

        logger.info("레시피 데이터 로드 완료", results=results)
        return results

    async def load_ingredients(self) -> int:
        """재료 사전 로드"""
        file_path = self.data_dir / "ingredients.json"
        if not file_path.exists():
            logger.info("ingredients.json 없음, 레시피에서 재료 추출 예정")
            return 0

        with open(file_path, "r", encoding="utf-8") as f:
            ingredients = json.load(f)

        count = 0
        for ing in ingredients:
            ingredient_id = await self._upsert_ingredient(
                name=ing.get("name"),
                category=ing.get("category"),
                is_processed=ing.get("is_processed", False),
            )
            if ingredient_id:
                count += 1

        logger.info("재료 사전 로드 완료", count=count)
        return count

    async def load_recipes(self) -> Tuple[int, int]:
        """레시피 데이터 로드

        Returns:
            (레시피 수, 재료 관계 수)
        """
        file_path = self.data_dir / "recipes.json"
        if not file_path.exists():
            logger.warning("recipes.json 파일 없음")
            return 0, 0

        with open(file_path, "r", encoding="utf-8") as f:
            recipes = json.load(f)

        recipe_count = 0
        relation_count = 0

        for recipe_data in recipes:
            # 레시피 삽입
            recipe_id = await self._insert_recipe(recipe_data)
            if recipe_id:
                recipe_count += 1

                # 재료 관계 삽입
                ingredients = recipe_data.get("ingredients", [])
                for idx, ing in enumerate(ingredients):
                    relation_id = await self._insert_recipe_ingredient(
                        recipe_id=recipe_id,
                        ingredient_data=ing,
                        display_order=idx,
                    )
                    if relation_id:
                        relation_count += 1

        logger.info("레시피 로드 완료", recipes=recipe_count, relations=relation_count)
        return recipe_count, relation_count

    async def _insert_recipe(self, data: Dict) -> Optional[int]:
        """레시피 삽입"""
        try:
            name = data.get("name", "").strip()
            if not name:
                return None

            name_normalized = self._normalize_text(name)

            result = await self.db.fetch_one(
                """
                INSERT INTO pred_recipes (
                    source_site, source_id, source_url,
                    name, name_normalized, description,
                    thumbnail_url, cooking_time_min, servings, difficulty,
                    view_count, like_count, rating, rating_count,
                    category_main, category_sub
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (source_site, source_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    name_normalized = EXCLUDED.name_normalized,
                    updated_at = NOW()
                RETURNING id
                """,
                data.get("source_site", "10000recipe"),
                str(data.get("source_id", "")),
                data.get("source_url"),
                name,
                name_normalized,
                data.get("description"),
                data.get("thumbnail_url"),
                data.get("cooking_time_min"),
                data.get("servings"),
                data.get("difficulty"),
                data.get("view_count", 0),
                data.get("like_count", 0),
                data.get("rating", 0),
                data.get("rating_count", 0),
                data.get("category_main"),
                data.get("category_sub"),
            )

            return result["id"] if result else None

        except Exception as e:
            logger.warning("레시피 삽입 실패", error=str(e), name=data.get("name"))
            return None

    async def _insert_recipe_ingredient(
        self,
        recipe_id: int,
        ingredient_data: Dict,
        display_order: int,
    ) -> Optional[int]:
        """레시피-재료 관계 삽입"""
        try:
            # 재료명 처리
            if isinstance(ingredient_data, str):
                ingredient_name = ingredient_data
                quantity_text = None
                is_required = True
                is_main = False
            else:
                ingredient_name = ingredient_data.get("name", "").strip()
                quantity_text = ingredient_data.get("quantity")
                is_required = ingredient_data.get("is_required", True)
                is_main = ingredient_data.get("is_main", False)

            if not ingredient_name:
                return None

            # 재료 ID 조회 또는 생성
            ingredient_id = await self._get_or_create_ingredient(ingredient_name)
            if not ingredient_id:
                return None

            # 수량 파싱
            quantity_value, quantity_unit = self._parse_quantity(quantity_text)

            result = await self.db.fetch_one(
                """
                INSERT INTO pred_recipe_ingredients (
                    recipe_id, ingredient_id,
                    quantity_text, quantity_value, quantity_unit,
                    is_required, is_main, display_order
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (recipe_id, ingredient_id)
                DO UPDATE SET
                    quantity_text = EXCLUDED.quantity_text,
                    is_required = EXCLUDED.is_required,
                    is_main = EXCLUDED.is_main
                RETURNING id
                """,
                recipe_id,
                ingredient_id,
                quantity_text,
                quantity_value,
                quantity_unit,
                is_required,
                is_main,
                display_order,
            )

            return result["id"] if result else None

        except Exception as e:
            logger.debug("재료 관계 삽입 실패", error=str(e))
            return None

    async def _get_or_create_ingredient(self, name: str) -> Optional[int]:
        """재료 ID 조회 또는 생성"""
        normalized_name = self._normalize_ingredient_name(name)

        # 캐시 확인
        if normalized_name in self._ingredient_cache:
            return self._ingredient_cache[normalized_name]

        # DB 조회
        result = await self.db.fetch_one(
            """
            SELECT id FROM pred_ingredients
            WHERE name_normalized = $1
            """,
            normalized_name,
        )

        if result:
            self._ingredient_cache[normalized_name] = result["id"]
            return result["id"]

        # 신규 생성
        ingredient_id = await self._upsert_ingredient(
            name=name,
            category=self._guess_ingredient_category(name),
            is_processed=self._is_processed_ingredient(name),
        )

        if ingredient_id:
            self._ingredient_cache[normalized_name] = ingredient_id

        return ingredient_id

    async def _upsert_ingredient(
        self,
        name: str,
        category: Optional[str] = None,
        is_processed: bool = False,
    ) -> Optional[int]:
        """재료 삽입/갱신"""
        try:
            name = name.strip()
            if not name:
                return None

            name_normalized = self._normalize_ingredient_name(name)

            result = await self.db.fetch_one(
                """
                INSERT INTO pred_ingredients (name, name_normalized, category, is_processed)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name) DO UPDATE SET
                    category = COALESCE(EXCLUDED.category, pred_ingredients.category),
                    is_processed = EXCLUDED.is_processed
                RETURNING id
                """,
                name,
                name_normalized,
                category,
                is_processed,
            )

            return result["id"] if result else None

        except Exception as e:
            logger.debug("재료 삽입 실패", error=str(e), name=name)
            return None

    async def generate_ingredient_product_mapping(self) -> int:
        """재료-상품 매핑 자동 생성

        SelF 상품명과 재료명을 매칭하여 매핑 테이블 생성

        Returns:
            생성된 매핑 수
        """
        logger.info("재료-상품 매핑 생성 시작")

        # 모든 재료 조회
        ingredients = await self.db.fetch_all(
            "SELECT id, name, name_normalized FROM pred_ingredients"
        )

        count = 0

        for ing in ingredients:
            # 상품명에 재료명이 포함된 상품 찾기
            # 1. 정확 매칭
            exact_matches = await self.db.fetch_all(
                """
                SELECT id, name
                FROM products
                WHERE status = 'active'
                  AND (
                      LOWER(name) LIKE '%' || $1 || '%'
                      OR LOWER(name) LIKE '%' || $2 || '%'
                  )
                LIMIT 5
                """,
                ing["name"].lower(),
                ing["name_normalized"],
            )

            for product in exact_matches:
                # 유사도 점수 계산
                similarity_score = self._calculate_name_similarity(
                    ing["name"],
                    product["name"],
                )

                mapping_method = "exact" if similarity_score >= 0.9 else "partial"

                await self.db.execute(
                    """
                    INSERT INTO pred_ingredient_products
                        (ingredient_id, product_id, similarity_score, mapping_method, priority)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (ingredient_id, product_id)
                    DO UPDATE SET
                        similarity_score = EXCLUDED.similarity_score,
                        mapping_method = EXCLUDED.mapping_method
                    """,
                    ing["id"],
                    product["id"],
                    similarity_score,
                    mapping_method,
                    1 if similarity_score >= 0.9 else 2,
                )
                count += 1

        logger.info("재료-상품 매핑 생성 완료", count=count)
        return count

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (검색용)"""
        # 소문자 변환
        normalized = text.lower()

        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        normalized = re.sub(r"[^\w\s가-힣]", "", normalized)

        # 연속 공백 제거
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _normalize_ingredient_name(self, name: str) -> str:
        """재료명 정규화

        양파, 양파, onion → 양파
        """
        # 기본 정규화
        normalized = self._normalize_text(name)

        # 단위 제거 (1개, 2큰술 등)
        normalized = re.sub(r"\d+[개큰술작은술컵g㎖ml]*", "", normalized).strip()

        # 수식어 제거
        prefixes = ["다진", "썰은", "데친", "삶은", "볶은", "구운", "튀긴"]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()

        return normalized

    def _guess_ingredient_category(self, name: str) -> Optional[str]:
        """재료 카테고리 추측"""
        categories = {
            "채소": ["양파", "마늘", "파", "고추", "배추", "무", "당근", "감자", "호박", "버섯"],
            "육류": ["돼지", "소고기", "닭", "오리", "양고기", "삼겹살", "목살"],
            "수산물": ["생선", "새우", "오징어", "조개", "꽃게", "멸치", "연어", "참치"],
            "양념": ["소금", "설탕", "간장", "고추장", "된장", "식초", "참기름", "후추"],
            "유제품": ["우유", "치즈", "버터", "요거트", "크림"],
            "곡류": ["쌀", "밀가루", "면", "떡", "빵"],
        }

        name_lower = name.lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        return "기타"

    def _is_processed_ingredient(self, name: str) -> bool:
        """가공식품 여부 판단"""
        processed_keywords = [
            "고추장", "된장", "간장", "쌈장", "케첩", "마요네즈",
            "소스", "드레싱", "잼", "통조림", "레토르트", "라면",
        ]

        name_lower = name.lower()
        return any(keyword in name_lower for keyword in processed_keywords)

    def _parse_quantity(self, quantity_text: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
        """수량 텍스트 파싱

        "1/2컵" → (0.5, "컵")
        "2큰술" → (2.0, "큰술")
        """
        if not quantity_text:
            return None, None

        # 분수 처리
        text = quantity_text.strip()
        if "/" in text:
            match = re.match(r"(\d+)/(\d+)", text)
            if match:
                value = float(match.group(1)) / float(match.group(2))
                unit = text[match.end():].strip()
                return value, unit if unit else None

        # 일반 숫자 처리
        match = re.match(r"([\d.]+)\s*(.+)?", text)
        if match:
            value = float(match.group(1))
            unit = match.group(2).strip() if match.group(2) else None
            return value, unit

        return None, quantity_text

    def _calculate_name_similarity(self, ing_name: str, product_name: str) -> float:
        """이름 유사도 계산"""
        ing_normalized = self._normalize_ingredient_name(ing_name)
        prod_normalized = self._normalize_text(product_name)

        # 정확 매칭
        if ing_normalized in prod_normalized:
            # 전체 길이 대비 재료명 길이 비율
            ratio = len(ing_normalized) / len(prod_normalized)
            return min(0.5 + ratio * 0.5, 1.0)

        # 부분 매칭 (자카드 유사도)
        ing_chars = set(ing_normalized)
        prod_chars = set(prod_normalized)

        if not ing_chars or not prod_chars:
            return 0.0

        intersection = len(ing_chars & prod_chars)
        union = len(ing_chars | prod_chars)

        return intersection / union if union > 0 else 0.0


async def run_recipe_loader(db: Database, data_dir: str) -> Dict[str, int]:
    """레시피 데이터 로더 실행

    Args:
        db: 데이터베이스 인스턴스
        data_dir: 데이터 디렉토리 경로

    Returns:
        로드 결과
    """
    loader = RecipeDataLoader(db, data_dir)
    return await loader.load_all()
