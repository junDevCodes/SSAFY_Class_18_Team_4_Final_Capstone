"""
S3 업로더 유틸

이미지 파일을 다운로드한 뒤 S3에 업로드하고 presigned URL을 반환한다.
"""

import hashlib
import os
import logging
from datetime import datetime
from typing import Optional

import boto3
import httpx

from crawler.config import AppConfig


logger = logging.getLogger(__name__)


class S3Uploader:
    """이미지 업로드 및 presigned URL 발급기"""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self.bucket = self.config.s3.bucket
        self.prefix_tpl = self.config.s3.prefix
        self.thumbnail_prefix_tpl = self.config.s3.thumbnail_prefix
        self.product_detail_prefix_tpl = self.config.s3.product_detail_prefix
        self.region = self.config.s3.region
        self.presign_expires = self.config.s3.presign_expires
        self.use_public_url = self.config.s3.use_public_url
        
        # boto3 클라이언트 생성 (자격 증명 명시적 전달 추가)
        s3_params = {
            "region_name": self.region
        }
        if self.config.s3.access_key and self.config.s3.secret_key:
            s3_params["aws_access_key_id"] = self.config.s3.access_key
            s3_params["aws_secret_access_key"] = self.config.s3.secret_key
            logger.info("환경변수로부터 S3 자격증명을 명시적으로 사용합니다.")
        
        self._s3 = boto3.client("s3", **s3_params) if self.bucket else None
        
        # 리디렉션(302) 응답을 따라가도록 설정해 rtd -> td 전환 시 업로드가 실패하지 않게 함
        self._http = httpx.Client(timeout=15.0, follow_redirects=True)
        
        # 초기화 시 자격증명 및 버킷 접근 테스트
        if self._s3 and self.bucket:
            try:
                # 자격증명 확인
                session = boto3.Session()
                credentials = session.get_credentials()
                if credentials:
                    logger.info("S3 자격증명 확인됨: Access Key ID=%s", credentials.access_key[:10] + "..." if credentials.access_key else "None")
                else:
                    logger.warning("S3 자격증명을 찾을 수 없습니다. EC2 IAM 역할 또는 환경변수를 확인하세요.")
                
                # 버킷 접근 테스트
                self._s3.head_bucket(Bucket=self.bucket)
                logger.info("S3 버킷 접근 성공: bucket=%s region=%s", self.bucket, self.region)
            except Exception as exc:
                logger.error("S3 초기화 실패: bucket=%s error=%s", self.bucket, exc)
                # 초기화 실패해도 계속 진행 (업로드 시점에 다시 시도)

    def _make_key(self, batch_id: str, item_no: str, idx: int, image_type: str = "thumbnail", image_hash: Optional[str] = None) -> str:
        """S3 오브젝트 키 생성
        
        Args:
            batch_id: 배치 ID (플레이스홀더 치환용)
            item_no: 상품 번호
            idx: 이미지 인덱스
            image_type: 이미지 타입 ("thumbnail" 또는 "product_detail")
            image_hash: 이미지 URL 해시 (중복 방지용, 선택)
        """
        import time
        # 이미지 타입에 따라 다른 prefix 사용
        if image_type == "product_detail":
            prefix = self.product_detail_prefix_tpl.rstrip('/')
        else:  # thumbnail (기본값)
            prefix = self.thumbnail_prefix_tpl.rstrip('/')
        
        # 플레이스홀더를 실제 값으로 치환
        now = datetime.utcnow()
        prefix = prefix.replace('{YYYY}', now.strftime('%Y'))
        prefix = prefix.replace('{MM}', now.strftime('%m'))
        prefix = prefix.replace('{batch_id}', batch_id)
        prefix = prefix.rstrip('/')
        
        # 파일명 생성: item_no + timestamp + hash/idx 조합으로 중복 철저히 방지
        timestamp = time.strftime("%Y%m%d%H%M%S")
        if image_hash:
            filename = f"{item_no}_{timestamp}_{idx}_{image_hash[:8]}.jpg"
        else:
            filename = f"{item_no}_{timestamp}_{idx}.jpg"
        return f"{prefix}/{filename}"

    def upload_and_presign(self, url: str, batch_id: str, item_no: str, idx: int, image_type: str = "thumbnail") -> Optional[str]:
        """이미지 다운로드 → S3 업로드 → Public URL 반환 (명칭 유지, 동작은 Public URL 우선)
        
        최적화:
        - 이미지 URL 해시를 계산하여 파일명에 포함
        - S3에 이미 존재하는지 확인하여 중복 업로드 방지
        - 항상 사용자에게 보여줄 수 있는 Public URL 반환
        """
        if not self._s3 or not self.bucket:
            logger.info("S3 비활성화 또는 버킷 미설정으로 원본 URL을 사용합니다: %s", url)
            return url
        try:
            # 이미지 URL 해시 계산 (중복 방지 및 파일명 생성용)
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            
            # S3 키 생성 (해시 포함)
            key = self._make_key(batch_id, str(item_no), idx, image_type=image_type, image_hash=url_hash)
            
            # S3에 이미 존재하는지 확인 (중복 업로드 방지)
            try:
                self._s3.head_object(Bucket=self.bucket, Key=key)
                # 이미 존재하면 업로드 스킵하고 URL만 생성
                logger.debug("S3에 이미 존재하는 이미지 (업로드 스킵): key=%s", key)
                # 항상 Public URL 반환
                public_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
                return public_url
            except self._s3.exceptions.ClientError as e:
                # 파일이 없으면 (404) 정상적으로 업로드 진행
                if e.response['Error']['Code'] != '404':
                    raise
            
            # 이미지 다운로드 및 업로드
            resp = self._http.get(url)
            resp.raise_for_status()
            
            # 실제 업로드 수행 (ACL 설정 제외하여 권한 오류 방지, 버킷 정책 의존)
            put_params = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": resp.content,
                "ContentType": "image/jpeg"
            }
            
            self._s3.put_object(**put_params)
            
            # 항상 Public URL 반환
            public_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
            logger.info("S3 업로드 성공 (Public URL 반환): bucket=%s key=%s url=%s", self.bucket, key, public_url)
            return public_url

        except Exception as exc:
            # 업로드 실패 시 원본 URL을 그대로 사용 (로그만 남기고 fallback)
            error_type = type(exc).__name__
            error_msg = str(exc)
            logger.warning(
                "S3 업로드 실패로 원본 URL을 사용합니다: url=%s error_type=%s error=%s bucket=%s key=%s",
                url, error_type, error_msg, self.bucket, key if 'key' in locals() else 'N/A'
            )
            # 자격증명 관련 에러인 경우 추가 정보 로깅
            if "NoCredentialsError" in error_type or "credentials" in error_msg.lower():
                logger.error(
                    "S3 자격증명 오류: EC2 IAM 역할(%s)이 부여되었는지 확인하세요. "
                    "또는 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 환경변수를 설정하세요.",
                    "ec2-self-json-backup"
                )
            elif "AccessDenied" in error_type or "access" in error_msg.lower():
                logger.error(
                    "S3 접근 거부: IAM 정책에서 bucket=%s key=%s 경로에 대한 PutObject 권한을 확인하세요.",
                    self.bucket, key if 'key' in locals() else 'N/A'
                )
            return url
