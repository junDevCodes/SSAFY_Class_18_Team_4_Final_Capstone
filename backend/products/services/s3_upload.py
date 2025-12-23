"""
S3 이미지 업로드 서비스

판매자 상품 이미지를 AWS S3에 업로드하고 URL을 반환합니다.

사용 예시:
    uploader = S3ImageUploader()

    # 메인 이미지(썸네일) 업로드
    url = uploader.upload_thumbnail(image_file, product_id)

    # 상세 설명 이미지 업로드
    urls = uploader.upload_detail_images(image_files, product_id)
"""
import uuid
import logging
from typing import List, BinaryIO

import boto3
from django.conf import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3UploadError(Exception):
    """S3 업로드 중 발생한 오류"""
    pass


class S3ImageUploader:
    """S3 이미지 업로드 서비스 클래스

    AWS S3에 이미지를 업로드하고 공개 URL을 반환합니다.

    Attributes:
        s3_client: boto3 S3 클라이언트
        bucket_name: S3 버킷명
        thumbnail_prefix: 메인 이미지(썸네일) S3 경로 접두사
        detail_prefix: 상세 설명 이미지 S3 경로 접두사
        custom_domain: S3 커스텀 도메인
    """

    def __init__(self):
        """S3 클라이언트 초기화"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.thumbnail_prefix = settings.AWS_S3_THUMBNAIL_PREFIX
        self.detail_prefix = settings.AWS_S3_PRODUCT_DETAIL_PREFIX
        self.custom_domain = settings.AWS_S3_CUSTOM_DOMAIN

    def _generate_unique_filename(self, original_filename: str, product_id: int) -> str:
        """고유한 파일명 생성

        형식: {product_id}_{uuid8자리}.{확장자}
        예: 123_a1b2c3d4.jpg

        Args:
            original_filename: 원본 파일명
            product_id: 상품 ID

        Returns:
            고유한 파일명
        """
        # 원본 파일명에서 확장자 추출
        if '.' in original_filename:
            ext = original_filename.rsplit('.', 1)[-1].lower()
        else:
            ext = 'jpg'

        # UUID 앞 8자리만 사용
        unique_id = uuid.uuid4().hex[:8]
        return f"{product_id}_{unique_id}.{ext}"

    def _upload_to_s3(self, file_obj: BinaryIO, s3_key: str, content_type: str) -> str:
        """파일을 S3에 업로드하고 URL 반환

        Args:
            file_obj: 업로드할 파일 객체 (InMemoryUploadedFile 등)
            s3_key: S3 객체 키 (경로 포함)
            content_type: 파일 MIME 타입

        Returns:
            업로드된 파일의 공개 URL

        Raises:
            S3UploadError: 업로드 실패 시
        """
        try:
            # 파일 포인터를 처음으로 리셋 (이미 읽힌 파일 대응)
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)

            extra_args = {
                'ContentType': content_type,
            }

            # ACL 설정 (public-read 허용 시)
            if hasattr(settings, 'AWS_DEFAULT_ACL') and settings.AWS_DEFAULT_ACL:
                extra_args['ACL'] = settings.AWS_DEFAULT_ACL

            # 캐시 설정
            if hasattr(settings, 'AWS_S3_OBJECT_PARAMETERS'):
                cache_control = settings.AWS_S3_OBJECT_PARAMETERS.get('CacheControl')
                if cache_control:
                    extra_args['CacheControl'] = cache_control

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            return f"https://{self.custom_domain}/{s3_key}"

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 업로드 실패 [{error_code}]: {error_message}")
            raise S3UploadError(f"이미지 업로드에 실패했습니다: {error_message}")
        except Exception as e:
            logger.error(f"S3 업로드 중 예상치 못한 오류: {e}")
            raise S3UploadError(f"이미지 업로드 중 오류가 발생했습니다: {str(e)}")

    def upload_thumbnail(self, file_obj, product_id: int, original_filename: str) -> str:
        """상품 메인 이미지(썸네일) 업로드

        S3 경로: homeplus/thumnail/{product_id}_{uuid}.{ext}

        Args:
            file_obj: 업로드할 이미지 파일
            product_id: 상품 ID
            original_filename: 원본 파일명

        Returns:
            S3에 업로드된 이미지 URL
        """
        filename = self._generate_unique_filename(original_filename, product_id)
        s3_key = f"{self.thumbnail_prefix}{filename}"
        content_type = getattr(file_obj, 'content_type', 'image/jpeg')

        logger.info(f"메인 이미지 업로드 시작: product_id={product_id}, s3_key={s3_key}")
        url = self._upload_to_s3(file_obj, s3_key, content_type)
        logger.info(f"메인 이미지 업로드 완료: {url}")

        return url

    def upload_detail_image(self, file_obj, product_id: int, original_filename: str) -> str:
        """상품 상세 설명 이미지 업로드

        S3 경로: homeplus/product_detail/{product_id}_{uuid}.{ext}

        Args:
            file_obj: 업로드할 이미지 파일
            product_id: 상품 ID
            original_filename: 원본 파일명

        Returns:
            S3에 업로드된 이미지 URL
        """
        filename = self._generate_unique_filename(original_filename, product_id)
        s3_key = f"{self.detail_prefix}{filename}"
        content_type = getattr(file_obj, 'content_type', 'image/jpeg')

        logger.info(f"상세 이미지 업로드 시작: product_id={product_id}, s3_key={s3_key}")
        url = self._upload_to_s3(file_obj, s3_key, content_type)
        logger.info(f"상세 이미지 업로드 완료: {url}")

        return url

    def upload_thumbnails(self, files: list, product_id: int) -> List[str]:
        """여러 메인 이미지(썸네일) 업로드

        Args:
            files: 업로드할 파일 리스트
            product_id: 상품 ID

        Returns:
            업로드된 이미지 URL 리스트
        """
        urls = []
        for file_obj in files:
            url = self.upload_thumbnail(file_obj, product_id, file_obj.name)
            urls.append(url)
        return urls

    def upload_detail_images(self, files: list, product_id: int) -> List[str]:
        """여러 상세 설명 이미지 업로드

        Args:
            files: 업로드할 파일 리스트
            product_id: 상품 ID

        Returns:
            업로드된 이미지 URL 리스트
        """
        urls = []
        for file_obj in files:
            url = self.upload_detail_image(file_obj, product_id, file_obj.name)
            urls.append(url)
        return urls

    def delete_image(self, image_url: str) -> bool:
        """S3에서 이미지 삭제

        Args:
            image_url: 삭제할 이미지 URL

        Returns:
            삭제 성공 여부
        """
        try:
            # URL에서 S3 키 추출
            if self.custom_domain in image_url:
                s3_key = image_url.split(self.custom_domain + '/')[-1]

                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                logger.info(f"S3 이미지 삭제 완료: {s3_key}")
                return True
            else:
                logger.warning(f"삭제 대상 URL이 현재 S3 도메인과 일치하지 않음: {image_url}")
                return False

        except ClientError as e:
            logger.warning(f"S3 이미지 삭제 실패: {e}")
            return False
        except Exception as e:
            logger.warning(f"S3 이미지 삭제 중 예상치 못한 오류: {e}")
            return False
