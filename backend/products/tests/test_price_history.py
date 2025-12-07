"""
가격 히스토리 모델 테스트

ProductPriceHistory 모델의 최적화된 가격 변동 기록 로직을 테스트합니다.

테스트 항목:
1. 가격 변동 시에만 히스토리 생성
2. is_current 플래그 관리
3. 변동폭/변동률 계산
4. 동시성 제어 (SELECT FOR UPDATE)
"""

from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.contrib.auth import get_user_model

from products.models import Product, ProductPriceHistory, Category
from sellers.models import Seller


User = get_user_model()


class ProductPriceHistoryModelTest(TestCase):
    """ProductPriceHistory 모델 기본 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 셋업"""
        # 테스트용 사용자 생성
        cls.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # 테스트용 판매자 생성
        cls.seller = Seller.objects.create(
            user=cls.user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
            status='active'
        )

        # 테스트용 카테고리 생성
        cls.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category'
        )

    def setUp(self):
        """각 테스트 전 상품 생성"""
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product-' + str(Product.objects.count()),
            price=10000,
            original_price=12000,
            status='active',
            product_type='main'
        )

    def test_초기_가격_히스토리_생성(self):
        """신규 상품의 초기 가격 히스토리 생성 테스트"""
        # 초기 가격 기록
        history, action = ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            new_original_price=12000,
            source='import'
        )

        # 검증
        self.assertIsNotNone(history)
        self.assertEqual(action, 'new')
        self.assertEqual(history.price, 10000)
        self.assertEqual(history.original_price, 12000)
        self.assertTrue(history.is_current)
        self.assertIsNone(history.previous_price)  # 첫 기록은 이전 가격 없음
        self.assertIsNone(history.price_change)
        self.assertEqual(history.source, 'import')

    def test_가격_변동_시_히스토리_생성(self):
        """가격 변동 시 새 히스토리 레코드 생성 테스트"""
        # 초기 가격 기록
        ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            source='import'
        )

        # 가격 변동 (10000 → 9000, 10% 할인)
        history, action = ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=9000,
            source='crawl'
        )

        # 검증
        self.assertIsNotNone(history)
        self.assertEqual(action, 'updated')
        self.assertEqual(history.price, 9000)
        self.assertEqual(history.previous_price, 10000)
        self.assertEqual(history.price_change, -1000)
        self.assertEqual(history.price_change_rate, Decimal('-10.00'))
        self.assertTrue(history.is_current)
        self.assertEqual(history.source, 'crawl')

        # 이전 레코드의 is_current가 False로 변경되었는지 확인
        old_history = ProductPriceHistory.objects.filter(
            product=self.product,
            price=10000
        ).first()
        self.assertFalse(old_history.is_current)

    def test_가격_변동_없으면_스킵(self):
        """가격 변동이 없으면 히스토리를 생성하지 않음"""
        # 초기 가격 기록
        ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            new_original_price=12000,
            source='import'
        )

        # 같은 가격으로 다시 기록 시도
        history, action = ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            new_original_price=12000,
            source='crawl'
        )

        # 검증
        self.assertIsNone(history)
        self.assertEqual(action, 'skipped')

        # 히스토리 레코드가 하나만 있어야 함
        count = ProductPriceHistory.objects.filter(product=self.product).count()
        self.assertEqual(count, 1)

    def test_가격_인상_기록(self):
        """가격 인상 시 양수 변동폭 기록"""
        # 초기 가격 기록
        ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            source='import'
        )

        # 가격 인상 (10000 → 11000, 10% 인상)
        history, action = ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=11000,
            source='crawl'
        )

        # 검증
        self.assertEqual(history.price_change, 1000)
        self.assertEqual(history.price_change_rate, Decimal('10.00'))

    def test_is_current_유일성(self):
        """상품당 is_current=True인 레코드는 하나만 존재"""
        # 여러 번 가격 변동
        prices = [10000, 9000, 9500, 8000, 8500]

        for price in prices:
            ProductPriceHistory.record_price_change(
                product=self.product,
                new_price=price,
                source='crawl'
            )

        # is_current=True인 레코드 개수 확인
        current_count = ProductPriceHistory.objects.filter(
            product=self.product,
            is_current=True
        ).count()

        self.assertEqual(current_count, 1)

        # 현재 가격이 마지막 가격인지 확인
        current = ProductPriceHistory.get_current_price(self.product)
        self.assertEqual(current.price, 8500)

    def test_가격_추이_조회(self):
        """가격 추이 조회 테스트"""
        # 여러 번 가격 변동
        prices = [10000, 9000, 9500, 8000]

        for price in prices:
            ProductPriceHistory.record_price_change(
                product=self.product,
                new_price=price,
                source='crawl'
            )

        # 가격 추이 조회
        trend = list(ProductPriceHistory.get_price_trend(self.product, days=30))

        # 검증
        self.assertEqual(len(trend), 4)

        # 가격 순서 확인 (시간순)
        retrieved_prices = [t['price'] for t in trend]
        self.assertEqual(retrieved_prices, prices)


class ProductPriceHistoryConcurrencyTest(TransactionTestCase):
    """ProductPriceHistory 동시성 테스트

    TransactionTestCase를 사용하여 실제 트랜잭션 환경에서 테스트합니다.
    """

    def setUp(self):
        """테스트 데이터 셋업"""
        self.user = User.objects.create_user(
            email='concurrent@example.com',
            username='concurrent_user',
            password='testpass123'
        )

        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='동시성 테스트 브랜드',
            brand_slug='concurrent-brand',
            status='active'
        )

        self.product = Product.objects.create(
            seller=self.seller,
            name='동시성 테스트 상품',
            slug='concurrent-test-product',
            price=10000,
            status='active',
            product_type='main'
        )

        # 초기 가격 기록
        ProductPriceHistory.record_price_change(
            product=self.product,
            new_price=10000,
            source='import'
        )

    def test_동시_가격_변경_시_하나만_성공(self):
        """동시에 가격 변경 시도 시 SELECT FOR UPDATE로 순차 처리"""
        import threading
        import time

        results = []
        errors = []

        def change_price(new_price):
            try:
                history, action = ProductPriceHistory.record_price_change(
                    product=self.product,
                    new_price=new_price,
                    source='crawl'
                )
                results.append({
                    'price': new_price,
                    'action': action,
                    'success': True
                })
            except Exception as e:
                errors.append({
                    'price': new_price,
                    'error': str(e)
                })

        # 두 스레드가 동시에 다른 가격으로 변경 시도
        t1 = threading.Thread(target=change_price, args=(9000,))
        t2 = threading.Thread(target=change_price, args=(8000,))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # 두 변경 모두 성공해야 함 (순차 처리)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 0)

        # 최종적으로 is_current=True인 레코드는 하나만 존재
        current_count = ProductPriceHistory.objects.filter(
            product=self.product,
            is_current=True
        ).count()
        self.assertEqual(current_count, 1)


class ProductPriceHistoryQueryTest(TestCase):
    """ProductPriceHistory 쿼리 최적화 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 셋업"""
        cls.user = User.objects.create_user(
            email='query@example.com',
            username='query_user',
            password='testpass123'
        )

        cls.seller = Seller.objects.create(
            user=cls.user,
            brand_name='쿼리 테스트 브랜드',
            brand_slug='query-brand',
            status='active'
        )

        # 여러 상품 생성
        cls.products = []
        for i in range(5):
            product = Product.objects.create(
                seller=cls.seller,
                name=f'쿼리 테스트 상품 {i}',
                slug=f'query-test-product-{i}',
                price=10000 + i * 1000,
                status='active',
                product_type='main'
            )
            cls.products.append(product)

            # 각 상품에 가격 히스토리 생성
            ProductPriceHistory.record_price_change(
                product=product,
                new_price=10000 + i * 1000,
                source='import'
            )

            # 가격 변동 추가
            ProductPriceHistory.record_price_change(
                product=product,
                new_price=9000 + i * 1000,
                source='crawl'
            )

    def test_현재_가격_일괄_조회(self):
        """여러 상품의 현재 가격을 효율적으로 조회"""
        # is_current=True 인덱스를 활용한 일괄 조회
        current_prices = ProductPriceHistory.objects.filter(
            product__in=self.products,
            is_current=True
        ).select_related('product')

        self.assertEqual(current_prices.count(), 5)

    def test_가격_인하_상품_조회(self):
        """최근 가격이 인하된 상품 조회"""
        discounted = ProductPriceHistory.objects.filter(
            is_current=True,
            price_change__lt=0
        ).select_related('product')

        # 모든 상품이 가격 인하됨 (10000→9000 등)
        self.assertEqual(discounted.count(), 5)

    def test_특정_변동률_이상_상품_조회(self):
        """특정 변동률 이상인 상품 조회"""
        # 5% 이상 할인된 상품
        significant_discounts = ProductPriceHistory.objects.filter(
            is_current=True,
            price_change_rate__lte=-5
        )

        self.assertTrue(significant_discounts.exists())
