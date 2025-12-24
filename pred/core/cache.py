"""
캐시 관리 모듈

Redis를 사용한 캐시 관리
"""

import json
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import settings
from core.exceptions import CacheConnectionError, CacheException
from core.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Redis 캐시 관리 클래스"""

    def __init__(self):
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        """Redis 클라이언트 반환"""
        if self._client is None:
            raise CacheConnectionError("Redis 연결이 초기화되지 않았습니다")
        return self._client

    async def connect(self) -> None:
        """Redis 연결"""
        try:
            logger.info(
                "Redis 연결 시도",
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
            )

            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            # 연결 테스트
            await self._client.ping()

            logger.info("Redis 연결 성공")

        except Exception as e:
            logger.error("Redis 연결 실패", error=str(e))
            # Redis 연결 실패해도 서비스는 계속 동작 (캐시 없이)
            self._client = None
            logger.warning("캐시 없이 서비스를 계속합니다")

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis 연결 종료")

    def is_connected(self) -> bool:
        """Redis 연결 상태 확인"""
        return self._client is not None

    async def get(self, key: str) -> Optional[str]:
        """캐시 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        if not self.is_connected():
            return None

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning("캐시 조회 실패", key=key, error=str(e))
            return None

    async def get_json(self, key: str) -> Optional[Any]:
        """JSON 캐시 조회

        Args:
            key: 캐시 키

        Returns:
            파싱된 JSON 값 또는 None
        """
        value = await self.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("캐시 JSON 파싱 실패", key=key)
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초)

        Returns:
            저장 성공 여부
        """
        if not self.is_connected():
            return False

        try:
            await self._client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.warning("캐시 저장 실패", key=key, error=str(e))
            return False

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """JSON 캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 값 (JSON 직렬화 가능)
            ttl: TTL (초)

        Returns:
            저장 성공 여부
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.warning("캐시 JSON 직렬화 실패", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        if not self.is_connected():
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("캐시 삭제 실패", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """패턴 매칭 캐시 삭제

        Args:
            pattern: 키 패턴 (예: "user:*:recommendations")

        Returns:
            삭제된 키 개수
        """
        if not self.is_connected():
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("패턴 캐시 삭제 실패", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """캐시 존재 여부 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        if not self.is_connected():
            return False

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.warning("캐시 존재 확인 실패", key=key, error=str(e))
            return False

    async def ttl(self, key: str) -> int:
        """캐시 TTL 조회

        Args:
            key: 캐시 키

        Returns:
            남은 TTL (초), -1이면 만료 없음, -2면 키 없음
        """
        if not self.is_connected():
            return -2

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.warning("캐시 TTL 조회 실패", key=key, error=str(e))
            return -2

    async def health_check(self) -> bool:
        """Redis 연결 상태 확인

        Returns:
            연결 정상 여부
        """
        if not self.is_connected():
            return False

        try:
            await self._client.ping()
            return True
        except Exception:
            return False


class CacheKeys:
    """캐시 키 생성 유틸리티"""

    # 캐시 키 프리픽스
    PREFIX = "pred"

    @classmethod
    def recommendation(
        cls,
        user_id: Optional[int],
        page_type: str,
        context_hash: str,
    ) -> str:
        """추천 결과 캐시 키 생성"""
        user_part = str(user_id) if user_id else "anonymous"
        return f"{cls.PREFIX}:rec:{user_part}:{page_type}:{context_hash}"

    @classmethod
    def price_anomaly(cls, category_id: Optional[int] = None) -> str:
        """가격 이상치 캐시 키 생성"""
        if category_id:
            return f"{cls.PREFIX}:anomaly:cat:{category_id}"
        return f"{cls.PREFIX}:anomaly:all"

    @classmethod
    def user_embedding(cls, user_id: int) -> str:
        """사용자 임베딩 캐시 키 생성"""
        return f"{cls.PREFIX}:user_emb:{user_id}"

    @classmethod
    def product_embedding(cls, product_id: int) -> str:
        """상품 임베딩 캐시 키 생성"""
        return f"{cls.PREFIX}:prod_emb:{product_id}"

    @classmethod
    def time_patterns(cls, time_slot: str, day_type: str) -> str:
        """시간대별 패턴 캐시 키 생성"""
        return f"{cls.PREFIX}:time_pattern:{time_slot}:{day_type}"

    @classmethod
    def similar_products(cls, product_id: int) -> str:
        """유사 상품 캐시 키 생성"""
        return f"{cls.PREFIX}:similar:{product_id}"


# 전역 캐시 인스턴스
cache = CacheManager()


async def get_cache() -> CacheManager:
    """FastAPI 의존성 주입용 캐시 인스턴스 반환"""
    return cache
