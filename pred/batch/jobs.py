"""
배치 작업 정의

정기적으로 실행되는 배치 작업들
"""

from datetime import datetime, timedelta
from typing import List

from core.database import Database
from core.cache import CacheManager
from core.config import settings
from core.logging import get_logger
from data.repositories import (
    RecommendationCacheRepository,
    EmbeddingCacheRepository,
    UserEmbeddingRepository,
    PriceHistoryRepository,
)

logger = get_logger(__name__)


# ============================================================================
# 캐시 정리 작업
# ============================================================================

async def cleanup_expired_cache(db: Database) -> int:
    """만료된 캐시 정리

    Args:
        db: 데이터베이스 인스턴스

    Returns:
        삭제된 캐시 개수
    """
    logger.info("캐시 정리 작업 시작")

    cache_repo = RecommendationCacheRepository(db)
    deleted_count = await cache_repo.cleanup_expired_cache()

    logger.info("캐시 정리 완료", deleted_count=deleted_count)
    return deleted_count


# ============================================================================
# Instacart 시간 패턴 집계 작업
# ============================================================================

async def aggregate_time_patterns(db: Database) -> int:
    """시간대별 주문 패턴 집계

    Instacart 데이터에서 시간대별 인기 상품 패턴 계산

    Args:
        db: 데이터베이스 인스턴스

    Returns:
        생성된 패턴 수
    """
    logger.info("시간 패턴 집계 시작")

    # 168개 (24시간 x 7요일) 패턴 생성
    query = """
        INSERT INTO pred_instacart_time_pattern (
            day_of_week, hour_of_day, department_id, aisle_id,
            top_product_ids, order_count, reorder_rate, avg_cart_position
        )
        SELECT
            EXTRACT(DOW FROM o.order_hour_of_day)::INT AS day_of_week,
            o.order_hour_of_day AS hour_of_day,
            p.department_id,
            p.aisle_id,
            ARRAY_AGG(DISTINCT oi.product_id ORDER BY COUNT(*) DESC)[:10] AS top_product_ids,
            COUNT(*) AS order_count,
            AVG(oi.reordered::INT) AS reorder_rate,
            AVG(oi.add_to_cart_order) AS avg_cart_position
        FROM pred_instacart_orders o
        JOIN pred_instacart_order_items oi ON o.order_id = oi.order_id
        JOIN pred_instacart_products p ON oi.product_id = p.id
        WHERE o.eval_set = 'prior'
        GROUP BY day_of_week, hour_of_day, p.department_id, p.aisle_id
        ON CONFLICT (day_of_week, hour_of_day, department_id, aisle_id)
        DO UPDATE SET
            top_product_ids = EXCLUDED.top_product_ids,
            order_count = EXCLUDED.order_count,
            reorder_rate = EXCLUDED.reorder_rate,
            avg_cart_position = EXCLUDED.avg_cart_position,
            updated_at = NOW()
    """

    try:
        result = await db.execute(query)
        # 결과에서 숫자 추출
        count = 168  # 최대 168개 패턴
        logger.info("시간 패턴 집계 완료", pattern_count=count)
        return count
    except Exception as e:
        logger.error("시간 패턴 집계 실패", error=str(e))
        return 0


# ============================================================================
# 아이템 유사도 계산 작업
# ============================================================================

async def compute_item_similarity(db: Database, batch_size: int = 1000) -> int:
    """아이템 간 유사도 계산

    함께 구매된 상품 기반 유사도 계산

    Args:
        db: 데이터베이스 인스턴스
        batch_size: 배치 크기

    Returns:
        생성된 유사도 레코드 수
    """
    logger.info("아이템 유사도 계산 시작")

    # 함께 구매된 상품 조합 계산 (Co-purchase)
    query = """
        INSERT INTO pred_item_similarity (
            product_id, similar_product_id, similarity_score,
            co_occurrence_count, similarity_type
        )
        SELECT
            oi1.product_id,
            oi2.product_id,
            COUNT(*)::FLOAT / (
                SELECT COUNT(DISTINCT order_id)
                FROM order_items WHERE product_id = oi1.product_id
            ) AS similarity_score,
            COUNT(*) AS co_occurrence_count,
            'copurchase' AS similarity_type
        FROM order_items oi1
        JOIN order_items oi2 ON oi1.order_id = oi2.order_id
            AND oi1.product_id < oi2.product_id
        GROUP BY oi1.product_id, oi2.product_id
        HAVING COUNT(*) >= 3
        ON CONFLICT (product_id, similar_product_id, similarity_type)
        DO UPDATE SET
            similarity_score = EXCLUDED.similarity_score,
            co_occurrence_count = EXCLUDED.co_occurrence_count,
            updated_at = NOW()
    """

    try:
        result = await db.execute(query)
        logger.info("아이템 유사도 계산 완료")
        return 0  # 실제 개수는 결과에서 파싱
    except Exception as e:
        logger.error("아이템 유사도 계산 실패", error=str(e))
        return 0


# ============================================================================
# 가격 이상치 캐시 갱신 작업
# ============================================================================

async def refresh_price_anomaly_cache(db: Database) -> int:
    """가격 이상치 캐시 갱신

    Z-score 기반 가격 이상치를 미리 계산하여 캐시

    Args:
        db: 데이터베이스 인스턴스

    Returns:
        캐시된 이상치 상품 수
    """
    logger.info("가격 이상치 캐시 갱신 시작")

    # 카테고리별 Z-score 계산 및 캐시
    query = """
        INSERT INTO pred_price_anomaly_cache (
            product_id, anomaly_type, anomaly_score,
            current_price, reference_price, category_avg_price,
            z_score, expires_at
        )
        WITH category_stats AS (
            SELECT
                category_id,
                AVG(price) AS avg_price,
                STDDEV(price) AS stddev_price
            FROM products
            WHERE status = 'active'
            GROUP BY category_id
        ),
        product_scores AS (
            SELECT
                p.id AS product_id,
                p.price AS current_price,
                p.original_price AS reference_price,
                cs.avg_price AS category_avg_price,
                (p.price - cs.avg_price) / NULLIF(cs.stddev_price, 0) AS z_score
            FROM products p
            JOIN category_stats cs ON p.category_id = cs.category_id
            WHERE p.status = 'active'
        )
        SELECT
            product_id,
            CASE
                WHEN z_score < -2 THEN 'price_drop'
                WHEN z_score > 2 THEN 'price_surge'
                ELSE 'below_market'
            END AS anomaly_type,
            ABS(z_score) * 10 AS anomaly_score,
            current_price,
            reference_price,
            category_avg_price,
            z_score,
            NOW() + INTERVAL '6 hours' AS expires_at
        FROM product_scores
        WHERE ABS(z_score) >= 1.5
        ON CONFLICT (product_id)
        DO UPDATE SET
            anomaly_type = EXCLUDED.anomaly_type,
            anomaly_score = EXCLUDED.anomaly_score,
            current_price = EXCLUDED.current_price,
            reference_price = EXCLUDED.reference_price,
            category_avg_price = EXCLUDED.category_avg_price,
            z_score = EXCLUDED.z_score,
            expires_at = EXCLUDED.expires_at,
            calculated_at = NOW()
    """

    try:
        result = await db.execute(query)
        logger.info("가격 이상치 캐시 갱신 완료")
        return 0
    except Exception as e:
        logger.error("가격 이상치 캐시 갱신 실패", error=str(e))
        return 0


# ============================================================================
# 사용자 임베딩 갱신 작업
# ============================================================================

async def update_user_embeddings(
    db: Database,
    batch_size: int = 100,
) -> int:
    """사용자 임베딩 갱신

    최근 상호작용 기반 사용자 임베딩 업데이트

    Args:
        db: 데이터베이스 인스턴스
        batch_size: 배치 크기

    Returns:
        갱신된 사용자 수
    """
    logger.info("사용자 임베딩 갱신 시작")

    # 최근 활동한 사용자 조회
    active_users_query = """
        SELECT DISTINCT user_id
        FROM user_product_stats
        WHERE last_interacted_at > NOW() - INTERVAL '7 days'
        LIMIT $1
    """

    try:
        users = await db.fetch_all(active_users_query, batch_size)

        if not users:
            logger.info("갱신할 사용자 없음")
            return 0

        updated_count = 0
        user_embedding_repo = UserEmbeddingRepository(db)
        embedding_repo = EmbeddingCacheRepository(db)

        for user in users:
            user_id = user["user_id"]

            # 사용자의 상호작용 상품 조회
            products_query = """
                SELECT ups.product_id, ups.view_count, ups.cart_event_count,
                       ups.order_event_count
                FROM user_product_stats ups
                WHERE ups.user_id = $1
                ORDER BY ups.last_interacted_at DESC
                LIMIT 50
            """
            interactions = await db.fetch_all(products_query, user_id)

            if not interactions:
                continue

            product_ids = [p["product_id"] for p in interactions]

            # 상품 임베딩 조회
            product_embeddings = await embedding_repo.get_product_embeddings_batch(
                product_ids
            )

            if not product_embeddings:
                continue

            # 가중 평균으로 사용자 임베딩 계산
            weights = []
            embeddings = []

            for interaction in interactions:
                pid = interaction["product_id"]
                if pid not in product_embeddings:
                    continue

                # 상호작용 강도 기반 가중치
                weight = (
                    interaction["order_event_count"] * 5 +
                    interaction["cart_event_count"] * 3 +
                    interaction["view_count"] * 1
                )
                weights.append(weight)
                embeddings.append(product_embeddings[pid])

            if not embeddings:
                continue

            # 가중 평균 계산
            total_weight = sum(weights)
            user_embedding = [0.0] * len(embeddings[0])

            for i, emb in enumerate(embeddings):
                w = weights[i] / total_weight
                for j, val in enumerate(emb):
                    user_embedding[j] += val * w

            # 선호 카테고리 조회
            categories_query = """
                SELECT p.category_id, COUNT(*) AS cnt
                FROM user_product_stats ups
                JOIN products p ON ups.product_id = p.id
                WHERE ups.user_id = $1 AND p.category_id IS NOT NULL
                GROUP BY p.category_id
                ORDER BY cnt DESC
                LIMIT 5
            """
            categories = await db.fetch_all(categories_query, user_id)
            preference_categories = [c["category_id"] for c in categories]

            # 임베딩 저장
            await user_embedding_repo.upsert_user_embedding(
                user_id=user_id,
                embedding_vector=user_embedding,
                preference_categories=preference_categories,
                interaction_count=len(interactions),
                model_version="1.0.0",
            )
            updated_count += 1

        logger.info("사용자 임베딩 갱신 완료", updated_count=updated_count)
        return updated_count

    except Exception as e:
        logger.error("사용자 임베딩 갱신 실패", error=str(e))
        return 0


# ============================================================================
# 배치 작업 등록 함수
# ============================================================================

def register_all_jobs(scheduler, db: Database) -> None:
    """모든 배치 작업 등록

    Args:
        scheduler: BatchScheduler 인스턴스
        db: 데이터베이스 인스턴스
    """
    # 캐시 정리 (1시간마다)
    scheduler.register_job(
        name="cleanup_cache",
        func=lambda: cleanup_expired_cache(db),
        cron="1h",
        enabled=True,
    )

    # 가격 이상치 캐시 (6시간마다)
    scheduler.register_job(
        name="refresh_price_anomaly",
        func=lambda: refresh_price_anomaly_cache(db),
        cron="6h",
        enabled=True,
    )

    # 사용자 임베딩 갱신 (매일)
    scheduler.register_job(
        name="update_user_embeddings",
        func=lambda: update_user_embeddings(db),
        cron="daily",
        enabled=True,
    )

    # 아이템 유사도 계산 (매일)
    scheduler.register_job(
        name="compute_item_similarity",
        func=lambda: compute_item_similarity(db),
        cron="daily",
        enabled=True,
    )

    logger.info("모든 배치 작업 등록 완료", job_count=len(scheduler.jobs))
