"""
환경 설정 모듈

Pydantic Settings를 사용한 환경 변수 기반 설정 관리
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정

    환경 변수 또는 .env 파일에서 설정을 로드합니다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 정의되지 않은 환경변수 무시
        populate_by_name=True,  # alias와 원래 이름 둘 다 허용
    )

    # 서비스 설정
    service_name: str = Field(default="self-pred", description="서비스 이름")
    service_version: str = Field(default="1.0.0", description="서비스 버전")
    debug: bool = Field(default=False, description="디버그 모드")
    log_level: str = Field(default="INFO", description="로그 레벨")

    # 서버 설정
    host: str = Field(default="0.0.0.0", description="서버 호스트")
    port: int = Field(default=8001, description="서버 포트")

    # PostgreSQL 설정
    db_host: str = Field(default="localhost", description="DB 호스트")
    db_port: int = Field(default=5432, description="DB 포트")
    db_name: str = Field(default="selfdb", description="DB 이름")
    db_user: str = Field(default="selfuser", description="DB 사용자")
    db_password: str = Field(default="selfpass", description="DB 비밀번호")
    db_min_connections: int = Field(default=5, description="최소 DB 연결 수")
    db_max_connections: int = Field(default=20, description="최대 DB 연결 수")

    # Redis 설정
    redis_host: str = Field(default="localhost", description="Redis 호스트")
    redis_port: int = Field(default=6379, description="Redis 포트")
    redis_db: int = Field(default=0, description="Redis DB 번호")
    redis_password: Optional[str] = Field(default=None, description="Redis 비밀번호")

    # 캐시 TTL (초)
    cache_ttl_recommendation: int = Field(
        default=1800, description="추천 캐시 TTL (30분)"
    )
    cache_ttl_price_anomaly: int = Field(
        default=3600, description="가격 이상치 캐시 TTL (1시간)"
    )
    cache_ttl_user_embedding: int = Field(
        default=86400, description="사용자 임베딩 캐시 TTL (24시간)"
    )

    # ML 모델 설정
    bert_model_name: str = Field(
        default="klue/bert-base", description="BERT 모델명"
    )
    embedding_dimension: int = Field(default=768, description="임베딩 차원")

    # 타임아웃 설정 (밀리초)
    model_timeout_coldstart: int = Field(
        default=100, description="콜드스타트 모델 타임아웃 (ms)"
    )
    model_timeout_personalized: int = Field(
        default=200, description="개인화 모델 타임아웃 (ms)"
    )
    model_timeout_price: int = Field(
        default=150, description="가격 이상치 모델 타임아웃 (ms)"
    )
    model_timeout_recipe: int = Field(
        default=200, description="레시피 모델 타임아웃 (ms)"
    )
    model_timeout_airscout: int = Field(
        default=200, description="AIRScout 보조 모델 타임아웃 (ms)"
    )
    api_timeout: int = Field(default=500, description="API 전체 타임아웃 (ms)")

    # 배치 처리 설정
    batch_chunk_size: int = Field(default=1000, description="배치 청크 크기")
    batch_similarity_top_k: int = Field(
        default=100, description="유사도 계산 시 상위 K개"
    )

    # CORS 설정 (CORS_ORIGINS 또는 CORS_ORIGINS_STR 환경변수 사용)
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:8000",
        description="허용할 CORS 오리진 (쉼표로 구분)",
        alias="cors_origins",  # CORS_ORIGINS 환경변수도 인식
    )

    @property
    def cors_origins(self) -> List[str]:
        """CORS 오리진 목록"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    @property
    def database_url(self) -> str:
        """PostgreSQL 연결 URL (asyncpg용)"""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_async(self) -> str:
        """PostgreSQL 비동기 연결 URL (asyncpg용)"""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Redis 연결 URL"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}"
                f"@{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def model_timeouts(self) -> dict:
        """모델별 타임아웃 설정 (초 단위로 변환)"""
        return {
            "instacart": self.model_timeout_coldstart / 1000,
            "self": self.model_timeout_personalized / 1000,
            "price": self.model_timeout_price / 1000,
            "recipe": self.model_timeout_recipe / 1000,
            "airscout": self.model_timeout_airscout / 1000,
        }


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스 반환 (캐싱됨)"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
