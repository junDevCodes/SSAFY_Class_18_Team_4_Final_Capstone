"""
Pickle 기반 ML 모델 로더

사전 학습된 모델을 pickle 파일에서 로드하여 추천 서비스에 제공
싱글톤 패턴으로 모델을 한 번만 로드하여 메모리에 유지
"""

import os
import json
import pickle
import joblib
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


class ModelLoader:
    """Pickle 모델 로더

    싱글톤 패턴으로 모델을 한 번만 로드하여 메모리에 유지
    """

    _instance = None
    _models: Dict[str, Dict[str, Any]] = {}
    _metadata: Dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._models = {}
            cls._metadata = {}
            cls._loaded = False
        return cls._instance

    def __init__(self):
        # 모델 디렉토리 경로 (환경변수 또는 기본값)
        default_path = Path(__file__).parent.parent / "models"
        self.models_dir = Path(os.getenv("MODELS_DIR", str(default_path)))

    async def load_all_models(self) -> None:
        """모든 모델 로드

        서비스 시작 시 한 번 호출하여 모든 pickle 모델을 메모리에 로드
        """
        if self._loaded:
            logger.info("모델이 이미 로드됨, 스킵")
            return

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
            try:
                model_name = model_file.stem  # 확장자 제외 파일명
                
                # joblib.load를 사용하여 순수 딕셔너리 형태 로드 (클래스 경로 에러 무시)
                try:
                    # joblib.load는 기본적으로 클래스 경로를 찾으려 하지만, 
                    # 순수 딕셔너리만 저장되어 있다면 문제없이 로드됨
                    model_data = joblib.load(model_file, mmap_mode=None)
                except (ModuleNotFoundError, AttributeError, TypeError) as joblib_error:
                    # 클래스 경로 관련 에러인 경우, pickle로 재시도 (하위 호환성)
                    logger.warning(f"joblib.load 실패 (클래스 경로 에러 가능): {joblib_error}, pickle.load 시도")
                    try:
                        with open(model_file, 'rb') as f:
                            model_data = pickle.load(f)
                    except Exception as pickle_error:
                        logger.error(f"pickle.load도 실패: {pickle_error}")
                        raise pickle_error
                except Exception as joblib_error:
                    # 기타 에러는 그대로 전파
                    logger.error(f"joblib.load 실패: {joblib_error}")
                    raise joblib_error

                # 순수 딕셔너리인지 확인
                if not isinstance(model_data, dict):
                    logger.warning(f"모델 {model_name}이 딕셔너리 형태가 아닙니다: {type(model_data)}")
                    continue

                self._models[model_name] = model_data

                # 로드된 모델 정보 로깅
                version = model_data.get("version", "unknown")
                created_at = model_data.get("created_at", "unknown")
                components = list(model_data.get("components", {}).keys())

                logger.info(
                    f"모델 로드 완료: {model_name}",
                    extra={
                        "version": version,
                        "created_at": created_at,
                        "components": components,
                    }
                )
            except Exception as e:
                logger.error(f"모델 로드 실패: {model_file}", extra={"error": str(e)})

        self._loaded = True
        logger.info(f"총 {len(self._models)}개 모델 로드 완료")

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
            }

        return {
            "is_loaded": self._loaded,
            "models_dir": str(self.models_dir),
            "loaded_models": self.loaded_models,
            "model_count": len(self._models),
            "models": model_info,
            "active_models": self._metadata.get("active_models", {}),
        }


# 전역 싱글톤 인스턴스
model_loader = ModelLoader()
