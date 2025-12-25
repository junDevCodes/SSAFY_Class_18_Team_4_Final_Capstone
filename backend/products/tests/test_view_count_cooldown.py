"""
조회수 쿨타임 테스트

ViewCountService의 쿨타임 로직을 검증합니다.
- 2분 쿨타임 적용 확인
- 회원/비회원 구분 처리
- 쿨타임 만료 후 조회수 증가
"""
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth import get_user_model

from products.models import (
    Product, ProductStats, ProductViewLog, UserProductStats,
    Category
)
from products.services.view_count import ViewCountService, VIEW_COUNT_COOLDOWN_SECONDS
from sellers.models import Seller

User = get_user_model()


class ViewCountServiceTestCase(TestCase):
    """ViewCountService 단위 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 생성"""
        # 판매자 생성
        cls.seller_user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            username='testseller',
        )
        cls.seller = Seller.objects.create(
            user=cls.seller_user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
        )

        # 카테고리 생성
        cls.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category',
        )

        # 상품 생성
        cls.product = Product.objects.create(
            seller=cls.seller,
            category=cls.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
        )

        # 상품 통계 생성
        cls.product_stats = ProductStats.objects.create(
            product=cls.product,
            view_count=0,
        )

        # 테스트 사용자 생성
        cls.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            username='testuser',
        )

    def setUp(self):
        """각 테스트 전 초기화"""
        self.factory = RequestFactory()
        # 조회수 초기화
        ProductStats.objects.filter(product=self.product).update(view_count=0)
        # 조회 로그 삭제
        ProductViewLog.objects.all().delete()
        # 사용자별 통계 삭제
        UserProductStats.objects.all().delete()

    def _create_request(self, user=None, ip='127.0.0.1', user_agent='TestBrowser/1.0'):
        """테스트용 요청 객체 생성"""
        request = self.factory.get('/api/products/1/')
        request.META['REMOTE_ADDR'] = ip
        request.META['HTTP_USER_AGENT'] = user_agent
        if user:
            request.user = user
        else:
            request.user = Mock()
            request.user.is_authenticated = False
        return request

    # ==================== 회원 조회수 테스트 ====================

    def test_회원_첫_조회_시_조회수_증가(self):
        """회원이 처음 상품을 조회하면 조회수가 증가해야 함"""
        request = self._create_request(user=self.user)

        incremented, msg = ViewCountService.increment_view_count(request, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수 증가 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)

        # 조회 로그 확인
        self.assertEqual(ProductViewLog.objects.filter(user=self.user).count(), 1)

        # 사용자별 통계 확인
        user_stats = UserProductStats.objects.get(user=self.user, product=self.product)
        self.assertEqual(user_stats.view_count, 1)

    def test_회원_쿨타임_내_재조회_시_조회수_미증가(self):
        """회원이 쿨타임 내에 재조회하면 조회수가 증가하지 않아야 함"""
        request = self._create_request(user=self.user)

        # 첫 번째 조회
        ViewCountService.increment_view_count(request, self.product)

        # 두 번째 조회 (쿨타임 내)
        incremented, msg = ViewCountService.increment_view_count(request, self.product)

        self.assertFalse(incremented)
        self.assertEqual(msg, "cooldown")

        # 조회수가 1회만 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)

    def test_회원_쿨타임_만료_후_재조회_시_조회수_증가(self):
        """회원이 쿨타임 만료 후 재조회하면 조회수가 증가해야 함"""
        request = self._create_request(user=self.user)

        # 첫 번째 조회
        ViewCountService.increment_view_count(request, self.product)

        # 조회 로그의 시간을 과거로 변경 (쿨타임 만료 시뮬레이션)
        old_time = timezone.now() - timedelta(seconds=VIEW_COUNT_COOLDOWN_SECONDS + 10)
        ProductViewLog.objects.filter(user=self.user).update(viewed_at=old_time)

        # 두 번째 조회 (쿨타임 만료 후)
        incremented, msg = ViewCountService.increment_view_count(request, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수가 2회 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 2)

    # ==================== 비회원 조회수 테스트 ====================

    def test_비회원_첫_조회_시_조회수_증가(self):
        """비회원이 처음 상품을 조회하면 조회수가 증가해야 함"""
        request = self._create_request(ip='192.168.1.100', user_agent='Chrome/100')

        incremented, msg = ViewCountService.increment_view_count(request, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수 증가 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)

        # 조회 로그 확인 (visitor_hash가 있어야 함)
        log = ProductViewLog.objects.first()
        self.assertIsNone(log.user)
        self.assertIsNotNone(log.visitor_hash)

    def test_비회원_쿨타임_내_재조회_시_조회수_미증가(self):
        """비회원이 쿨타임 내에 재조회하면 조회수가 증가하지 않아야 함"""
        request = self._create_request(ip='192.168.1.100', user_agent='Chrome/100')

        # 첫 번째 조회
        ViewCountService.increment_view_count(request, self.product)

        # 두 번째 조회 (쿨타임 내, 같은 IP와 User-Agent)
        incremented, msg = ViewCountService.increment_view_count(request, self.product)

        self.assertFalse(incremented)
        self.assertEqual(msg, "cooldown")

        # 조회수가 1회만 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)

    def test_비회원_다른_IP에서_조회_시_조회수_증가(self):
        """비회원이 다른 IP에서 조회하면 조회수가 증가해야 함"""
        request1 = self._create_request(ip='192.168.1.100', user_agent='Chrome/100')
        request2 = self._create_request(ip='192.168.1.101', user_agent='Chrome/100')

        # 첫 번째 IP에서 조회
        ViewCountService.increment_view_count(request1, self.product)

        # 두 번째 IP에서 조회
        incremented, msg = ViewCountService.increment_view_count(request2, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수가 2회 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 2)

    def test_비회원_다른_UserAgent에서_조회_시_조회수_증가(self):
        """비회원이 다른 User-Agent로 조회하면 조회수가 증가해야 함"""
        request1 = self._create_request(ip='192.168.1.100', user_agent='Chrome/100')
        request2 = self._create_request(ip='192.168.1.100', user_agent='Firefox/90')

        # 첫 번째 브라우저에서 조회
        ViewCountService.increment_view_count(request1, self.product)

        # 두 번째 브라우저에서 조회
        incremented, msg = ViewCountService.increment_view_count(request2, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수가 2회 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 2)

    # ==================== 회원/비회원 혼합 테스트 ====================

    def test_회원과_비회원_별도_쿨타임_적용(self):
        """회원과 비회원은 각각 별도로 쿨타임이 적용되어야 함"""
        guest_request = self._create_request(ip='192.168.1.100')
        member_request = self._create_request(user=self.user)

        # 비회원 조회
        ViewCountService.increment_view_count(guest_request, self.product)

        # 회원 조회 (비회원 쿨타임과 무관하게 증가해야 함)
        incremented, msg = ViewCountService.increment_view_count(member_request, self.product)

        self.assertTrue(incremented)
        self.assertEqual(msg, "success")

        # 조회수가 2회 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 2)

    # ==================== 유틸리티 메서드 테스트 ====================

    def test_visitor_hash_생성(self):
        """visitor_hash가 일관되게 생성되어야 함"""
        hash1 = ViewCountService.generate_visitor_hash('192.168.1.1', 'Chrome/100')
        hash2 = ViewCountService.generate_visitor_hash('192.168.1.1', 'Chrome/100')
        hash3 = ViewCountService.generate_visitor_hash('192.168.1.2', 'Chrome/100')

        # 같은 입력 → 같은 해시
        self.assertEqual(hash1, hash2)
        # 다른 입력 → 다른 해시
        self.assertNotEqual(hash1, hash3)
        # 해시 길이 확인 (SHA256 = 64자)
        self.assertEqual(len(hash1), 64)

    def test_X_Forwarded_For_헤더_IP_추출(self):
        """X-Forwarded-For 헤더에서 클라이언트 IP를 추출해야 함"""
        request = self.factory.get('/api/products/1/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.195, 70.41.3.18, 150.172.238.178'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = ViewCountService.get_client_ip(request)

        # 첫 번째 IP (실제 클라이언트)를 추출해야 함
        self.assertEqual(ip, '203.0.113.195')

    # ==================== 로그 정리 테스트 ====================

    def test_오래된_로그_정리(self):
        """오래된 조회 로그가 정리되어야 함"""
        request = self._create_request(user=self.user)
        ViewCountService.increment_view_count(request, self.product)

        # 로그의 시간을 2일 전으로 변경
        old_time = timezone.now() - timedelta(days=2)
        ProductViewLog.objects.all().update(viewed_at=old_time)

        # 1일 이상 된 로그 정리
        deleted_count = ViewCountService.cleanup_old_logs(days=1)

        self.assertEqual(deleted_count, 1)
        self.assertEqual(ProductViewLog.objects.count(), 0)


class ViewCountAPITestCase(TestCase):
    """ProductDetailView 조회수 API 통합 테스트"""

    @classmethod
    def setUpTestData(cls):
        """테스트 데이터 생성"""
        cls.seller_user = User.objects.create_user(
            email='seller@test.com',
            password='testpass123',
            username='testseller',
        )
        cls.seller = Seller.objects.create(
            user=cls.seller_user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
        )
        cls.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category',
        )
        cls.product = Product.objects.create(
            seller=cls.seller,
            category=cls.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
        )
        cls.product_stats = ProductStats.objects.create(
            product=cls.product,
            view_count=0,
        )
        cls.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            username='testuser',
        )

    def setUp(self):
        """각 테스트 전 초기화"""
        ProductStats.objects.filter(product=self.product).update(view_count=0)
        ProductViewLog.objects.all().delete()

    def test_상품_상세_조회_시_조회수_증가(self):
        """상품 상세 API 호출 시 조회수가 증가해야 함"""
        from django.test import Client
        client = Client()

        response = client.get(f'/api/products/{self.product.id}/')

        self.assertEqual(response.status_code, 200)

        # 조회수 증가 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)

    def test_상품_상세_연속_조회_시_쿨타임_적용(self):
        """상품 상세 API 연속 호출 시 쿨타임이 적용되어야 함"""
        from django.test import Client
        client = Client()

        # 첫 번째 조회
        client.get(f'/api/products/{self.product.id}/')

        # 두 번째 조회 (쿨타임 내)
        client.get(f'/api/products/{self.product.id}/')

        # 조회수가 1회만 증가했는지 확인
        self.product_stats.refresh_from_db()
        self.assertEqual(self.product_stats.view_count, 1)
