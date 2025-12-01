"""
제품 API 뷰 테스트
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Category, Product


class ProductAPITest(TestCase):
    """제품 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()

        # 카테고리 생성
        self.category1 = Category.objects.create(name='과일/견과', slug='fruit-nuts')
        self.category2 = Category.objects.create(name='채소', slug='vegetables')

        # 제품 생성
        self.product1 = Product.objects.create(
            category=self.category1,
            name='냉동 칠레산 블루베리 1kg',
            price=9990,
            description='맛있는 블루베리',
            image_url='https://example.com/image1.jpg',
            original_price=12000,
            discount=17,
            is_best=True
        )
        self.product2 = Product.objects.create(
            category=self.category1,
            name='사과 1kg',
            price=5000,
            description='신선한 사과',
            image_url='https://example.com/image2.jpg',
            is_best=False
        )
        self.product3 = Product.objects.create(
            category=self.category2,
            name='유기농 상추',
            price=3000,
            description='유기농 상추',
            image_url='https://example.com/image3.jpg',
            is_best=True
        )

    def test_get_product_list(self):
        """제품 목록 조회 테스트"""
        url = reverse('product-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_get_product_detail(self):
        """제품 상세 조회 테스트"""
        url = reverse('product-detail', kwargs={'pk': self.product1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '냉동 칠레산 블루베리 1kg')
        self.assertEqual(response.data['price'], 9990)
        self.assertEqual(response.data['category']['name'], '과일/견과')

    def test_filter_products_by_category(self):
        """카테고리별 제품 필터링 테스트"""
        url = reverse('product-list')
        response = self.client.get(url, {'category': self.category1.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # 모든 제품이 과일/견과 카테고리여야 함
        for product in response.data['results']:
            self.assertEqual(product['category']['id'], self.category1.id)

    def test_filter_best_products(self):
        """베스트 제품 필터링 테스트"""
        url = reverse('product-list')
        response = self.client.get(url, {'is_best': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # 모든 제품이 베스트여야 함
        for product in response.data['results']:
            self.assertTrue(product['is_best'])

    def test_search_products_by_name(self):
        """제품명으로 검색 테스트"""
        url = reverse('product-list')
        response = self.client.get(url, {'search': '블루베리'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], '냉동 칠레산 블루베리 1kg')

    def test_search_products_case_insensitive(self):
        """대소문자 구분 없이 검색 테스트"""
        url = reverse('product-list')
        response = self.client.get(url, {'search': '사과'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_pagination(self):
        """페이지네이션 테스트"""
        # 추가 제품 생성 (총 20개)
        for i in range(17):
            Product.objects.create(
                category=self.category1,
                name=f'테스트 제품 {i}',
                price=1000 * (i + 1),
                image_url=f'https://example.com/test{i}.jpg'
            )

        url = reverse('product-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 기본 페이지 크기는 20개
        self.assertLessEqual(len(response.data['results']), 20)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 20)


class CategoryAPITest(TestCase):
    """카테고리 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()
        self.category1 = Category.objects.create(name='과일/견과', slug='fruit-nuts')
        self.category2 = Category.objects.create(name='채소', slug='vegetables')

    def test_get_category_list(self):
        """카테고리 목록 조회 테스트"""
        url = reverse('category-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_category_detail(self):
        """카테고리 상세 조회 테스트"""
        url = reverse('category-detail', kwargs={'pk': self.category1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '과일/견과')
        self.assertEqual(response.data['slug'], 'fruit-nuts')
