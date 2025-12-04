"""
상품 모델 v2.1 TDD 테스트

신규 ERD(SelF_ERD_V2.1)에 맞는 테이블 구조 테스트입니다.
ERD V2.1: Product는 seller_id 필수, ProductPriceHistory 제거됨
"""

from django.test import TestCase
from django.db import IntegrityError
from decimal import Decimal
from authentication.models import User
from sellers.models import Seller


class ProductDetailsModelTest(TestCase):
    """product_details 테이블 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        from products.models import Product, Category

        # ERD V2.1: seller 필수
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testuser',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        # 카테고리 생성
        self.category = Category.objects.create(
            name="과일/견과",
            slug="fruit-nut"
        )

        # 상품 생성 (ERD V2.1: seller 필수)
        self.product = Product.objects.create(
            seller=self.seller,
            name="테스트 사과",
            slug="test-apple",
            price=10000,
            category=self.category,
            product_type='main',
            status='active',
        )

    def test_product_detail_creation(self):
        """product_details 1:1 관계 생성 테스트"""
        from products.models import ProductDetail

        detail = ProductDetail.objects.create(
            product=self.product,
            short_description="달콤한 사과입니다",
            full_description="청송에서 재배한 달콤한 사과입니다. 아삭한 식감이 일품입니다.",
            meta_title="달콤한 청송 사과 - 테스트 마트",
            meta_keywords="사과,청송,과일",
        )

        self.assertEqual(detail.product_id, self.product.id)
        self.assertEqual(detail.short_description, "달콤한 사과입니다")

    def test_product_detail_one_to_one(self):
        """product_details 1:1 제약 조건 테스트"""
        from products.models import ProductDetail

        ProductDetail.objects.create(product=self.product)

        # 동일 상품에 대해 중복 생성 시도 시 오류 발생
        with self.assertRaises(IntegrityError):
            ProductDetail.objects.create(product=self.product)

    def test_product_reverse_relation(self):
        """Product에서 detail 역참조 테스트"""
        from products.models import ProductDetail

        detail = ProductDetail.objects.create(
            product=self.product,
            short_description="테스트 설명",
        )

        # Product.detail로 접근 가능
        self.assertEqual(self.product.detail.short_description, "테스트 설명")


class ProductInventoryModelTest(TestCase):
    """product_inventories 테이블 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        from products.models import Product, Category

        # ERD V2.1: seller 필수
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testuser',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        self.category = Category.objects.create(
            name="채소",
            slug="vegetable"
        )

        self.product = Product.objects.create(
            seller=self.seller,
            name="테스트 당근",
            slug="test-carrot",
            price=5000,
            category=self.category,
            product_type='seller',
            status='active',
        )

    def test_inventory_creation(self):
        """product_inventories 생성 테스트"""
        from products.models import ProductInventory

        inventory = ProductInventory.objects.create(
            product=self.product,
            stock_quantity=100,
            safe_stock_level=20,
        )

        self.assertEqual(inventory.product_id, self.product.id)
        self.assertEqual(inventory.stock_quantity, 100)
        self.assertEqual(inventory.safe_stock_level, 20)

    def test_inventory_default_values(self):
        """product_inventories 기본값 테스트"""
        from products.models import ProductInventory

        inventory = ProductInventory.objects.create(product=self.product)

        self.assertEqual(inventory.stock_quantity, 0)
        self.assertEqual(inventory.safe_stock_level, 10)

    def test_inventory_one_to_one(self):
        """product_inventories 1:1 제약 조건 테스트"""
        from products.models import ProductInventory

        ProductInventory.objects.create(product=self.product)

        with self.assertRaises(IntegrityError):
            ProductInventory.objects.create(product=self.product)

    def test_is_low_stock_property(self):
        """재고 부족 여부 프로퍼티 테스트"""
        from products.models import ProductInventory

        inventory = ProductInventory.objects.create(
            product=self.product,
            stock_quantity=5,
            safe_stock_level=10,
        )

        self.assertTrue(inventory.is_low_stock)

        inventory.stock_quantity = 15
        inventory.save()

        self.assertFalse(inventory.is_low_stock)


class ProductStatsModelTest(TestCase):
    """product_stats 테이블 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        from products.models import Product, Category

        # ERD V2.1: seller 필수
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testuser',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        self.category = Category.objects.create(
            name="수산물",
            slug="seafood"
        )

        self.product = Product.objects.create(
            seller=self.seller,
            name="테스트 연어",
            slug="test-salmon",
            price=30000,
            category=self.category,
        )

    def test_stats_creation(self):
        """product_stats 생성 테스트"""
        from products.models import ProductStats

        stats = ProductStats.objects.create(
            product=self.product,
            view_count=1000,
            cart_event_count=50,
            order_event_count=20,
            wishlist_count=30,
            review_count=10,
            average_rating=Decimal('4.50'),
        )

        self.assertEqual(stats.product_id, self.product.id)
        self.assertEqual(stats.view_count, 1000)
        self.assertEqual(stats.average_rating, Decimal('4.50'))

    def test_stats_default_values(self):
        """product_stats 기본값 테스트"""
        from products.models import ProductStats

        stats = ProductStats.objects.create(product=self.product)

        self.assertEqual(stats.view_count, 0)
        self.assertEqual(stats.cart_event_count, 0)
        self.assertEqual(stats.order_event_count, 0)
        self.assertEqual(stats.wishlist_count, 0)
        self.assertEqual(stats.review_count, 0)
        self.assertEqual(stats.average_rating, Decimal('0.00'))
        self.assertEqual(stats.quality_score, Decimal('50.00'))

    def test_stats_one_to_one(self):
        """product_stats 1:1 제약 조건 테스트"""
        from products.models import ProductStats

        ProductStats.objects.create(product=self.product)

        with self.assertRaises(IntegrityError):
            ProductStats.objects.create(product=self.product)

    def test_product_stats_reverse_relation(self):
        """Product에서 stats 역참조 테스트"""
        from products.models import ProductStats

        stats = ProductStats.objects.create(
            product=self.product,
            view_count=500,
        )

        self.assertEqual(self.product.stats.view_count, 500)


class ProductPriceHistoryModelTest(TestCase):
    """product_price_histories 테이블 테스트

    상품 가격 변동 이력을 누적 기록하여 가격 추이를 추적합니다.
    예: 1번 상품이 1000원 → 900원 → 1100원으로 변경된 이력 저장
    """

    def setUp(self):
        """테스트 데이터 준비"""
        from products.models import Product, Category

        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testuser',
            password='testpass123'
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        self.category = Category.objects.create(
            name="과일/견과",
            slug="fruit-nut"
        )

        self.product = Product.objects.create(
            seller=self.seller,
            name="테스트 사과",
            slug="test-apple",
            price=10000,
            category=self.category,
        )

    def test_price_history_creation(self):
        """가격 이력 생성 테스트"""
        from products.models import ProductPriceHistory

        history = ProductPriceHistory.objects.create(
            product=self.product,
            price=10000,
            source='import',
        )

        self.assertEqual(history.product_id, self.product.id)
        self.assertEqual(history.price, 10000)
        self.assertEqual(history.source, 'import')
        self.assertIsNotNone(history.recorded_at)

    def test_price_history_multiple_records(self):
        """가격 이력 다중 레코드 (누적) 테스트

        같은 상품에 대해 여러 가격 이력 기록 가능.
        1000원 → 900원 → 1100원 순서로 기록.
        """
        from products.models import ProductPriceHistory
        import time

        # 초기 가격
        ProductPriceHistory.objects.create(
            product=self.product,
            price=10000,
            source='import',
        )

        time.sleep(0.01)  # recorded_at 순서 보장

        # 가격 인하
        ProductPriceHistory.objects.create(
            product=self.product,
            price=9000,
            source='crawl',
        )

        time.sleep(0.01)

        # 가격 인상
        ProductPriceHistory.objects.create(
            product=self.product,
            price=11000,
            source='manual',
        )

        # 3개의 이력 레코드가 있어야 함
        histories = self.product.price_histories.order_by('recorded_at')
        self.assertEqual(histories.count(), 3)

        # 시간순으로 가격 변화 확인
        prices = list(histories.values_list('price', flat=True))
        self.assertEqual(prices, [10000, 9000, 11000])

    def test_price_history_with_original_price(self):
        """원가(할인 전 가격) 포함 이력 테스트"""
        from products.models import ProductPriceHistory

        history = ProductPriceHistory.objects.create(
            product=self.product,
            price=8000,
            original_price=10000,
            source='crawl',
        )

        self.assertEqual(history.price, 8000)
        self.assertEqual(history.original_price, 10000)

    def test_price_history_reverse_relation(self):
        """Product에서 price_histories 역참조 테스트"""
        from products.models import ProductPriceHistory

        ProductPriceHistory.objects.create(
            product=self.product,
            price=10000,
            source='import',
        )
        ProductPriceHistory.objects.create(
            product=self.product,
            price=9000,
            source='crawl',
        )

        # 상품에서 가격 이력 조회
        self.assertEqual(self.product.price_histories.count(), 2)

    def test_price_history_ordering(self):
        """가격 이력 기본 정렬 테스트 (최신순)"""
        from products.models import ProductPriceHistory
        import time

        h1 = ProductPriceHistory.objects.create(
            product=self.product,
            price=10000,
            source='import',
        )
        time.sleep(0.01)
        h2 = ProductPriceHistory.objects.create(
            product=self.product,
            price=9000,
            source='crawl',
        )

        # ordering = ['product', '-recorded_at'] 확인
        histories = list(self.product.price_histories.all())
        # 최신 기록이 먼저
        self.assertEqual(histories[0].price, 9000)
        self.assertEqual(histories[1].price, 10000)
