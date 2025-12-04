"""
사용자 비밀번호 정규화 커맨드

ERD v2.1 기준:
- 실제 비밀번호 해시는 auth_email_credentials.password_hash 에만 저장
- users.password 필드는 Django AbstractUser 때문에 물리적으로 존재하지만
  애플리케이션에서 인증에 사용하지 않는 unusable 값이어야 한다.

이 커맨드는 기존 데이터에서 중복/누락 상태를 정리한다.

1) AuthEmailCredential 이 있는 사용자:
   - user.password 에 사용 가능한 해시가 들어있으면 set_unusable_password() 로 변경
2) AuthEmailCredential 이 없고 user.password 에 해시가 있는 사용자:
   - 해당 해시를 그대로 AuthEmailCredential.password_hash 로 옮기고
     is_email_verified=True 로 생성
   - 이후 user.set_unusable_password() 적용
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from authentication.models import AuthEmailCredential


class Command(BaseCommand):
    help = "users.password / auth_email_credentials.password_hash 중복을 제거하고 ERD v2.1 기준으로 정규화합니다."

    def handle(self, *args, **options):
        User = get_user_model()

        fixed_users = 0
        created_credentials = 0

        for user in User.objects.all():
            has_usable = user.has_usable_password()

            try:
                cred = user.email_credential  # type: ignore[attr-defined]
            except AuthEmailCredential.DoesNotExist:
                cred = None

            # 1) 자격 증명은 있는데 User.password 가 사용 가능한 해시인 경우 → User.password 비우기
            if cred is not None:
                if has_usable:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                    fixed_users += 1
                continue

            # 2) cred 가 없고, user.password 에 사용 가능한 해시가 있는 경우
            if cred is None and has_usable:
                # 기존 해시를 그대로 password_hash 로 옮기고, User.password 는 unusable 로 변경
                AuthEmailCredential.objects.create(
                    user=user,
                    password_hash=user.password,
                    is_email_verified=True,
                )
                created_credentials += 1

                user.set_unusable_password()
                user.save(update_fields=["password"])
                fixed_users += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"정규화 완료: 비밀번호 정리된 사용자 {fixed_users}명, "
                f"새로 생성된 AuthEmailCredential {created_credentials}개"
            )
        )

