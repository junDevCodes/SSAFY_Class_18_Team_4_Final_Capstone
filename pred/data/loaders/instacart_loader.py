"""
Instacart 데이터 로더

Instacart Kaggle 데이터셋을 DB에 적재하고 사전 집계 테이블 생성
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.database import Database
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


class InstacartDataLoader:
    """Instacart 데이터 로더

    Kaggle 데이터셋 CSV 파일들을 읽어 DB에 적재합니다.

    필요한 파일:
    - departments.csv
    - aisles.csv
    - products.csv
    - orders.csv
    - order_products_prior.csv
    - order_products_train.csv
    """

    def __init__(self, db: Database, data_dir: str):
        """
        Args:
            db: 데이터베이스 인스턴스
            data_dir: Instacart 데이터 디렉토리 경로
        """
        self.db = db
        self.data_dir = Path(data_dir)
        self.batch_size = settings.batch_chunk_size

    async def load_all(self) -> Dict[str, int]:
        """모든 Instacart 데이터 로드

        Returns:
            테이블별 적재 건수
        """
        logger.info("Instacart 데이터 로드 시작", data_dir=str(self.data_dir))

        results = {}

        # 1. 마스터 테이블 (의존성 순서대로)
        results["departments"] = await self.load_departments()
        results["aisles"] = await self.load_aisles()
        results["products"] = await self.load_products()

        # 2. 트랜잭션 테이블
        results["orders"] = await self.load_orders()
        results["order_items"] = await self.load_order_items()

        # 3. 통계 업데이트
        await self.update_product_stats()

        # 4. 사전 집계 테이블 생성
        results["time_patterns"] = await self.aggregate_time_patterns()

        logger.info("Instacart 데이터 로드 완료", results=results)
        return results

    async def load_departments(self) -> int:
        """부서(대분류) 데이터 로드"""
        file_path = self.data_dir / "departments.csv"
        if not file_path.exists():
            logger.warning("departments.csv 파일 없음")
            return 0

        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                await self.db.execute(
                    """
                    INSERT INTO pred_instacart_departments (id, name)
                    VALUES ($1, $2)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                    """,
                    int(row["department_id"]),
                    row["department"],
                )
                count += 1

        logger.info("부서 데이터 로드 완료", count=count)
        return count

    async def load_aisles(self) -> int:
        """통로(소분류) 데이터 로드"""
        file_path = self.data_dir / "aisles.csv"
        if not file_path.exists():
            logger.warning("aisles.csv 파일 없음")
            return 0

        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # department_id는 별도 매핑 필요 (products.csv에서 확인)
                # 일단 기본값으로 삽입 후 products 로드 시 업데이트
                await self.db.execute(
                    """
                    INSERT INTO pred_instacart_aisles (id, department_id, name)
                    VALUES ($1, 1, $2)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                    """,
                    int(row["aisle_id"]),
                    row["aisle"],
                )
                count += 1

        logger.info("통로 데이터 로드 완료", count=count)
        return count

    async def load_products(self) -> int:
        """상품 데이터 로드"""
        file_path = self.data_dir / "products.csv"
        if not file_path.exists():
            logger.warning("products.csv 파일 없음")
            return 0

        # aisle-department 매핑 업데이트용 딕셔너리
        aisle_dept_map: Dict[int, int] = {}

        count = 0
        batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_id = int(row["product_id"])
                aisle_id = int(row["aisle_id"])
                department_id = int(row["department_id"])
                product_name = row["product_name"]

                # 정규화된 이름 생성
                name_normalized = self._normalize_name(product_name)

                batch.append((
                    product_id,
                    aisle_id,
                    product_name,
                    name_normalized,
                ))

                aisle_dept_map[aisle_id] = department_id

                if len(batch) >= self.batch_size:
                    await self._insert_products_batch(batch)
                    count += len(batch)
                    batch = []

            if batch:
                await self._insert_products_batch(batch)
                count += len(batch)

        # aisle의 department_id 업데이트
        for aisle_id, dept_id in aisle_dept_map.items():
            await self.db.execute(
                """
                UPDATE pred_instacart_aisles
                SET department_id = $2
                WHERE id = $1
                """,
                aisle_id,
                dept_id,
            )

        logger.info("상품 데이터 로드 완료", count=count)
        return count

    async def _insert_products_batch(self, batch: List[Tuple]) -> None:
        """상품 배치 삽입"""
        for item in batch:
            await self.db.execute(
                """
                INSERT INTO pred_instacart_products
                    (id, aisle_id, name, name_normalized)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    name_normalized = EXCLUDED.name_normalized
                """,
                *item,
            )

    async def load_orders(self) -> int:
        """주문 데이터 로드"""
        file_path = self.data_dir / "orders.csv"
        if not file_path.exists():
            logger.warning("orders.csv 파일 없음")
            return 0

        count = 0
        batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                days_since = row.get("days_since_prior_order")
                days_since = int(float(days_since)) if days_since and days_since != "" else None

                batch.append((
                    int(row["order_id"]),
                    int(row["user_id"]),
                    int(row["order_number"]),
                    int(row["order_dow"]),
                    int(row["order_hour_of_day"]),
                    days_since,
                    row["eval_set"],
                ))

                if len(batch) >= self.batch_size:
                    await self._insert_orders_batch(batch)
                    count += len(batch)
                    batch = []
                    logger.debug("주문 로드 진행", count=count)

            if batch:
                await self._insert_orders_batch(batch)
                count += len(batch)

        logger.info("주문 데이터 로드 완료", count=count)
        return count

    async def _insert_orders_batch(self, batch: List[Tuple]) -> None:
        """주문 배치 삽입"""
        for item in batch:
            await self.db.execute(
                """
                INSERT INTO pred_instacart_orders
                    (id, user_id, order_number, order_dow, order_hour_of_day,
                     days_since_prior_order, eval_set)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id, eval_set) DO NOTHING
                """,
                *item,
            )

    async def load_order_items(self) -> int:
        """주문 상품 데이터 로드"""
        total_count = 0

        # prior 데이터
        prior_file = self.data_dir / "order_products__prior.csv"
        if prior_file.exists():
            count = await self._load_order_items_file(prior_file)
            total_count += count
            logger.info("prior 주문 상품 로드 완료", count=count)

        # train 데이터
        train_file = self.data_dir / "order_products__train.csv"
        if train_file.exists():
            count = await self._load_order_items_file(train_file)
            total_count += count
            logger.info("train 주문 상품 로드 완료", count=count)

        return total_count

    async def _load_order_items_file(self, file_path: Path) -> int:
        """주문 상품 파일 로드"""
        count = 0
        batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                batch.append((
                    int(row["order_id"]),
                    int(row["product_id"]),
                    int(row["add_to_cart_order"]),
                    row["reordered"] == "1",
                ))

                if len(batch) >= self.batch_size:
                    await self._insert_order_items_batch(batch)
                    count += len(batch)
                    batch = []

            if batch:
                await self._insert_order_items_batch(batch)
                count += len(batch)

        return count

    async def _insert_order_items_batch(self, batch: List[Tuple]) -> None:
        """주문 상품 배치 삽입"""
        for item in batch:
            await self.db.execute(
                """
                INSERT INTO pred_instacart_order_items
                    (order_id, product_id, add_to_cart_order, is_reordered)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (order_id, product_id) DO NOTHING
                """,
                *item,
            )

    async def update_product_stats(self) -> None:
        """상품별 통계 업데이트 (order_count, reorder_rate)"""
        logger.info("상품 통계 업데이트 시작")

        await self.db.execute(
            """
            UPDATE pred_instacart_products p
            SET
                order_count = stats.order_count,
                reorder_count = stats.reorder_count,
                reorder_rate = CASE
                    WHEN stats.order_count > 0
                    THEN stats.reorder_count::DECIMAL / stats.order_count
                    ELSE 0
                END,
                updated_at = NOW()
            FROM (
                SELECT
                    product_id,
                    COUNT(*) as order_count,
                    SUM(CASE WHEN is_reordered THEN 1 ELSE 0 END) as reorder_count
                FROM pred_instacart_order_items
                GROUP BY product_id
            ) stats
            WHERE p.id = stats.product_id
            """
        )

        logger.info("상품 통계 업데이트 완료")

    async def aggregate_time_patterns(self) -> int:
        """시간대별 카테고리 인기 패턴 집계

        32M 주문 데이터를 사전 집계하여 168행 (4시간대 x 2요일타입 x 21부서) 생성
        """
        logger.info("시간대별 패턴 집계 시작")

        # 기존 데이터 삭제
        await self.db.execute("DELETE FROM pred_instacart_time_patterns")

        # 집계 쿼리
        result = await self.db.execute(
            """
            INSERT INTO pred_instacart_time_patterns
                (time_slot, day_type, instacart_department_id, popularity_score, reorder_rate)
            SELECT
                CASE
                    WHEN o.order_hour_of_day BETWEEN 6 AND 10 THEN 'morning'
                    WHEN o.order_hour_of_day BETWEEN 11 AND 14 THEN 'lunch'
                    WHEN o.order_hour_of_day BETWEEN 17 AND 21 THEN 'dinner'
                    ELSE 'night'
                END AS time_slot,
                CASE
                    WHEN o.order_dow IN (0, 6) THEN 'weekend'
                    ELSE 'weekday'
                END AS day_type,
                a.department_id,
                COUNT(*) AS popularity_score,
                AVG(CASE WHEN oi.is_reordered THEN 1 ELSE 0 END) AS reorder_rate
            FROM pred_instacart_order_items oi
            JOIN pred_instacart_orders o ON oi.order_id = o.id
            JOIN pred_instacart_products p ON oi.product_id = p.id
            JOIN pred_instacart_aisles a ON p.aisle_id = a.id
            WHERE o.eval_set = 'prior'
            GROUP BY time_slot, day_type, a.department_id
            ON CONFLICT (time_slot, day_type, instacart_department_id)
            DO UPDATE SET
                popularity_score = EXCLUDED.popularity_score,
                reorder_rate = EXCLUDED.reorder_rate,
                aggregated_at = NOW()
            """
        )

        count = await self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM pred_instacart_time_patterns"
        )
        pattern_count = count["cnt"] if count else 0

        logger.info("시간대별 패턴 집계 완료", pattern_count=pattern_count)
        return pattern_count

    def _normalize_name(self, name: str) -> str:
        """상품명 정규화

        소문자 변환, 특수문자 제거

        Args:
            name: 원본 상품명

        Returns:
            정규화된 상품명
        """
        import re

        # 소문자 변환
        normalized = name.lower()

        # 특수문자 제거 (알파벳, 숫자, 공백만 유지)
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

        # 연속 공백 제거
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized


async def run_instacart_loader(db: Database, data_dir: str) -> Dict[str, int]:
    """Instacart 데이터 로더 실행

    Args:
        db: 데이터베이스 인스턴스
        data_dir: 데이터 디렉토리 경로

    Returns:
        로드 결과
    """
    loader = InstacartDataLoader(db, data_dir)
    return await loader.load_all()
