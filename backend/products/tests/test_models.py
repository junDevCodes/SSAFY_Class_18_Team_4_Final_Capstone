"""
제품 관련 테스트 (ERD V2.1)
"""
from django.test import TestCase
from products.models import Category, Product
from authentication.models import User
from sellers.models import Seller


class CategoryModelTest(TestCase):
    """카테고리 모델 테스트"""

    def test_category_creation(self):
        """카테고리가 정상적으로 생성되는지 테스트"""
        category = Category.objects.create(
            name="과일/견과",
            slug="fruits-nuts"
        )
        self.assertEqual(category.name, "과일/견과")
        self.assertEqual(category.slug, "fruits-nuts")
        self.assertEqual(str(category), "과일/견과")

    def test_category_unique_slug(self):
        """카테고리 slug가 중복되지 않는지 테스트"""
        Category.objects.create(name="과일/견과", slug="fruits-nuts")

        # 동일한 slug로 생성 시 에러 발생
        with self.assertRaises(Exception):
            Category.objects.create(name="과일/견과2", slug="fruits-nuts")


class ProductModelTest(TestCase):
    """제품 모델 테스트 (ERD V2.1)"""

    def setUp(self):
        """테스트용 카테고리, 유저, 셀러 생성"""
        self.category = Category.objects.create(
            name="과일/견과",
            slug="fruits-nuts"
        )
        # ERD V2.1: Product는 seller_id 필수
        self.user = User.objects.create_user(
            email="seller@test.com",
            username="testuser",
            password="testpass123"
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name="테스트 판매자",
            brand_slug="test-seller"
        )

    def test_product_creation(self):
        """제품이 정상적으로 생성되는지 테스트 (ERD V2.1)"""
        product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="냉동 칠레산 블루베리 1kg",
            slug="frozen-blueberry-1kg",
            price=9990,
        )
        self.assertEqual(product.name, "냉동 칠레산 블루베리 1kg")
        self.assertEqual(product.price, 9990)
        self.assertEqual(product.category.name, "과일/견과")
        self.assertEqual(product.seller.brand_name, "테스트 판매자")
        self.assertEqual(str(product), "냉동 칠레산 블루베리 1kg")

    def test_product_without_category(self):
        """카테고리 없이도 제품 생성 가능한지 테스트"""
        product = Product.objects.create(
            seller=self.seller,
            name="테스트 상품",
            slug="test-product",
            price=5000,
        )
        self.assertIsNone(product.category)
        self.assertEqual(product.price, 5000)

    def test_product_positive_price_constraint(self):
        """음수 가격이 저장되지 않는지 테스트"""
        # 음수 가격으로 제품 생성 시도
        with self.assertRaises(Exception):
            product = Product.objects.create(
                seller=self.seller,
                name="잘못된 상품",
                slug="invalid-product",
                price=-1000,
            )
            # 제약조건 확인을 위해 save 호출
            product.full_clean()

    def test_product_default_values(self):
        """제품의 기본값이 올바르게 설정되는지 테스트 (ERD V2.1)"""
        product = Product.objects.create(
            seller=self.seller,
            name="기본값 테스트",
            slug="default-test",
            price=1000,
        )
        # ERD V2.1 기본값
        self.assertEqual(product.status, "active")
        self.assertEqual(product.product_type, "main")
        self.assertTrue(product.shipping_required)
        self.assertEqual(product.shipping_fee, 0)
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)

    def test_product_category_deletion(self):
        """카테고리 삭제 시 제품의 category가 NULL이 되는지 테스트"""
        product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="카테고리 삭제 테스트",
            slug="category-deletion-test",
            price=5000,
        )

        # 카테고리 삭제
        self.category.delete()

        # 제품 다시 조회
        product.refresh_from_db()

        # category가 NULL이 되어야 함
        self.assertIsNone(product.category)
