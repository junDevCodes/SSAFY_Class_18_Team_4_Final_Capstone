"""
최근 본 상품 API 테스트 (REC-005)

TDD 기반 테스트:
- 비로그인 사용자 → 401 반환
- 빈 목록 → [] 반환
- 최신순 정렬 확인
- limit 파라미터 동작 확인
"""
import time
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from sellers.models import Seller
from products.models import Category, Product, UserProductStats, ProductViewLog
from products.services.view_count import VIEW_COUNT_COOLDOWN_SECONDS


class RecentViewedProductsAPITest(TestCase):
    """최근 본 상품 API 테스트 (REC-005)"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.client = APIClient()

        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # 판매자 생성 (Product에 seller 필수)
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        # 카테고리 생성
        self.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category'
        )

        # 테스트 상품 생성
        self.products = []
        for i in range(5):
            product = Product.objects.create(
                seller=self.seller,
                category=self.category,
                name=f'테스트 상품 {i}',
                slug=f'test-product-{i}',
                price=10000 * (i + 1),
                status='active'
            )
            self.products.append(product)

        self.url = '/api/recommendations/recent/'

    def test_비로그인_사용자_401_반환(self):
        """비로그인 사용자는 401 에러 반환"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_최근_본_상품_없을_때_빈_목록_반환(self):
        """최근 본 상품이 없으면 빈 목록 반환"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['products'], [])

    def test_최근_본_상품_목록_반환(self):
        """조회 기록이 있으면 상품 목록 반환"""
        self.client.force_authenticate(user=self.user)

        # 상품 조회 기록 생성
        UserProductStats.objects.create(
            user=self.user,
            product=self.products[0],
            view_count=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 1)
        self.assertEqual(response.data['products'][0]['name'], '테스트 상품 0')

    def test_최근_본_상품_최신순_정렬(self):
        """최근 본 상품은 마지막 조회 시간 기준 내림차순 정렬"""
        self.client.force_authenticate(user=self.user)

        # 상품 조회 기록 생성 (순서대로 - 마지막에 생성된 것이 가장 최근)
        base_time = timezone.now()
        for i, product in enumerate(self.products):
            stats = UserProductStats.objects.create(
                user=self.user,
                product=product,
                view_count=1
            )
            # last_interacted_at을 명시적으로 설정 (auto_now 우회)
            UserProductStats.objects.filter(pk=stats.pk).update(
                last_interacted_at=base_time + timezone.timedelta(seconds=i)
            )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = response.data['products']

        # 마지막에 조회한 상품(products[4])이 첫 번째로 나와야 함
        self.assertEqual(len(products), 5)
        self.assertEqual(products[0]['name'], '테스트 상품 4')
        self.assertEqual(products[4]['name'], '테스트 상품 0')

    def test_limit_파라미터_동작(self):
        """limit 파라미터로 조회 개수 제한"""
        self.client.force_authenticate(user=self.user)

        # 5개 상품 조회 기록 생성
        for product in self.products:
            UserProductStats.objects.create(
                user=self.user,
                product=product,
                view_count=1
            )

        response = self.client.get(f'{self.url}?limit=3')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 3)

    def test_기본_limit_10(self):
        """limit 미지정 시 기본값 10"""
        self.client.force_authenticate(user=self.user)

        # 15개 상품 생성 및 조회 기록
        for i in range(15):
            product = Product.objects.create(
                seller=self.seller,
                category=self.category,
                name=f'추가 상품 {i}',
                slug=f'additional-product-{i}',
                price=1000,
                status='active'
            )
            UserProductStats.objects.create(
                user=self.user,
                product=product,
                view_count=1
            )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 10)

    def test_view_count_0인_상품_제외(self):
        """view_count가 0인 상품은 제외 (장바구니만 추가한 경우 등)"""
        self.client.force_authenticate(user=self.user)

        # view_count=0인 기록 (장바구니만 추가)
        UserProductStats.objects.create(
            user=self.user,
            product=self.products[0],
            view_count=0,
            cart_event_count=1
        )

        # view_count=1인 기록 (실제 조회)
        UserProductStats.objects.create(
            user=self.user,
            product=self.products[1],
            view_count=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 1)
        self.assertEqual(response.data['products'][0]['name'], '테스트 상품 1')

    def test_다른_사용자_기록_제외(self):
        """다른 사용자의 조회 기록은 제외"""
        # 다른 사용자 생성
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )

        # 다른 사용자의 조회 기록
        UserProductStats.objects.create(
            user=other_user,
            product=self.products[0],
            view_count=1
        )

        # 현재 사용자 로그인
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['products']), 0)

    def test_응답_형식_ProductListDTO(self):
        """응답이 ProductListDTO 형식인지 확인"""
        self.client.force_authenticate(user=self.user)

        UserProductStats.objects.create(
            user=self.user,
            product=self.products[0],
            view_count=1
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        product = response.data['products'][0]

        # ProductListSerializerV2 필드 확인
        expected_fields = [
            'id', 'slug', 'name', 'price', 'original_price',
            'main_image', 'category', 'category_name', 'status'
        ]
        for field in expected_fields:
            self.assertIn(field, product, f"'{field}' 필드가 응답에 없습니다")


class ProductDetailViewUserStatsTest(TestCase):
    """상품 상세 조회 시 사용자별 통계 기록 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 판매자',
            brand_slug='test-seller'
        )

        self.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category'
        )

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
            status='active'
        )

    def test_로그인_사용자_상품_조회시_UserProductStats_생성(self):
        """로그인 사용자가 상품을 조회하면 UserProductStats 레코드가 생성된다"""
        self.client.force_authenticate(user=self.user)

        # 상품 상세 조회
        url = reverse('product-detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # UserProductStats 확인
        stats = UserProductStats.objects.filter(
            user=self.user,
            product=self.product
        ).first()

        self.assertIsNotNone(stats)
        self.assertEqual(stats.view_count, 1)

    def test_로그인_사용자_반복_조회시_쿨타임_만료후_view_count_증가(self):
        """로그인 사용자가 쿨타임 만료 후 재조회하면 view_count가 증가한다"""
        self.client.force_authenticate(user=self.user)

        url = reverse('product-detail', kwargs={'pk': self.product.pk})

        # 첫 번째 조회
        self.client.get(url)

        stats = UserProductStats.objects.get(
            user=self.user,
            product=self.product
        )
        self.assertEqual(stats.view_count, 1)

        # 쿨타임 만료 시뮬레이션 (조회 로그의 시간을 과거로 변경)
        old_time = timezone.now() - timedelta(seconds=VIEW_COUNT_COOLDOWN_SECONDS + 10)
        ProductViewLog.objects.filter(user=self.user, product=self.product).update(viewed_at=old_time)

        # 두 번째 조회 (쿨타임 만료 후)
        self.client.get(url)

        stats.refresh_from_db()
        self.assertEqual(stats.view_count, 2)

        # 쿨타임 만료 시뮬레이션
        ProductViewLog.objects.filter(user=self.user, product=self.product).update(viewed_at=old_time)

        # 세 번째 조회
        self.client.get(url)

        stats.refresh_from_db()
        self.assertEqual(stats.view_count, 3)

    def test_비로그인_사용자_조회시_UserProductStats_미생성(self):
        """비로그인 사용자가 상품을 조회해도 UserProductStats는 생성되지 않는다"""
        url = reverse('product-detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # UserProductStats 없어야 함
        stats_count = UserProductStats.objects.filter(
            product=self.product
        ).count()

        self.assertEqual(stats_count, 0)

    def test_조회시_last_interacted_at_갱신(self):
        """쿨타임 만료 후 재조회 시 last_interacted_at이 갱신된다"""
        self.client.force_authenticate(user=self.user)

        url = reverse('product-detail', kwargs={'pk': self.product.pk})

        # 첫 번째 조회
        self.client.get(url)
        stats1 = UserProductStats.objects.get(
            user=self.user,
            product=self.product
        )
        first_time = stats1.last_interacted_at

        # 쿨타임 만료 시뮬레이션 (조회 로그의 시간을 과거로 변경)
        old_time = timezone.now() - timedelta(seconds=VIEW_COUNT_COOLDOWN_SECONDS + 10)
        ProductViewLog.objects.filter(user=self.user, product=self.product).update(viewed_at=old_time)

        # 두 번째 조회 (쿨타임 만료 후)
        self.client.get(url)

        stats2 = UserProductStats.objects.get(
            user=self.user,
            product=self.product
        )

        # last_interacted_at이 갱신되어야 함
        self.assertGreater(stats2.last_interacted_at, first_time)
