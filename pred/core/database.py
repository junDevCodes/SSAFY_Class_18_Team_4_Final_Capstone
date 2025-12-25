"""
데이터베이스 연결 모듈

asyncpg를 사용한 PostgreSQL 비동기 연결 풀 관리
"""

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import asyncpg
from asyncpg import Pool, Record

from core.config import settings
from core.exceptions import DatabaseConnectionError, DatabaseQueryError
from core.logging import get_logger

logger = get_logger(__name__)


async def _init_connection(conn: asyncpg.Connection) -> None:
    """커넥션 초기화 - JSON/JSONB 타입 코덱 등록

    asyncpg는 기본적으로 JSON/JSONB 필드를 문자열로 반환합니다.
    이 함수는 각 커넥션에 JSON 코덱을 등록하여 Python dict로 자동 변환합니다.

    Args:
        conn: 초기화할 asyncpg 커넥션
    """
    # JSON 타입 코덱 등록 (PostgreSQL OID: 114)
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )
    # JSONB 타입 코덱 등록 (PostgreSQL OID: 3802)
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )


class Database:
    """PostgreSQL 데이터베이스 연결 관리 클래스

    asyncpg 기반 커넥션 풀을 관리합니다.
    """

    def __init__(self):
        self._pool: Optional[Pool] = None

    @property
    def pool(self) -> Pool:
        """커넥션 풀 반환"""
        if self._pool is None:
            raise DatabaseConnectionError("데이터베이스 연결이 초기화되지 않았습니다")
        return self._pool

    async def connect(self) -> None:
        """데이터베이스 연결 풀 생성"""
        try:
            logger.info(
                "데이터베이스 연결 시도",
                host=settings.db_host,
                port=settings.db_port,
                database=settings.db_name,
            )

            self._pool = await asyncpg.create_pool(
                host=settings.db_host,
                port=settings.db_port,
                database=settings.db_name,
                user=settings.db_user,
                password=settings.db_password,
                min_size=settings.db_min_connections,
                max_size=settings.db_max_connections,
                command_timeout=30,
                init=_init_connection,  # JSON/JSONB 타입 코덱 등록
            )

            logger.info(
                "데이터베이스 연결 성공",
                min_connections=settings.db_min_connections,
                max_connections=settings.db_max_connections,
            )

        except Exception as e:
            logger.error("데이터베이스 연결 실패", error=str(e))
            raise DatabaseConnectionError(
                f"데이터베이스 연결에 실패했습니다: {e}",
                details={"host": settings.db_host, "port": settings.db_port},
            )

    async def disconnect(self) -> None:
        """데이터베이스 연결 풀 종료"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("데이터베이스 연결 종료")

    async def fetch_one(
        self,
        query: str,
        *args: Any,
        timeout: Optional[float] = None,
    ) -> Optional[Record]:
        """단일 레코드 조회

        Args:
            query: SQL 쿼리 ($1, $2 형태의 파라미터 사용)
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃 (초)

        Returns:
            조회된 레코드 또는 None
        """
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args, timeout=timeout)
        except Exception as e:
            logger.error("쿼리 실행 실패", query=query[:100], error=str(e))
            raise DatabaseQueryError(
                f"쿼리 실행에 실패했습니다: {e}",
                query=query[:200],
            )

    async def fetch_all(
        self,
        query: str,
        *args: Any,
        timeout: Optional[float] = None,
    ) -> List[Record]:
        """다중 레코드 조회

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃 (초)

        Returns:
            조회된 레코드 목록
        """
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args, timeout=timeout)
        except Exception as e:
            logger.error("쿼리 실행 실패", query=query[:100], error=str(e))
            raise DatabaseQueryError(
                f"쿼리 실행에 실패했습니다: {e}",
                query=query[:200],
            )

    async def fetch_val(
        self,
        query: str,
        *args: Any,
        column: int = 0,
        timeout: Optional[float] = None,
    ) -> Any:
        """단일 값 조회

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            column: 반환할 컬럼 인덱스 (기본 0)
            timeout: 쿼리 타임아웃 (초)

        Returns:
            조회된 값
        """
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args, column=column, timeout=timeout)
        except Exception as e:
            logger.error("쿼리 실행 실패", query=query[:100], error=str(e))
            raise DatabaseQueryError(
                f"쿼리 실행에 실패했습니다: {e}",
                query=query[:200],
            )

    async def execute(
        self,
        query: str,
        *args: Any,
        timeout: Optional[float] = None,
    ) -> str:
        """쿼리 실행 (INSERT, UPDATE, DELETE 등)

        Args:
            query: SQL 쿼리
            *args: 쿼리 파라미터
            timeout: 쿼리 타임아웃 (초)

        Returns:
            실행 결과 문자열 (예: "INSERT 0 1")
        """
        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args, timeout=timeout)
        except Exception as e:
            logger.error("쿼리 실행 실패", query=query[:100], error=str(e))
            raise DatabaseQueryError(
                f"쿼리 실행에 실패했습니다: {e}",
                query=query[:200],
            )

    async def execute_many(
        self,
        query: str,
        args_list: List[tuple],
        timeout: Optional[float] = None,
    ) -> None:
        """배치 쿼리 실행

        Args:
            query: SQL 쿼리
            args_list: 파라미터 튜플 목록
            timeout: 쿼리 타임아웃 (초)
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.executemany(query, args_list, timeout=timeout)
        except Exception as e:
            logger.error("배치 쿼리 실행 실패", query=query[:100], error=str(e))
            raise DatabaseQueryError(
                f"배치 쿼리 실행에 실패했습니다: {e}",
                query=query[:200],
            )

    @asynccontextmanager
    async def transaction(
        self,
        isolation: str = "read_committed",
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """트랜잭션 컨텍스트 관리자

        Args:
            isolation: 격리 수준 (read_committed, repeatable_read, serializable)

        Yields:
            트랜잭션이 활성화된 커넥션
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction(isolation=isolation):
                yield conn

    async def health_check(self) -> bool:
        """데이터베이스 연결 상태 확인

        Returns:
            연결 정상 여부
        """
        try:
            result = await self.fetch_val("SELECT 1")
            return result == 1
        except Exception:
            return False


# 전역 데이터베이스 인스턴스
db = Database()


async def get_database() -> Database:
    """FastAPI 의존성 주입용 데이터베이스 인스턴스 반환"""
    return db
