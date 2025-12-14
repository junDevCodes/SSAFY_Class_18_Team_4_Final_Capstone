"""
모델 내보내기 유틸리티

학습된 모델을 pickle 파일로 저장하고 로드하는 헬퍼 함수들
"""

import os
import json
import pickle
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime


# 기본 모델 저장 경로
DEFAULT_MODELS_DIR = Path(__file__).parent.parent.parent / "pred" / "models"


def save_model(
    model_data: Dict[str, Any],
    model_name: str,
    version: str = "1.0.0",
    output_dir: Optional[Path] = None,
) -> Path:
    """모델을 pickle 파일로 저장

    Args:
        model_data: 저장할 모델 데이터 (components, hyperparameters 등)
        model_name: 모델 이름 (예: 'self_personalized')
        version: 모델 버전 (예: '1.0.0')
        output_dir: 저장 디렉토리 (기본: pred/models/)

    Returns:
        저장된 파일 경로
    """
    output_dir = output_dir or DEFAULT_MODELS_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성 (버전 포함)
    filename = f"{model_name}_v{version.replace('.', '_')}.pkl"
    filepath = output_dir / filename

    # 메타데이터 추가
    model_data["model_name"] = model_name
    model_data["version"] = version
    model_data["created_at"] = datetime.now().isoformat()

    # pickle 저장
    with open(filepath, 'wb') as f:
        pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"모델 저장 완료: {filepath}")
    print(f"  - 파일 크기: {filepath.stat().st_size / 1024 / 1024:.2f} MB")

    # 메타데이터 업데이트
    _update_metadata(output_dir, model_name, version, filename)

    return filepath


def load_model(
    model_name: str,
    version: Optional[str] = None,
    models_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """pickle 파일에서 모델 로드

    Args:
        model_name: 모델 이름
        version: 특정 버전 (없으면 최신 버전)
        models_dir: 모델 디렉토리

    Returns:
        로드된 모델 데이터 또는 None
    """
    models_dir = models_dir or DEFAULT_MODELS_DIR
    models_dir = Path(models_dir)

    if version:
        # 특정 버전 로드
        filename = f"{model_name}_v{version.replace('.', '_')}.pkl"
        filepath = models_dir / filename
    else:
        # 최신 버전 찾기
        pattern = f"{model_name}_v*.pkl"
        files = list(models_dir.glob(pattern))
        if not files:
            print(f"모델 파일 없음: {pattern}")
            return None
        filepath = max(files, key=lambda p: p.stat().st_mtime)

    if not filepath.exists():
        print(f"모델 파일 없음: {filepath}")
        return None

    with open(filepath, 'rb') as f:
        model_data = pickle.load(f)

    print(f"모델 로드 완료: {filepath}")
    print(f"  - 버전: {model_data.get('version', 'unknown')}")
    print(f"  - 생성일: {model_data.get('created_at', 'unknown')}")

    return model_data


def _update_metadata(
    models_dir: Path,
    model_name: str,
    version: str,
    filename: str,
) -> None:
    """모델 메타데이터 파일 업데이트"""
    metadata_path = models_dir / "model_metadata.json"

    # 기존 메타데이터 로드
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    else:
        metadata = {
            "models": {},
            "active_models": {},
        }

    # 모델 정보 업데이트
    model_key = f"{model_name}_v{version.replace('.', '_')}"
    metadata["models"][model_key] = {
        "file": filename,
        "version": version,
        "created_at": datetime.now().isoformat(),
    }

    # 활성 모델로 설정
    metadata["active_models"][model_name] = model_key
    metadata["last_updated"] = datetime.now().isoformat()

    # 저장
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"메타데이터 업데이트: {metadata_path}")


class ModelExporter:
    """모델 내보내기 클래스

    일관된 형식으로 모델을 저장하고 관리
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Args:
            output_dir: 모델 저장 디렉토리
        """
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_MODELS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_self_personalized(
        self,
        user_product_matrix,
        user_embeddings,
        product_embeddings,
        user_id_to_idx: Dict[int, int],
        product_id_to_idx: Dict[int, int],
        category_popular: Dict[int, list],
        global_popular: list,
        hyperparameters: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        version: str = "1.0.0",
    ) -> Path:
        """개인화 모델 내보내기

        Args:
            user_product_matrix: 사용자-상품 희소 행렬
            user_embeddings: 사용자 임베딩 (numpy array)
            product_embeddings: 상품 임베딩 (numpy array)
            user_id_to_idx: 사용자 ID -> 인덱스 매핑
            product_id_to_idx: 상품 ID -> 인덱스 매핑
            category_popular: 카테고리별 인기 상품
            global_popular: 전체 인기 상품
            hyperparameters: 하이퍼파라미터
            metrics: 평가 지표
            version: 모델 버전

        Returns:
            저장된 파일 경로
        """
        model_data = {
            "components": {
                "user_product_matrix": user_product_matrix,
                "user_embeddings": user_embeddings,
                "product_embeddings": product_embeddings,
                "user_id_to_idx": user_id_to_idx,
                "idx_to_user_id": {v: k for k, v in user_id_to_idx.items()},
                "product_id_to_idx": product_id_to_idx,
                "idx_to_product_id": {v: k for k, v in product_id_to_idx.items()},
                "category_popular": category_popular,
                "global_popular": global_popular,
            },
            "hyperparameters": hyperparameters or {
                "embedding_dim": user_embeddings.shape[1] if hasattr(user_embeddings, 'shape') else 64,
                "similarity_metric": "cosine",
            },
            "metrics": metrics or {},
        }

        return save_model(model_data, "self_personalized", version, self.output_dir)

    def export_price_anomaly(
        self,
        category_price_stats: Dict[int, Dict],
        best_deals: list,
        hyperparameters: Optional[Dict] = None,
        version: str = "1.0.0",
    ) -> Path:
        """가격 이상치 모델 내보내기

        Args:
            category_price_stats: 카테고리별 가격 통계
            best_deals: 베스트 딜 목록
            hyperparameters: 하이퍼파라미터
            version: 모델 버전

        Returns:
            저장된 파일 경로
        """
        model_data = {
            "components": {
                "category_price_stats": category_price_stats,
                "best_deals": best_deals,
            },
            "hyperparameters": hyperparameters or {
                "z_threshold": 2.0,
                "min_discount_rate": 10.0,
            },
        }

        return save_model(model_data, "price_anomaly", version, self.output_dir)

    def export_collaborative(
        self,
        similar_users: Dict[int, list],
        similar_products: Dict[int, list],
        user_interactions: Dict[int, set],
        hyperparameters: Optional[Dict] = None,
        version: str = "1.0.0",
    ) -> Path:
        """협업 필터링 모델 내보내기

        Args:
            similar_users: 유사 사용자 매핑
            similar_products: 유사 상품 매핑
            user_interactions: 사용자별 상호작용 상품
            hyperparameters: 하이퍼파라미터
            version: 모델 버전

        Returns:
            저장된 파일 경로
        """
        model_data = {
            "components": {
                "similar_users": similar_users,
                "similar_products": similar_products,
                "user_interactions": user_interactions,
            },
            "hyperparameters": hyperparameters or {
                "k_neighbors": 50,
                "similarity_metric": "cosine",
            },
        }

        return save_model(model_data, "collaborative", version, self.output_dir)

    def list_models(self) -> Dict[str, Any]:
        """저장된 모델 목록 조회

        Returns:
            모델 메타데이터
        """
        metadata_path = self.output_dir / "model_metadata.json"

        if not metadata_path.exists():
            print("메타데이터 파일 없음")
            return {}

        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
