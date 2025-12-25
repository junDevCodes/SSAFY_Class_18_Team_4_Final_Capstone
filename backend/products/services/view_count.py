"""
조회수 쿨타임 관리 서비스

이커머스 플랫폼에 적합한 방어적 조회수 시스템:
- 2분 쿨타임 적용 (어뷰징 방지)
- 회원/비회원 구분 처리
- IP + User-Agent 해시 기반 비회원 추적
"""
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Tuple

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.models import Product, ProductStats, ProductViewLog, UserProductStats

logger = logging.getLogger(__name__)


# 조회수 쿨타임 설정 (초 단위)
VIEW_COUNT_COOLDOWN_SECONDS = 120  # 2분


class ViewCountService:
    """상품 조회수 관리 서비스

    이커머스 플랫폼에 적합한 방어적 조회수 시스템:
    - 2분 쿨타임 적용 (어뷰징 방지)
    - 회원/비회원 구분 처리
    - IP + User-Agent 해시 기반 비회원 추적
    - Race condition 방지
    - 원자적 카운터 증가
    """

    @staticmethod
    def get_client_ip(request) -> Optional[str]:
        """요청에서 클라이언트 IP 추출

        X-Forwarded-For 헤더 우선 (리버스 프록시 환경 대응)
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For: client, proxy1, proxy2
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_user_agent(request) -> str:
        """요청에서 User-Agent 추출"""
        return request.META.get('HTTP_USER_AGENT', '')

    @staticmethod
    def generate_visitor_hash(ip: str, user_agent: str) -> str:
        """비회원 식별용 해시 생성

        IP + User-Agent를 SHA256 해시로 변환하여
        개인정보를 직접 저장하지 않고 식별 가능하게 함.
        """
        raw = f"{ip}:{user_agent}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def check_cooldown(
        cls,
        product: Product,
        user=None,
        visitor_hash: Optional[str] = None,
    ) -> bool:
        """쿨타임 내 조회 여부 확인

        Args:
            product: 상품 인스턴스
            user: 로그인 사용자 (Optional)
            visitor_hash: 비회원 해시 (Optional)

        Returns:
            True: 쿨타임 내 (조회수 증가 불가)
            False: 쿨타임 만료 (조회수 증가 가능)
        """
        cooldown_threshold = timezone.now() - timedelta(seconds=VIEW_COUNT_COOLDOWN_SECONDS)

        if user and user.is_authenticated:
            # 로그인 사용자: user_id 기반 체크
            return ProductViewLog.objects.filter(
                product=product,
                user=user,
                viewed_at__gte=cooldown_threshold,
            ).exists()
        elif visitor_hash:
            # 비회원: visitor_hash 기반 체크
            return ProductViewLog.objects.filter(
                product=product,
                visitor_hash=visitor_hash,
                viewed_at__gte=cooldown_threshold,
            ).exists()

        # 식별 정보가 없으면 쿨타임 적용 안 함 (드문 경우)
        return False

    @classmethod
    @transaction.atomic
    def increment_view_count(
        cls,
        request,
        product: Product,
    ) -> Tuple[bool, str]:
        """조회수 증가 (쿨타임 적용)

        Args:
            request: HTTP 요청 객체
            product: 상품 인스턴스

        Returns:
            Tuple[bool, str]: (증가 여부, 메시지)
            - (True, "success"): 조회수 증가됨
            - (False, "cooldown"): 쿨타임 내
            - (False, "error"): 에러 발생
        """
        try:
            user = request.user if request.user.is_authenticated else None
            ip_address = cls.get_client_ip(request)
            user_agent = cls.get_user_agent(request)

            # 비회원인 경우 visitor_hash 생성
            visitor_hash = None
            if not user:
                if ip_address:
                    visitor_hash = cls.generate_visitor_hash(ip_address, user_agent)
                else:
                    # IP를 알 수 없는 경우 User-Agent만으로 해시 생성
                    visitor_hash = cls.generate_visitor_hash('unknown', user_agent)

            # 쿨타임 체크
            if cls.check_cooldown(product, user, visitor_hash):
                logger.debug(
                    f"조회수 쿨타임: product={product.id}, "
                    f"user={user.id if user else 'guest'}"
                )
                return False, "cooldown"

            # 조회 로그 기록
            ProductViewLog.objects.create(
                product=product,
                user=user,
                visitor_hash=visitor_hash if not user else None,
                ip_address=ip_address,
            )

            # ProductStats 조회수 증가 (원자적 연산)
            updated = ProductStats.objects.filter(product_id=product.id).update(
                view_count=F('view_count') + 1
            )

            # ProductStats가 없으면 생성 (드문 경우)
            if updated == 0:
                ProductStats.objects.get_or_create(
                    product=product,
                    defaults={'view_count': 1}
                )

            # 로그인 사용자: UserProductStats 업데이트
            if user:
                rows_updated = UserProductStats.objects.filter(
                    user=user,
                    product=product
                ).update(
                    view_count=F('view_count') + 1,
                    last_interacted_at=timezone.now()
                )

                # 기존 레코드가 없으면 생성
                if rows_updated == 0:
                    UserProductStats.objects.get_or_create(
                        user=user,
                        product=product,
                        defaults={'view_count': 1}
                    )

            logger.info(
                f"조회수 증가: product={product.id}, "
                f"user={user.id if user else 'guest'}"
            )
            return True, "success"

        except Exception as e:
            logger.error(f"조회수 증가 실패: product={product.id}, error={str(e)}")
            return False, "error"

    @classmethod
    def cleanup_old_logs(cls, days: int = 1) -> int:
        """오래된 조회 로그 정리 (배치 작업용)

        Args:
            days: 보관 기간 (일)

        Returns:
            삭제된 로그 수
        """
        threshold = timezone.now() - timedelta(days=days)
        deleted_count, _ = ProductViewLog.objects.filter(
            viewed_at__lt=threshold
        ).delete()

        if deleted_count > 0:
            logger.info(f"조회 로그 정리: {deleted_count}건 삭제 ({days}일 이전)")

        return deleted_count
