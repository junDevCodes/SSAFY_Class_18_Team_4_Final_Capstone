"""
Pickle 기반 ML 모델 로더

사전 학습된 모델을 pickle 파일에서 로드하여 추천 서비스에 제공
싱글톤 패턴으로 모델을 한 번만 로드하여 메모리에 유지

Hot Reload 기능:
- 파일 변경 감지 (mtime 기반)
- 백그라운드 모니터링 태스크
- 변경 시 자동 리로드
"""

import os
import io
import json
import pickle
import asyncio
import shutil
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


class SafeUnpickler(pickle.Unpickler):
    """안전한 Unpickler

    notebooks/utils/gap_filling/ 모듈의 클래스들을
    None 또는 더미 객체로 대체하여 로드 오류 방지
    """

    # 무시할 모듈 패턴 (해당 모듈의 클래스는 None으로 대체)
    IGNORED_MODULES = {'utils.gap_filling', 'utils'}

    def find_class(self, module: str, name: str):
        """클래스 찾기 - 알 수 없는 모듈은 None 반환"""
        # 무시할 모듈 패턴에 해당하는 경우
        for ignored in self.IGNORED_MODULES:
            if module.startswith(ignored):
                logger.debug(f"Pickle 로드 시 무시: {module}.{name}")
                return type(name, (), {})  # 빈 더미 클래스 반환

        # 일반적인 클래스 찾기
        return super().find_class(module, name)


def safe_pickle_load(file_path: Path) -> Any:
    """안전한 pickle 로드

    Args:
        file_path: pickle 파일 경로

    Returns:
        로드된 객체
    """
    with open(file_path, 'rb') as f:
        return SafeUnpickler(f).load()


class ModelLoader:
    """Pickle 모델 로더

    싱글톤 패턴으로 모델을 한 번만 로드하여 메모리에 유지

    Hot Reload 기능:
    - 파일 mtime 변경 감지
    - 백그라운드 태스크로 주기적 체크
    - 변경된 모델만 선택적 리로드
    - 리로드 콜백 지원 (SelfPersonalizedModel 재초기화 등)
    - Atomic Swap으로 읽기/쓰기 동시성 문제 해결
    """

    _instance = None
    _init_lock = asyncio.Lock()  # 싱글톤 초기화용 Lock

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            # 인스턴스 변수로 초기화 (클래스 변수 공유 문제 해결)
            instance._models: Dict[str, Dict[str, Any]] = {}
            instance._metadata: Dict[str, Any] = {}
            instance._loaded: bool = False
            instance._file_mtimes: Dict[str, float] = {}
            instance._reload_callbacks: List[Callable[[str], None]] = []
            instance._monitor_task: Optional[asyncio.Task] = None
            instance._monitor_interval: int = 30
            instance._reload_lock = asyncio.Lock()  # 리로드 동시성 제어용 Lock
            cls._instance = instance
        return cls._instance

    def __init__(self):
        # __new__에서 이미 초기화된 경우 스킵 (싱글톤이므로 __init__이 여러 번 호출될 수 있음)
        if hasattr(self, 'models_dir'):
            return

        # 모델 디렉토리 경로 (환경변수 또는 기본값)
        default_path = Path(__file__).parent.parent / "models"
        self.models_dir = Path(os.getenv("MODELS_DIR", str(default_path)))
        # 모니터링 간격 (환경변수로 설정 가능)
        self._monitor_interval = int(os.getenv("MODEL_RELOAD_INTERVAL", "30"))

    async def load_all_models(self) -> None:
        """모든 모델 로드

        서비스 시작 시 한 번 호출하여 모든 pickle 모델을 메모리에 로드
        """
        if self._loaded:
            logger.info("모델이 이미 로드됨, 스킵")
            return

        print(f"\n[ModelLoader] 모델 로딩 시작: {self.models_dir}")
        logger.info(f"모델 로딩 시작: {self.models_dir}")

        if not self.models_dir.exists():
            logger.warning(f"모델 디렉토리 없음: {self.models_dir}")
            self._loaded = True
            return

        # 메타데이터 로드
        metadata_path = self.models_dir / "model_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
                logger.info(f"메타데이터 로드: {metadata_path}")
            except Exception as e:
                logger.warning(f"메타데이터 로드 실패: {e}")

        # pickle 모델들 로드
        model_files = list(self.models_dir.glob("*.pkl"))
        logger.info(f"발견된 모델 파일: {len(model_files)}개")

        for model_file in model_files:
            await self._load_single_model(model_file)

        self._loaded = True
        print(f"[ModelLoader] ✓ 총 {len(self._models)}개 모델 로드 완료: {self.loaded_models}")
        logger.info(f"총 {len(self._models)}개 모델 로드 완료")

    async def _load_single_model(self, model_file: Path, is_reload: bool = False) -> bool:
        """단일 모델 파일 로드 (Atomic Swap 패턴)

        파일에서 모델 데이터를 완전히 로드한 후에만 _models에 할당합니다.
        이를 통해 읽기 연산이 항상 완전한 모델 데이터를 얻도록 보장합니다.

        Args:
            model_file: 모델 파일 경로
            is_reload: 리로드 여부 (로깅용)

        Returns:
            로드 성공 여부
        """
        model_name = model_file.stem  # 확장자 제외 파일명

        try:
            # 1단계: 파일에서 모델 데이터 완전히 로드 (아직 _models에 할당 안 함)
            model_data = safe_pickle_load(model_file)
            file_mtime = model_file.stat().st_mtime

            # 2단계: 로드 성공 후 검증
            if model_data is None:
                logger.error(f"모델 로드 결과가 None: {model_file}")
                return False

            # 3단계: Atomic Swap - Lock 하에 참조만 교체
            # asyncio는 단일 스레드이므로 딕셔너리 할당 자체는 atomic하지만,
            # 명시적 Lock으로 의도를 명확히 하고 향후 확장성 확보
            async with self._reload_lock:
                self._models[model_name] = model_data
                self._file_mtimes[model_name] = file_mtime

            # 4단계: 로깅 (Lock 밖에서 수행)
            action = "리로드" if is_reload else "로드"
            if isinstance(model_data, dict):
                version = model_data.get("version", "unknown")
                created_at = model_data.get("created_at", "unknown")
                model_type = model_data.get("model_type", "unknown")
                components = list(model_data.get("components", {}).keys()) if "components" in model_data else []

                # v2 모델 (Masked Set Transformer) 추가 정보
                if "model_state_dict" in model_data:
                    vocab_size = len(model_data.get("tokenizer_vocab", {}))
                    print(f"  └─ {model_name}: v{version} (Transformer, vocab={vocab_size})")
                    logger.info(
                        f"모델 {action} 완료: {model_name} (Transformer)",
                        extra={
                            "version": version,
                            "vocab_size": vocab_size,
                        }
                    )
                else:
                    print(f"  └─ {model_name}: v{version} ({model_type})")
                    logger.info(
                        f"모델 {action} 완료: {model_name}",
                        extra={
                            "version": version,
                            "created_at": created_at,
                            "components": components,
                        }
                    )
            else:
                print(f"  └─ {model_name}: {type(model_data).__name__}")
                logger.info(f"모델 {action} 완료: {model_name} (type={type(model_data).__name__})")

            return True

        except Exception as e:
            logger.error(f"모델 로드 실패: {model_file}", extra={"error": str(e)})
            return False

    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """특정 모델 조회

        Args:
            model_name: 모델 이름 (예: 'self_personalized')

        Returns:
            모델 데이터 딕셔너리 또는 None
        """
        # 정확한 이름으로 먼저 검색
        if model_name in self._models:
            return self._models[model_name]

        # 버전 접미사가 있는 경우 검색 (예: self_personalized_v1_0_0)
        for key in self._models:
            if key.startswith(model_name):
                return self._models[key]

        # 활성 모델 확인 (메타데이터 기반)
        active_models = self._metadata.get("active_models", {})
        if model_name in active_models:
            active_key = active_models[model_name]
            if active_key in self._models:
                return self._models[active_key]

        return None

    def get_component(
        self,
        model_name: str,
        component_name: str,
    ) -> Optional[Any]:
        """모델의 특정 컴포넌트 조회

        Args:
            model_name: 모델 이름
            component_name: 컴포넌트 이름 (예: 'user_embeddings')

        Returns:
            컴포넌트 데이터 또는 None
        """
        model = self.get_model(model_name)
        if model and "components" in model:
            return model["components"].get(component_name)
        return None

    def get_hyperparameter(
        self,
        model_name: str,
        param_name: str,
    ) -> Optional[Any]:
        """모델의 하이퍼파라미터 조회

        Args:
            model_name: 모델 이름
            param_name: 파라미터 이름

        Returns:
            파라미터 값 또는 None
        """
        model = self.get_model(model_name)
        if model and "hyperparameters" in model:
            return model["hyperparameters"].get(param_name)
        return None

    def get_model_version(self, model_name: str) -> Optional[str]:
        """모델 버전 조회

        Args:
            model_name: 모델 이름

        Returns:
            버전 문자열 또는 None
        """
        model = self.get_model(model_name)
        if model:
            return model.get("version")
        return None

    def get_model_metrics(self, model_name: str) -> Optional[Dict[str, Any]]:
        """모델 평가 지표 조회

        Args:
            model_name: 모델 이름

        Returns:
            평가 지표 딕셔너리 또는 None
        """
        model = self.get_model(model_name)
        if model:
            return model.get("metrics")
        return None

    def has_model(self, model_name: str) -> bool:
        """모델 존재 여부 확인

        Args:
            model_name: 모델 이름

        Returns:
            모델 존재 여부
        """
        return self.get_model(model_name) is not None

    @property
    def loaded_models(self) -> List[str]:
        """로드된 모델 이름 목록"""
        return list(self._models.keys())

    @property
    def is_loaded(self) -> bool:
        """로드 완료 여부"""
        return self._loaded

    @property
    def metadata(self) -> Dict[str, Any]:
        """메타데이터 조회"""
        return self._metadata

    def get_status(self) -> Dict[str, Any]:
        """로더 상태 조회

        Returns:
            상태 정보 딕셔너리
        """
        model_info = {}
        for name, data in self._models.items():
            model_info[name] = {
                "version": data.get("version", "unknown"),
                "created_at": data.get("created_at", "unknown"),
                "components": list(data.get("components", {}).keys()),
                "last_loaded_mtime": self._file_mtimes.get(name),
            }

        return {
            "is_loaded": self._loaded,
            "models_dir": str(self.models_dir),
            "loaded_models": self.loaded_models,
            "model_count": len(self._models),
            "models": model_info,
            "active_models": self._metadata.get("active_models", {}),
            "monitor_active": self._monitor_task is not None and not self._monitor_task.done(),
            "monitor_interval": self._monitor_interval,
        }

    # ===== Hot Reload 기능 =====

    def register_reload_callback(self, callback: Callable[[str], None]) -> None:
        """모델 리로드 시 호출될 콜백 등록

        콜백은 리로드된 모델 이름을 인자로 받습니다.
        예: SelfPersonalizedModel.reinitialize()

        Args:
            callback: 리로드 시 호출될 함수
        """
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)
            logger.info(f"리로드 콜백 등록: {callback.__name__}")

    def unregister_reload_callback(self, callback: Callable[[str], None]) -> None:
        """콜백 등록 해제

        Args:
            callback: 해제할 콜백 함수
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    async def check_and_reload_models(self) -> List[str]:
        """파일 변경 감지 및 변경된 모델 리로드

        Returns:
            리로드된 모델 이름 목록
        """
        if not self.models_dir.exists():
            return []

        reloaded = []
        model_files = list(self.models_dir.glob("*.pkl"))

        for model_file in model_files:
            model_name = model_file.stem
            current_mtime = model_file.stat().st_mtime
            stored_mtime = self._file_mtimes.get(model_name)

            # 새 파일이거나 변경된 파일
            if stored_mtime is None or current_mtime > stored_mtime:
                logger.info(
                    f"모델 파일 변경 감지: {model_name}",
                    extra={
                        "old_mtime": stored_mtime,
                        "new_mtime": current_mtime,
                    }
                )

                # 리로드 수행
                success = await self._load_single_model(model_file, is_reload=True)
                if success:
                    reloaded.append(model_name)

                    # 콜백 호출
                    for callback in self._reload_callbacks:
                        try:
                            result = callback(model_name)
                            # async 콜백 지원
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(
                                f"리로드 콜백 실행 실패: {callback.__name__}",
                                extra={"error": str(e)}
                            )

        if reloaded:
            logger.info(f"모델 리로드 완료: {reloaded}")

        return reloaded

    async def start_file_monitor(self) -> None:
        """백그라운드 파일 모니터링 시작

        주기적으로 모델 파일 변경을 체크하고 변경 시 자동 리로드
        """
        if self._monitor_task is not None and not self._monitor_task.done():
            logger.warning("파일 모니터가 이미 실행 중")
            return

        async def _monitor_loop():
            logger.info(
                f"모델 파일 모니터링 시작",
                extra={"interval_seconds": self._monitor_interval}
            )
            while True:
                try:
                    await asyncio.sleep(self._monitor_interval)
                    await self.check_and_reload_models()
                except asyncio.CancelledError:
                    logger.info("모델 파일 모니터링 종료")
                    break
                except Exception as e:
                    logger.error(f"모니터링 중 오류: {e}")

        self._monitor_task = asyncio.create_task(_monitor_loop())

    async def stop_file_monitor(self) -> None:
        """백그라운드 파일 모니터링 중지"""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("모델 파일 모니터링 중지됨")

    async def reload_model(self, model_name: str) -> bool:
        """특정 모델 수동 리로드

        Args:
            model_name: 리로드할 모델 이름

        Returns:
            리로드 성공 여부
        """
        model_file = self.models_dir / f"{model_name}.pkl"
        if not model_file.exists():
            logger.error(f"모델 파일 없음: {model_file}")
            return False

        success = await self._load_single_model(model_file, is_reload=True)

        if success:
            # 콜백 호출
            for callback in self._reload_callbacks:
                try:
                    result = callback(model_name)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"리로드 콜백 실행 실패: {e}")

        return success

    async def reload_all_models(self) -> List[str]:
        """모든 모델 강제 리로드

        mtime과 관계없이 모든 모델을 리로드합니다.

        Returns:
            리로드된 모델 이름 목록
        """
        # mtime 초기화하여 강제 리로드
        self._file_mtimes.clear()
        return await self.check_and_reload_models()

    def backup_model(self, model_name: str) -> Optional[Path]:
        """모델 백업 생성

        학습 전 기존 모델을 백업합니다.

        Args:
            model_name: 백업할 모델 이름

        Returns:
            백업 파일 경로 또는 None
        """
        model_file = self.models_dir / f"{model_name}.pkl"
        if not model_file.exists():
            logger.warning(f"백업 대상 모델 없음: {model_name}")
            return None

        # 백업 디렉토리 생성
        backup_dir = self.models_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # 타임스탬프 포함 백업 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{model_name}_backup_{timestamp}.pkl"

        try:
            shutil.copy2(model_file, backup_file)
            logger.info(
                f"모델 백업 완료",
                extra={
                    "model": model_name,
                    "backup_path": str(backup_file),
                }
            )
            return backup_file
        except Exception as e:
            logger.error(f"모델 백업 실패: {e}")
            return None

    def restore_model(self, model_name: str, backup_path: Path) -> bool:
        """백업에서 모델 복원

        Args:
            model_name: 복원할 모델 이름
            backup_path: 백업 파일 경로

        Returns:
            복원 성공 여부
        """
        if not backup_path.exists():
            logger.error(f"백업 파일 없음: {backup_path}")
            return False

        model_file = self.models_dir / f"{model_name}.pkl"

        try:
            shutil.copy2(backup_path, model_file)
            logger.info(
                f"모델 복원 완료",
                extra={
                    "model": model_name,
                    "from_backup": str(backup_path),
                }
            )
            return True
        except Exception as e:
            logger.error(f"모델 복원 실패: {e}")
            return False

    def list_backups(self, model_name: str) -> List[Path]:
        """모델 백업 목록 조회

        Args:
            model_name: 모델 이름

        Returns:
            백업 파일 경로 목록 (최신순)
        """
        backup_dir = self.models_dir / "backups"
        if not backup_dir.exists():
            return []

        backups = list(backup_dir.glob(f"{model_name}_backup_*.pkl"))
        # 최신순 정렬
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups


# 전역 싱글톤 인스턴스
model_loader = ModelLoader()
