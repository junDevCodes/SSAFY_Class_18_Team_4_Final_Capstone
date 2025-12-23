"""
AIRScout 가중치 스케줄러

user_type 기반 + Sigmoid 보조 가중치 계산

설계 원칙:
1. 비회원(guest, user_id=0/None): AIRScout 100% 적용 (무조건)
2. user_type이 "warm"이면 AIRScout 완전 비활성화 (ALS 임베딩 존재)
3. user_type이 "cold"/"lukewarm"일 때만 AIRScout 활성화
4. Sigmoid는 점진적 전환을 위한 보조 역할 (days_since_signup 기반)

가중치 전략:
- guest: (1.0, 0.0) - AIRScout 100%, 개인화 없음 (비회원)
- warm: (0.0, 1.0) - AIRScout 비활성화, 개인화 100%
- lukewarm: (0.5, 0.5) - 반반 혼합
- cold: Sigmoid 스케줄 적용 (점진적 전환 준비)
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, Tuple

from core.logging import get_logger

logger = get_logger(__name__)


def sigmoid(x: float) -> float:
    """Sigmoid 함수

    Args:
        x: 입력값

    Returns:
        0~1 사이의 sigmoid 출력
    """
    # 오버플로우 방지
    if x >= 500:
        return 1.0
    if x <= -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class AIRScoutWeightScheduler:
    """AIRScout 가중치 스케줄러

    ranking_config.json의 personal_schedule 설정 기반:
    - type: "sigmoid"
    - t0: 21 (전환점: 가입 후 21일에 0.5)
    - k: 0.2 (기울기)

    가중치 계산:
        w_personal = sigmoid(k * (days - t0))
        w_airscout = 1 - w_personal

    사용법:
        scheduler = AIRScoutWeightScheduler(config)
        w_airscout, w_personal = scheduler.get_weights(days_since_signup=14)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: ranking_config.json 전체 또는 personal_schedule 부분
        """
        schedule = config.get("personal_schedule", config)

        self.schedule_type = schedule.get("type", "sigmoid")
        self.t0 = float(schedule.get("t0", 21.0))
        self.k = float(schedule.get("k", 0.2))

        logger.info(
            "AIRScoutWeightScheduler 초기화",
            extra={
                "type": self.schedule_type,
                "t0": self.t0,
                "k": self.k,
            }
        )

    @classmethod
    def from_config_file(cls, config_path: Path) -> "AIRScoutWeightScheduler":
        """ranking_config.json 파일에서 스케줄러 생성

        Args:
            config_path: ranking_config.json 파일 경로

        Returns:
            초기화된 AIRScoutWeightScheduler 인스턴스
        """
        if not config_path.exists():
            logger.warning(f"설정 파일 없음, 기본값 사용: {config_path}")
            return cls({})

        config = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(config)

    def get_weights(self, days_since_signup: int) -> Tuple[float, float]:
        """가입 경과일 기반 가중치 반환

        Args:
            days_since_signup: 가입 후 경과일

        Returns:
            (w_airscout, w_personal) 튜플
            - days < 0: (1.0, 0.0) - 완전 AIRScout
            - days = t0: (0.5, 0.5) - 반반
            - days >> t0: (~0, ~1) - 완전 개인화

        Examples:
            >>> scheduler.get_weights(0)   # (0.985, 0.015)
            >>> scheduler.get_weights(21)  # (0.500, 0.500)
            >>> scheduler.get_weights(60)  # (0.000, 1.000)
        """
        if self.schedule_type != "sigmoid":
            # Linear fallback
            ratio = min(1.0, max(0.0, days_since_signup / 60.0))
            return (1.0 - ratio, ratio)

        w_personal = sigmoid(self.k * (days_since_signup - self.t0))
        w_airscout = 1.0 - w_personal

        return (w_airscout, w_personal)

    def should_apply_airscout(self, days_since_signup: int, threshold: float = 0.05) -> bool:
        """AIRScout 적용 여부 판단 (days_since_signup 기반, deprecated)

        가중치가 threshold 미만이면 AIRScout 스킵 (효율성)

        Args:
            days_since_signup: 가입 후 경과일
            threshold: 적용 최소 가중치 (기본 0.05 = 5%)

        Returns:
            AIRScout 적용 여부

        Note:
            user_type 기반 should_apply_airscout_by_type() 사용 권장
        """
        w_airscout, _ = self.get_weights(days_since_signup)
        return w_airscout >= threshold

    def get_weights_by_user_type(
        self,
        user_type: str,
        days_since_signup: int = 0,
        is_guest: bool = False,
    ) -> Tuple[float, float]:
        """user_type 기반 가중치 반환 (Primary 메서드)

        ALS 모델의 user_type을 기준으로 AIRScout 가중치를 결정합니다.
        user_type은 실제 사용자 임베딩 존재 여부를 반영하므로
        days_since_signup보다 더 정확한 개인화 상태를 나타냅니다.

        Args:
            user_type: 사용자 타입 ('cold', 'lukewarm', 'warm')
            days_since_signup: 가입 후 경과일 (cold일 때 Sigmoid 보조용)
            is_guest: 비회원 여부 (user_id=0 또는 None)

        Returns:
            (w_airscout, w_personal) 튜플

        가중치 전략:
            - guest: (1.0, 0.0) - 비회원, AIRScout 100%
            - warm: (0.0, 1.0) - ALS 임베딩 존재, AIRScout 불필요
            - lukewarm: (0.5, 0.5) - 탐색 중, 반반 혼합
            - cold: Sigmoid 스케줄 적용 (점진적 전환 준비)

        Examples:
            >>> scheduler.get_weights_by_user_type("cold", is_guest=True)  # (1.0, 0.0)
            >>> scheduler.get_weights_by_user_type("warm")      # (0.0, 1.0)
            >>> scheduler.get_weights_by_user_type("lukewarm")  # (0.5, 0.5)
            >>> scheduler.get_weights_by_user_type("cold", 0)   # (0.985, 0.015)
            >>> scheduler.get_weights_by_user_type("cold", 21)  # (0.5, 0.5)
        """
        # 비회원은 무조건 AIRScout 100%
        if is_guest:
            return (1.0, 0.0)

        if user_type == "warm":
            # ALS 임베딩이 충분히 학습됨 → AIRScout 불필요
            return (0.0, 1.0)

        if user_type == "lukewarm":
            # 탐색 중인 사용자 → 반반 혼합
            return (0.5, 0.5)

        # cold: Sigmoid 스케줄로 점진적 전환 준비
        return self.get_weights(days_since_signup)

    def should_apply_airscout_by_type(
        self,
        user_type: str,
        is_guest: bool = False,
    ) -> bool:
        """user_type 기반 AIRScout 적용 여부 판단 (Primary 메서드)

        Args:
            user_type: 사용자 타입 ('cold', 'lukewarm', 'warm')
            is_guest: 비회원 여부 (user_id=0 또는 None)

        Returns:
            AIRScout 적용 여부
        """
        # 비회원은 무조건 AIRScout 적용
        if is_guest:
            return True

        # warm 사용자는 AIRScout 스킵
        return user_type in ("cold", "lukewarm")

    def get_hybrid_formula_weights(self) -> Tuple[float, float]:
        """하이브리드 스코어 공식 가중치 반환

        airscout_formula: "0.7*semantic + 0.3*user_score"

        Returns:
            (semantic_weight, user_score_weight) = (0.7, 0.3)
        """
        # TODO: ranking_config.json에서 동적으로 파싱
        return (0.7, 0.3)

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환 (디버깅/모니터링용)"""
        return {
            "schedule_type": self.schedule_type,
            "t0": self.t0,
            "k": self.k,
            "semantic_weight": 0.7,
            "user_score_weight": 0.3,
        }


# 기본 설정으로 사용할 수 있는 싱글톤 인스턴스 생성 헬퍼
_default_scheduler: AIRScoutWeightScheduler = None


def get_default_scheduler() -> AIRScoutWeightScheduler:
    """기본 설정의 스케줄러 반환 (싱글톤)"""
    global _default_scheduler
    if _default_scheduler is None:
        # 기본 설정
        _default_scheduler = AIRScoutWeightScheduler({
            "personal_schedule": {
                "type": "sigmoid",
                "t0": 21,
                "k": 0.2,
            }
        })
    return _default_scheduler
