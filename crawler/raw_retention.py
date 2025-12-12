"""
raw HTML/스크린샷 장기 보관·정리 유틸

- 30일 지난 raw 데이터를 삭제
- 특정 월 데이터 tar.gz로 묶어 보관
- S3 버킷으로 업로드(옵션)
"""

from __future__ import annotations

import re
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import boto3


def cleanup_old_raw(base_dir: Path | str, days: int = 30) -> List[Path]:
    """지정 일수보다 오래된 raw 파일/폴더를 삭제"""
    root = Path(base_dir)
    if not root.exists():
        return []
    removed: List[Path] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for path in root.rglob("*"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            try:
                if path.is_file():
                    path.unlink()
                else:
                    for child in path.rglob("*"):
                        if child.is_file():
                            child.unlink(missing_ok=True)
                    path.rmdir()
                removed.append(path)
            except FileNotFoundError:
                continue
    return removed


def _month_key(dir_name: str) -> Optional[str]:
    """YYYYMMDD 형식 디렉터리명에서 월 키 추출"""
    m = re.match(r"^(\d{4})(\d{2})\d{2}$", dir_name)
    if not m:
        return None
    return f"{m.group(1)}{m.group(2)}"


def archive_month(raw_root: Path | str, year_month: str, output_dir: Path | str) -> Path:
    """특정 연월(YYYYMM)의 raw 데이터를 tar.gz로 압축"""
    raw_root = Path(raw_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = output_dir / f"homeplus_raw_{year_month}.tar.gz"

    with tarfile.open(archive_name, "w:gz") as tar:
        for day_dir in raw_root.iterdir():
            if not day_dir.is_dir():
                continue
            if _month_key(day_dir.name) != year_month:
                continue
            tar.add(day_dir, arcname=day_dir.name)
    return archive_name


def upload_archive_to_s3(archive_path: Path | str, bucket: str, prefix: str, s3_client=None) -> str:
    """tar.gz 아카이브를 S3에 업로드하고 presigned URL 반환"""
    archive_path = Path(archive_path)
    client = s3_client or boto3.client("s3")
    key = f"{prefix.rstrip('/')}/{archive_path.name}"
    client.upload_file(str(archive_path), bucket, key)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )
    return url


def perform_retention(
    raw_root: Path | str,
    archive_root: Path | str,
    bucket: Optional[str] = None,
    prefix_template: str = "homeplus/raw/{YYYY}/{MM}/{batch_id}",
    now: Optional[datetime] = None,
    s3_client=None,
    days: int = 30,
) -> Dict[str, Optional[Path] | List[Path] | Optional[str]]:
    """
    raw 보관 정책 실행: 오래된 파일 삭제, 전월 데이터를 tar.gz로 압축 후 S3 업로드

    bucket이 없으면 로컬 정리와 압축까지만 수행한다.
    """
    removed = cleanup_old_raw(raw_root, days=days)

    current = now or datetime.now(timezone.utc)
    prev_month = (current.replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    archive_path = archive_month(raw_root, prev_month, archive_root)

    presigned_url: Optional[str] = None
    if bucket:
        prefix = prefix_template.format(YYYY=prev_month[:4], MM=prev_month[4:], batch_id="archive")
        presigned_url = upload_archive_to_s3(archive_path, bucket, prefix, s3_client=s3_client)

    return {"removed": removed, "archive": archive_path, "presigned_url": presigned_url}
