"""
S3 이미지 업로드 테스트

판매자 상품 이미지 업로드 API와 S3 연동 테스트입니다.
"""
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image

from products.models import (
    Category, Product, ProductImage,
    ProductDetail, ProductInventory, ProductStats
)
from products.services.s3_upload import S3ImageUploader, S3UploadError
from authentication.models import User
from sellers.models import Seller


def create_test_image(name='test.jpg', size=(100, 100), format='JPEG'):
    """테스트용 이미지 파일 생성"""
    file = BytesIO()
    image = Image.new('RGB', size, color='red')
    image.save(file, format)
    file.seek(0)
    return SimpleUploadedFile(
        name,
        file.getvalue(),
        content_type=f'image/{format.lower()}'
    )


class S3ImageUploaderTest(TestCase):
    """S3ImageUploader 단위 테스트"""

    def test_고유한_파일명_생성(self):
        """파일명이 product_id와 UUID를 포함하여 생성되어야 한다"""
        uploader = S3ImageUploader()
        filename = uploader._generate_unique_filename('test.jpg', 123)

        self.assertIn('123_', filename)
        self.assertTrue(filename.endswith('.jpg'))

    def test_확장자_없는_파일도_처리(self):
        """확장자 없는 파일은 jpg로 기본 처리해야 한다"""
        uploader = S3ImageUploader()
        filename = uploader._generate_unique_filename('noextension', 456)

        self.assertTrue(filename.endswith('.jpg'))

    def test_다양한_확장자_지원(self):
        """PNG, GIF, WebP 확장자도 올바르게 처리해야 한다"""
        uploader = S3ImageUploader()

        png_filename = uploader._generate_unique_filename('image.PNG', 1)
        self.assertTrue(png_filename.endswith('.png'))

        gif_filename = uploader._generate_unique_filename('animation.GIF', 2)
        self.assertTrue(gif_filename.endswith('.gif'))

        webp_filename = uploader._generate_unique_filename('modern.WEBP', 3)
        self.assertTrue(webp_filename.endswith('.webp'))


class ProductImageUploadAPITest(TestCase):
    """상품 메인 이미지 업로드 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()

        # 판매자 유저 생성
        self.user = User.objects.create_user(
            email="seller@test.com",
            username="testseller",
            password="testpass123"
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name="테스트 판매자",
            brand_slug="test-seller",
            status='active'  # 활성 상태
        )

        # 카테고리 및 상품 생성
        self.category = Category.objects.create(name='테스트', slug='test')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
            status='draft',
            product_type='seller'
        )

        # 관련 테이블 생성
        ProductDetail.objects.create(product=self.product)
        ProductInventory.objects.create(product=self.product)
        ProductStats.objects.create(product=self.product)

        self.client.force_authenticate(user=self.user)

    @patch.object(S3ImageUploader, '_upload_to_s3')
    def test_이미지_업로드_성공(self, mock_upload):
        """이미지 파일을 업로드하면 S3에 저장되고 ProductImage가 생성되어야 한다"""
        mock_upload.return_value = 'https://test.s3.amazonaws.com/test.jpg'

        image = create_test_image()
        url = reverse('product-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['images']), 1)
        self.assertEqual(ProductImage.objects.filter(product=self.product).count(), 1)

    def test_권한_없는_사용자_접근_거부(self):
        """판매자가 아닌 사용자는 접근이 거부되어야 한다"""
        # 일반 사용자로 변경
        normal_user = User.objects.create_user(
            email="normal@test.com",
            username="normaluser",
            password="testpass123"
        )
        self.client.force_authenticate(user=normal_user)

        image = create_test_image()
        url = reverse('product-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_타인의_상품에_이미지_업로드_거부(self):
        """다른 판매자의 상품에는 이미지를 업로드할 수 없어야 한다"""
        # 다른 판매자 생성
        other_user = User.objects.create_user(
            email="other@test.com",
            username="otherseller",
            password="testpass123"
        )
        other_seller = Seller.objects.create(
            user=other_user,
            brand_name="다른 판매자",
            brand_slug="other-seller",
            status='active'
        )
        other_product = Product.objects.create(
            seller=other_seller,
            category=self.category,
            name='다른 상품',
            slug='other-product',
            price=5000
        )

        image = create_test_image()
        url = reverse('product-image-upload', kwargs={'product_id': other_product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch.object(S3ImageUploader, '_upload_to_s3')
    def test_이미지_순서_자동_할당(self, mock_upload):
        """업로드된 이미지에 display_order가 순서대로 할당되어야 한다"""
        # 기존 이미지 생성
        ProductImage.objects.create(
            product=self.product,
            image_url='https://existing.com/image.jpg',
            display_order=0
        )

        mock_upload.return_value = 'https://test.s3.amazonaws.com/new.jpg'

        image = create_test_image()
        url = reverse('product-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_image = ProductImage.objects.filter(product=self.product).order_by('-display_order').first()
        self.assertEqual(new_image.display_order, 1)

    def test_이미지_없이_요청시_에러(self):
        """이미지 없이 요청하면 에러가 발생해야 한다"""
        url = reverse('product-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductDetailImageUploadAPITest(TestCase):
    """상품 상세 설명 이미지 업로드 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="seller@test.com",
            username="testseller",
            password="testpass123"
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name="테스트 판매자",
            brand_slug="test-seller",
            status='active'
        )

        self.category = Category.objects.create(name='테스트', slug='test')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
            product_type='seller'
        )

        ProductDetail.objects.create(product=self.product, full_image_description=[])
        ProductInventory.objects.create(product=self.product)
        ProductStats.objects.create(product=self.product)

        self.client.force_authenticate(user=self.user)

    @patch.object(S3ImageUploader, '_upload_to_s3')
    def test_상세_이미지_업로드_성공(self, mock_upload):
        """상세 이미지 업로드 시 full_image_description 배열에 추가되어야 한다"""
        mock_upload.return_value = 'https://test.s3.amazonaws.com/detail.jpg'

        image = create_test_image()
        url = reverse('product-detail-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # ProductDetail 확인
        self.product.detail.refresh_from_db()
        self.assertEqual(len(self.product.detail.full_image_description), 1)

    @patch.object(S3ImageUploader, '_upload_to_s3')
    def test_기존_이미지에_추가(self, mock_upload):
        """기존 이미지가 있으면 배열 끝에 추가되어야 한다"""
        # 기존 이미지 설정
        self.product.detail.full_image_description = ['https://existing.com/1.jpg']
        self.product.detail.save()

        mock_upload.return_value = 'https://test.s3.amazonaws.com/new.jpg'

        image = create_test_image()
        url = reverse('product-detail-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': [image]}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.product.detail.refresh_from_db()
        self.assertEqual(len(self.product.detail.full_image_description), 2)
        self.assertEqual(self.product.detail.full_image_description[0], 'https://existing.com/1.jpg')

    @patch.object(S3ImageUploader, '_upload_to_s3')
    def test_여러_이미지_동시_업로드(self, mock_upload):
        """여러 이미지를 동시에 업로드할 수 있어야 한다"""
        mock_upload.side_effect = [
            'https://test.s3.amazonaws.com/detail1.jpg',
            'https://test.s3.amazonaws.com/detail2.jpg',
            'https://test.s3.amazonaws.com/detail3.jpg',
        ]

        images = [create_test_image(f'test{i}.jpg') for i in range(3)]
        url = reverse('product-detail-image-upload', kwargs={'product_id': self.product.id})

        response = self.client.post(url, {'images': images}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_images'], 3)


class SellerProductCreateAPITest(TestCase):
    """판매자 상품 생성 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="seller@test.com",
            username="testseller",
            password="testpass123"
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name="테스트 판매자",
            brand_slug="test-seller",
            status='active'
        )

        self.category = Category.objects.create(name='테스트', slug='test')
        self.client.force_authenticate(user=self.user)

    def test_상품_생성_시_관련_테이블_자동_생성(self):
        """상품 생성 시 ProductDetail, ProductInventory, ProductStats가 자동 생성되어야 한다"""
        url = reverse('seller-product-list')
        data = {
            'name': '신규 상품',
            'slug': 'new-product',
            'price': 15000,
            'category_id': self.category.id,
            'stock_quantity': 100,
            'short_description': '짧은 설명',
            'full_description': '상세 설명'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(slug='new-product')

        # 관련 테이블 존재 확인
        self.assertTrue(hasattr(product, 'detail'))
        self.assertTrue(hasattr(product, 'inventory'))
        self.assertTrue(hasattr(product, 'stats'))

        # 값 확인
        self.assertEqual(product.detail.short_description, '짧은 설명')
        self.assertEqual(product.inventory.stock_quantity, 100)
        self.assertEqual(product.status, 'draft')  # 초기 상태
        self.assertEqual(product.product_type, 'seller')  # 판매자 상품

    def test_상품_생성_시_full_image_description_빈_배열(self):
        """상품 생성 시 full_image_description은 빈 배열이어야 한다"""
        url = reverse('seller-product-list')
        data = {
            'name': '테스트 상품2',
            'slug': 'test-product-2',
            'price': 10000,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(name='테스트 상품2')
        self.assertEqual(product.detail.full_image_description, [])


class ProductImageDeleteAPITest(TestCase):
    """상품 이미지 삭제 API 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="seller@test.com",
            username="testseller",
            password="testpass123"
        )
        self.seller = Seller.objects.create(
            user=self.user,
            brand_name="테스트 판매자",
            brand_slug="test-seller",
            status='active'
        )

        self.category = Category.objects.create(name='테스트', slug='test')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name='테스트 상품',
            slug='test-product',
            price=10000,
            product_type='seller'
        )

        self.image = ProductImage.objects.create(
            product=self.product,
            image_url='https://test.s3.amazonaws.com/test.jpg',
            display_order=0
        )

        self.client.force_authenticate(user=self.user)

    @patch.object(S3ImageUploader, 'delete_image')
    def test_이미지_삭제_성공(self, mock_delete):
        """이미지 삭제 시 DB와 S3 모두에서 삭제되어야 한다"""
        mock_delete.return_value = True

        url = reverse('product-image-delete', kwargs={
            'product_id': self.product.id,
            'image_id': self.image.id
        })

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductImage.objects.filter(id=self.image.id).exists())
        mock_delete.assert_called_once()

    def test_타인의_이미지_삭제_거부(self):
        """다른 판매자의 이미지는 삭제할 수 없어야 한다"""
        # 다른 판매자 생성
        other_user = User.objects.create_user(
            email="other@test.com",
            username="otherseller",
            password="testpass123"
        )
        other_seller = Seller.objects.create(
            user=other_user,
            brand_name="다른 판매자",
            brand_slug="other-seller",
            status='active'
        )
        other_product = Product.objects.create(
            seller=other_seller,
            category=self.category,
            name='다른 상품',
            slug='other-product',
            price=5000
        )
        other_image = ProductImage.objects.create(
            product=other_product,
            image_url='https://test.s3.amazonaws.com/other.jpg',
            display_order=0
        )

        url = reverse('product-image-delete', kwargs={
            'product_id': other_product.id,
            'image_id': other_image.id
        })

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
