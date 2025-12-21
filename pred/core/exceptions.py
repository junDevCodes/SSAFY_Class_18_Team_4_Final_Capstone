"""
커스텀 예외 클래스

추천 시스템에서 사용하는 예외 정의
"""

from typing import Any, Dict, Optional


class PredServiceException(Exception):
    """Pred 서비스 기본 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_code: str = "PRED_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ===================================
# 데이터베이스 관련 예외
# ===================================


class DatabaseException(PredServiceException):
    """데이터베이스 관련 예외"""

    def __init__(
        self,
        message: str = "데이터베이스 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "DB_ERROR", details)


class DatabaseConnectionError(DatabaseException):
    """데이터베이스 연결 오류"""

    def __init__(
        self,
        message: str = "데이터베이스 연결에 실패했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.error_code = "DB_CONNECTION_ERROR"


class DatabaseQueryError(DatabaseException):
    """데이터베이스 쿼리 오류"""

    def __init__(
        self,
        message: str = "데이터베이스 쿼리 실행에 실패했습니다",
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if query:
            details["query"] = query
        super().__init__(message, details)
        self.error_code = "DB_QUERY_ERROR"


# ===================================
# 캐시 관련 예외
# ===================================


class CacheException(PredServiceException):
    """캐시 관련 예외"""

    def __init__(
        self,
        message: str = "캐시 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "CACHE_ERROR", details)


class CacheConnectionError(CacheException):
    """캐시 연결 오류"""

    def __init__(
        self,
        message: str = "Redis 연결에 실패했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.error_code = "CACHE_CONNECTION_ERROR"


# ===================================
# 모델 관련 예외
# ===================================


class ModelException(PredServiceException):
    """모델 관련 예외"""

    def __init__(
        self,
        message: str = "모델 오류가 발생했습니다",
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if model_name:
            details["model_name"] = model_name
        super().__init__(message, "MODEL_ERROR", details)


class ModelTimeoutError(ModelException):
    """모델 타임아웃 오류"""

    def __init__(
        self,
        model_name: str,
        timeout_ms: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"모델 '{model_name}' 실행이 {timeout_ms}ms 내에 완료되지 않았습니다"
        details = details or {}
        details["timeout_ms"] = timeout_ms
        super().__init__(message, model_name, details)
        self.error_code = "MODEL_TIMEOUT"


class ModelNotReadyError(ModelException):
    """모델 준비 안됨 오류"""

    def __init__(
        self,
        model_name: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"모델 '{model_name}'이(가) 아직 준비되지 않았습니다"
        super().__init__(message, model_name, details)
        self.error_code = "MODEL_NOT_READY"


class InsufficientDataError(ModelException):
    """데이터 부족 오류"""

    def __init__(
        self,
        model_name: str,
        required_data: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"모델 '{model_name}' 실행에 필요한 데이터가 부족합니다: {required_data}"
        details = details or {}
        details["required_data"] = required_data
        super().__init__(message, model_name, details)
        self.error_code = "INSUFFICIENT_DATA"


# ===================================
# API 관련 예외
# ===================================


class ValidationError(PredServiceException):
    """입력 검증 오류"""

    def __init__(
        self,
        message: str = "입력 값이 올바르지 않습니다",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class ResourceNotFoundError(PredServiceException):
    """리소스 찾을 수 없음 오류"""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource_type}을(를) 찾을 수 없습니다: {resource_id}"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(message, "NOT_FOUND", details)


class UserNotFoundError(ResourceNotFoundError):
    """사용자 찾을 수 없음 오류"""

    def __init__(self, user_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__("사용자", user_id, details)


class ProductNotFoundError(ResourceNotFoundError):
    """상품 찾을 수 없음 오류"""

    def __init__(self, product_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__("상품", product_id, details)


class CategoryNotFoundError(ResourceNotFoundError):
    """카테고리 찾을 수 없음 오류"""

    def __init__(self, category_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__("카테고리", category_id, details)


# ===================================
# 배치 처리 관련 예외
# ===================================


class BatchProcessingError(PredServiceException):
    """배치 처리 오류"""

    def __init__(
        self,
        message: str = "배치 처리 중 오류가 발생했습니다",
        batch_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if batch_name:
            details["batch_name"] = batch_name
        super().__init__(message, "BATCH_ERROR", details)


class DataLoadError(BatchProcessingError):
    """데이터 로드 오류"""

    def __init__(
        self,
        source: str,
        message: str = "데이터 로드에 실패했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["source"] = source
        super().__init__(message, None, details)
        self.error_code = "DATA_LOAD_ERROR"
