"""
캐시 데이터 Repository

추천 결과 캐시 및 임베딩 캐시 관리
Redis fallback을 위한 PostgreSQL 캐시 테이블 접근
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from data.repositories.base import WritableRepository
from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)


class RecommendationCacheRepository(WritableRepository):
    """추천 결과 캐시 Repository

    Redis 장애 시 PostgreSQL 테이블을 fallback으로 사용
    """

    @property
    def table_name(self) -> str:
        return "pred_recommendation_cache"

    async def get_cached_recommendations(
        self,
        user_id: int,
        page_type: str,
        context_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """캐시된 추천 결과 조회

        Args:
            user_id: 사용자 ID
            page_type: 페이지 타입
            context_key: 추가 컨텍스트 키 (예: category_id, product_id)

        Returns:
            캐시된 추천 결과 또는 None
        """
        query = """
            SELECT recommendations, model_versions, created_at, expires_at
            FROM pred_recommendation_cache
            WHERE user_id = $1
              AND page_type = $2
              AND (context_key = $3 OR ($3 IS NULL AND context_key IS NULL))
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """

        record = await self.db.fetch_one(query, user_id, page_type, context_key)

        if record:
            return {
                "recommendations": record["recommendations"],
                "model_versions": record["model_versions"],
                "created_at": record["created_at"],
                "expires_at": record["expires_at"],
                "source": "postgres_cache",
            }
        return None

    async def set_cached_recommendations(
        self,
        user_id: int,
        page_type: str,
        recommendations: List[Dict[str, Any]],
        model_versions: Dict[str, str],
        context_key: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> bool:
        """추천 결과 캐시 저장

        Args:
            user_id: 사용자 ID
            page_type: 페이지 타입
            recommendations: 추천 결과
            model_versions: 사용된 모델 버전 정보
            context_key: 추가 컨텍스트 키
            ttl_seconds: TTL (초)

        Returns:
            저장 성공 여부
        """
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        # UPSERT 사용
        query = """
            INSERT INTO pred_recommendation_cache
                (user_id, page_type, context_key, recommendations, model_versions, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id, page_type, context_key)
            DO UPDATE SET
                recommendations = EXCLUDED.recommendations,
                model_versions = EXCLUDED.model_versions,
                expires_at = EXCLUDED.expires_at,
                created_at = NOW()
        """

        try:
            await self.db.execute(
                query,
                user_id,
                page_type,
                context_key,
                json.dumps(recommendations, ensure_ascii=False),
                json.dumps(model_versions, ensure_ascii=False),
                expires_at,
            )
            return True
        except Exception as e:
            logger.error("추천 캐시 저장 실패", error=str(e), user_id=user_id)
            return False

    async def invalidate_user_cache(
        self,
        user_id: int,
        page_type: Optional[str] = None,
    ) -> int:
        """사용자 캐시 무효화

        Args:
            user_id: 사용자 ID
            page_type: 페이지 타입 (None이면 전체)

        Returns:
            삭제된 캐시 개수
        """
        if page_type:
            query = """
                DELETE FROM pred_recommendation_cache
                WHERE user_id = $1 AND page_type = $2
            """
            result = await self.db.execute(query, user_id, page_type)
        else:
            query = """
                DELETE FROM pred_recommendation_cache
                WHERE user_id = $1
            """
            result = await self.db.execute(query, user_id)

        # 삭제된 행 수 파싱
        try:
            count = int(result.split()[-1])
            return count
        except:
            return 0

    async def cleanup_expired_cache(self) -> int:
        """만료된 캐시 정리 (배치 작업용)

        Returns:
            삭제된 캐시 개수
        """
        query = """
            DELETE FROM pred_recommendation_cache
            WHERE expires_at < NOW()
        """

        result = await self.db.execute(query)

        try:
            count = int(result.split()[-1])
            logger.info("만료된 추천 캐시 정리 완료", deleted_count=count)
            return count
        except:
            return 0


class EmbeddingCacheRepository(WritableRepository):
    """임베딩 캐시 Repository

    상품/사용자 임베딩 벡터 캐시
    """

    @property
    def table_name(self) -> str:
        return "pred_product_embeddings"

    async def get_product_embedding(
        self,
        product_id: int,
    ) -> Optional[List[float]]:
        """상품 임베딩 조회

        Args:
            product_id: 상품 ID

        Returns:
            임베딩 벡터 (768차원)
        """
        query = """
            SELECT embedding_vector
            FROM pred_product_embeddings
            WHERE product_id = $1
        """

        result = await self.db.fetch_val(query, product_id)
        return result  # PostgreSQL의 vector 타입은 리스트로 반환됨

    async def get_product_embeddings_batch(
        self,
        product_ids: List[int],
    ) -> Dict[int, List[float]]:
        """여러 상품 임베딩 일괄 조회

        Args:
            product_ids: 상품 ID 목록

        Returns:
            {product_id: embedding_vector} 딕셔너리
        """
        if not product_ids:
            return {}

        query = """
            SELECT product_id, embedding_vector
            FROM pred_product_embeddings
            WHERE product_id = ANY($1)
        """

        records = await self.db.fetch_all(query, product_ids)
        return {r["product_id"]: r["embedding_vector"] for r in records}

    async def upsert_product_embedding(
        self,
        product_id: int,
        embedding_vector: List[float],
        model_version: str,
    ) -> bool:
        """상품 임베딩 저장/갱신

        Args:
            product_id: 상품 ID
            embedding_vector: 임베딩 벡터
            model_version: 모델 버전

        Returns:
            저장 성공 여부
        """
        query = """
            INSERT INTO pred_product_embeddings
                (product_id, embedding_vector, model_version)
            VALUES ($1, $2, $3)
            ON CONFLICT (product_id)
            DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                model_version = EXCLUDED.model_version,
                updated_at = NOW()
        """

        try:
            await self.db.execute(query, product_id, embedding_vector, model_version)
            return True
        except Exception as e:
            logger.error("상품 임베딩 저장 실패", error=str(e), product_id=product_id)
            return False

    async def find_similar_products_by_embedding(
        self,
        embedding_vector: List[float],
        limit: int = 10,
        exclude_product_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """임베딩 유사도 기반 상품 검색

        pgvector의 코사인 유사도 사용

        Args:
            embedding_vector: 기준 임베딩 벡터
            limit: 조회 개수
            exclude_product_ids: 제외할 상품 ID 목록

        Returns:
            유사 상품 목록
        """
        exclude_ids = exclude_product_ids or []

        query = """
            SELECT pe.product_id,
                   1 - (pe.embedding_vector <=> $1::vector) AS similarity,
                   p.name, p.price, p.category_id
            FROM pred_product_embeddings pe
            JOIN products p ON pe.product_id = p.id
            WHERE p.status = 'active'
              AND pe.product_id != ALL($2)
            ORDER BY pe.embedding_vector <=> $1::vector
            LIMIT $3
        """

        records = await self.db.fetch_all(
            query, embedding_vector, exclude_ids, limit
        )
        return self._records_to_list(records)


class UserEmbeddingRepository(WritableRepository):
    """사용자 임베딩 Repository"""

    @property
    def table_name(self) -> str:
        return "pred_user_embeddings"

    async def get_user_embedding(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:
        """사용자 임베딩 조회

        Args:
            user_id: 사용자 ID

        Returns:
            임베딩 정보 딕셔너리
        """
        query = """
            SELECT user_id, embedding_vector, preference_categories,
                   interaction_count, model_version, updated_at
            FROM pred_user_embeddings
            WHERE user_id = $1
        """

        record = await self.db.fetch_one(query, user_id)
        return self._record_to_dict(record) if record else None

    async def upsert_user_embedding(
        self,
        user_id: int,
        embedding_vector: List[float],
        preference_categories: List[int],
        interaction_count: int,
        model_version: str,
    ) -> bool:
        """사용자 임베딩 저장/갱신

        Args:
            user_id: 사용자 ID
            embedding_vector: 임베딩 벡터
            preference_categories: 선호 카테고리 ID 목록
            interaction_count: 상호작용 횟수
            model_version: 모델 버전

        Returns:
            저장 성공 여부
        """
        query = """
            INSERT INTO pred_user_embeddings
                (user_id, embedding_vector, preference_categories,
                 interaction_count, model_version)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id)
            DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                preference_categories = EXCLUDED.preference_categories,
                interaction_count = EXCLUDED.interaction_count,
                model_version = EXCLUDED.model_version,
                updated_at = NOW()
        """

        try:
            await self.db.execute(
                query, user_id, embedding_vector,
                preference_categories, interaction_count, model_version
            )
            return True
        except Exception as e:
            logger.error("사용자 임베딩 저장 실패", error=str(e), user_id=user_id)
            return False

    async def find_similar_users(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """유사 사용자 검색

        Args:
            user_id: 기준 사용자 ID
            limit: 조회 개수

        Returns:
            유사 사용자 목록
        """
        query = """
            WITH user_vec AS (
                SELECT embedding_vector FROM pred_user_embeddings WHERE user_id = $1
            )
            SELECT ue.user_id,
                   1 - (ue.embedding_vector <=> (SELECT embedding_vector FROM user_vec)) AS similarity,
                   ue.preference_categories,
                   ue.interaction_count
            FROM pred_user_embeddings ue
            WHERE ue.user_id != $1
              AND EXISTS (SELECT 1 FROM user_vec)
            ORDER BY ue.embedding_vector <=> (SELECT embedding_vector FROM user_vec)
            LIMIT $2
        """

        records = await self.db.fetch_all(query, user_id, limit)
        return self._records_to_list(records)
