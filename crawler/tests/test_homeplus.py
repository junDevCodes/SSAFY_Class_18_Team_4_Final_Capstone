import os
import unittest
from datetime import datetime

from crawler.config import AlertConfig, AppConfig, CrawlConfig, S3Config, StoreConfig
from crawler.homeplus.mappers import map_item_to_product
from crawler.homeplus.parsers import GrainCategory, extract_grain_categories
from crawler.homeplus.service import HomeplusService, _parse_item_list
from crawler.homeplus.client import HomeplusClient
from crawler.http_client import HttpClient
from crawler.raw_storage import RawStorage


class GrainCategoryParserTest(unittest.TestCase):
    def test_쌀잡곡_카테고리_중복없이_추출(self) -> None:
        sample_map = {
            "data": {
                "categoryList": [
                    {
                        "cateDepth": "R",
                        "cateCd": 2,
                        "cateNm": "식품",
                        "children": [
                            {
                                "cateDepth": "L",
                                "cateCd": "100002",
                                "cateNm": "쌀/잡곡",
                                "childList": [
                                    {
                                        "cateDepth": "M",
                                        "cateCd": 200015,
                                        "cateNm": "백미",
                                        "childList": [
                                            {"cateDepth": "S", "cateCd": 300049, "cateNm": "10kg 이상 ~ 20kg 미만"},
                                            {"cateDepth": "S", "cateCd": 300049, "cateNm": "10kg 이상 ~ 20kg 미만"},
                                        ],
                                    },
                                    {
                                        "cateDepth": "M",
                                        "cateCd": "200016",
                                        "cateNm": "혼합곡",
                                        "childList": [],
                                    },
                                ],
                            },
                            {"cateDepth": "L", "cateCd": "100003", "cateNm": "과일", "children": []},
                        ],
                    }
                ]
            }
        }

        categories = extract_grain_categories(sample_map)
        as_set = {(
            c.lcateCd,
            c.mcateCd,
            c.scateCd,
            c.lcateNm,
            c.mcateNm,
            c.scateNm,
        ) for c in categories}

        expected = {
            (100002, 200015, 300049, "쌀/잡곡", "백미", "10kg 이상 ~ 20kg 미만"),
            (100002, 200016, None, "쌀/잡곡", "혼합곡", None),
        }
        self.assertEqual(expected, as_set)


class ItemListParserTest(unittest.TestCase):
    def test_페이지네이션과_아이템리스트를_파싱한다(self) -> None:
        resp = {
            "items": [{"id": 1}],
            "pagination": {"totalPage": 2, "totalCount": 5},
        }

        items, total_page, total_count = _parse_item_list(resp)

        self.assertEqual(1, len(items))
        self.assertEqual(2, total_page)
        self.assertEqual(5, total_count)

    def test_데이터_중첩구조에서도_파싱한다(self) -> None:
        resp = {
            "data": {
                "list": [{"id": 10}, {"id": 11}],
                "totalCount": "7",
            },
            "pagination": {"total_page": "3"},
        }

        items, total_page, total_count = _parse_item_list(resp)

        self.assertEqual(2, len(items))
        self.assertEqual(3, total_page)
        self.assertEqual(7, total_count)


class ProductMappingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StoreConfig(store_id=99, store_type="TEST", store_kind="NOR", item_ship_method="TD_DRCT")

    def test_상품_매핑시_가격_카테고리_가공도_단위를_적용한다(self) -> None:
        item = {
            "itemNo": "123",
            "itemNm": "즉석밥 3입",
            "dcPrice": 4500,
            "salePrice": 5000,
            "lcateNm": "쌀/잡곡",
            "mcateNm": "백미",
            "scateNm": "즉석밥",
            "totalUnitQty": 3,
            "unitMeasure": "개",
            "recomMsg": "추천 문구",
            "brandNm": "브랜드",
            "imageUrl": "https://example.com/main.jpg",
        }
        detail_html = "<div><img src='http://example.com/detail1.jpg'><img src='https://facebook.com/ignored.png'></div><p>설명</p>"

        product = map_item_to_product(item, self.store, detail_html=detail_html)

        self.assertEqual("즉석밥", product.category_name)
        self.assertEqual("GRAIN", product.service_category)
        self.assertEqual("백미", product.service_subcategory)
        self.assertEqual(4500, product.price)
        self.assertEqual(5000, product.original_price)
        self.assertEqual("3개", product.unit)
        self.assertEqual("ambient", product.storage_type)
        self.assertEqual("processed", product.processing_level)
        self.assertTrue(product.crawled_at)
        datetime.fromisoformat(product.crawled_at)
        self.assertEqual("https://mfront.homeplus.co.kr/item?itemNo=123&storeType=TEST&storeId=99", product.source_url)
        self.assertEqual("쌀/잡곡 > 백미 > 즉석밥", product.source_category_path)
        self.assertEqual("https://example.com/main.jpg", product.images[0].image_url)
        self.assertIn("http://example.com/detail1.jpg", product.full_image_description)
        self.assertIn("설명", product.full_text_description)

    def test_대표이미지없으면_상세이미지를_사용한다(self) -> None:
        item = {
            "itemNo": "999",
            "itemNm": "현미",
            "salePrice": 3200,
            "lcateNm": "쌀/잡곡",
            "mcateNm": "현미",
            "scateNm": None,
        }
        detail_html = "<div><img src='http://example.com/detail2.jpg'></div>"

        product = map_item_to_product(item, self.store, detail_html=detail_html)

        self.assertEqual("현미", product.category_name)
        self.assertEqual("http://example.com/detail2.jpg", product.images[0].image_url)
        self.assertEqual(3200, product.price)
        self.assertIsNone(product.original_price)


class AppConfigLoadTest(unittest.TestCase):
    def test_env_설정으로_스토어값을_로드한다(self) -> None:
        original = {k: os.environ.get(k) for k in ("STORE_ID", "STORE_TYPE", "STORE_KIND", "ITEM_SHIP_METHOD")}
        try:
            os.environ["STORE_ID"] = "55"
            os.environ["STORE_TYPE"] = "TEST"
            os.environ["STORE_KIND"] = "LAB"
            os.environ["ITEM_SHIP_METHOD"] = "SHIP"

            config = AppConfig.load()

            self.assertEqual(55, config.store.store_id)
            self.assertEqual("TEST", config.store.store_type)
            self.assertEqual("LAB", config.store.store_kind)
            self.assertEqual("SHIP", config.store.item_ship_method)
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_env_없을때_기본값을_사용한다(self) -> None:
        original = {k: os.environ.get(k) for k in ("STORE_ID", "STORE_TYPE", "STORE_KIND", "ITEM_SHIP_METHOD")}
        try:
            for key in original:
                os.environ.pop(key, None)

            config = AppConfig.load()

            self.assertEqual(37, config.store.store_id)
            self.assertEqual("HYPER", config.store.store_type)
            self.assertEqual("NOR", config.store.store_kind)
            self.assertEqual("TD_DRCT", config.store.item_ship_method)
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class DummyHttp:
    def __init__(self) -> None:
        self.calls = []

    def get_json(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return {}


class HomeplusClientParamTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = DummyHttp()
        self.config = AppConfig(
            crawl=CrawlConfig(),
            store=StoreConfig(store_id=88, store_type="TEST", store_kind="LAB", item_ship_method="SHIP"),
            alert=AlertConfig(),
            s3=S3Config(),
        )
        self.client = HomeplusClient(config=self.config, http_client=self.http)

    def test_item_list_호출시_스토어_파라미터가_포함된다(self) -> None:
        self.client.fetch_item_list(
            category_depth=3,
            category_id=300049,
            page=2,
            per_page=20,
            add_sub_category="Y",
            search_type="NONE",
        )

        call = self.http.calls[0]
        self.assertTrue(call["url"].endswith("/category/item.json"))
        self.assertEqual(
            {
                "categoryDepth": 3,
                "categoryId": 300049,
                "page": 2,
                "perPage": 20,
                "sort": "RANK",
                "storeId": 88,
                "storeType": "TEST",
                "storeKind": "LAB",
                "itemShipMethod": "SHIP",
                "addSubCategoryYn": "Y",
                "searchType": "NONE",
            },
            call["params"],
        )

    def test_filter_meta_호출시_스토어_파라미터가_포함된다(self) -> None:
        self.client.fetch_filter_meta(
            category_depth=2,
            category_id=200015,
            page=1,
            per_page=10,
        )

        call = self.http.calls[0]
        self.assertTrue(call["url"].endswith("/category/filter.json"))
        self.assertEqual(
            {
                "categoryDepth": 2,
                "categoryId": 200015,
                "page": 1,
                "perPage": 10,
                "sort": "RANK",
                "storeId": 88,
                "storeType": "TEST",
                "storeKind": "LAB",
                "itemShipMethod": "SHIP",
            },
            call["params"],
        )


class HttpClientLoggingTest(unittest.TestCase):
    def test_요청_로그에_상태와_시간이_남는다(self) -> None:
        class FakeResponse:
            def __init__(self) -> None:
                self.status_code = 200
                self.request = None

            def json(self) -> dict:
                return {"ok": True}

            def raise_for_status(self) -> None:
                return

        class FakeClient:
            def __init__(self) -> None:
                self.calls = 0

            def get(self, url, params=None, headers=None):
                self.calls += 1
                return FakeResponse()

        http = HttpClient()
        http._client = FakeClient()

        with self.assertLogs("crawler.http_client", level="INFO") as log:
            data = http.get_json("http://example.com/api", params={"a": 1})

        self.assertTrue(data.get("ok"))
        self.assertTrue(any("요청 완료" in entry for entry in log.output))


class RawStorageTest(unittest.TestCase):
    def test_html와_에러를_파일로_저장한다(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            storage = RawStorage(base_dir=Path(tmp))
            html_path = storage.save_html("batch1", "123", "<html></html>")
            err_path = storage.save_error("batch1", "123", "missing", {"a": 1})

            self.assertTrue(html_path.exists())
            self.assertTrue(err_path.exists())
            self.assertIn("batch1", str(html_path))
            self.assertIn("123", html_path.name)
            self.assertIn("missing", err_path.read_text(encoding="utf-8"))


class RawStoreOnMissingTest(unittest.TestCase):
    def test_이미지없으면_raw_html을_저장한다(self) -> None:
        class DummyClient(HomeplusClient):
            def __init__(self):
                pass

            def fetch_detail_html(self, item_no):
                return "<html><body>no image</body></html>"

        class DummyRaw(RawStorage):
            def __init__(self):
                self.saved = False

            def save_html(self, batch_id, item_no, html):
                self.saved = True
                from pathlib import Path

                return Path("/tmp/dummy.html")

        cfg = AppConfig(
            crawl=CrawlConfig(fetch_detail=True, store_html=True),
            store=StoreConfig(),
            alert=AlertConfig(),
            s3=S3Config(),
        )
        service = HomeplusService(config=cfg, client=DummyClient(), raw_storage=DummyRaw())
        service.current_batch_id = "test_batch"
        items = [
            {
                "itemNo": "999",
                "itemNm": "테스트",
                "salePrice": 1000,
                "lcateNm": "쌀/잡곡",
                "mcateNm": "테스트",
            }
        ]

        service._map_items(items)
        self.assertTrue(service.raw_storage.saved)


if __name__ == "__main__":
    unittest.main()
