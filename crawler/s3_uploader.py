"""
S3 업로더 유틸

이미지 파일을 다운로드한 뒤 S3에 업로드하고 presigned URL을 반환한다.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional

import boto3
import httpx

from crawler.config import AppConfig


class S3Uploader:
    """이미지 업로드 및 presigned URL 발급기"""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self.bucket = self.config.s3.bucket
        self.prefix_tpl = self.config.s3.prefix
        self.region = self.config.s3.region
        self.presign_expires = self.config.s3.presign_expires
        self._s3 = boto3.client("s3", region_name=self.region) if self.bucket else None
        self._http = httpx.Client(timeout=15.0)

    def _make_key(self, batch_id: str, item_no: str, idx: int) -> str:
        """S3 오브젝트 키 생성"""
        now = datetime.utcnow()
        prefix = self.prefix_tpl.format(
            YYYY=now.strftime("%Y"),
            MM=now.strftime("%m"),
            batch_id=batch_id,
        )
        filename = f"{item_no}_{idx}.jpg"
        return f"{prefix.rstrip('/')}/{filename}"

    def upload_and_presign(self, url: str, batch_id: str, item_no: str, idx: int) -> Optional[str]:
        """이미지 다운로드 → S3 업로드 → presigned URL 반환"""
        if not self._s3 or not self.bucket:
            return url
        try:
            resp = self._http.get(url)
            resp.raise_for_status()
            key = self._make_key(batch_id, str(item_no), idx)
            self._s3.put_object(Bucket=self.bucket, Key=key, Body=resp.content, ContentType="image/jpeg")
            presigned = self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=self.presign_expires,
            )
            return presigned
        except Exception:
            # 업로드 실패 시 원본 URL을 그대로 사용
            return url
