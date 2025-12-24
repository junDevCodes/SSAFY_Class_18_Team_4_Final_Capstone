"""
원본 HTML/에러 로그 저장 유틸

문제 케이스에서만 HTML을 저장해 추후 파싱 오류를 분석한다.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class RawStorage:
    """원본 HTML과 에러 정보를 파일로 저장"""

    def __init__(self, base_dir: str | Path | None = None):
        project_root = Path(__file__).parent.parent
        docker_data_path = Path("/app/data")
        if base_dir:
            root = Path(base_dir)
        elif docker_data_path.exists():
            root = docker_data_path
        else:
            root = project_root / "data"
        self.base_dir = root / "raw" / "homeplus"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _build_dir(self, batch_id: str) -> Path:
        """배치/날짜 경로를 생성"""
        date_dir = datetime.now(timezone.utc).strftime("%Y%m%d")
        path = self.base_dir / date_dir / batch_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _make_filename(self, item_no: str, ext: str) -> str:
        """항목별 파일명 생성"""
        digest = hashlib.md5(item_no.encode("utf-8")).hexdigest()  # noqa: S324 md5 허용(파일명 해시용)
        return f"{item_no}_{digest}.{ext}"

    def save_html(self, batch_id: str, item_no: str, html: str) -> Path:
        """문제 케이스 HTML 저장"""
        target_dir = self._build_dir(batch_id)
        filename = self._make_filename(item_no, "html")
        path = target_dir / filename
        path.write_text(html, encoding="utf-8")
        return path

    def save_error(self, batch_id: str, item_no: str, reason: str, payload: Dict[str, Any]) -> Path:
        """에러 메타 정보 저장"""
        target_dir = self._build_dir(batch_id)
        filename = self._make_filename(item_no, "json")
        path = target_dir / filename
        data = {
            "batch_id": batch_id,
            "item_no": item_no,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
