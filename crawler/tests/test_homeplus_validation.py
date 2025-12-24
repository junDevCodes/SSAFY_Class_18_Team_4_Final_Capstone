import unittest

from backend.data_pipeline.schemas import CrawlBatch, ProductData, ProductImage
from crawler.homeplus.validator import validate_batch, validate_product


class HomeplusValidationTest(unittest.TestCase):
    def test_유효한_상품은_이슈가_없어야_한다(self) -> None:
        # 유효한 ProductData 구성
        product = ProductData(
            name="테스트 상품",
            price=1000,
            source_site="homeplus",
            source_url="https://mfront.homeplus.co.kr/item?itemNo=123",
            crawled_at="2025-12-13T00:00:00Z",
            category_name="쌀/잡곡",
            service_category="GRAIN",
            images=[ProductImage(image_url="https://image.homeplus.kr/rtd/test", display_order=0)],
        )
        issues = validate_product(0, product)
        self.assertEqual([], issues)

    def test_필수_필드_누락시_에러가_발생해야_한다(self) -> None:
        # 필수 필드가 일부 누락된 ProductData
        product = ProductData(
            name="",
            price=0,
            source_site="homeplus",
            source_url="not-a-url",
            crawled_at="2025-12-13T00:00:00Z",
        )
        issues = validate_product(0, product)
        # 이름/가격/source_url 관련 에러가 포함되어야 함
        codes = {i.code for i in issues}
        self.assertIn("MISSING_NAME", codes)
        self.assertIn("INVALID_PRICE", codes)
        self.assertIn("INVALID_SOURCE_URL", codes)

    def test_batch_total_count_불일치시_경고가_발생해야_한다(self) -> None:
        batch = CrawlBatch(
            batch_id="homeplus_20251213_000000",
            source="homeplus",
            crawled_at="2025-12-13T00:00:00Z",
            total_count=2,
            products=[],
        )
        issues = validate_batch(batch)
        codes = {i.code for i in issues}
        self.assertIn("TOTAL_COUNT_MISMATCH", codes)

    def test_대표이미지_없으면_에러가_발생해야_한다(self) -> None:
        product = ProductData(
            name="이미지 없는 상품",
            price=1000,
            source_site="homeplus",
            source_url="https://mfront.homeplus.co.kr/item?itemNo=999",
            crawled_at="2025-12-13T00:00:00Z",
            category_name="쌀/잡곡",
            service_category="GRAIN",
            images=[],
        )
        issues = validate_product(0, product)
        codes = {i.code for i in issues}
        levels = {i.code: i.level for i in issues}
        self.assertIn("MISSING_IMAGES", codes)
        self.assertEqual("error", levels["MISSING_IMAGES"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


