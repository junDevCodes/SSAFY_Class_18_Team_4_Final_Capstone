"""
ML 모델 기본 클래스

모든 추천 모델의 공통 인터페이스와 기본 기능을 정의합니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio

from core.database import Database
from core.cache import CacheManager
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


@dataclass
class RecommendationContext:
    """추천 요청 컨텍스트

    모든 추천 모델에 전달되는 공통 컨텍스트 정보
    """

    user_id: int
    page_type: str  # 'home', 'category', 'product_detail', 'cart', 'search'
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    cart_product_ids: List[int] = field(default_factory=list)
    search_query: Optional[str] = None

    # 시간 컨텍스트
    time_context: str = "default"  # 'morning', 'lunch', 'dinner', 'night'
    is_weekend: bool = False
    day_of_week: int = 0  # 0=월요일, 6=일요일
    hour_of_day: int = 12

    # 사용자 분류
    user_type: str = "cold"  # 'cold', 'lukewarm', 'warm'
    interaction_count: int = 0  # 사용자 상호작용 횟수 (동적 가중치용)

    # 추가 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationResult:
    """추천 결과

    개별 추천 모델의 결과를 담는 데이터 클래스
    """

    model_name: str
    products: List[Dict[str, Any]]
    scores: List[float] = field(default_factory=list)
    confidence: float = 1.0
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """결과 성공 여부"""
        return self.error is None and len(self.products) > 0


class BaseRecommendationModel(ABC):
    """추천 모델 기본 클래스

    모든 추천 모델은 이 클래스를 상속받아야 합니다.
    """

    def __init__(
        self,
        db: Database,
        cache: Optional[CacheManager] = None,
    ):
        """
        Args:
            db: 데이터베이스 인스턴스
            cache: 캐시 매니저 (선택적)
        """
        self.db = db
        self.cache = cache
        self._initialized = False

    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델 이름"""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """모델 버전"""
        pass

    @property
    def timeout_ms(self) -> int:
        """모델 타임아웃 (밀리초)"""
        return settings.model_timeouts.get(self.model_name, 500)

    async def initialize(self) -> None:
        """모델 초기화

        필요한 리소스 로딩 등을 수행합니다.
        서브클래스에서 오버라이드할 수 있습니다.
        """
        self._initialized = True
        logger.info(
            "모델 초기화 완료",
            model=self.model_name,
            version=self.model_version,
        )

    @abstractmethod
    async def _recommend(
        self,
        context: RecommendationContext,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """추천 로직 구현 (서브클래스에서 구현)

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 상품 목록
        """
        pass

    async def recommend(
        self,
        context: RecommendationContext,
        limit: int = 10,
    ) -> RecommendationResult:
        """추천 실행 (타임아웃 및 에러 처리 포함)

        Args:
            context: 추천 컨텍스트
            limit: 추천 개수

        Returns:
            추천 결과
        """
        start_time = datetime.now()

        try:
            # 타임아웃 적용
            products = await asyncio.wait_for(
                self._recommend(context, limit),
                timeout=self.timeout_ms / 1000.0,
            )

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return RecommendationResult(
                model_name=self.model_name,
                products=products[:limit],
                confidence=self._calculate_confidence(context, products),
                execution_time_ms=execution_time,
                metadata={
                    "version": self.model_version,
                    "user_type": context.user_type,
                    "page_type": context.page_type,
                },
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.warning(
                "모델 타임아웃",
                model=self.model_name,
                timeout_ms=self.timeout_ms,
                user_id=context.user_id,
            )
            return RecommendationResult(
                model_name=self.model_name,
                products=[],
                execution_time_ms=execution_time,
                error=f"Timeout after {self.timeout_ms}ms",
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                "모델 실행 오류",
                model=self.model_name,
                error=str(e),
                user_id=context.user_id,
            )
            return RecommendationResult(
                model_name=self.model_name,
                products=[],
                execution_time_ms=execution_time,
                error=str(e),
            )

    def _calculate_confidence(
        self,
        context: RecommendationContext,
        products: List[Dict[str, Any]],
    ) -> float:
        """결과 신뢰도 계산

        서브클래스에서 오버라이드하여 모델별 신뢰도 계산 로직 구현

        Args:
            context: 추천 컨텍스트
            products: 추천 상품 목록

        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not products:
            return 0.0

        # 기본: 요청 개수 대비 결과 개수 비율
        return min(1.0, len(products) / 10.0)

    async def get_cache_key(self, context: RecommendationContext) -> str:
        """캐시 키 생성

        Args:
            context: 추천 컨텍스트

        Returns:
            캐시 키 문자열
        """
        parts = [
            f"rec:{self.model_name}",
            f"u:{context.user_id}",
            f"p:{context.page_type}",
            f"t:{context.user_type}",
        ]

        if context.category_id:
            parts.append(f"c:{context.category_id}")
        if context.product_id:
            parts.append(f"pid:{context.product_id}")
        if context.time_context:
            parts.append(f"tc:{context.time_context}")

        return ":".join(parts)

    async def get_cached_result(
        self,
        context: RecommendationContext,
    ) -> Optional[RecommendationResult]:
        """캐시된 결과 조회

        Args:
            context: 추천 컨텍스트

        Returns:
            캐시된 결과 또는 None
        """
        if not self.cache:
            return None

        cache_key = await self.get_cache_key(context)
        cached = await self.cache.get_json(cache_key)

        if cached:
            logger.debug(
                "캐시 히트",
                model=self.model_name,
                user_id=context.user_id,
            )
            return RecommendationResult(
                model_name=self.model_name,
                products=cached.get("products", []),
                scores=cached.get("scores", []),
                confidence=cached.get("confidence", 1.0),
                execution_time_ms=0,
                metadata={"source": "cache", **cached.get("metadata", {})},
            )

        return None

    async def cache_result(
        self,
        context: RecommendationContext,
        result: RecommendationResult,
        ttl: int = 3600,
    ) -> None:
        """결과 캐시 저장

        Args:
            context: 추천 컨텍스트
            result: 추천 결과
            ttl: TTL (초)
        """
        if not self.cache or not result.success:
            return

        cache_key = await self.get_cache_key(context)
        cache_data = {
            "products": result.products,
            "scores": result.scores,
            "confidence": result.confidence,
            "metadata": result.metadata,
        }

        await self.cache.set_json(cache_key, cache_data, ttl)


class ColdStartModel(BaseRecommendationModel):
    """Cold Start 모델 기본 클래스

    신규/비로그인 사용자를 위한 추천 모델
    """

    @property
    def supported_user_types(self) -> List[str]:
        """지원하는 사용자 유형"""
        return ["cold"]


class PersonalizedModel(BaseRecommendationModel):
    """개인화 모델 기본 클래스

    상호작용 이력이 있는 사용자를 위한 추천 모델
    """

    @property
    def supported_user_types(self) -> List[str]:
        """지원하는 사용자 유형"""
        return ["lukewarm", "warm"]


class HybridModel(BaseRecommendationModel):
    """하이브리드 모델 기본 클래스

    모든 사용자 유형을 지원하는 추천 모델
    """

    @property
    def supported_user_types(self) -> List[str]:
        """지원하는 사용자 유형"""
        return ["cold", "lukewarm", "warm"]
