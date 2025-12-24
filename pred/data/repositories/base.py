"""
베이스 Repository 클래스

데이터 접근 계층의 기본 클래스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from asyncpg import Record

from core.database import Database
from core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """데이터 접근 기본 클래스

    모든 Repository는 이 클래스를 상속받습니다.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: 데이터베이스 인스턴스
        """
        self.db = db

    @property
    @abstractmethod
    def table_name(self) -> str:
        """테이블 이름"""
        pass

    def _record_to_dict(self, record: Record) -> Dict[str, Any]:
        """Record를 딕셔너리로 변환

        Args:
            record: asyncpg Record

        Returns:
            딕셔너리
        """
        return dict(record)

    def _records_to_list(self, records: List[Record]) -> List[Dict[str, Any]]:
        """Record 리스트를 딕셔너리 리스트로 변환

        Args:
            records: asyncpg Record 리스트

        Returns:
            딕셔너리 리스트
        """
        return [self._record_to_dict(r) for r in records]

    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """ID로 단일 레코드 조회

        Args:
            id: 레코드 ID

        Returns:
            레코드 딕셔너리 또는 None
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = $1"
        record = await self.db.fetch_one(query, id)
        return self._record_to_dict(record) if record else None

    async def get_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        """여러 ID로 레코드 조회

        Args:
            ids: 레코드 ID 리스트

        Returns:
            레코드 딕셔너리 리스트
        """
        if not ids:
            return []

        query = f"SELECT * FROM {self.table_name} WHERE id = ANY($1)"
        records = await self.db.fetch_all(query, ids)
        return self._records_to_list(records)

    async def count(self, where_clause: str = "", *args: Any) -> int:
        """레코드 수 조회

        Args:
            where_clause: WHERE 절 (예: "WHERE status = $1")
            *args: WHERE 절 파라미터

        Returns:
            레코드 수
        """
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" {where_clause}"

        count = await self.db.fetch_val(query, *args)
        return count or 0

    async def exists(self, id: int) -> bool:
        """레코드 존재 여부 확인

        Args:
            id: 레코드 ID

        Returns:
            존재 여부
        """
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE id = $1)"
        return await self.db.fetch_val(query, id) or False


class ReadOnlyRepository(BaseRepository[T], ABC):
    """읽기 전용 Repository

    기존 테이블(products, users 등)을 읽기만 할 때 사용
    """

    pass


class WritableRepository(BaseRepository[T], ABC):
    """쓰기 가능 Repository

    추천 시스템 전용 테이블(pred_*)에 사용
    """

    async def insert(self, data: Dict[str, Any]) -> Optional[int]:
        """레코드 삽입

        Args:
            data: 삽입할 데이터 딕셔너리

        Returns:
            생성된 레코드 ID
        """
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())

        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """

        return await self.db.fetch_val(query, *values)

    async def update(self, id: int, data: Dict[str, Any]) -> bool:
        """레코드 수정

        Args:
            id: 레코드 ID
            data: 수정할 데이터 딕셔너리

        Returns:
            수정 성공 여부
        """
        if not data:
            return False

        set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(data.keys())]
        values = [id] + list(data.values())

        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = $1
        """

        result = await self.db.execute(query, *values)
        return "UPDATE 1" in result

    async def delete(self, id: int) -> bool:
        """레코드 삭제

        Args:
            id: 레코드 ID

        Returns:
            삭제 성공 여부
        """
        query = f"DELETE FROM {self.table_name} WHERE id = $1"
        result = await self.db.execute(query, id)
        return "DELETE 1" in result

    async def upsert(
        self,
        data: Dict[str, Any],
        conflict_columns: List[str],
        update_columns: Optional[List[str]] = None,
    ) -> Optional[int]:
        """UPSERT (INSERT 또는 UPDATE)

        Args:
            data: 삽입할 데이터
            conflict_columns: 충돌 감지 컬럼들
            update_columns: 업데이트할 컬럼들 (None이면 전체)

        Returns:
            레코드 ID
        """
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())

        update_cols = update_columns or [c for c in columns if c not in conflict_columns]
        update_clauses = [f"{c} = EXCLUDED.{c}" for c in update_cols]

        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT ({', '.join(conflict_columns)})
            DO UPDATE SET {', '.join(update_clauses)}
            RETURNING id
        """

        return await self.db.fetch_val(query, *values)

    async def bulk_insert(self, records: List[Dict[str, Any]]) -> int:
        """대량 삽입

        Args:
            records: 삽입할 레코드 리스트

        Returns:
            삽입된 레코드 수
        """
        if not records:
            return 0

        columns = list(records[0].keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]

        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """

        args_list = [tuple(r[c] for c in columns) for r in records]
        await self.db.execute_many(query, args_list)

        return len(records)
