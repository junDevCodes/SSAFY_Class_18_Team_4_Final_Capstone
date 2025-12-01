"""
제품 Serializer 테스트
"""
from django.test import TestCase
from products.models import Category, Product
from products.serializers import CategorySerializer, ProductSerializer


class CategorySerializerTest(TestCase):
    """카테고리 Serializer 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.category = Category.objects.create(
            name='과일/견과',
            slug='fruit-nuts'
        )

    def test_category_serialization(self):
        """카테고리가 올바르게 직렬화되는지 테스트"""
        serializer = CategorySerializer(self.category)
        data = serializer.data

        self.assertEqual(data['id'], self.category.id)
        self.assertEqual(data['name'], '과일/견과')
        self.assertEqual(data['slug'], 'fruit-nuts')
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_category_deserialization(self):
        """카테고리가 올바르게 역직렬화되는지 테스트"""
        data = {
            'name': '채소',
            'slug': 'vegetables'
        }
        serializer = CategorySerializer(data=data)

        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertEqual(category.name, '채소')
        self.assertEqual(category.slug, 'vegetables')


class ProductSerializerTest(TestCase):
    """제품 Serializer 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.category = Category.objects.create(
            name='과일/견과',
            slug='fruit-nuts'
        )
        self.product = Product.objects.create(
            category=self.category,
            site_name='네이버쇼핑_컬리N마트',
            name='냉동 칠레산 블루베리 1kg',
            price=9990,
            unit='',
            description='냉동 칠레산 블루베리 1kg',
            product_url='https://example.com/product',
            image_url='https://example.com/image.jpg',
            detail_info='',
            original_price=12000,
            discount=17,
            is_best=True
        )

    def test_product_serialization(self):
        """제품이 올바르게 직렬화되는지 테스트"""
        serializer = ProductSerializer(self.product)
        data = serializer.data

        self.assertEqual(data['id'], self.product.id)
        self.assertEqual(data['name'], '냉동 칠레산 블루베리 1kg')
        self.assertEqual(data['price'], 9990)
        self.assertEqual(data['original_price'], 12000)
        self.assertEqual(data['discount'], 17)
        self.assertEqual(data['is_best'], True)
        self.assertEqual(data['image_url'], 'https://example.com/image.jpg')
        self.assertEqual(data['description'], '냉동 칠레산 블루베리 1kg')

        # 카테고리 정보 확인
        self.assertIn('category', data)
        self.assertEqual(data['category']['id'], self.category.id)
        self.assertEqual(data['category']['name'], '과일/견과')

    def test_product_serialization_without_category(self):
        """카테고리 없는 제품도 올바르게 직렬화되는지 테스트"""
        product = Product.objects.create(
            name='테스트 제품',
            price=5000,
            image_url='https://example.com/test.jpg'
        )
        serializer = ProductSerializer(product)
        data = serializer.data

        self.assertIsNone(data['category'])

    def test_product_list_serialization(self):
        """제품 목록이 올바르게 직렬화되는지 테스트"""
        # 추가 제품 생성
        Product.objects.create(
            category=self.category,
            name='테스트 제품 2',
            price=15000,
            image_url='https://example.com/test2.jpg'
        )

        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)

        self.assertEqual(len(serializer.data), 2)
        # 제품 이름 목록 확인 (순서 무관)
        product_names = [p['name'] for p in serializer.data]
        self.assertIn('냉동 칠레산 블루베리 1kg', product_names)
        self.assertIn('테스트 제품 2', product_names)

    def test_product_deserialization(self):
        """제품이 올바르게 역직렬화되는지 테스트"""
        data = {
            'category_id': self.category.id,
            'name': '신규 제품',
            'price': 8000,
            'image_url': 'https://example.com/new.jpg',
            'description': '신규 제품 설명',
            'original_price': 10000,
            'discount': 20,
            'is_best': False
        }
        serializer = ProductSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        self.assertEqual(product.name, '신규 제품')
        self.assertEqual(product.price, 8000)
        self.assertEqual(product.category, self.category)
