# 농산물 직거래 플랫폼 - 상세 구현 계획

## ⚡ 개발 우선순위 및 원칙

### 🎯 핵심 원칙
1. **기능 동작 우선**: 모든 기능이 동작하는 것을 1차 목표로 함
2. **혼자서 테스트 가능**: 복잡한 외부 인증 없이 개발자가 모든 기능을 테스트 가능해야 함
3. **선택적 필드**: 실제 서비스에서도 필수가 아닌 필드는 모두 nullable 처리
4. **간소화된 인증**: 초기 단계에서는 복잡한 인증 프로세스 생략, 나중에 강화

### 📝 개발 단계별 접근

#### Phase 1-3: MVP (최소 기능 제품)
- ✅ **모든 필드는 선택 사항**: phone_number, date_of_birth 등 모두 nullable
- ✅ **결제 수단**: 저장만 가능, 실제 결제 연동은 나중
- ✅ **판매자 인증**: 사업자번호 입력만으로 즉시 등록 가능
- ✅ **이미지 업로드**: URL만 저장, 실제 파일 업로드는 나중
- ✅ **실시간 알림**: 나중 구현, 지금은 DB에만 저장
- ✅ **복잡한 검증**: 최소화, 기본 동작에 집중

#### Phase 4-5: 프로덕션 준비
- 🔒 **인증 강화**: 사업자번호 실제 검증 (국세청 API)
- 🔒 **결제 연동**: PG사 연동 (아임포트, 토스페이먼츠)
- 🔒 **이미지 처리**: S3 업로드, 리사이징, CDN
- 🔒 **실시간 기능**: WebSocket, 알림 푸시
- 🔒 **보안 강화**: Rate limiting, CAPTCHA 등

### 🚀 현재 구현 방식

**예시 1: 판매자 등록**
```python
# 현재 (MVP): 간단하게
seller = Seller.objects.create(
    user=user,
    brand_name="농부마트",
    business_registration_number="123-45-67890",  # 그냥 저장만
    status="active"  # 즉시 활성화
)

# 나중 (프로덕션): 엄격하게
seller = Seller.objects.create(
    user=user,
    brand_name="농부마트",
    business_registration_number="123-45-67890",
    status="pending"  # 관리자 승인 대기
)
# + 국세청 API 검증
# + 서류 업로드 필수
# + 관리자 승인 프로세스
```

**예시 2: 결제 수단**
```python
# 현재 (MVP): 저장만
payment_method = UserPaymentMethod.objects.create(
    user=user,
    type="credit_card",
    card_number_last4="1234"  # 그냥 저장
)

# 나중 (프로덕션): 실제 연동
payment_method = UserPaymentMethod.objects.create(
    user=user,
    type="credit_card",
    payment_gateway_token=encrypted_token,  # PG사 빌링키
)
# + PG사 연동
# + 카드 유효성 검증
# + 암호화 처리
```

---

## 목차
1. [Phase 1: 데이터베이스 및 백엔드 기반 구축](#phase-1)
2. [Phase 2: 판매자 시스템 구현](#phase-2)
3. [Phase 3: 사용자 기능 완성](#phase-3)
4. [Phase 4: 추천 시스템 및 최적화](#phase-4)
5. [Phase 5: 관리자 시스템 및 배포](#phase-5)

---

## Phase 1: 데이터베이스 및 백엔드 기반 구축

### 1.1 데이터베이스 마이그레이션 및 모델 확장

#### Task 1.1.1: User 모델 확장
**파일**: `backend/authentication/models.py`

**작업 내용**:
```python
# 추가 필드
- phone_number (PhoneNumberField, nullable)
- date_of_birth (DateField, nullable)
- gender (CharField, nullable)
- language (CharField, default='ko')
- notification_enabled (BooleanField, default=True)
- marketing_agreed (BooleanField, default=False)
- deleted_at (DateTimeField, nullable)  # 소프트 삭제
```

**마이그레이션**:
```bash
python manage.py makemigrations authentication
python manage.py migrate authentication
```

**테스트**:
- User 생성/조회/수정/삭제
- 필드 nullable 검증
- 소프트 삭제 동작 확인

**커밋**: `feat: User 모델 확장 (전화번호, 생년월일, 언어 설정 등)`

---

#### Task 1.1.2: UserAddress 모델 생성
**파일**: `backend/authentication/models.py`

**작업 내용**:
```python
class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)  # 배송지명
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    postal_code = models.CharField(max_length=10)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=2, default='KR')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_addresses'
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]

    def save(self, *args, **kwargs):
        # is_default=True일 때 다른 주소 is_default=False 처리
        if self.is_default:
            UserAddress.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)
```

**API 엔드포인트**:
- `GET /auth/addresses/` - 배송지 목록
- `POST /auth/addresses/` - 배송지 추가
- `PATCH /auth/addresses/<id>/` - 배송지 수정
- `DELETE /auth/addresses/<id>/` - 배송지 삭제
- `POST /auth/addresses/<id>/set-default/` - 기본 배송지 설정

**시리얼라이저**: `backend/authentication/serializers.py`
```python
class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = '__all__'
        read_only_fields = ['user']
```

**뷰**: `backend/authentication/views.py`
```python
class UserAddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

**테스트**: `backend/authentication/tests/test_address.py`

**커밋**: `feat: 배송지 관리 기능 구현`

---

#### Task 1.1.3: UserPaymentMethod 모델 생성
**파일**: `backend/authentication/models.py`

**작업 내용**:
```python
class UserPaymentMethod(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('credit_card', '신용카드'),
        ('debit_card', '체크카드'),
        ('bank_account', '계좌이체'),
        ('virtual_account', '가상계좌'),
        ('mobile', '간편결제'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    provider = models.CharField(max_length=50)  # 'kakaopay', 'tosspay', etc.

    # 카드 정보 (마지막 4자리만)
    card_number_last4 = models.CharField(max_length=4, null=True, blank=True)
    card_issuer = models.CharField(max_length=50, null=True, blank=True)
    card_type = models.CharField(max_length=20, null=True, blank=True)

    # PG사 빌링키 (암호화 필요)
    payment_gateway_token = models.TextField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_payment_methods'
```

**API 엔드포인트**:
- `GET /auth/payment-methods/` - 결제 수단 목록
- `POST /auth/payment-methods/` - 결제 수단 추가
- `DELETE /auth/payment-methods/<id>/` - 결제 수단 삭제

**커밋**: `feat: 결제 수단 관리 기능 구현`

---

#### Task 1.1.4: Category 모델 계층 구조 확장
**파일**: `backend/products/models.py`

**작업 내용**:
```python
class Category(models.Model):
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    path = models.CharField(max_length=255)  # '/1/5/12/'
    level = models.SmallIntegerField(default=0)

    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    icon_url = models.TextField(null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)

    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['path']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
        ]

    def save(self, *args, **kwargs):
        # path와 level 자동 계산
        if self.parent:
            self.path = f"{self.parent.path}{self.parent.id}/"
            self.level = self.parent.level + 1
        else:
            self.path = "/"
            self.level = 0
        super().save(*args, **kwargs)

    def get_ancestors(self):
        """조상 카테고리 반환"""
        if not self.parent:
            return []
        return list(self.parent.get_ancestors()) + [self.parent]

    def get_descendants(self):
        """자손 카테고리 반환 (재귀)"""
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants
```

**CSV 데이터에서 카테고리 자동 생성**:
```python
# management/commands/import_products.py
def get_or_create_category_hierarchy(category_path):
    """
    '과일/견과/사과' -> Category 객체 생성
    계층 구조 자동 생성
    """
    parts = category_path.split('/')
    parent = None

    for i, name in enumerate(parts):
        slug = slugify(name, allow_unicode=True)
        category, created = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'parent': parent}
        )
        parent = category

    return parent
```

**API 확장**:
- `GET /api/categories/?level=0` - 최상위 카테고리만
- `GET /api/categories/?parent=<id>` - 자식 카테고리
- `GET /api/categories/<id>/tree/` - 전체 트리 구조

**커밋**: `feat: 카테고리 계층 구조 구현 (Nested Set)`

---

#### Task 1.1.5: Product 모델 확장 (메인 + 판매자 통합)
**파일**: `backend/products/models.py`

**작업 내용**:
```python
class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('main', '메인 상품'),
        ('seller', '판매자 상품'),
    ]

    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('active', '판매중'),
        ('inactive', '판매중지'),
        ('out_of_stock', '품절'),
        ('discontinued', '단종'),
    ]

    # 상품 유형
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='main')

    # 관계
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey('sellers.Seller', on_delete=models.CASCADE, null=True, blank=True)
    # seller는 product_type='seller'일 때만 NOT NULL

    # 크롤링 메타데이터
    source_site = models.CharField(max_length=100, null=True, blank=True)
    source_url = models.TextField(null=True, blank=True)
    crawled_at = models.DateTimeField(null=True, blank=True)

    # 기본 정보
    name = models.CharField(max_length=500)
    name_en = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(max_length=500, null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    # 가격
    price = models.IntegerField(validators=[MinValueValidator(0)])
    original_price = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    discount_rate = models.SmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    cost_price = models.IntegerField(null=True, blank=True)  # 판매자용

    # 단위
    unit = models.CharField(max_length=50, null=True, blank=True)
    unit_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)

    # 재고 (판매자 상품만)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    is_in_stock = models.BooleanField(default=True)

    # 이미지
    main_image_url = models.TextField()

    # 상품 품질 점수 (추천 알고리즘용)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, validators=[MinValueValidator(0), MaxValueValidator(100)])
    image_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    content_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)

    # 통계 (비정규화)
    view_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    cart_count = models.IntegerField(default=0)
    wishlist_count = models.IntegerField(default=0)
    purchase_count = models.IntegerField(default=0)
    review_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    ctr = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)  # CTR

    # 배송
    shipping_required = models.BooleanField(default=True)
    shipping_fee = models.IntegerField(default=0)
    free_shipping_threshold = models.IntegerField(null=True, blank=True)
    estimated_delivery_days = models.SmallIntegerField(null=True, blank=True)

    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    is_best = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_on_sale = models.BooleanField(default=False)

    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # SEO
    meta_title = models.CharField(max_length=200, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    meta_keywords = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['product_type']),
            models.Index(fields=['category']),
            models.Index(fields=['seller']),
            models.Index(fields=['status']),
            models.Index(fields=['-quality_score']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-ctr']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_featured', 'status']),
            models.Index(fields=['is_best', 'status']),
            models.Index(fields=['slug']),
            # 복합 인덱스
            models.Index(fields=['product_type', 'status', '-quality_score', '-ctr']),
            models.Index(fields=['category', 'status', '-quality_score']),
        ]

    def save(self, *args, **kwargs):
        # slug 자동 생성
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)

        # quality_score 자동 계산
        self.quality_score = (self.image_quality_score + self.content_quality_score) / 2

        # CTR 계산
        if self.view_count > 0:
            self.ctr = self.click_count / self.view_count

        super().save(*args, **kwargs)

    def calculate_image_quality_score(self):
        """이미지 품질 점수 계산"""
        score = 50.0

        # 이미지 URL 유효성 검증
        if self.main_image_url:
            try:
                response = requests.head(self.main_image_url, timeout=5)
                if response.status_code == 200:
                    score += 30

                    # 이미지 크기 확인 (Content-Length)
                    size = int(response.headers.get('Content-Length', 0))
                    if size > 50000:  # 50KB 이상
                        score += 10

                    # 이미지 형식 확인
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' in content_type:
                        score += 10
            except:
                score = 20  # 접근 불가

        return min(score, 100)

    def calculate_content_quality_score(self):
        """콘텐츠 품질 점수 계산"""
        score = 0

        # 제품명 길이
        if len(self.name) > 10:
            score += 20

        # 설명 존재 여부
        if self.description and len(self.description) > 50:
            score += 30

        # 카테고리 설정 여부
        if self.category:
            score += 20

        # 가격 설정 여부
        if self.price > 0:
            score += 20

        # 추가 이미지 존재 여부
        if self.images.count() > 1:
            score += 10

        return min(score, 100)
```

**마이그레이션**:
```bash
python manage.py makemigrations products
python manage.py migrate products
```

**커밋**: `feat: Product 모델 확장 (품질 점수, CTR, 판매자 상품 지원)`

---

#### Task 1.1.6: ProductImage 모델 생성
**파일**: `backend/products/models.py`

```python
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.TextField()
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    display_order = models.IntegerField(default=0)

    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    format = models.CharField(max_length=10, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['product', 'display_order']),
        ]
```

**API 엔드포인트**:
- `GET /api/products/<id>/images/` - 상품 이미지 목록
- `POST /api/products/<id>/images/` - 이미지 추가
- `DELETE /api/products/<id>/images/<image_id>/` - 이미지 삭제

**커밋**: `feat: 상품 이미지 다중 업로드 지원`

---

#### Task 1.1.7: Seller 모델 생성
**파일**: `backend/sellers/models.py` (새 앱 생성)

```bash
python manage.py startapp sellers
```

**작업 내용**:
```python
class Seller(models.Model):
    BUSINESS_TYPE_CHOICES = [
        ('individual', '개인사업자'),
        ('corporate', '법인사업자'),
        ('cooperative', '협동조합'),
    ]

    STATUS_CHOICES = [
        ('pending', '승인대기'),
        ('active', '활성'),
        ('suspended', '정지'),
        ('inactive', '비활성'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 브랜드 정보
    brand_name = models.CharField(max_length=200, unique=True)
    brand_name_en = models.CharField(max_length=200, unique=True, null=True, blank=True)
    brand_slug = models.SlugField(max_length=200, unique=True)
    brand_description = models.TextField(null=True, blank=True)
    brand_logo_url = models.TextField(null=True, blank=True)
    brand_banner_url = models.TextField(null=True, blank=True)

    # 사업자 정보
    business_registration_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES, null=True, blank=True)
    company_name = models.CharField(max_length=200, null=True, blank=True)
    ceo_name = models.CharField(max_length=100, null=True, blank=True)

    # 인증 정보
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_document_url = models.TextField(null=True, blank=True)

    # 연락처
    business_phone = models.CharField(max_length=20, null=True, blank=True)
    business_email = models.EmailField(null=True, blank=True)
    customer_service_phone = models.CharField(max_length=20, null=True, blank=True)

    # 주소
    business_address = models.TextField(null=True, blank=True)
    warehouse_address = models.TextField(null=True, blank=True)

    # 정산 정보 (암호화 필요)
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    bank_account_number = models.CharField(max_length=50, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)

    # 운영 정보
    min_order_amount = models.IntegerField(default=0)
    shipping_fee = models.IntegerField(default=0)
    free_shipping_threshold = models.IntegerField(null=True, blank=True)

    # 통계 (비정규화)
    total_products = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    total_reviews = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sellers'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['brand_slug']),
            models.Index(fields=['status']),
            models.Index(fields=['is_verified']),
        ]

    def save(self, *args, **kwargs):
        if not self.brand_slug:
            self.brand_slug = slugify(self.brand_name, allow_unicode=True)
        super().save(*args, **kwargs)
```

**API 엔드포인트**:
- `POST /api/sellers/register/` - 판매자 등록 신청
- `GET /api/sellers/me/` - 내 판매자 정보
- `PATCH /api/sellers/me/` - 판매자 정보 수정
- `GET /api/sellers/<brand_slug>/` - 브랜드 페이지 조회
- `GET /api/sellers/<brand_slug>/products/` - 브랜드 상품 목록

**권한 클래스**: `backend/sellers/permissions.py`
```python
class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'seller'
```

**커밋**: `feat: 판매자 모델 및 브랜드 등록 기능 구현`

---

#### Task 1.1.8: CSV 데이터 대량 임포트 개선
**파일**: `backend/products/management/commands/import_all_csvs.py`

**작업 내용**:
```python
import os
import glob
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Category, ProductImage
from django.utils import timezone
from django.utils.text import slugify
import requests

class Command(BaseCommand):
    help = 'Import all CSV files from data/ directory'

    def add_arguments(self, parser):
        parser.add_argument('--directory', type=str, default='data/', help='CSV directory path')

    def handle(self, *args, **options):
        directory = options['directory']
        csv_files = glob.glob(os.path.join(directory, '*.csv'))

        self.stdout.write(f'Found {len(csv_files)} CSV files')

        for csv_file in csv_files:
            self.stdout.write(f'\nProcessing {csv_file}...')
            self.import_csv(csv_file)

        self.stdout.write(self.style.SUCCESS('\n✅ All CSV files imported successfully'))

    @transaction.atomic
    def import_csv(self, file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            imported = 0
            skipped = 0

            for row in reader:
                # 중복 체크 (product_url 기준)
                product_url = row.get('product_url', '').strip()
                if product_url and Product.objects.filter(source_url=product_url).exists():
                    skipped += 1
                    continue

                # 카테고리 처리
                category = None
                category_name = row.get('category', '').strip()
                if category_name:
                    category = self.get_or_create_category(category_name)

                # 가격 처리
                price = self.parse_price(row.get('price', '0'))

                # 이미지 품질 검증
                image_url = row.get('image_url', '').strip()
                image_quality_score = self.validate_image(image_url)

                # 제품 생성
                product = Product.objects.create(
                    product_type='main',
                    category=category,
                    source_site=row.get('site_name', '').strip(),
                    source_url=product_url,
                    crawled_at=self.parse_datetime(row.get('crawled_at')),

                    name=row.get('product_name', '').strip(),
                    description=row.get('description', '').strip(),

                    price=price,
                    original_price=price,  # 향후 할인가 계산

                    unit=row.get('unit', '').strip() or None,

                    main_image_url=image_url,
                    image_quality_score=image_quality_score,

                    status='active',
                )

                # content_quality_score 계산
                product.content_quality_score = product.calculate_content_quality_score()
                product.save()

                imported += 1

                if imported % 100 == 0:
                    self.stdout.write(f'  Imported {imported} products...')

            self.stdout.write(self.style.SUCCESS(f'  ✅ Imported: {imported}, Skipped: {skipped}'))

    def get_or_create_category(self, category_path):
        """
        카테고리 계층 구조 생성
        예: '과일/견과/사과' -> Category 생성
        """
        parts = [p.strip() for p in category_path.split('/') if p.strip()]
        parent = None

        for name in parts:
            slug = slugify(name, allow_unicode=True)
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'parent': parent,
                    'is_active': True,
                }
            )
            parent = category

        return parent

    def parse_price(self, price_str):
        """가격 파싱"""
        if not price_str:
            return 0
        # 숫자만 추출
        return int(''.join(filter(str.isdigit, str(price_str))) or '0')

    def parse_datetime(self, datetime_str):
        """날짜 파싱"""
        if not datetime_str:
            return None
        try:
            from dateutil import parser
            return parser.parse(datetime_str)
        except:
            return timezone.now()

    def validate_image(self, image_url):
        """이미지 URL 유효성 검증 및 점수 계산"""
        if not image_url:
            return 0.0

        try:
            response = requests.head(image_url, timeout=3)
            if response.status_code == 200:
                score = 50.0

                # 이미지 크기 확인
                size = int(response.headers.get('Content-Length', 0))
                if size > 50000:  # 50KB 이상
                    score += 30

                # 이미지 타입 확인
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    score += 20

                return min(score, 100)
            else:
                return 20.0
        except Exception as e:
            self.stderr.write(f'    Image validation failed: {image_url} - {e}')
            return 10.0
```

**실행**:
```bash
python manage.py import_all_csvs --directory=data/
```

**테스트**:
- 290개 데이터 임포트 확인
- 중복 제거 확인
- 카테고리 계층 구조 확인
- 이미지 품질 점수 확인

**커밋**: `feat: CSV 대량 임포트 개선 (중복 제거, 이미지 검증)`

---

### 1.2 PostgreSQL 전환

#### Task 1.2.1: PostgreSQL 설치 및 설정
**파일**: `backend/project_self/settings.py`

**작업 내용**:
1. PostgreSQL 설치 (Windows/Mac/Linux)
2. 데이터베이스 생성
   ```sql
   CREATE DATABASE ssafy_capstone;
   CREATE USER ssafy_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE ssafy_capstone TO ssafy_user;
   ```

3. `.env` 파일 설정
   ```env
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=ssafy_capstone
   DB_USER=ssafy_user
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. `settings.py` 수정
   ```python
   import os
   from dotenv import load_load_env()

   DATABASES = {
       'default': {
           'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
           'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
           'USER': os.getenv('DB_USER', ''),
           'PASSWORD': os.getenv('DB_PASSWORD', ''),
           'HOST': os.getenv('DB_HOST', ''),
           'PORT': os.getenv('DB_PORT', ''),
       }
   }
   ```

5. psycopg2 설치
   ```bash
   pip install psycopg2-binary
   pip freeze > requirements.txt
   ```

6. 마이그레이션
   ```bash
   python manage.py migrate
   python manage.py import_all_csvs
   ```

**커밋**: `feat: PostgreSQL 데이터베이스 전환`

---

#### Task 1.2.2: PostgreSQL 전체 텍스트 검색 설정
**파일**: `backend/products/models.py`

**작업 내용**:
```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.indexes import GinIndex

class Product(models.Model):
    # ... 기존 필드

    class Meta:
        # ... 기존 Meta
        indexes = [
            # ... 기존 인덱스
            GinIndex(fields=['name'], name='product_name_gin_idx', opclasses=['gin_trgm_ops']),
        ]

    @staticmethod
    def search(query):
        """전체 텍스트 검색"""
        search_vector = SearchVector('name', weight='A') + SearchVector('description', weight='B')
        search_query = SearchQuery(query, config='korean')

        return Product.objects.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query).order_by('-rank')
```

**마이그레이션**:
```python
# products/migrations/0XXX_add_fulltext_search.py
from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
```

**API 수정**: `backend/products/views.py`
```python
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        queryset = Product.objects.filter(status='active')

        # 검색
        search = self.request.query_params.get('search')
        if search:
            queryset = Product.search(search)

        return queryset
```

**커밋**: `feat: PostgreSQL 전체 텍스트 검색 구현`

---

### 1.3 API 개선

#### Task 1.3.1: Product 상세 API 개선
**파일**: `backend/products/views.py`

**작업 내용**:
```python
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.select_related('category', 'seller').prefetch_related('images')
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'  # slug로 조회

    def retrieve(self, request, *args, **kwargs):
        # 조회수 증가
        instance = self.get_object()
        Product.objects.filter(id=instance.id).update(view_count=F('view_count') + 1)

        # ProductView 로그 기록 (비동기 권장)
        self.log_product_view(request, instance)

        return super().retrieve(request, *args, **kwargs)

    def log_product_view(self, request, product):
        from products.models import ProductView

        ProductView.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key or '',
            referrer=request.META.get('HTTP_REFERER'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            ip_address=self.get_client_ip(request),
        )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**시리얼라이저**: `backend/products/serializers.py`
```python
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'display_order']

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    seller = SellerSerializer(read_only=True, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)

    # 추가 정보
    is_wishlist = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_is_wishlist(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from products.models import Wishlist
            return Wishlist.objects.filter(user=request.user, product=obj).exists()
        return False

    def get_related_products(self, obj):
        # 같은 카테고리 상품 추천
        related = Product.objects.filter(
            category=obj.category,
            status='active'
        ).exclude(id=obj.id).order_by('-quality_score')[:6]

        return ProductListSerializer(related, many=True).data
```

**URL**: `backend/products/urls.py`
```python
urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]
```

**커밋**: `feat: 상품 상세 API 구현 (조회수, 관련 상품)`

---

#### Task 1.3.2: 상품 목록 필터링 및 정렬 개선
**파일**: `backend/products/filters.py` (새 파일)

**작업 내용**:
```python
import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    # 가격 범위
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # 카테고리 (자손 포함)
    category = django_filters.NumberFilter(method='filter_category')

    # 판매자
    seller = django_filters.NumberFilter(field_name='seller__id')
    brand_slug = django_filters.CharFilter(field_name='seller__brand_slug')

    # 상품 유형
    product_type = django_filters.ChoiceFilter(choices=Product.PRODUCT_TYPE_CHOICES)

    # 태그
    is_best = django_filters.BooleanFilter()
    is_new = django_filters.BooleanFilter()
    is_on_sale = django_filters.BooleanFilter()

    # 검색
    search = django_filters.CharFilter(method='filter_search')

    # 정렬
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'newest'),
            ('price', 'price'),
            ('view_count', 'popular'),
            ('purchase_count', 'best_selling'),
            ('quality_score', 'recommended'),
            ('average_rating', 'rating'),
        )
    )

    class Meta:
        model = Product
        fields = []

    def filter_category(self, queryset, name, value):
        """카테고리 및 자손 카테고리 필터링"""
        try:
            category = Category.objects.get(id=value)
            descendants = category.get_descendants()
            category_ids = [category.id] + [c.id for c in descendants]
            return queryset.filter(category__in=category_ids)
        except Category.DoesNotExist:
            return queryset.none()

    def filter_search(self, queryset, name, value):
        """전체 텍스트 검색"""
        return Product.search(value)
```

**뷰 수정**: `backend/products/views.py`
```python
from django_filters.rest_framework import DjangoFilterBackend

class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return Product.objects.filter(status='active').select_related('category', 'seller')
```

**커밋**: `feat: 상품 필터링 및 정렬 기능 구현`

---

### 1.4 프론트엔드 기본 페이지 완성

#### Task 1.4.1: 상품 상세 페이지 구현
**파일**: `frontend/src/pages/ProductDetailPage.vue`

**작업 내용**:
```vue
<template>
  <div class="product-detail-page">
    <div v-if="loading" class="loading">로딩 중...</div>

    <div v-else-if="product" class="product-detail">
      <!-- 이미지 갤러리 -->
      <div class="image-gallery">
        <img :src="selectedImage" :alt="product.name" class="main-image" />
        <div class="thumbnail-list">
          <img
            v-for="(image, index) in allImages"
            :key="index"
            :src="image"
            @click="selectedImage = image"
            :class="{ active: selectedImage === image }"
          />
        </div>
      </div>

      <!-- 상품 정보 -->
      <div class="product-info">
        <h1>{{ product.name }}</h1>

        <div v-if="product.seller" class="brand">
          <router-link :to="`/brands/${product.seller.brand_slug}`">
            {{ product.seller.brand_name }}
          </router-link>
        </div>

        <div class="price">
          <span v-if="product.discount_rate > 0" class="original-price">
            {{ formatPrice(product.original_price) }}원
          </span>
          <span class="current-price">{{ formatPrice(product.price) }}원</span>
          <span v-if="product.discount_rate > 0" class="discount">
            {{ product.discount_rate }}%
          </span>
        </div>

        <div class="rating">
          ⭐ {{ product.average_rating }} ({{ product.review_count }}개 리뷰)
        </div>

        <div class="description">
          {{ product.short_description || product.description }}
        </div>

        <!-- 옵션 선택 -->
        <div class="options">
          <!-- TODO: 옵션 구현 -->
        </div>

        <!-- 수량 선택 -->
        <div class="quantity">
          <button @click="decreaseQuantity">-</button>
          <input v-model.number="quantity" type="number" min="1" />
          <button @click="increaseQuantity">+</button>
        </div>

        <!-- 액션 버튼 -->
        <div class="actions">
          <button @click="addToCart" class="btn-add-cart">장바구니</button>
          <button @click="addToWishlist" class="btn-wishlist">
            {{ product.is_wishlist ? '♥' : '♡' }}
          </button>
          <button @click="buyNow" class="btn-buy-now">바로구매</button>
        </div>
      </div>
    </div>

    <!-- 상세 탭 -->
    <div class="detail-tabs">
      <div class="tabs">
        <button @click="activeTab = 'detail'" :class="{ active: activeTab === 'detail' }">
          상세정보
        </button>
        <button @click="activeTab = 'reviews'" :class="{ active: activeTab === 'reviews' }">
          리뷰 ({{ product?.review_count }})
        </button>
        <button @click="activeTab = 'qna'" :class="{ active: activeTab === 'qna' }">
          문의
        </button>
      </div>

      <div class="tab-content">
        <div v-if="activeTab === 'detail'" class="detail-content">
          <div v-html="product?.description"></div>
        </div>
        <div v-else-if="activeTab === 'reviews'" class="reviews-content">
          <!-- TODO: 리뷰 목록 -->
        </div>
        <div v-else-if="activeTab === 'qna'" class="qna-content">
          <!-- TODO: 문의 목록 -->
        </div>
      </div>
    </div>

    <!-- 관련 상품 -->
    <div v-if="product?.related_products?.length" class="related-products">
      <h2>이런 상품은 어떠세요?</h2>
      <div class="product-grid">
        <ProductCard
          v-for="relatedProduct in product.related_products"
          :key="relatedProduct.id"
          :product="relatedProduct"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { productsAPI } from '@/api/products'
import { useCartStore } from '@/stores/cart'
import { useWishlistStore } from '@/stores/wishlist'
import { formatPrice } from '@/utils/format'
import ProductCard from '@/components/ui/ProductCard.vue'

const route = useRoute()
const cartStore = useCartStore()
const wishlistStore = useWishlistStore()

const product = ref(null)
const loading = ref(true)
const selectedImage = ref('')
const quantity = ref(1)
const activeTab = ref('detail')

const allImages = computed(() => {
  if (!product.value) return []
  const images = [product.value.main_image_url]
  if (product.value.images) {
    images.push(...product.value.images.map(img => img.image_url))
  }
  return images
})

onMounted(async () => {
  await loadProduct()
})

async function loadProduct() {
  try {
    loading.value = true
    const slug = route.params.slug
    product.value = await productsAPI.getProductBySlug(slug)
    selectedImage.value = product.value.main_image_url
  } catch (error) {
    console.error('Failed to load product:', error)
  } finally {
    loading.value = false
  }
}

function decreaseQuantity() {
  if (quantity.value > 1) quantity.value--
}

function increaseQuantity() {
  quantity.value++
}

function addToCart() {
  cartStore.addItem(product.value, quantity.value)
}

function addToWishlist() {
  wishlistStore.toggleItem(product.value)
}

function buyNow() {
  addToCart()
  // TODO: 주문 페이지로 이동
}
</script>
```

**API 수정**: `frontend/src/api/products.ts`
```typescript
export const productsAPI = {
  // ... 기존 메서드

  getProductBySlug: async (slug: string): Promise<Product> => {
    const response = await apiClient.get(`/api/products/${slug}/`)
    return response.data
  },
}
```

**라우터 추가**: `frontend/src/router/index.ts`
```typescript
{
  path: '/products/:slug',
  name: 'product-detail',
  component: () => import('@/pages/ProductDetailPage.vue'),
}
```

**커밋**: `feat: 상품 상세 페이지 구현`

---

#### Task 1.4.2: Wishlist 스토어 및 API 구현
**백엔드**: `backend/products/models.py`
```python
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlist_items'
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['product']),
        ]
```

**API**: `backend/products/views.py`
```python
class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """찜하기 토글"""
        product_id = request.data.get('product_id')
        wishlist, created = Wishlist.objects.get_or_create(
            user=request.user,
            product_id=product_id
        )

        if not created:
            wishlist.delete()
            return Response({'status': 'removed'})

        return Response({'status': 'added'})
```

**프론트엔드**: `frontend/src/stores/wishlist.ts`
```typescript
export const useWishlistStore = defineStore('wishlist', () => {
  const items = ref<Product[]>([])

  async function loadWishlist() {
    const response = await apiClient.get('/api/wishlist/')
    items.value = response.data.results
  }

  async function toggleItem(product: Product) {
    await apiClient.post('/api/wishlist/toggle/', { product_id: product.id })
    await loadWishlist()
  }

  return { items, loadWishlist, toggleItem }
})
```

**커밋**: `feat: 찜하기 기능 구현`

---

## Phase 2: 판매자 시스템 구현

### 2.1 판매자 등록 및 인증

#### Task 2.1.1: 판매자 등록 신청 API
**파일**: `backend/sellers/views.py`

**작업 내용**:
```python
class SellerRegistrationView(generics.CreateAPIView):
    serializer_class = SellerRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # User role을 seller로 변경
        user = self.request.user

        if hasattr(user, 'seller'):
            raise ValidationError('이미 판매자로 등록되어 있습니다.')

        seller = serializer.save(user=user, status='pending')

        # User role 업데이트는 관리자 승인 후
        # user.role = 'seller'
        # user.save()

        # 관리자에게 알림 (TODO: 이메일 발송)

        return seller
```

**시리얼라이저**:
```python
class SellerRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = [
            'brand_name', 'brand_description',
            'business_registration_number', 'business_type',
            'company_name', 'ceo_name',
            'business_phone', 'business_email',
            'business_address',
            'verification_document_url',
        ]

    def validate_business_registration_number(self, value):
        """사업자등록번호 검증"""
        if Seller.objects.filter(business_registration_number=value).exists():
            raise ValidationError('이미 등록된 사업자등록번호입니다.')

        # TODO: 국세청 API 연동하여 실제 검증

        return value
```

**URL**:
```python
path('sellers/register/', SellerRegistrationView.as_view(), name='seller-register'),
```

**커밋**: `feat: 판매자 등록 신청 API 구현`

---

#### Task 2.1.2: 판매자 인증 (관리자 승인)
**파일**: `backend/sellers/views.py`

```python
class SellerApprovalView(generics.UpdateAPIView):
    queryset = Seller.objects.all()
    serializer_class = SellerApprovalSerializer
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        seller = self.get_object()
        action = request.data.get('action')  # 'approve' or 'reject'

        if action == 'approve':
            seller.status = 'active'
            seller.is_verified = True
            seller.verified_at = timezone.now()
            seller.save()

            # User role 업데이트
            seller.user.role = 'seller'
            seller.user.save()

            # 판매자에게 승인 알림 (TODO: 이메일)

        elif action == 'reject':
            seller.status = 'inactive'
            seller.save()

            # 판매자에게 거절 알림

        return Response(self.get_serializer(seller).data)
```

**커밋**: `feat: 판매자 승인/거절 기능 구현`

---

### 2.2 판매자 상품 등록

#### Task 2.2.1: 판매자 상품 등록 API
**파일**: `backend/products/views.py`

```python
class SellerProductViewSet(viewsets.ModelViewSet):
    serializer_class = SellerProductSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        # 자신의 상품만 조회
        return Product.objects.filter(
            seller=self.request.user.seller
        ).select_related('category')

    def perform_create(self, serializer):
        serializer.save(
            seller=self.request.user.seller,
            product_type='seller',
            status='draft'  # 임시저장
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """상품 발행"""
        product = self.get_object()

        # 필수 정보 검증
        if not all([product.name, product.price, product.main_image_url, product.category]):
            raise ValidationError('필수 정보를 모두 입력해주세요.')

        product.status = 'active'
        product.published_at = timezone.now()
        product.save()

        return Response(self.get_serializer(product).data)
```

**시리얼라이저**:
```python
class SellerProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        exclude = ['seller', 'product_type']  # 자동 설정
        read_only_fields = ['view_count', 'click_count', 'purchase_count', ...]

    def validate(self, data):
        # 재고 관리 필수
        if 'stock_quantity' not in data:
            raise ValidationError('재고 수량을 입력해주세요.')

        return data
```

**URL**:
```python
router.register(r'seller/products', SellerProductViewSet, basename='seller-product')
```

**커밋**: `feat: 판매자 상품 등록 API 구현`

---

#### Task 2.2.2: 이미지 업로드 API
**파일**: `backend/products/views.py`

**작업 내용**:
```python
from django.core.files.storage import default_storage
from django.conf import settings

class ProductImageUploadView(APIView):
    permission_classes = [IsSeller]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, seller=request.user.seller)

        files = request.FILES.getlist('images')
        uploaded_images = []

        for file in files:
            # S3 또는 로컬 스토리지에 저장
            file_path = default_storage.save(f'products/{product_id}/{file.name}', file)
            file_url = default_storage.url(file_path)

            # ProductImage 생성
            image = ProductImage.objects.create(
                product=product,
                image_url=file_url,
                alt_text=file.name,
            )
            uploaded_images.append(image)

        serializer = ProductImageSerializer(uploaded_images, many=True)
        return Response(serializer.data)
```

**설정**: `backend/project_self/settings.py`
```python
# 로컬 개발 환경
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 프로덕션 (S3)
if not DEBUG:
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

**커밋**: `feat: 상품 이미지 업로드 API 구현`

---

### 2.3 판매자 대시보드

#### Task 2.3.1: 판매자 통계 API
**파일**: `backend/sellers/views.py`

```python
class SellerDashboardView(APIView):
    permission_classes = [IsSeller]

    def get(self, request):
        seller = request.user.seller

        # 기간 설정
        period = request.query_params.get('period', '7d')  # 7d, 30d, 90d
        start_date = self.get_start_date(period)

        # 통계 계산
        stats = {
            # 매출 통계
            'total_sales': self.get_total_sales(seller, start_date),
            'sales_chart': self.get_sales_chart(seller, start_date),

            # 주문 통계
            'total_orders': self.get_total_orders(seller, start_date),
            'order_status_breakdown': self.get_order_status_breakdown(seller),

            # 상품 통계
            'total_products': seller.total_products,
            'active_products': Product.objects.filter(seller=seller, status='active').count(),
            'out_of_stock': Product.objects.filter(seller=seller, stock_quantity=0).count(),

            # 리뷰 통계
            'total_reviews': seller.total_reviews,
            'average_rating': seller.average_rating,
            'recent_reviews': self.get_recent_reviews(seller),

            # 인기 상품
            'top_products': self.get_top_products(seller),
        }

        return Response(stats)

    def get_total_sales(self, seller, start_date):
        from orders.models import OrderItem
        return OrderItem.objects.filter(
            seller=seller,
            created_at__gte=start_date
        ).aggregate(total=Sum('total_price'))['total'] or 0

    def get_sales_chart(self, seller, start_date):
        """일별 매출 차트 데이터"""
        from orders.models import OrderItem
        from django.db.models.functions import TruncDate

        sales = OrderItem.objects.filter(
            seller=seller,
            created_at__gte=start_date
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            total=Sum('total_price')
        ).order_by('date')

        return list(sales)

    # ... 기타 통계 메서드
```

**URL**:
```python
path('sellers/dashboard/', SellerDashboardView.as_view(), name='seller-dashboard'),
```

**커밋**: `feat: 판매자 대시보드 통계 API 구현`

---

### 2.4 프론트엔드 판매자 페이지

#### Task 2.4.1: 판매자 등록 페이지
**파일**: `frontend/src/pages/seller/SellerRegistrationPage.vue`

**작업 내용**:
```vue
<template>
  <div class="seller-registration-page">
    <h1>판매자 등록</h1>

    <form @submit.prevent="handleSubmit">
      <!-- 브랜드 정보 -->
      <section>
        <h2>브랜드 정보</h2>
        <input v-model="form.brand_name" placeholder="브랜드명" required />
        <textarea v-model="form.brand_description" placeholder="브랜드 소개"></textarea>
      </section>

      <!-- 사업자 정보 -->
      <section>
        <h2>사업자 정보</h2>
        <select v-model="form.business_type" required>
          <option value="individual">개인사업자</option>
          <option value="corporate">법인사업자</option>
          <option value="cooperative">협동조합</option>
        </select>
        <input v-model="form.business_registration_number" placeholder="사업자등록번호" required />
        <input v-model="form.company_name" placeholder="상호명" />
        <input v-model="form.ceo_name" placeholder="대표자명" />
      </section>

      <!-- 연락처 -->
      <section>
        <h2>연락처</h2>
        <input v-model="form.business_phone" placeholder="사업장 전화번호" />
        <input v-model="form.business_email" type="email" placeholder="사업장 이메일" />
      </section>

      <!-- 사업자등록증 업로드 -->
      <section>
        <h2>서류 제출</h2>
        <input type="file" @change="handleFileUpload" accept=".pdf,.jpg,.png" />
      </section>

      <button type="submit" :disabled="loading">
        {{ loading ? '제출 중...' : '등록 신청' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { sellersAPI } from '@/api/sellers'

const router = useRouter()
const loading = ref(false)

const form = ref({
  brand_name: '',
  brand_description: '',
  business_type: 'individual',
  business_registration_number: '',
  company_name: '',
  ceo_name: '',
  business_phone: '',
  business_email: '',
  business_address: '',
  verification_document_url: '',
})

async function handleFileUpload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  const response = await sellersAPI.uploadDocument(formData)
  form.value.verification_document_url = response.url
}

async function handleSubmit() {
  try {
    loading.value = true
    await sellersAPI.register(form.value)
    alert('판매자 등록 신청이 완료되었습니다. 승인까지 1-3일 소요될 수 있습니다.')
    router.push('/mypage')
  } catch (error) {
    alert('등록 실패: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>
```

**API**: `frontend/src/api/sellers.ts`
```typescript
export const sellersAPI = {
  register: async (data: SellerRegistrationRequest): Promise<Seller> => {
    const response = await apiClient.post('/api/sellers/register/', data)
    return response.data
  },

  uploadDocument: async (formData: FormData): Promise<{ url: string }> => {
    const response = await apiClient.post('/api/sellers/upload-document/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },
}
```

**커밋**: `feat: 판매자 등록 페이지 구현`

---

#### Task 2.4.2: 판매자 대시보드 페이지
**파일**: `frontend/src/pages/seller/DashboardPage.vue`

**작업 내용**: (쿠팡 파트너스, 네이버 스마트스토어 참고)
```vue
<template>
  <div class="seller-dashboard">
    <!-- 상단 통계 카드 -->
    <div class="stats-cards">
      <div class="card">
        <h3>오늘의 매출</h3>
        <p class="amount">{{ formatPrice(stats.today_sales) }}원</p>
        <span class="change">+12.5% vs 어제</span>
      </div>
      <div class="card">
        <h3>주문 건수</h3>
        <p class="count">{{ stats.total_orders }}건</p>
      </div>
      <div class="card">
        <h3>평균 평점</h3>
        <p class="rating">⭐ {{ stats.average_rating }}</p>
      </div>
      <div class="card">
        <h3>등록 상품</h3>
        <p class="count">{{ stats.total_products }}개</p>
      </div>
    </div>

    <!-- 매출 차트 -->
    <div class="sales-chart">
      <h2>매출 추이</h2>
      <!-- TODO: Chart.js 또는 ECharts 사용 -->
      <canvas ref="salesChartCanvas"></canvas>
    </div>

    <!-- 최근 주문 -->
    <div class="recent-orders">
      <h2>최근 주문</h2>
      <table>
        <thead>
          <tr>
            <th>주문번호</th>
            <th>상품명</th>
            <th>수량</th>
            <th>금액</th>
            <th>상태</th>
            <th>액션</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in recentOrders" :key="order.id">
            <td>{{ order.order_number }}</td>
            <td>{{ order.product_name }}</td>
            <td>{{ order.quantity }}</td>
            <td>{{ formatPrice(order.total_price) }}원</td>
            <td>{{ order.status }}</td>
            <td>
              <button @click="handleOrder(order)">처리</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 인기 상품 -->
    <div class="top-products">
      <h2>인기 상품 Top 10</h2>
      <!-- 상품 목록 -->
    </div>

    <!-- 최근 리뷰 -->
    <div class="recent-reviews">
      <h2>최근 리뷰</h2>
      <!-- 리뷰 목록 -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { sellersAPI } from '@/api/sellers'
import { formatPrice } from '@/utils/format'

const stats = ref({})
const recentOrders = ref([])

onMounted(async () => {
  await loadDashboard()
})

async function loadDashboard() {
  stats.value = await sellersAPI.getDashboard({ period: '7d' })
  // ... 차트 렌더링
}
</script>
```

**커밋**: `feat: 판매자 대시보드 페이지 구현`

---

## Phase 3: 사용자 기능 완성

### 3.1 마이페이지

#### Task 3.1.1: 마이페이지 메인
**파일**: `frontend/src/pages/MyPage.vue`

```vue
<template>
  <div class="mypage">
    <aside class="sidebar">
      <nav>
        <router-link to="/mypage/profile">프로필</router-link>
        <router-link to="/mypage/orders">주문내역</router-link>
        <router-link to="/mypage/wishlist">찜한 상품</router-link>
        <router-link to="/mypage/reviews">내 리뷰</router-link>
        <router-link to="/mypage/addresses">배송지 관리</router-link>
        <router-link to="/mypage/payment-methods">결제 수단</router-link>

        <hr />

        <router-link v-if="user?.role === 'user'" to="/mypage/become-seller">
          판매자 전환
        </router-link>
        <router-link v-if="user?.role === 'seller'" to="/seller/dashboard">
          판매자 대시보드
        </router-link>
      </nav>
    </aside>

    <main class="content">
      <router-view />
    </main>
  </div>
</template>
```

**라우터**:
```typescript
{
  path: '/mypage',
  component: MyPage,
  meta: { requiresAuth: true },
  children: [
    { path: '', redirect: '/mypage/profile' },
    { path: 'profile', component: ProfilePage },
    { path: 'orders', component: OrdersPage },
    { path: 'wishlist', component: WishlistPage },
    { path: 'reviews', component: ReviewsPage },
    { path: 'addresses', component: AddressesPage },
    { path: 'payment-methods', component: PaymentMethodsPage },
    { path: 'become-seller', component: BecomeSellerPage },
  ]
}
```

**커밋**: `feat: 마이페이지 레이아웃 구현`

---

#### Task 3.1.2: 프로필 수정 페이지
**파일**: `frontend/src/pages/mypage/ProfilePage.vue`

```vue
<template>
  <div class="profile-page">
    <h1>프로필 수정</h1>

    <form @submit.prevent="handleSubmit">
      <!-- 프로필 이미지 -->
      <div class="profile-image">
        <img :src="form.profile_image_url || '/default-avatar.png'" alt="프로필" />
        <input type="file" @change="handleImageUpload" accept="image/*" />
      </div>

      <!-- 기본 정보 -->
      <input v-model="form.username" placeholder="사용자명" required />
      <input v-model="form.email" type="email" placeholder="이메일" disabled />
      <input v-model="form.phone_number" placeholder="전화번호" />

      <!-- 생년월일 -->
      <input v-model="form.date_of_birth" type="date" />

      <!-- 성별 -->
      <select v-model="form.gender">
        <option value="">선택 안함</option>
        <option value="male">남성</option>
        <option value="female">여성</option>
        <option value="other">기타</option>
      </select>

      <!-- 알림 설정 -->
      <label>
        <input v-model="form.notification_enabled" type="checkbox" />
        알림 수신
      </label>
      <label>
        <input v-model="form.marketing_agreed" type="checkbox" />
        마케팅 정보 수신
      </label>

      <button type="submit" :disabled="loading">저장</button>
    </form>

    <!-- 비밀번호 변경 -->
    <section class="password-section">
      <h2>비밀번호 변경</h2>
      <button @click="showPasswordModal = true">비밀번호 변경</button>
    </section>

    <!-- 회원 탈퇴 -->
    <section class="danger-zone">
      <h2>회원 탈퇴</h2>
      <button @click="handleDeleteAccount" class="btn-danger">회원 탈퇴</button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const authStore = useAuthStore()
const loading = ref(false)

const form = ref({
  username: '',
  email: '',
  phone_number: '',
  date_of_birth: '',
  gender: '',
  profile_image_url: '',
  notification_enabled: true,
  marketing_agreed: false,
})

onMounted(() => {
  if (authStore.user) {
    Object.assign(form.value, authStore.user)
  }
})

async function handleSubmit() {
  try {
    loading.value = true
    await authStore.updateUser(form.value)
    alert('프로필이 수정되었습니다.')
  } catch (error) {
    alert('수정 실패: ' + error.message)
  } finally {
    loading.value = false
  }
}

async function handleImageUpload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('profile_image', file)

  const response = await authApi.uploadProfileImage(formData)
  form.value.profile_image_url = response.url
}

async function handleDeleteAccount() {
  if (!confirm('정말로 탈퇴하시겠습니까?')) return

  await authApi.deleteAccount()
  await authStore.logout()
  router.push('/')
}
</script>
```

**커밋**: `feat: 프로필 수정 페이지 구현`

---

### 3.2 주문 및 결제

#### Task 3.2.1: Order 모델 생성
**파일**: `backend/orders/models.py` (새 앱 생성)

```bash
python manage.py startapp orders
```

**작업 내용**: (DATABASE_ERD.md 참고)
- Order 모델
- OrderItem 모델
- 주문 상태 관리
- 결제 연동 (아임포트/토스페이먼츠)

**커밋**: `feat: 주문 모델 구현`

---

#### Task 3.2.2: 주문 페이지 구현
**파일**: `frontend/src/pages/CheckoutPage.vue`

**작업 내용**:
- 장바구니에서 선택한 상품
- 배송지 선택/추가
- 결제 수단 선택
- 주문 금액 계산 (상품금액 + 배송비 - 할인)
- 결제 API 연동

**커밋**: `feat: 주문/결제 페이지 구현`

---

### 3.3 리뷰 시스템

#### Task 3.3.1: Review 모델 구현
**파일**: `backend/reviews/models.py`

**작업 내용**: (DATABASE_ERD.md 참고)
- Review 모델
- ReviewImage 모델
- ReviewHelpful 모델
- 리뷰 작성 (구매 인증)
- 판매자 답글

**커밋**: `feat: 리뷰 모델 구현`

---

#### Task 3.3.2: 리뷰 작성 페이지
**파일**: `frontend/src/components/ReviewForm.vue`

**작업 내용**:
- 별점 선택
- 리뷰 내용 작성
- 사진 업로드 (다중)
- 구매 인증 확인

**커밋**: `feat: 리뷰 작성 기능 구현`

---

## Phase 4: 추천 시스템 및 최적화

### 4.1 사용자 행동 로그 수집

#### Task 4.1.1: 행동 로그 모델 구현
**파일**: `backend/analytics/models.py`

**작업 내용**: (DATABASE_ERD.md 참고)
- ProductView 모델
- ProductClick 모델
- SearchLog 모델
- RecentlyViewedProduct 모델
- UserInteraction 모델

**커밋**: `feat: 사용자 행동 로그 모델 구현`

---

#### Task 4.1.2: 로그 수집 미들웨어
**파일**: `backend/analytics/middleware.py`

```python
class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 요청 전 처리
        request.start_time = time.time()

        response = self.get_response(request)

        # 요청 후 처리
        self.log_request(request, response)

        return response

    def log_request(self, request, response):
        # 특정 엔드포인트만 로깅
        if request.path.startswith('/api/products/'):
            # ProductView 로그 저장
            pass
```

**커밋**: `feat: 분석 로그 수집 미들웨어 구현`

---

### 4.2 기본 추천 알고리즘

#### Task 4.2.1: 품질 점수 기반 추천
**파일**: `backend/recommendations/services.py`

```python
class RecommendationService:
    @staticmethod
    def get_quality_based_recommendations(category_id=None, limit=20):
        """품질 점수 기반 추천 (콜드스타트)"""
        queryset = Product.objects.filter(status='active')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # 품질 점수 + CTR + 인기도 종합
        queryset = queryset.annotate(
            recommendation_score=F('quality_score') * 0.4 + F('ctr') * 100 * 0.3 + F('purchase_count') * 0.3
        ).order_by('-recommendation_score')

        return queryset[:limit]

    @staticmethod
    def get_personalized_recommendations(user, limit=20):
        """개인화 추천 (협업 필터링 기반)"""
        if not user.is_authenticated:
            return RecommendationService.get_quality_based_recommendations(limit=limit)

        # 사용자의 최근 관심사 (카테고리, 브랜드)
        recent_interactions = UserInteraction.objects.filter(user=user).order_by('-created_at')[:50]

        # ... 추천 로직

        return products
```

**커밋**: `feat: 기본 추천 알고리즘 구현 (품질 점수 기반)`

---

### 4.3 성능 최적화

#### Task 4.3.1: Redis 캐싱
**파일**: `backend/project_self/settings.py`

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

**캐싱 적용**:
```python
from django.core.cache import cache

class ProductListView(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        cache_key = f'products:list:{request.query_params.urlencode()}'
        data = cache.get(cache_key)

        if not data:
            data = super().list(request, *args, **kwargs).data
            cache.set(cache_key, data, 300)  # 5분

        return Response(data)
```

**커밋**: `feat: Redis 캐싱 구현`

---

#### Task 4.3.2: Celery 비동기 작업
**파일**: `backend/project_self/celery.py`

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('project_self')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 주기적 작업
app.conf.beat_schedule = {
    'update-product-stats': {
        'task': 'products.tasks.update_product_stats',
        'schedule': crontab(minute=0, hour='*/1'),  # 매 시간
    },
    'calculate-quality-scores': {
        'task': 'products.tasks.calculate_quality_scores',
        'schedule': crontab(minute=0, hour=3),  # 매일 새벽 3시
    },
}
```

**작업 정의**: `backend/products/tasks.py`
```python
from celery import shared_task

@shared_task
def update_product_stats():
    """상품 통계 업데이트 (view_count, purchase_count 등)"""
    # ... 배치 업데이트
    pass

@shared_task
def calculate_quality_scores():
    """상품 품질 점수 재계산"""
    for product in Product.objects.all():
        product.image_quality_score = product.calculate_image_quality_score()
        product.content_quality_score = product.calculate_content_quality_score()
        product.save()
```

**커밋**: `feat: Celery 비동기 작업 설정`

---

### 4.4 SEO 최적화

#### Task 4.4.1: 메타 태그 및 sitemap
**프론트엔드**: `frontend/src/utils/seo.ts`

```typescript
export function updateMetaTags(meta: {
  title?: string
  description?: string
  keywords?: string
  image?: string
  url?: string
}) {
  // Title
  document.title = meta.title || '농산물 직거래 플랫폼'

  // Meta tags
  const metaTags = [
    { name: 'description', content: meta.description },
    { name: 'keywords', content: meta.keywords },
    { property: 'og:title', content: meta.title },
    { property: 'og:description', content: meta.description },
    { property: 'og:image', content: meta.image },
    { property: 'og:url', content: meta.url },
    { name: 'twitter:card', content: 'summary_large_image' },
  ]

  metaTags.forEach(({ name, property, content }) => {
    if (!content) return

    const selector = name ? `meta[name="${name}"]` : `meta[property="${property}"]`
    let tag = document.querySelector(selector) as HTMLMetaElement

    if (!tag) {
      tag = document.createElement('meta')
      if (name) tag.name = name
      if (property) tag.setAttribute('property', property)
      document.head.appendChild(tag)
    }

    tag.content = content
  })
}
```

**상품 상세 페이지에 적용**:
```typescript
onMounted(async () => {
  await loadProduct()

  updateMetaTags({
    title: `${product.value.name} - 농산물 직거래`,
    description: product.value.short_description,
    keywords: `${product.value.category?.name}, ${product.value.name}`,
    image: product.value.main_image_url,
    url: window.location.href,
  })
})
```

**백엔드 sitemap**: `backend/project_self/sitemap.py`
```python
from django.contrib.sitemaps import Sitemap
from products.models import Product

class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Product.objects.filter(status='active')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/products/{obj.slug}'
```

**커밋**: `feat: SEO 최적화 (메타 태그, sitemap)`

---

## Phase 5: 관리자 시스템 및 배포

### 5.1 관리자 페이지

#### Task 5.1.1: Django Admin 커스터마이징
**파일**: `backend/products/admin.py`

```python
from django.contrib import admin
from .models import Product, Category

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_type', 'category', 'price', 'status', 'created_at']
    list_filter = ['product_type', 'status', 'category', 'is_best', 'is_featured']
    search_fields = ['name', 'description']
    readonly_fields = ['view_count', 'purchase_count', 'quality_score', 'ctr']

    fieldsets = (
        ('기본 정보', {
            'fields': ('product_type', 'category', 'seller', 'name', 'description')
        }),
        ('가격', {
            'fields': ('price', 'original_price', 'discount_rate')
        }),
        ('이미지', {
            'fields': ('main_image_url',)
        }),
        ('통계', {
            'fields': ('view_count', 'purchase_count', 'quality_score', 'ctr'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_best', 'mark_as_featured']

    def mark_as_best(self, request, queryset):
        queryset.update(is_best=True)
    mark_as_best.short_description = '베스트 상품으로 설정'

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = '추천 상품으로 설정'
```

**커밋**: `feat: Django Admin 커스터마이징`

---

### 5.2 배포 준비

#### Task 5.2.1: Docker 컨테이너화
**파일**: `Dockerfile` (백엔드)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY backend/ .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Gunicorn 실행
CMD ["gunicorn", "project_self.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**파일**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: ssafy_capstone
      POSTGRES_USER: ssafy_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build: .
    command: gunicorn project_self.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - ./backend:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DB_ENGINE=django.db.backends.postgresql
      - DB_NAME=ssafy_capstone
      - DB_USER=ssafy_user
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A project_self worker -l info
    volumes:
      - ./backend:/app
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A project_self beat -l info
    volumes:
      - ./backend:/app
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/static
      - media_volume:/media
    depends_on:
      - backend

  frontend:
    build: ./frontend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

**커밋**: `feat: Docker 컨테이너화 구성`

---

#### Task 5.2.2: CI/CD 파이프라인
**파일**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Django tests
        run: |
          cd backend
          pip install -r requirements.txt
          python manage.py test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to server
        run: |
          # SSH로 서버 접속 후 배포
          ssh user@server 'cd /app && docker-compose pull && docker-compose up -d'
```

**커밋**: `feat: GitHub Actions CI/CD 설정`

---

## 커밋 컨벤션

모든 커밋은 다음 형식을 따릅니다:

```
<타입>: <제목>

<본문 (선택사항)>
```

**타입**:
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가
- `chore`: 빌드 업무 수정, 패키지 매니저 설정 등

**예시**:
```
feat: 상품 상세 API 구현

- 상품 조회수 자동 증가
- ProductView 로그 기록
- 관련 상품 추천 로직 추가
```

---

## 프로젝트 완료 체크리스트

### Phase 1: 데이터베이스 및 백엔드 기반 구축
- [ ] User 모델 확장
- [ ] UserAddress 모델
- [ ] UserPaymentMethod 모델
- [ ] Category 계층 구조
- [ ] Product 모델 확장
- [ ] ProductImage 모델
- [ ] Seller 모델
- [ ] CSV 대량 임포트
- [ ] PostgreSQL 전환
- [ ] 전체 텍스트 검색
- [ ] Product 상세 API
- [ ] 상품 필터링/정렬
- [ ] 상품 상세 페이지 (프론트)
- [ ] Wishlist 기능

### Phase 2: 판매자 시스템
- [ ] 판매자 등록 API
- [ ] 판매자 인증
- [ ] 판매자 상품 등록 API
- [ ] 이미지 업로드
- [ ] 판매자 대시보드 API
- [ ] 판매자 등록 페이지 (프론트)
- [ ] 판매자 대시보드 페이지 (프론트)
- [ ] 판매자 상품 관리 페이지

### Phase 3: 사용자 기능
- [ ] 마이페이지 레이아웃
- [ ] 프로필 수정
- [ ] 배송지 관리
- [ ] 결제 수단 관리
- [ ] Order 모델
- [ ] 주문/결제 API
- [ ] 주문 페이지 (프론트)
- [ ] Review 모델
- [ ] 리뷰 API
- [ ] 리뷰 작성 페이지

### Phase 4: 추천 시스템 및 최적화
- [ ] 행동 로그 모델
- [ ] 로그 수집 미들웨어
- [ ] 품질 점수 기반 추천
- [ ] Redis 캐싱
- [ ] Celery 비동기 작업
- [ ] SEO 최적화

### Phase 5: 관리자 및 배포
- [ ] Django Admin 커스터마이징
- [ ] 관리자 웹 인터페이스 (선택)
- [ ] Docker 컨테이너화
- [ ] CI/CD 파이프라인
- [ ] 프로덕션 배포

---

## 최종 목표

✅ **MVP (Minimum Viable Product)**: Phase 1-2 완료 시 달성
✅ **Full Service**: Phase 1-4 완료 시 서비스 가능
✅ **Production Ready**: Phase 5 완료 시 실서비스 런칭 가능

**예상 소요 기간**:
- Phase 1: 2주
- Phase 2: 2주
- Phase 3: 3주
- Phase 4: 2주
- Phase 5: 1주

**총 예상 기간**: 10주 (약 2.5개월)
