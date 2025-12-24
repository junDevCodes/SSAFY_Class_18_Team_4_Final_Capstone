import os
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import unittest

from crawler.raw_retention import archive_month, cleanup_old_raw, _month_key, perform_retention


class RawRetentionTest(unittest.TestCase):
    def test_30일_지난_파일을_삭제한다(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_file = root / "old.html"
            new_file = root / "new.html"
            old_file.write_text("old", encoding="utf-8")
            new_file.write_text("new", encoding="utf-8")
            old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).timestamp()
            os.utime(old_file, (old_ts, old_ts))

            removed = cleanup_old_raw(root, days=30)

            self.assertIn(old_file, removed)
            self.assertFalse(old_file.exists())
            self.assertTrue(new_file.exists())

    def test_월별_아카이브를_생성한다(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            out_dir = Path(tmp) / "out"
            raw_root.mkdir()
            (raw_root / "20251201").mkdir()
            sample = raw_root / "20251201" / "sample.html"
            sample.write_text("html", encoding="utf-8")

            archive = archive_month(raw_root, "202512", out_dir)

            self.assertTrue(archive.exists())
            with tarfile.open(archive, "r:gz") as tar:
                names = tar.getnames()
                self.assertIn("20251201", names)
                self.assertTrue(any(name.endswith("sample.html") for name in names))

    def test_month_key_추출(self) -> None:
        self.assertEqual("202512", _month_key("20251205"))
        self.assertIsNone(_month_key("invalid"))

    def test_retention이_전월을_압축하고_S3_업로드한다(self) -> None:
        class FakeS3:
            def __init__(self):
                self.uploads = []

            def upload_file(self, filename, bucket, key):
                self.uploads.append((filename, bucket, key))

            def generate_presigned_url(self, op, Params, ExpiresIn):
                return f"presigned://{Params['Key']}"

        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp) / "raw"
            out_dir = Path(tmp) / "out"
            raw_root.mkdir()
            (raw_root / "20251205").mkdir(parents=True, exist_ok=True)
            (raw_root / "20251205" / "sample.html").write_text("html", encoding="utf-8")

            fake_s3 = FakeS3()
            now = datetime(2025, 12, 15, tzinfo=timezone.utc)
            result = perform_retention(
                raw_root=raw_root,
                archive_root=out_dir,
                bucket="bucket",
                prefix_template="homeplus/raw/{YYYY}/{MM}/archive",
                now=now,
                s3_client=fake_s3,
                days=0,
            )

            self.assertTrue(result["archive"].exists())
            self.assertTrue(fake_s3.uploads)
            uploaded_key = fake_s3.uploads[0][2]
            self.assertIn("homeplus/raw/2025/11/archive", uploaded_key)
            self.assertTrue(str(result["presigned_url"]).startswith("presigned://"))


if __name__ == "__main__":
    unittest.main()
