"""
판매자 앱 테스트

Seller 모델, 시그널, on_delete 동작 검증
"""
from django.db.models import ProtectedError
from django.test import TestCase

from authentication.models import User
from products.models import Category, Product, ProductStatus
from sellers.models import Seller, SellerStatus


class SellerModelTest(TestCase):
    """Seller 모델 기본 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testseller',
            password='testpass123',
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
            status=SellerStatus.ACTIVE,
        )

    def test_seller_creation(self):
        """판매자가 정상적으로 생성되는지 테스트"""
        self.assertEqual(self.seller.brand_name, '테스트 브랜드')
        self.assertEqual(self.seller.status, SellerStatus.ACTIVE)
        self.assertEqual(self.seller.user, self.user)

    def test_seller_str_representation(self):
        """판매자 문자열 표현 테스트"""
        self.assertEqual(str(self.seller), '테스트 브랜드')


class SellerDeleteProtectionTest(TestCase):
    """판매자 삭제 시 PROTECT 동작 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testseller',
            password='testpass123',
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
            status=SellerStatus.ACTIVE,
        )
        self.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category',
        )

    def test_seller_delete_blocked_when_products_exist(self):
        """상품이 있는 판매자는 삭제가 차단되는지 테스트 (PROTECT)"""
        # 상품 생성
        Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
            status=ProductStatus.ACTIVE,
        )

        # 판매자 삭제 시도 - ProtectedError 발생해야 함
        with self.assertRaises(ProtectedError):
            self.seller.delete()

        # 판매자가 여전히 존재하는지 확인
        self.assertTrue(Seller.objects.filter(pk=self.seller.pk).exists())

    def test_seller_delete_allowed_when_no_products(self):
        """상품이 없는 판매자는 삭제가 가능한지 테스트"""
        # 상품 없이 판매자 삭제
        seller_pk = self.seller.pk
        self.seller.delete()

        # 판매자가 삭제되었는지 확인
        self.assertFalse(Seller.objects.filter(pk=seller_pk).exists())


class SellerStatusChangeSignalTest(TestCase):
    """판매자 상태 변경 시 상품 자동 비활성화 시그널 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            email='seller@test.com',
            username='testseller',
            password='testpass123',
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name='테스트 브랜드',
            brand_slug='test-brand',
            status=SellerStatus.ACTIVE,
        )
        self.category = Category.objects.create(
            name='테스트 카테고리',
            slug='test-category',
        )

        # 활성 상품 3개 생성
        for i in range(3):
            Product.objects.create(
                seller=self.seller,
                category=self.category,
                name=f'테스트 상품 {i}',
                slug=f'test-product-{i}',
                price=10000,
                status=ProductStatus.ACTIVE,
            )

        # 비활성 상품 1개 생성 (이미 비활성인 상품은 영향받지 않아야 함)
        Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='비활성 상품',
            slug='inactive-product',
            price=10000,
            status=ProductStatus.INACTIVE,
        )

    def test_products_deactivated_when_seller_becomes_inactive(self):
        """판매자가 INACTIVE 상태로 변경되면 상품이 비활성화되는지 테스트"""
        # 활성 상품 수 확인
        active_count_before = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.ACTIVE
        ).count()
        self.assertEqual(active_count_before, 3)

        # 판매자 상태를 INACTIVE로 변경
        self.seller.status = SellerStatus.INACTIVE
        self.seller.save()

        # 모든 활성 상품이 비활성화되었는지 확인
        active_count_after = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.ACTIVE
        ).count()
        self.assertEqual(active_count_after, 0)

        # 비활성 상품 수 확인 (기존 1개 + 새로 비활성화된 3개 = 4개)
        inactive_count = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.INACTIVE
        ).count()
        self.assertEqual(inactive_count, 4)

    def test_products_deactivated_when_seller_becomes_suspended(self):
        """판매자가 SUSPENDED 상태로 변경되면 상품이 비활성화되는지 테스트"""
        # 판매자 상태를 SUSPENDED로 변경
        self.seller.status = SellerStatus.SUSPENDED
        self.seller.save()

        # 모든 활성 상품이 비활성화되었는지 확인
        active_count = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.ACTIVE
        ).count()
        self.assertEqual(active_count, 0)

    def test_products_not_affected_when_seller_stays_active(self):
        """판매자가 ACTIVE 상태를 유지하면 상품에 영향이 없는지 테스트"""
        # 판매자 다른 필드만 변경 (상태는 ACTIVE 유지)
        self.seller.brand_description = '업데이트된 설명'
        self.seller.save()

        # 활성 상품 수가 변하지 않았는지 확인
        active_count = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.ACTIVE
        ).count()
        self.assertEqual(active_count, 3)

    def test_products_not_auto_activated_when_seller_becomes_active(self):
        """판매자가 ACTIVE로 변경되어도 상품이 자동 활성화되지 않는지 테스트"""
        # 먼저 판매자를 INACTIVE로 변경 (상품 비활성화)
        self.seller.status = SellerStatus.INACTIVE
        self.seller.save()

        # 모든 상품이 비활성화되었는지 확인
        self.assertEqual(
            Product.objects.filter(seller=self.seller, status=ProductStatus.ACTIVE).count(),
            0
        )

        # 판매자를 다시 ACTIVE로 변경
        self.seller.status = SellerStatus.ACTIVE
        self.seller.save()

        # 상품이 자동 활성화되지 않았는지 확인 (수동 검토 필요)
        active_count = Product.objects.filter(
            seller=self.seller,
            status=ProductStatus.ACTIVE
        ).count()
        self.assertEqual(active_count, 0)  # 자동 활성화 안 됨
