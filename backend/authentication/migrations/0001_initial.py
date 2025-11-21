"""
# ========================= 인증 모듈 시작(이식 가이드) =========================
# 최초 마이그레이션: 커스텀 사용자 모델 생성
# 주의: 프로젝트 시작 전에 AUTH_USER_MODEL 설정 후 적용해야 충돌이 없습니다.
# ============================================================================
"""

from django.db import migrations, models
import django.contrib.auth.models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="사용자가 모든 권한을 가지는지 여부", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "이미 존재하는 사용자명입니다."}, help_text="필수. 150자 이하. 문자, 숫자 및 @/./+/-/_ 문자만 사용 가능.", max_length=150, unique=True, verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="이메일 주소")),
                ("is_staff", models.BooleanField(default=False, help_text="사용자가 관리자 사이트에 접근할 수 있는지 여부", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="이 사용자가 활성 상태인지 표시", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("role", models.CharField(choices=[("guest", "게스트"), ("member", "일반회원"), ("vip", "VIP회원"), ("admin", "관리자")], default="guest", max_length=20)),
                ("provider", models.CharField(choices=[("email", "이메일"), ("google", "구글"), ("kakao", "카카오")], default="email", help_text="해당 계정이 마지막으로 로그인한 제공자", max_length=20)),
                ("provider_id", models.CharField(blank=True, help_text="OAuth 제공자의 사용자 고유 ID", max_length=255, null=True)),
                ("profile_image_url", models.URLField(blank=True, help_text="프로필 이미지 URL", null=True)),
                ("timezone", models.CharField(default="Asia/Seoul", help_text="사용자 타임존 (IANA 표준)", max_length=64)),
                ("groups", models.ManyToManyField(blank=True, help_text="이 사용자가 속한 그룹. 이 그룹의 권한은 해당 사용자에게 부여됩니다.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="이 사용자에 대한 특정 권한", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "verbose_name": "사용자",
                "verbose_name_plural": "사용자들",
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["email"], name="ix_user_email"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["provider", "provider_id"], name="ix_user_provider_pair"),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(fields=("provider", "provider_id"), name="uq_user_provider_provider_id"),
        ),
    ]
