"""
Numpy 버전 호환성 유틸리티

numpy 2.x에서 생성된 pickle이 numpy 1.x에서 로드되지 않는 문제를 해결하기 위한
호환성 레이어를 제공합니다.

노트북에서 pickle 생성 시 numpy 배열을 bytes + metadata 형식으로 저장하고,
서비스에서 로드 시 이를 다시 numpy 배열로 복원합니다.
"""

from typing import Any, Dict, Union

import numpy as np


def load_numpy_compatible(data: Any) -> np.ndarray:
    """numpy 버전 호환 형식에서 배열 복원

    지원하는 형식:
    1. dict 형식 (bytes + metadata): {'data': bytes, 'shape': tuple, 'dtype': str}
    2. 직접 numpy 배열 (구버전 pickle)

    Args:
        data: pickle에서 로드된 임베딩 데이터

    Returns:
        복원된 numpy 배열
    """
    # dict 형식 (호환 모드)
    if isinstance(data, dict) and "data" in data and "shape" in data:
        return np.frombuffer(
            data["data"],
            dtype=data["dtype"]
        ).reshape(data["shape"])

    # 이미 numpy 배열인 경우 (구버전 pickle)
    if isinstance(data, np.ndarray):
        return data

    raise ValueError(f"지원하지 않는 데이터 형식: {type(data)}")


def save_numpy_compatible(arr: np.ndarray) -> Dict[str, Any]:
    """numpy 배열을 버전 호환 가능한 형태로 변환

    numpy 2.x에서 생성된 pickle은 numpy 1.x에서 로드할 수 없으므로,
    표준 Python bytes로 저장합니다.

    Args:
        arr: 저장할 numpy 배열

    Returns:
        bytes + metadata 딕셔너리
    """
    return {
        "data": arr.tobytes(),
        "shape": arr.shape,
        "dtype": str(arr.dtype)
    }


def is_compatible_format(data: Any) -> bool:
    """데이터가 호환 형식인지 확인

    Args:
        data: 확인할 데이터

    Returns:
        호환 형식 여부
    """
    if isinstance(data, dict):
        return "data" in data and "shape" in data and "dtype" in data
    return isinstance(data, np.ndarray)
