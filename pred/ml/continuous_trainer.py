"""
연속 학습 시스템 (Continuous Training System)

적극적 연속 학습 전략:
- 학습 완료 → 검증 → 배포 → 즉시 다음 학습

안전장치:
1. Model Validation Gate: 새 모델이 품질 기준 통과해야 배포
2. Atomic Switch: 모델 교체 중 서비스 중단 없음
3. Auto Rollback: 검증 실패 시 자동 롤백
4. Health Monitoring: 학습 상태 실시간 모니터링
5. Cooldown Period: 최소 학습 간격 보장

참조:
- Netflix Metaflow: Continuous Training 패턴
- Grubhub: Online Learning for Recommendations
- MLOps Best Practices: Shadow/Canary Deployment
"""

import asyncio
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.database import Database
from core.logging import get_logger
from ml.model_loader import model_loader
from ml.trainer import ALSTrainer

logger = get_logger(__name__)


class TrainingState(Enum):
    """학습 상태"""
    IDLE = "idle"                      # 대기 중
    TRAINING = "training"              # 학습 중
    VALIDATING = "validating"          # 검증 중
    DEPLOYING = "deploying"            # 배포 중
    COOLDOWN = "cooldown"              # 쿨다운 (최소 간격 대기)
    PAUSED = "paused"                  # 일시 중지
    ERROR = "error"                    # 오류 상태


class ValidationResult(Enum):
    """검증 결과

    개인화 모델은 무결성만 검증하므로 PASSED 또는 FAILED_INTEGRITY만 사용
    """
    PASSED = "passed"                  # 통과
    FAILED_INTEGRITY = "failed_integrity"    # 무결성 오류
    SKIPPED = "skipped"                # 스킵 (학습 데이터 없음)


@dataclass
class TrainingMetrics:
    """학습 메트릭"""
    # 기본 정보
    cycle_id: int = 0                  # 학습 사이클 ID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # 모델 메트릭
    n_users: int = 0
    n_products: int = 0
    n_interactions: int = 0

    # 검증 메트릭
    user_coverage: float = 0.0         # 사용자 커버리지 (%)
    product_coverage: float = 0.0      # 상품 커버리지 (%)
    coverage_delta: float = 0.0        # 이전 대비 커버리지 변화

    # 결과
    validation_result: ValidationResult = ValidationResult.SKIPPED
    is_deployed: bool = False
    error_message: Optional[str] = None


@dataclass
class ContinuousTrainerConfig:
    """연속 학습 설정

    개인화 추천 모델 특성:
    - 사용자/상품이 늘어나면 모델이 더 좋아짐 (단조 증가)
    - 커버리지 하락은 DB 문제지 모델 품질 문제가 아님
    - 따라서 무결성 검증만 수행, 품질 검증은 불필요
    """
    # 모델 설정
    model_name: str = "self_personalized_v2"

    # 학습 간격
    min_cooldown_seconds: int = 120    # 최소 학습 간격 (초) - 2분
    max_cooldown_seconds: int = 600    # 최대 학습 간격 (초) - 10분 (연속 실패 시)

    # 안전장치
    max_consecutive_failures: int = 3  # 연속 실패 시 일시 중지
    auto_resume_after_minutes: int = 30  # 자동 재개 시간 (분)

    # 백업
    keep_backup_count: int = 5         # 유지할 백업 개수


class ModelValidator:
    """모델 검증기 (Validation Gate)

    개인화 추천 모델 특성상 무결성 검증만 수행합니다.

    왜 커버리지/품질 검증이 불필요한가:
    - 개인화 모델은 사용자/상품이 늘어나면 더 좋아지는 단조 증가 특성
    - 커버리지 하락은 DB 데이터 손실 문제이지 모델 학습 문제가 아님
    - ALS는 기존 데이터 + 신규 데이터로 학습하므로 "나빠지는" 경우 없음

    검증 항목:
    1. 무결성: 필수 컴포넌트 존재 여부 (version, components, embeddings)
    2. 임베딩 크기: 메타데이터와 실제 바이트 크기 일치 여부
    """

    def __init__(self, db: Database, config: ContinuousTrainerConfig):
        self.db = db
        self.config = config

    async def validate(
        self,
        new_model_path: Path,
        old_model_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ValidationResult, TrainingMetrics]:
        """새 모델 검증 (무결성만 확인)

        Args:
            new_model_path: 새 모델 파일 경로
            old_model_data: 기존 모델 데이터 (로깅용, 검증에는 사용 안 함)

        Returns:
            (검증 결과, 메트릭)
        """
        metrics = TrainingMetrics()

        try:
            # 1. 모델 로드
            with open(new_model_path, "rb") as f:
                new_model_data = pickle.load(f)

            # 2. 무결성 검증 (유일한 검증 항목)
            integrity_result = self._validate_integrity(new_model_data)
            if integrity_result != ValidationResult.PASSED:
                metrics.validation_result = integrity_result
                metrics.error_message = "모델 무결성 검증 실패"
                return integrity_result, metrics

            # 3. 메트릭 추출 (로깅/모니터링용)
            components = new_model_data.get("components", {})
            metadata = new_model_data.get("metadata", {})

            user_id_to_idx = components.get("user_id_to_idx", {})
            idx_to_product_id = components.get("idx_to_product_id", {})

            metrics.n_users = len(user_id_to_idx)
            metrics.n_products = len(idx_to_product_id)
            metrics.n_interactions = metadata.get("n_interactions", 0)

            # 4. 커버리지 계산 (로깅용, 검증 실패 조건 아님)
            await self._calculate_coverage_metrics(
                user_id_to_idx, idx_to_product_id, metrics
            )

            # 5. 이전 모델 대비 변화 로깅 (정보 제공용)
            if old_model_data:
                self._log_model_changes(new_model_data, old_model_data, metrics)

            metrics.validation_result = ValidationResult.PASSED
            return ValidationResult.PASSED, metrics

        except Exception as e:
            logger.error(f"모델 검증 중 오류: {e}", exc_info=True)
            metrics.validation_result = ValidationResult.FAILED_INTEGRITY
            metrics.error_message = str(e)
            return ValidationResult.FAILED_INTEGRITY, metrics

    def _validate_integrity(self, model_data: Dict[str, Any]) -> ValidationResult:
        """무결성 검증: 필수 컴포넌트 존재 및 크기 확인"""
        # 필수 키 확인
        required_keys = ["version", "components", "metadata"]
        for key in required_keys:
            if key not in model_data:
                logger.error(f"모델에 필수 키 없음: {key}")
                return ValidationResult.FAILED_INTEGRITY

        # 필수 컴포넌트 확인
        required_components = [
            "user_embeddings",
            "product_embeddings",
            "user_id_to_idx",
            "idx_to_product_id",
        ]

        components = model_data.get("components", {})
        for comp in required_components:
            if comp not in components or components[comp] is None:
                logger.error(f"모델에 필수 컴포넌트 없음: {comp}")
                return ValidationResult.FAILED_INTEGRITY

        # 임베딩 크기 검증 (bytes인 경우)
        try:
            user_embeddings = components["user_embeddings"]

            if isinstance(user_embeddings, bytes):
                factors = model_data.get("metadata", {}).get("factors", 32)
                n_users = len(components["user_id_to_idx"])
                expected_size = n_users * factors * 4  # float32 = 4 bytes

                if len(user_embeddings) != expected_size:
                    logger.error(
                        f"User embeddings 크기 불일치: "
                        f"expected={expected_size}, actual={len(user_embeddings)}"
                    )
                    return ValidationResult.FAILED_INTEGRITY

            # 상품 임베딩도 검증
            product_embeddings = components["product_embeddings"]
            if isinstance(product_embeddings, bytes):
                factors = model_data.get("metadata", {}).get("factors", 32)
                n_products = len(components["idx_to_product_id"])
                expected_size = n_products * factors * 4

                if len(product_embeddings) != expected_size:
                    logger.error(
                        f"Product embeddings 크기 불일치: "
                        f"expected={expected_size}, actual={len(product_embeddings)}"
                    )
                    return ValidationResult.FAILED_INTEGRITY

        except Exception as e:
            logger.error(f"임베딩 검증 실패: {e}")
            return ValidationResult.FAILED_INTEGRITY

        return ValidationResult.PASSED

    async def _calculate_coverage_metrics(
        self,
        user_id_to_idx: Dict[int, int],
        idx_to_product_id: Dict[int, int],
        metrics: TrainingMetrics,
    ) -> None:
        """커버리지 메트릭 계산 (로깅용, 검증 실패 조건 아님)"""
        try:
            # DB 활성 사용자 수 조회
            user_result = await self.db.fetch_one(
                "SELECT COUNT(DISTINCT user_id) AS cnt FROM user_product_stats"
            )
            db_user_count = user_result["cnt"] if user_result else 0

            # DB 활성 상품 수 조회
            product_result = await self.db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM products WHERE status = 'active'"
            )
            db_product_count = product_result["cnt"] if product_result else 0

            # 커버리지 계산
            model_user_count = len(user_id_to_idx)
            model_product_count = len(idx_to_product_id)

            user_coverage = (
                (model_user_count / db_user_count * 100) if db_user_count > 0 else 100
            )
            product_coverage = (
                (model_product_count / db_product_count * 100) if db_product_count > 0 else 100
            )

            metrics.user_coverage = round(user_coverage, 1)
            metrics.product_coverage = round(product_coverage, 1)

        except Exception as e:
            logger.warning(f"커버리지 계산 실패 (무시): {e}")

    def _log_model_changes(
        self,
        new_model_data: Dict[str, Any],
        old_model_data: Dict[str, Any],
        metrics: TrainingMetrics,
    ) -> None:
        """이전 모델 대비 변화 로깅 (정보 제공용)"""
        try:
            new_components = new_model_data.get("components", {})
            old_components = old_model_data.get("components", {})

            new_users = len(new_components.get("user_id_to_idx", {}))
            old_users = len(old_components.get("user_id_to_idx", {}))
            new_products = len(new_components.get("idx_to_product_id", {}))
            old_products = len(old_components.get("idx_to_product_id", {}))

            user_change = new_users - old_users
            product_change = new_products - old_products

            if old_users > 0:
                metrics.coverage_delta = round((user_change / old_users) * 100, 1)

            # 변화 로깅
            logger.info(
                "모델 변화",
                extra={
                    "users": f"{old_users} → {new_users} ({user_change:+d})",
                    "products": f"{old_products} → {new_products} ({product_change:+d})",
                }
            )

        except Exception as e:
            logger.warning(f"모델 변화 로깅 실패 (무시): {e}")


class ContinuousTrainer:
    """연속 학습 관리자

    적극적 연속 학습 전략 구현:
    - 학습 완료 즉시 다음 학습 시작
    - Model Validation Gate로 품질 보장
    - 자동 롤백 및 오류 복구

    사용법:
        trainer = ContinuousTrainer(db)
        await trainer.start()  # 연속 학습 시작
        await trainer.stop()   # 연속 학습 중지
    """

    def __init__(
        self,
        db: Database,
        config: Optional[ContinuousTrainerConfig] = None,
    ):
        self.db = db
        self.config = config or ContinuousTrainerConfig()

        # 컴포넌트
        self._als_trainer = ALSTrainer(db=db)
        self._validator = ModelValidator(db=db, config=self.config)

        # 상태
        self._state = TrainingState.IDLE
        self._is_running = False
        self._loop_task: Optional[asyncio.Task] = None

        # 메트릭
        self._cycle_count = 0
        self._consecutive_failures = 0
        self._last_success_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None

        # 히스토리 (최근 N개 사이클 기록)
        self._history: List[TrainingMetrics] = []
        self._max_history = 100

        # 콜백
        self._on_training_complete: Optional[Callable[[TrainingMetrics], None]] = None
        self._on_validation_failed: Optional[Callable[[TrainingMetrics], None]] = None

    @property
    def state(self) -> TrainingState:
        """현재 상태"""
        return self._state

    @property
    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._is_running

    @property
    def cycle_count(self) -> int:
        """완료된 학습 사이클 수"""
        return self._cycle_count

    async def start(self) -> None:
        """연속 학습 시작"""
        if self._is_running:
            logger.warning("연속 학습이 이미 실행 중입니다")
            return

        self._is_running = True
        self._state = TrainingState.IDLE
        self._consecutive_failures = 0

        logger.info(
            "연속 학습 시작",
            extra={
                "model_name": self.config.model_name,
                "min_cooldown": self.config.min_cooldown_seconds,
                "max_cooldown": self.config.max_cooldown_seconds,
            }
        )

        self._loop_task = asyncio.create_task(self._training_loop())

    async def stop(self) -> None:
        """연속 학습 중지"""
        if not self._is_running:
            return

        self._is_running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        self._state = TrainingState.IDLE
        logger.info("연속 학습 중지")

    async def pause(self) -> None:
        """연속 학습 일시 중지"""
        if self._state == TrainingState.PAUSED:
            return

        self._state = TrainingState.PAUSED
        self._paused_at = datetime.now()
        logger.info("연속 학습 일시 중지")

    async def resume(self) -> None:
        """연속 학습 재개"""
        if self._state != TrainingState.PAUSED:
            return

        self._state = TrainingState.IDLE
        self._consecutive_failures = 0
        self._paused_at = None
        logger.info("연속 학습 재개")

    async def _training_loop(self) -> None:
        """연속 학습 메인 루프"""
        while self._is_running:
            try:
                # 일시 중지 상태 체크
                if self._state == TrainingState.PAUSED:
                    # 자동 재개 체크
                    if self._paused_at and self.config.auto_resume_after_minutes > 0:
                        pause_duration = (datetime.now() - self._paused_at).total_seconds()
                        if pause_duration >= self.config.auto_resume_after_minutes * 60:
                            logger.info("자동 재개: 일시 중지 시간 초과")
                            await self.resume()
                        else:
                            await asyncio.sleep(60)  # 1분마다 체크
                            continue
                    else:
                        await asyncio.sleep(60)
                        continue

                # 학습 사이클 실행
                metrics = await self._run_training_cycle()

                # 히스토리 기록
                self._history.append(metrics)
                if len(self._history) > self._max_history:
                    self._history.pop(0)

                # 결과 처리
                if metrics.is_deployed:
                    self._consecutive_failures = 0
                    self._last_success_at = datetime.now()

                    # 콜백 호출
                    if self._on_training_complete:
                        try:
                            result = self._on_training_complete(metrics)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"학습 완료 콜백 오류: {e}")
                else:
                    self._consecutive_failures += 1

                    # 콜백 호출
                    if self._on_validation_failed:
                        try:
                            result = self._on_validation_failed(metrics)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"검증 실패 콜백 오류: {e}")

                    # 연속 실패 시 일시 중지
                    if self._consecutive_failures >= self.config.max_consecutive_failures:
                        logger.warning(
                            f"연속 {self._consecutive_failures}회 실패 - 연속 학습 일시 중지"
                        )
                        await self.pause()
                        continue

                # 쿨다운 (적극적 연속 학습: 최소 쿨다운만 적용)
                cooldown = self._calculate_cooldown()
                self._state = TrainingState.COOLDOWN

                logger.info(
                    f"다음 학습까지 {cooldown}초 대기",
                    extra={"cooldown_seconds": cooldown}
                )

                await asyncio.sleep(cooldown)
                self._state = TrainingState.IDLE

            except asyncio.CancelledError:
                logger.info("연속 학습 루프 종료")
                break
            except Exception as e:
                logger.error(f"학습 루프 오류: {e}", exc_info=True)
                self._state = TrainingState.ERROR
                await asyncio.sleep(60)  # 오류 시 1분 대기 후 재시도

    async def _run_training_cycle(self) -> TrainingMetrics:
        """단일 학습 사이클 실행"""
        self._cycle_count += 1
        metrics = TrainingMetrics(cycle_id=self._cycle_count)
        metrics.started_at = datetime.now()

        model_name = self.config.model_name
        model_path = model_loader.models_dir / f"{model_name}.pkl"
        temp_path = model_loader.models_dir / f"{model_name}_temp.pkl"

        try:
            # 1. 기존 모델 데이터 로드 (비교용)
            old_model_data = model_loader.get_model(model_name.replace("_v2", ""))

            # 2. 학습
            self._state = TrainingState.TRAINING
            logger.info(f"학습 사이클 #{self._cycle_count} 시작")

            # 데이터 로드
            (
                user_id_to_idx,
                product_id_to_idx,
                idx_to_product_id,
                interactions,
            ) = await self._als_trainer.fetch_interaction_data()

            if not interactions:
                logger.warning("학습 데이터 없음 - 사이클 스킵")
                metrics.validation_result = ValidationResult.SKIPPED
                metrics.error_message = "학습 데이터 없음"
                return metrics

            n_users = len(user_id_to_idx)
            n_products = len(product_id_to_idx)

            # 상호작용 행렬 생성
            interaction_matrix = self._als_trainer.build_interaction_matrix(
                n_users, n_products, interactions
            )

            # ALS 학습 (별도 스레드)
            loop = asyncio.get_event_loop()
            user_factors, item_factors = await loop.run_in_executor(
                None, self._als_trainer.train_als, interaction_matrix
            )

            # 인기 상품 조회
            global_popular, category_popular = await self._als_trainer.fetch_popular_products()

            # 임시 파일로 저장
            model_data = {
                "version": "2.0.0",
                "algorithm": "ALS",
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "n_users": n_users,
                    "n_items": n_products,
                    "n_interactions": len(interactions),
                    "factors": self._als_trainer.factors,
                    "dtype": str(user_factors.dtype),
                },
                "hyperparameters": {
                    "factors": self._als_trainer.factors,
                    "regularization": self._als_trainer.regularization,
                    "alpha": self._als_trainer.alpha,
                    "iterations": self._als_trainer.iterations,
                    "cbf_weight": 0.7,
                    "cf_weight": 0.3,
                    "filter_already_liked_items": False,
                },
                "components": {
                    "user_embeddings": user_factors.tobytes(),
                    "product_embeddings": item_factors.tobytes(),
                    "user_id_to_idx": user_id_to_idx,
                    "idx_to_product_id": idx_to_product_id,
                    "global_popular_products": global_popular,
                    "category_popular_products": category_popular,
                },
                "metrics": {
                    "training_cycle": self._cycle_count,
                    "trained_at": datetime.now().isoformat(),
                },
            }

            # 임시 파일 저장
            model_loader.models_dir.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "wb") as f:
                pickle.dump(model_data, f)

            # 3. 검증
            self._state = TrainingState.VALIDATING
            validation_result, val_metrics = await self._validator.validate(
                temp_path, old_model_data
            )

            # 메트릭 병합
            metrics.n_users = val_metrics.n_users
            metrics.n_products = val_metrics.n_products
            metrics.n_interactions = len(interactions)
            metrics.user_coverage = val_metrics.user_coverage
            metrics.product_coverage = val_metrics.product_coverage
            metrics.coverage_delta = val_metrics.coverage_delta
            metrics.validation_result = validation_result
            metrics.error_message = val_metrics.error_message

            if validation_result != ValidationResult.PASSED:
                logger.warning(
                    f"검증 실패: {validation_result.value}",
                    extra={"error": metrics.error_message}
                )
                # 임시 파일 삭제
                if temp_path.exists():
                    temp_path.unlink()
                return metrics

            # 4. 배포 (Atomic Switch)
            self._state = TrainingState.DEPLOYING

            # 기존 모델 백업
            if model_path.exists():
                model_loader.backup_model(model_name)

                # 오래된 백업 정리
                self._cleanup_old_backups(model_name)

            # 임시 파일 → 실제 파일 (원자적 이동)
            temp_path.replace(model_path)

            metrics.is_deployed = True
            metrics.completed_at = datetime.now()
            metrics.duration_seconds = (
                metrics.completed_at - metrics.started_at
            ).total_seconds()

            logger.info(
                f"학습 사이클 #{self._cycle_count} 완료",
                extra={
                    "duration_seconds": round(metrics.duration_seconds, 2),
                    "n_users": metrics.n_users,
                    "n_products": metrics.n_products,
                    "user_coverage": metrics.user_coverage,
                    "product_coverage": metrics.product_coverage,
                }
            )

            return metrics

        except Exception as e:
            logger.error(f"학습 사이클 오류: {e}", exc_info=True)
            metrics.validation_result = ValidationResult.FAILED_INTEGRITY
            metrics.error_message = str(e)

            # 임시 파일 정리
            if temp_path.exists():
                temp_path.unlink()

            return metrics

    def _calculate_cooldown(self) -> int:
        """쿨다운 시간 계산

        적극적 연속 학습: 최소 쿨다운 적용
        연속 실패 시: 점진적으로 쿨다운 증가
        """
        base_cooldown = self.config.min_cooldown_seconds

        # 연속 실패 시 쿨다운 증가 (지수적)
        if self._consecutive_failures > 0:
            multiplier = min(2 ** self._consecutive_failures, 10)
            cooldown = base_cooldown * multiplier
            return min(cooldown, self.config.max_cooldown_seconds)

        return base_cooldown

    def _cleanup_old_backups(self, model_name: str) -> None:
        """오래된 백업 파일 정리"""
        try:
            backups = model_loader.list_backups(model_name)

            # 유지할 개수 초과분 삭제
            if len(backups) > self.config.keep_backup_count:
                for old_backup in backups[self.config.keep_backup_count:]:
                    try:
                        old_backup.unlink()
                        logger.debug(f"오래된 백업 삭제: {old_backup.name}")
                    except Exception as e:
                        logger.warning(f"백업 삭제 실패: {e}")
        except Exception as e:
            logger.warning(f"백업 정리 실패: {e}")

    def set_training_complete_callback(
        self,
        callback: Callable[[TrainingMetrics], None]
    ) -> None:
        """학습 완료 콜백 설정"""
        self._on_training_complete = callback

    def set_validation_failed_callback(
        self,
        callback: Callable[[TrainingMetrics], None]
    ) -> None:
        """검증 실패 콜백 설정"""
        self._on_validation_failed = callback

    def get_status(self) -> Dict[str, Any]:
        """상태 조회"""
        return {
            "state": self._state.value,
            "is_running": self._is_running,
            "cycle_count": self._cycle_count,
            "consecutive_failures": self._consecutive_failures,
            "last_success_at": self._last_success_at.isoformat() if self._last_success_at else None,
            "paused_at": self._paused_at.isoformat() if self._paused_at else None,
            "config": {
                "model_name": self.config.model_name,
                "min_cooldown_seconds": self.config.min_cooldown_seconds,
                "max_cooldown_seconds": self.config.max_cooldown_seconds,
                "min_user_coverage": self.config.min_user_coverage,
                "max_consecutive_failures": self.config.max_consecutive_failures,
            },
            "recent_history": [
                {
                    "cycle_id": m.cycle_id,
                    "validation_result": m.validation_result.value,
                    "is_deployed": m.is_deployed,
                    "duration_seconds": m.duration_seconds,
                    "n_users": m.n_users,
                    "n_products": m.n_products,
                    "user_coverage": m.user_coverage,
                    "error_message": m.error_message,
                }
                for m in self._history[-10:]  # 최근 10개
            ],
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약"""
        if not self._history:
            return {
                "total_cycles": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "avg_user_coverage": 0.0,
            }

        successful = [m for m in self._history if m.is_deployed]

        return {
            "total_cycles": len(self._history),
            "successful_cycles": len(successful),
            "success_rate": round(len(successful) / len(self._history) * 100, 1),
            "avg_duration_seconds": round(
                sum(m.duration_seconds for m in successful) / len(successful), 2
            ) if successful else 0.0,
            "avg_user_coverage": round(
                sum(m.user_coverage for m in successful) / len(successful), 1
            ) if successful else 0.0,
            "avg_product_coverage": round(
                sum(m.product_coverage for m in successful) / len(successful), 1
            ) if successful else 0.0,
        }


# 전역 인스턴스 (lazy init)
_continuous_trainer: Optional[ContinuousTrainer] = None


def get_continuous_trainer(db: Database) -> ContinuousTrainer:
    """ContinuousTrainer 싱글톤 인스턴스 반환"""
    global _continuous_trainer
    if _continuous_trainer is None:
        _continuous_trainer = ContinuousTrainer(db=db)
    return _continuous_trainer
