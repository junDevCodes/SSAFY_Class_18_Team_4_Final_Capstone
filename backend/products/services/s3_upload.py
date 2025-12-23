"""
S3 이미지 업로드 서비스

판매자 상품/브랜드 이미지를 AWS S3에 업로드하고 URL을 반환합니다.

S3 경로 구조:
    seller_profile/
    ├── seller_product_thumbnail/   # 상품 메인 이미지
    ├── seller_product_detail/      # 상품 상세 이미지
    ├── seller_profile/             # 판매자 프로필 이미지
    ├── brand_logo/                 # 브랜드 로고
    └── brand_banner/               # 브랜드 배너

사용 예시:
    uploader = S3ImageUploader()

    # 상품 이미지 업로드
    url = uploader.upload_thumbnail(image_file, product_id)
    urls = uploader.upload_detail_images(image_files, product_id)

    # 판매자/브랜드 이미지 업로드
    url = uploader.upload_seller_profile(image_file, seller_id)
    url = uploader.upload_brand_logo(image_file, seller_id)
    url = uploader.upload_brand_banner(image_file, seller_id)
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

    Raises:
        S3UploadError: S3 버킷명이 설정되지 않은 경우
    """

    def __init__(self):
        """S3 클라이언트 초기화

        boto3는 자동으로 자격증명을 찾습니다:
        1. 환경변수 (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. ~/.aws/credentials 파일
        3. EC2 IAM Role (메타데이터 서비스)

        Raises:
            S3UploadError: S3 버킷명이 설정되지 않은 경우
        """
        # S3 버킷명 검증
        if not settings.AWS_STORAGE_BUCKET_NAME:
            logger.error("S3 버킷명이 설정되지 않았습니다.")
            raise S3UploadError(
                "S3 버킷명이 설정되지 않았습니다. "
                "AWS_S3_BUCKET 환경변수를 확인해주세요."
            )

        # boto3는 자동으로 자격증명을 찾습니다 (환경변수 → credentials 파일 → EC2 IAM Role)
        # 크롤러와 동일하게 명시적으로 자격증명을 전달하지 않음
        # boto3가 자동으로 AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY 환경변수 또는 EC2 IAM Role을 찾음
        self.s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME)

        # 초기화 시 자격증명 확인 (디버깅용)
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials and credentials.access_key:
                logger.info("S3 자격증명 확인됨: Access Key ID=%s...", credentials.access_key[:10])
            else:
                logger.warning("S3 자격증명을 찾을 수 없습니다. EC2 IAM 역할 또는 환경변수를 확인하세요.")
        except Exception as e:
            logger.warning("S3 자격증명 확인 중 오류: %s", e)
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.custom_domain = settings.AWS_S3_CUSTOM_DOMAIN

        # 상품 이미지 경로
        self.thumbnail_prefix = settings.AWS_S3_THUMBNAIL_PREFIX
        self.detail_prefix = settings.AWS_S3_PRODUCT_DETAIL_PREFIX

        # 판매자/브랜드 이미지 경로
        self.seller_profile_prefix = getattr(settings, 'AWS_S3_SELLER_PROFILE_PREFIX', 'seller_profile/seller_profile/')
        self.brand_logo_prefix = getattr(settings, 'AWS_S3_BRAND_LOGO_PREFIX', 'seller_profile/brand_logo/')
        self.brand_banner_prefix = getattr(settings, 'AWS_S3_BRAND_BANNER_PREFIX', 'seller_profile/brand_banner/')

        logger.info(f"S3ImageUploader 초기화: bucket={self.bucket_name}, region={settings.AWS_S3_REGION_NAME}")

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

        S3 경로: homeplus/thumbnail/{product_id}_{uuid}.{ext}

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

    def _generate_seller_filename(self, original_filename: str, seller_id: int) -> str:
        """판매자용 고유 파일명 생성

        형식: seller_{seller_id}_{uuid8자리}.{확장자}
        예: seller_5_a1b2c3d4.jpg

        Args:
            original_filename: 원본 파일명
            seller_id: 판매자 ID

        Returns:
            고유한 파일명
        """
        if '.' in original_filename:
            ext = original_filename.rsplit('.', 1)[-1].lower()
        else:
            ext = 'jpg'

        unique_id = uuid.uuid4().hex[:8]
        return f"seller_{seller_id}_{unique_id}.{ext}"

    def upload_seller_profile(self, file_obj, seller_id: int, original_filename: str) -> str:
        """판매자 프로필 이미지 업로드

        S3 경로: seller_profile/seller_profile/seller_{seller_id}_{uuid}.{ext}

        Args:
            file_obj: 업로드할 이미지 파일
            seller_id: 판매자 ID
            original_filename: 원본 파일명

        Returns:
            S3에 업로드된 이미지 URL
        """
        filename = self._generate_seller_filename(original_filename, seller_id)
        s3_key = f"{self.seller_profile_prefix}{filename}"
        content_type = getattr(file_obj, 'content_type', 'image/jpeg')

        logger.info(f"판매자 프로필 이미지 업로드 시작: seller_id={seller_id}, s3_key={s3_key}")
        url = self._upload_to_s3(file_obj, s3_key, content_type)
        logger.info(f"판매자 프로필 이미지 업로드 완료: {url}")

        return url

    def upload_brand_logo(self, file_obj, seller_id: int, original_filename: str) -> str:
        """브랜드 로고 업로드

        S3 경로: seller_profile/brand_logo/seller_{seller_id}_{uuid}.{ext}

        Args:
            file_obj: 업로드할 이미지 파일
            seller_id: 판매자 ID
            original_filename: 원본 파일명

        Returns:
            S3에 업로드된 이미지 URL
        """
        filename = self._generate_seller_filename(original_filename, seller_id)
        s3_key = f"{self.brand_logo_prefix}{filename}"
        content_type = getattr(file_obj, 'content_type', 'image/jpeg')

        logger.info(f"브랜드 로고 업로드 시작: seller_id={seller_id}, s3_key={s3_key}")
        url = self._upload_to_s3(file_obj, s3_key, content_type)
        logger.info(f"브랜드 로고 업로드 완료: {url}")

        return url

    def upload_brand_banner(self, file_obj, seller_id: int, original_filename: str) -> str:
        """브랜드 배너 업로드

        S3 경로: seller_profile/brand_banner/seller_{seller_id}_{uuid}.{ext}

        Args:
            file_obj: 업로드할 이미지 파일
            seller_id: 판매자 ID
            original_filename: 원본 파일명

        Returns:
            S3에 업로드된 이미지 URL
        """
        filename = self._generate_seller_filename(original_filename, seller_id)
        s3_key = f"{self.brand_banner_prefix}{filename}"
        content_type = getattr(file_obj, 'content_type', 'image/jpeg')

        logger.info(f"브랜드 배너 업로드 시작: seller_id={seller_id}, s3_key={s3_key}")
        url = self._upload_to_s3(file_obj, s3_key, content_type)
        logger.info(f"브랜드 배너 업로드 완료: {url}")

        return url

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
