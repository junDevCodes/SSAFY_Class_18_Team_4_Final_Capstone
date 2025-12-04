"""
CSV 데이터 임포트 커맨드 테스트 (ERD V2.1)
"""
import os
import tempfile
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from products.models import Category, Product, ProductImage


class ImportProductsCommandTest(TestCase):
    """CSV 데이터 임포트 커맨드 테스트 (ERD V2.1)"""

    def setUp(self):
        """테스트용 임시 CSV 파일 생성"""
        self.test_csv_content = """site_name,category,product_name,price,unit,description,product_url,image_url,detail_info,crawled_at
네이버쇼핑_컬리N마트,과일/견과,냉동 칠레산 블루베리 1kg,9990,,냉동 칠레산 블루베리 1kg,https://example.com/product1,https://example.com/image1.jpg,,2025-11-23 05:24:55
네이버쇼핑_컬리N마트,채소,친환경 유기농 쌈채소 모듬,4500,,당일 수확 아삭한 식감,https://example.com/product2,https://example.com/image2.jpg,,2025-11-23 05:24:56
네이버쇼핑_컬리N마트,수산/건어물,노르웨이 생연어 회/초밥용,21900,,항공 직송 신선함,https://example.com/product3,https://example.com/image3.jpg,,2025-11-23 05:24:57"""

        # 임시 CSV 파일 생성
        self.temp_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8')
        self.temp_csv.write(self.test_csv_content)
        self.temp_csv.close()

    def tearDown(self):
        """임시 CSV 파일 삭제"""
        if os.path.exists(self.temp_csv.name):
            os.unlink(self.temp_csv.name)

    def test_import_products_creates_categories(self):
        """카테고리가 정상적으로 생성되는지 테스트"""
        out = StringIO()
        call_command('import_products', self.temp_csv.name, stdout=out)

        # 3개의 고유한 카테고리가 생성되어야 함
        self.assertEqual(Category.objects.count(), 3)
        self.assertTrue(Category.objects.filter(name='과일/견과').exists())
        self.assertTrue(Category.objects.filter(name='채소').exists())
        self.assertTrue(Category.objects.filter(name='수산/건어물').exists())

    def test_import_products_creates_products(self):
        """제품이 정상적으로 생성되는지 테스트 (ERD V2.1)"""
        out = StringIO()
        call_command('import_products', self.temp_csv.name, stdout=out)

        # 3개의 제품이 생성되어야 함
        self.assertEqual(Product.objects.count(), 3)

        # 첫 번째 제품 검증 (ERD V2.1 필드)
        product1 = Product.objects.get(name='냉동 칠레산 블루베리 1kg')
        self.assertEqual(product1.price, 9990)
        self.assertEqual(product1.source_site, '네이버쇼핑_컬리N마트')  # ERD V2.1: source_site
        self.assertEqual(product1.category.name, '과일/견과')

        # ERD V2.1: seller 필수
        self.assertIsNotNone(product1.seller)
        self.assertEqual(product1.seller.brand_name, '시스템 임포트')

        # ERD V2.1: 이미지는 ProductImage 테이블에 저장
        self.assertEqual(product1.images.count(), 1)
        primary_image = product1.images.order_by('display_order').first()
        self.assertEqual(primary_image.image_url, 'https://example.com/image1.jpg')
        self.assertEqual(primary_image.display_order, 0)

    def test_import_products_with_duplicate_categories(self):
        """중복된 카테고리 이름이 있을 때 하나만 생성되는지 테스트"""
        # 같은 카테고리를 가진 제품 추가
        csv_content = self.test_csv_content + "\n네이버쇼핑_컬리N마트,과일/견과,사과,5000,,맛있는 사과,https://example.com/product4,https://example.com/image4.jpg,,2025-11-23 05:24:58"

        temp_csv2 = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8')
        temp_csv2.write(csv_content)
        temp_csv2.close()

        try:
            out = StringIO()
            call_command('import_products', temp_csv2.name, stdout=out)

            # 카테고리는 여전히 3개여야 함 (중복 제거)
            self.assertEqual(Category.objects.count(), 3)
            # 제품은 4개여야 함
            self.assertEqual(Product.objects.count(), 4)
        finally:
            os.unlink(temp_csv2.name)

    def test_import_products_clears_existing_data(self):
        """기존 데이터가 삭제되고 새로운 데이터로 교체되는지 테스트"""
        # 먼저 데이터 임포트
        out = StringIO()
        call_command('import_products', self.temp_csv.name, stdout=out)

        initial_product_count = Product.objects.count()
        self.assertEqual(initial_product_count, 3)

        # 다시 임포트 (기존 데이터 삭제되어야 함)
        out = StringIO()
        call_command('import_products', self.temp_csv.name, '--clear-existing', stdout=out)

        # 제품 수가 동일해야 함 (중복이 아닌 교체)
        self.assertEqual(Product.objects.count(), 3)

    def test_import_products_with_missing_csv_file(self):
        """존재하지 않는 CSV 파일로 호출 시 에러 처리 테스트"""
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command('import_products', 'nonexistent_file.csv')

    def test_import_products_output_message(self):
        """커맨드 실행 후 출력 메시지 테스트"""
        out = StringIO()
        call_command('import_products', self.temp_csv.name, stdout=out)

        output = out.getvalue()
        self.assertIn('성공적으로 임포트', output)
        self.assertIn('3', output)  # 제품 개수

    def test_import_products_creates_images(self):
        """이미지가 ProductImage 테이블에 정상적으로 생성되는지 테스트 (ERD V2.1)"""
        out = StringIO()
        call_command('import_products', self.temp_csv.name, stdout=out)

        # 3개의 이미지가 생성되어야 함 (각 제품당 1개)
        self.assertEqual(ProductImage.objects.count(), 3)

        # 모든 이미지가 display_order=0이어야 함 (ERD V2.1: display_order 기준으로 대표 이미지 결정)
        self.assertEqual(ProductImage.objects.filter(display_order=0).count(), 3)
