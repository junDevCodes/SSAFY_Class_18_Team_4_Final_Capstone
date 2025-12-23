"""
S3 업로드 설정 검증용 관리 커맨드

현재 백엔드 컨테이너에서 로드된 AWS 자격 증명과 설정을 사용해
테스트 파일을 S3에 업로드해보는 명령입니다.

사용 예시:
    python manage.py test_s3_upload
"""
import io
import uuid
import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from products.services.s3_upload import S3ImageUploader, S3UploadError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "현재 백엔드 환경에서 S3 업로드가 정상 동작하는지 테스트합니다"

    def handle(self, *args, **options):
        # 기본 환경 정보 출력
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        region = getattr(settings, "AWS_S3_REGION_NAME", None)
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)

        self.stdout.write(self.style.WARNING("=== S3 업로드 테스트 시작 ==="))
        self.stdout.write(f"- bucket: {bucket}")
        self.stdout.write(f"- region: {region}")
        self.stdout.write(f"- access_key_prefix: {(access_key or '')[:6]}****")

        # 업로더 초기화
        try:
            uploader = S3ImageUploader()
        except S3UploadError as e:
            msg = f"S3 업로더 초기화 실패: {e}"
            self.stderr.write(self.style.ERROR(msg))
            logger.error(msg)
            return

        # 테스트용 파일 객체 생성
        content = b"test-upload-from-test_s3_upload-command"
        file_obj = io.BytesIO(content)
        file_obj.name = "test_s3_upload.txt"
        # 컨텐트 타입 힌트 추가 (선택)
        file_obj.content_type = "text/plain"  # type: ignore[attr-defined]

        # 0번 상품 ID 라는 가상의 값을 사용해 썸네일 업로드 테스트
        try:
            url = uploader.upload_thumbnail(file_obj, product_id=0, original_filename=file_obj.name)
        except S3UploadError as e:
            msg = f"S3 업로드 실패: {e}"
            self.stderr.write(self.style.ERROR(msg))
            logger.error(msg)
            return

        self.stdout.write(self.style.SUCCESS("S3 업로드 성공"))
        self.stdout.write(self.style.SUCCESS(f"→ 업로드된 URL: {url}"))
        self.stdout.write(self.style.WARNING("S3 콘솔에서 해당 객체가 생성되었는지도 함께 확인해보세요."))


