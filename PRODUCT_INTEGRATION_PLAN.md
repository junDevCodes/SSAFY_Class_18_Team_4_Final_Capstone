# 제품 데이터 통합 MVP 구현 계획서

## 📋 프로젝트 목표

### 현재 단계: MVP (Minimum Viable Product)
**목표**: CSV 데이터를 백엔드 DB에 넣고, 프론트엔드에서 단순 검색/조회 기능 확인

**명확한 범위**:
1. ✅ CSV 데이터 → Django 데이터베이스 임포트
2. ✅ 백엔드 API 구축 (제품 리스트, 검색)
3. ✅ 프론트엔드 연동 (더미 데이터 → 실제 API 데이터)
4. ✅ 검색 페이지 기본 구현
5. ✅ 메인 페이지 "상품 더보기" 연결

**제외 사항** (향후 구현):
- ❌ 복잡한 추천 알고리즘 (SASRec, BERT4Rec 등)
- ❌ 상품 상세 페이지
- ❌ Redis 캐싱
- ❌ Celery 비동기 작업
- ❌ 고급 검색 알고리즘 (일단 단순 검색만)

## 📊 데이터 분석

### CSV 파일 구조
- **파일**: `data/merged_all_naver.csv`
- **총 제품 수**: 290개
- **카테고리**:
  - 과일/견과 (50개)
  - 수산물 (50개)
  - 육류 (50개)
  - 채소 (50개)
  - 간식/과자 (15개)
  - 냉동식품 (15개)
  - 밀키트/간편식 (15개)
  - 베이커리 (15개)
  - 수산/해산 (15개)
  - 우유/유제품 (15개)

### CSV 컬럼 매핑
```
CSV 컬럼                프론트엔드 필드
──────────────────────────────────────
category            →   category
product_name        →   name
price               →   price
image_url           →   image
description         →   desc
```

## 🏗️ 기술 스택 (확정)

### 백엔드
- **Framework**: Django 5.2.8
- **Database**: PostgreSQL 15
- **API**: Django REST Framework
- **인증**: 기존 authentication 모듈 (JWT)

### 프론트엔드
- **Framework**: Vue 3.5+ (Composition API)
- **Build Tool**: Vite 7+
- **Language**: TypeScript 5+
- **State**: Pinia 2+
- **Styling**: Tailwind CSS 3+
- **HTTP**: Axios
- **Icons**: Lucide Vue

### 미정 (향후 결정)
- Redis (캐싱)
- Celery (비동기 작업)

## 🗄️ 데이터베이스 스키마 (Simple MVP)

### 1. Category 테이블
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- "과일/견과", "수산물" 등
    slug VARCHAR(100) UNIQUE NOT NULL,  -- "fruits-nuts", "seafood" 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Product 테이블
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,

    -- CSV 데이터 매핑
    site_name VARCHAR(100),           -- 출처 (네이버쇼핑_컬리N마트)
    name VARCHAR(500) NOT NULL,       -- 제품명
    price INTEGER NOT NULL,           -- 가격
    unit VARCHAR(50),                 -- 단위
    description TEXT,                 -- 설명
    product_url TEXT,                 -- 제품 URL
    image_url TEXT NOT NULL,          -- 이미지 URL
    detail_info TEXT,                 -- 상세정보
    crawled_at TIMESTAMP,             -- 크롤링 시간

    -- MVP 추가 필드 (프론트엔드 호환)
    original_price INTEGER,           -- 원가 (할인 계산용)
    discount INTEGER DEFAULT 0,       -- 할인율 (%)
    is_best BOOLEAN DEFAULT FALSE,    -- 베스트 상품 여부

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 제약조건
    CONSTRAINT positive_price CHECK (price >= 0),
    CONSTRAINT valid_discount CHECK (discount >= 0 AND discount <= 100)
);

-- 기본 인덱스
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_name ON products(name);
```

**Note**: PostgreSQL 확장(pg_trgm), 풀텍스트 검색은 **Phase 2 (향후)**에 추가

## 📡 백엔드 API 설계 (MVP)

### 1. 제품 리스트 API
```
GET /api/products/

Query Parameters:
- category: 카테고리 필터 (optional)
- search: 검색어 (optional, 단순 LIKE 검색)
- page: 페이지 번호 (default: 1)
- page_size: 페이지 크기 (default: 20)

Response:
{
    "count": 290,
    "next": "http://localhost:8000/api/products/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "냉동 칠레산 블루베리 1kg",
            "price": 9990,
            "original_price": 9990,
            "discount": 0,
            "category": "과일/견과",
            "image_url": "https://...",
            "description": "냉동 칠레산 블루베리 1kg",
            "is_best": false
        },
        ...
    ]
}
```

### 2. 카테고리 리스트 API
```
GET /api/categories/

Response:
{
    "results": [
        {"id": 1, "name": "과일/견과", "slug": "fruits-nuts"},
        {"id": 2, "name": "수산물", "slug": "seafood"},
        ...
    ]
}
```

### 3. 검색 API (단순 버전)
```
GET /api/products/search/?q=사과

Response: (제품 리스트와 동일 구조)
```

## 🎨 프론트엔드 수정 사항

### 1. 타입 정의 업데이트
```typescript
// src/types/product.ts
export interface Product {
  id: number
  name: string
  price: number
  original_price: number
  discount: number
  category: string        // 추가: 카테고리명
  image_url: string       // 수정: image → image_url
  description: string     // 수정: desc → description
  is_best: boolean
}

export interface Category {
  id: number
  name: string
  slug: string
}
```

### 2. API 클라이언트
```typescript
// src/services/api/products.ts
import axios from 'axios'
import type { Product, Category } from '@/types/product'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const productsAPI = {
  // 제품 리스트 가져오기
  getProducts: async (params?: {
    category?: string
    search?: string
    page?: number
    page_size?: number
  }) => {
    const response = await axios.get(`${API_BASE_URL}/api/products/`, { params })
    return response.data
  },

  // 카테고리 리스트
  getCategories: async () => {
    const response = await axios.get(`${API_BASE_URL}/api/categories/`)
    return response.data
  },

  // 검색
  search: async (query: string, page = 1) => {
    const response = await axios.get(`${API_BASE_URL}/api/products/search/`, {
      params: { q: query, page }
    })
    return response.data
  }
}
```

### 3. Pinia 스토어 수정
```typescript
// src/stores/products.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product, Category } from '@/types/product'
import { productsAPI } from '@/services/api/products'

export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 제품 목록 가져오기
  const fetchProducts = async (params?: any) => {
    loading.value = true
    error.value = null
    try {
      const data = await productsAPI.getProducts(params)
      products.value = data.results
      return data
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // 카테고리 목록 가져오기
  const fetchCategories = async () => {
    try {
      const data = await productsAPI.getCategories()
      categories.value = data.results
    } catch (e: any) {
      console.error('카테고리 로딩 실패:', e)
    }
  }

  return {
    products,
    categories,
    loading,
    error,
    fetchProducts,
    fetchCategories
  }
})
```

### 4. 기존 컴포넌트 수정
- **ProductCard.vue**: `image` → `image_url`, `desc` → `description`
- **ProductList.vue**: API 호출 추가
- **HeroSection.vue**: "상품 더보기" 버튼 라우터 연결

### 5. 새 페이지 생성 (간단 버전)
```typescript
// src/views/SearchPage.vue - 단순 검색 결과 페이지
// src/views/ProductListPage.vue - 전체 상품 목록 페이지
```

## 📝 작업 계획 (MVP 단계)

### Phase 1: 백엔드 기본 구축 (1-2일)

#### Task 1.1: Django 앱 및 모델 생성
```bash
# products 앱 생성
cd backend
python manage.py startapp products

# settings.py에 앱 추가
INSTALLED_APPS += ['products']
```

**모델 정의** (`products/models.py`):
```python
from django.db import models

class Category(models.Model):
    """카테고리 모델"""
    name = models.CharField(max_length=100, unique=True, verbose_name="카테고리명")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="슬러그")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    """제품 모델"""
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        verbose_name="카테고리"
    )

    # CSV 필드
    site_name = models.CharField(max_length=100, null=True, verbose_name="출처")
    name = models.CharField(max_length=500, verbose_name="제품명")
    price = models.IntegerField(verbose_name="가격")
    unit = models.CharField(max_length=50, null=True, blank=True, verbose_name="단위")
    description = models.TextField(null=True, blank=True, verbose_name="설명")
    product_url = models.TextField(null=True, blank=True, verbose_name="제품 URL")
    image_url = models.TextField(verbose_name="이미지 URL")
    detail_info = models.TextField(null=True, blank=True, verbose_name="상세정보")
    crawled_at = models.DateTimeField(null=True, blank=True, verbose_name="크롤링 시간")

    # 추가 필드
    original_price = models.IntegerField(null=True, blank=True, verbose_name="원가")
    discount = models.IntegerField(default=0, verbose_name="할인율")
    is_best = models.BooleanField(default=False, verbose_name="베스트")

    # 메타
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = '제품'
        verbose_name_plural = '제품'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
```

**테스트** (`products/tests.py`):
```python
from django.test import TestCase
from products.models import Category, Product

class CategoryModelTest(TestCase):
    def test_category_creation(self):
        """카테고리가 정상적으로 생성되는지 테스트"""
        category = Category.objects.create(
            name="과일/견과",
            slug="fruits-nuts"
        )
        self.assertEqual(category.name, "과일/견과")
        self.assertEqual(str(category), "과일/견과")

class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="과일/견과",
            slug="fruits-nuts"
        )

    def test_product_creation(self):
        """제품이 정상적으로 생성되는지 테스트"""
        product = Product.objects.create(
            category=self.category,
            name="냉동 칠레산 블루베리 1kg",
            price=9990,
            image_url="https://example.com/image.jpg",
            description="맛있는 블루베리"
        )
        self.assertEqual(product.name, "냉동 칠레산 블루베리 1kg")
        self.assertEqual(product.price, 9990)
        self.assertEqual(product.category.name, "과일/견과")
```

```bash
# 마이그레이션 생성 및 적용
python manage.py makemigrations products
python manage.py migrate

# 테스트 실행
python manage.py test products
```

#### Task 1.2: CSV 데이터 임포트
**Management Command** (`products/management/commands/import_products.py`):
```python
import csv
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category, Product

class Command(BaseCommand):
    help = 'CSV 파일에서 제품 데이터 임포트'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='CSV 파일 경로')

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 카테고리 가져오기 또는 생성
                category_name = row['category']
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': slugify(category_name)}
                )

                # 가격 파싱
                try:
                    price = int(row['price']) if row['price'] else 0
                except ValueError:
                    price = 0

                # 이미지 URL 검증 (base64 placeholder 제외)
                image_url = row['image_url']
                if image_url.startswith('data:image'):
                    image_url = 'https://via.placeholder.com/400x500?text=No+Image'

                # 제품 생성 또는 업데이트
                Product.objects.update_or_create(
                    name=row['product_name'],
                    defaults={
                        'category': category,
                        'site_name': row['site_name'],
                        'price': price,
                        'original_price': price,  # MVP에서는 동일
                        'unit': row['unit'],
                        'description': row['description'],
                        'product_url': row['product_url'],
                        'image_url': image_url,
                        'detail_info': row['detail_info'],
                        'crawled_at': row['crawled_at'],
                    }
                )

        self.stdout.write(self.style.SUCCESS(f'Successfully imported products from {csv_file}'))
```

**테스트** (`products/tests.py`에 추가):
```python
from django.core.management import call_command
from io import StringIO

class ImportProductsTest(TestCase):
    def test_import_csv(self):
        """CSV 임포트가 정상 작동하는지 테스트"""
        # 테스트용 CSV 파일 경로
        csv_path = 'data/merged_all_naver.csv'

        # 임포트 실행
        out = StringIO()
        call_command('import_products', csv_path, stdout=out)

        # 데이터 확인
        self.assertGreater(Product.objects.count(), 0)
        self.assertGreater(Category.objects.count(), 0)
```

```bash
# CSV 임포트 실행
python manage.py import_products ../data/merged_all_naver.csv

# 확인
python manage.py shell
>>> from products.models import Product, Category
>>> Product.objects.count()  # 290개 확인
>>> Category.objects.all()   # 카테고리 확인
```

### Phase 2: 백엔드 API 구현 (1-2일)

#### Task 2.1: Serializer 작성
```python
# products/serializers.py
from rest_framework import serializers
from products.models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    """카테고리 시리얼라이저"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    """제품 시리얼라이저"""
    category = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'original_price', 'discount',
            'category', 'image_url', 'description', 'is_best'
        ]
```

**테스트**:
```python
from products.serializers import ProductSerializer

class ProductSerializerTest(TestCase):
    def test_product_serialization(self):
        """제품 시리얼라이저가 올바르게 작동하는지 테스트"""
        category = Category.objects.create(name="과일/견과", slug="fruits-nuts")
        product = Product.objects.create(
            category=category,
            name="테스트 상품",
            price=10000,
            image_url="https://example.com/image.jpg"
        )

        serializer = ProductSerializer(product)
        data = serializer.data

        self.assertEqual(data['name'], "테스트 상품")
        self.assertEqual(data['category'], "과일/견과")
        self.assertIn('image_url', data)
```

#### Task 2.2: ViewSet 작성
```python
# products/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from products.models import Category, Product
from products.serializers import CategorySerializer, ProductSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """카테고리 ViewSet (읽기 전용)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """제품 ViewSet (읽기 전용)"""
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # 카테고리 필터
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name=category)

        # 단순 검색 (LIKE)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """검색 액션"""
        query = request.query_params.get('q', '')

        if not query:
            return Response({'results': []})

        products = self.get_queryset().filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
```

**테스트**:
```python
from rest_framework.test import APITestCase
from rest_framework import status

class ProductAPITest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="과일/견과", slug="fruits-nuts")
        Product.objects.create(
            category=self.category,
            name="사과",
            price=5000,
            image_url="https://example.com/apple.jpg"
        )
        Product.objects.create(
            category=self.category,
            name="배",
            price=8000,
            image_url="https://example.com/pear.jpg"
        )

    def test_product_list(self):
        """제품 리스트 API 테스트"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_category_filter(self):
        """카테고리 필터 테스트"""
        response = self.client.get('/api/products/?category=과일/견과')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_search(self):
        """검색 API 테스트"""
        response = self.client.get('/api/products/search/?q=사과')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
```

#### Task 2.3: URL 설정
```python
# products/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.views import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]
```

```python
# project_self/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('api/', include('products.urls')),  # 추가
]
```

```bash
# API 테스트
python manage.py test products

# 서버 실행
python manage.py runserver 8000

# 브라우저에서 확인
# http://localhost:8000/api/products/
# http://localhost:8000/api/categories/
```

### Phase 3: 프론트엔드 연동 (2-3일)

#### Task 3.1: 환경 변수 설정
```bash
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8000
```

#### Task 3.2: 타입 정의 업데이트
```typescript
// frontend/src/types/product.ts
export interface Product {
  id: number
  name: string
  price: number
  original_price: number
  discount: number
  category: string
  image_url: string
  description: string
  is_best: boolean
}

export interface Category {
  id: number
  name: string
  slug: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
```

#### Task 3.3: API 클라이언트 구현
```typescript
// frontend/src/services/api/client.ts
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export default apiClient
```

```typescript
// frontend/src/services/api/products.ts
import apiClient from './client'
import type { Product, Category, PaginatedResponse } from '@/types/product'

export const productsAPI = {
  getProducts: async (params?: {
    category?: string
    search?: string
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Product>> => {
    const response = await apiClient.get('/api/products/', { params })
    return response.data
  },

  getCategories: async (): Promise<{ results: Category[] }> => {
    const response = await apiClient.get('/api/categories/')
    return response.data
  },

  search: async (query: string, page = 1): Promise<PaginatedResponse<Product>> => {
    const response = await apiClient.get('/api/products/search/', {
      params: { q: query, page }
    })
    return response.data
  }
}
```

#### Task 3.4: Pinia 스토어 리팩토링
```typescript
// frontend/src/stores/products.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product, Category } from '@/types/product'
import { productsAPI } from '@/services/api/products'

export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([])
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const totalCount = ref(0)

  const fetchProducts = async (params?: any) => {
    loading.value = true
    error.value = null
    try {
      const data = await productsAPI.getProducts(params)
      products.value = data.results
      totalCount.value = data.count
      return data
    } catch (e: any) {
      error.value = e.message
      console.error('제품 로딩 실패:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  const fetchCategories = async () => {
    try {
      const data = await productsAPI.getCategories()
      categories.value = data.results
    } catch (e: any) {
      console.error('카테고리 로딩 실패:', e)
    }
  }

  return {
    products,
    categories,
    loading,
    error,
    totalCount,
    fetchProducts,
    fetchCategories
  }
})
```

#### Task 3.5: 기존 컴포넌트 수정

**ProductCard.vue** (필드명 수정):
```vue
<template>
  <div class="group relative flex flex-col cursor-pointer">
    <div class="relative aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden mb-5">
      <!-- image → image_url -->
      <img :src="product.image_url" :alt="product.name" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105">

      <button
        @click.stop="handleAddToCart"
        class="absolute bottom-4 right-4 w-12 h-12 bg-white/90 backdrop-blur text-gray-900 rounded-full shadow-lg flex items-center justify-center opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 hover:bg-brand-600 hover:text-white transition-all duration-300 z-10"
      >
        <Plus :size="24" />
      </button>

      <div v-if="product.is_best" class="absolute top-0 left-0 bg-gray-900 text-white text-[10px] font-bold px-3 py-1.5 uppercase tracking-wider">Best</div>
    </div>

    <div>
      <!-- desc → description -->
      <div class="text-xs text-gray-500 mb-1 font-medium">{{ product.description }}</div>
      <h4 class="text-lg font-normal text-gray-900 mb-2 line-clamp-1 leading-tight group-hover:text-brand-600 transition-colors">{{ product.name }}</h4>
      <div class="flex items-center gap-2">
        <span v-if="product.discount > 0" class="text-red-500 font-bold">{{ product.discount }}%</span>
        <span class="font-bold text-xl text-gray-900">{{ formatPrice(product.price) }}</span>
      </div>
    </div>
  </div>
</template>
```

**ProductList.vue** (API 호출 추가):
```vue
<template>
  <section class="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
      <div>
        <h3 class="text-3xl font-display font-bold text-gray-900 mb-3">MD's Pick</h3>
        <p class="text-gray-500">전문 MD가 엄선한 가장 신선한 제철 상품</p>
      </div>
      <router-link to="/products" class="text-sm font-bold border-b border-gray-900 pb-0.5 hover:text-brand-600 hover:border-brand-600 transition-colors">전체보기</router-link>
    </div>

    <div v-if="productStore.loading" class="text-center py-20">
      <p class="text-gray-500">로딩 중...</p>
    </div>

    <div v-else-if="productStore.error" class="text-center py-20">
      <p class="text-red-500">{{ productStore.error }}</p>
    </div>

    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
      <ProductCard
        v-for="product in productStore.products.slice(0, 8)"
        :key="product.id"
        :product="product"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useProductStore } from '@/stores/products'
import ProductCard from '@/components/ui/ProductCard.vue'

const productStore = useProductStore()

onMounted(async () => {
  await productStore.fetchProducts({ page_size: 8 })
})
</script>
```

**HeroSection.vue** (라우터 연결):
```vue
<template>
  <section class="relative w-full h-[85vh] overflow-hidden bg-gray-900">
    <!-- ... 기존 코드 ... -->

    <div class="absolute inset-0 flex flex-col justify-center items-center text-center text-white px-4 z-10 mt-10">
      <!-- ... 기존 코드 ... -->

      <router-link to="/products">
        <button class="group relative px-8 py-4 bg-white text-gray-900 rounded-full font-bold text-sm tracking-wide overflow-hidden transition-all hover:scale-105 animate-fade-in-up shadow-[0_0_20px_rgba(255,255,255,0.3)]" style="animation-delay: 0.6s;">
          <span class="relative z-10 flex items-center gap-2">
            상품 더보기 <ArrowRight :size="16" class="transition-transform group-hover:translate-x-1" />
          </span>
        </button>
      </router-link>
    </div>
  </section>
</template>
```

#### Task 3.6: 라우터 설정
```typescript
// frontend/src/router/index.ts (새로 생성)
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/App.vue')
    },
    {
      path: '/products',
      name: 'ProductList',
      component: () => import('@/views/ProductListPage.vue')
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('@/views/SearchPage.vue')
    }
  ]
})

export default router
```

```typescript
// frontend/src/main.ts 수정
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

#### Task 3.7: 제품 리스트 페이지 생성
```vue
<!-- frontend/src/views/ProductListPage.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- 헤더 -->
    <AppHeader />

    <!-- 메인 컨텐츠 -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 class="text-4xl font-display font-bold mb-8">전체 상품</h1>

      <!-- 카테고리 필터 -->
      <div class="mb-8 flex gap-2 flex-wrap">
        <button
          @click="selectedCategory = null"
          :class="[
            'px-4 py-2 rounded-full text-sm font-medium transition-colors',
            selectedCategory === null
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          ]"
        >
          전체
        </button>
        <button
          v-for="category in productStore.categories"
          :key="category.id"
          @click="selectedCategory = category.name"
          :class="[
            'px-4 py-2 rounded-full text-sm font-medium transition-colors',
            selectedCategory === category.name
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          ]"
        >
          {{ category.name }}
        </button>
      </div>

      <!-- 로딩 -->
      <div v-if="productStore.loading" class="text-center py-20">
        <p class="text-gray-500">로딩 중...</p>
      </div>

      <!-- 에러 -->
      <div v-else-if="productStore.error" class="text-center py-20">
        <p class="text-red-500">{{ productStore.error }}</p>
      </div>

      <!-- 제품 그리드 -->
      <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
        <ProductCard
          v-for="product in productStore.products"
          :key="product.id"
          :product="product"
        />
      </div>

      <!-- 빈 상태 -->
      <div v-if="!productStore.loading && productStore.products.length === 0" class="text-center py-20">
        <p class="text-gray-500">제품이 없습니다.</p>
      </div>
    </main>

    <!-- 푸터 -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useProductStore } from '@/stores/products'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import ProductCard from '@/components/ui/ProductCard.vue'

const productStore = useProductStore()
const selectedCategory = ref<string | null>(null)

onMounted(async () => {
  await productStore.fetchCategories()
  await productStore.fetchProducts()
})

watch(selectedCategory, async (newCategory) => {
  await productStore.fetchProducts({
    category: newCategory || undefined
  })
})
</script>
```

#### Task 3.8: 검색 페이지 생성 (간단 버전)
```vue
<!-- frontend/src/views/SearchPage.vue -->
<template>
  <div class="min-h-screen bg-white">
    <AppHeader />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <!-- 검색바 -->
      <div class="mb-8">
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="상품을 검색하세요..."
          class="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-full focus:border-gray-900 focus:outline-none transition-colors"
        />
      </div>

      <!-- 검색 결과 -->
      <div v-if="loading" class="text-center py-20">
        <p class="text-gray-500">검색 중...</p>
      </div>

      <div v-else-if="searchResults.length > 0">
        <p class="mb-6 text-gray-600">
          "<strong>{{ searchQuery }}</strong>" 검색 결과 {{ searchResults.length }}개
        </p>
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-12">
          <ProductCard
            v-for="product in searchResults"
            :key="product.id"
            :product="product"
          />
        </div>
      </div>

      <div v-else-if="searchQuery" class="text-center py-20">
        <p class="text-gray-500">검색 결과가 없습니다.</p>
      </div>
    </main>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { productsAPI } from '@/services/api/products'
import type { Product } from '@/types/product'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import ProductCard from '@/components/ui/ProductCard.vue'

const searchQuery = ref('')
const searchResults = ref<Product[]>([])
const loading = ref(false)

let debounceTimer: number | null = null

const handleSearch = () => {
  if (debounceTimer) clearTimeout(debounceTimer)

  debounceTimer = window.setTimeout(async () => {
    if (searchQuery.value.trim().length < 2) {
      searchResults.value = []
      return
    }

    loading.value = true
    try {
      const data = await productsAPI.search(searchQuery.value)
      searchResults.value = data.results
    } catch (error) {
      console.error('검색 실패:', error)
    } finally {
      loading.value = false
    }
  }, 300)
}
</script>
```

### Phase 4: 통합 테스트 및 검증 (1일)

#### Task 4.1: 백엔드 테스트
```bash
cd backend
python manage.py test products

# 모든 테스트 통과 확인
# - 모델 테스트
# - CSV 임포트 테스트
# - API 테스트
```

#### Task 4.2: 프론트엔드 빌드 테스트
```bash
cd frontend
npm run type-check  # TypeScript 에러 없음
npm run build       # 빌드 성공
```

#### Task 4.3: 통합 확인
1. 백엔드 서버 실행: `python manage.py runserver 8000`
2. 프론트엔드 서버 실행: `npm run dev`
3. 브라우저에서 확인:
   - [ ] 메인 페이지에 실제 제품 데이터 표시
   - [ ] "상품 더보기" 버튼 클릭 → 제품 리스트 페이지 이동
   - [ ] 카테고리 필터링 작동
   - [ ] 검색 페이지에서 검색 작동
   - [ ] 이미지 로딩 확인
   - [ ] 장바구니 추가 기능 확인

## ✅ 완료 기준

### MVP 성공 조건
1. ✅ CSV 290개 제품 데이터 DB 임포트 완료
2. ✅ 백엔드 API 정상 작동 (제품 리스트, 카테고리, 검색)
3. ✅ 프론트엔드 더미 데이터 → 실제 API 데이터 전환
4. ✅ 메인 페이지 제품 표시
5. ✅ 제품 리스트 페이지 작동
6. ✅ 검색 페이지 기본 기능 작동
7. ✅ 카테고리 필터링 작동
8. ✅ 모든 테스트 통과

### 품질 기준
- [ ] 백엔드 테스트 모두 통과
- [ ] TypeScript 컴파일 에러 0개
- [ ] ESLint/Prettier 통과
- [ ] API 응답 시간 <500ms (현재 규모)
- [ ] 이미지 로딩 처리 (placeholder 대응)

## 📚 기술 문서

### API 문서 (DRF Browsable API)
- 제품 리스트: `http://localhost:8000/api/products/`
- 카테고리 리스트: `http://localhost:8000/api/categories/`
- 검색: `http://localhost:8000/api/products/search/?q=검색어`

### 다음 단계 (Phase 2 - 향후)
1. PostgreSQL 풀텍스트 검색 (pg_trgm, GIN 인덱스)
2. 검색 알고리즘 개선 (BM25 + Trigram)
3. 추천 시스템 데이터 수집
4. 상품 상세 페이지
5. Redis 캐싱
6. Celery 비동기 작업
7. SASRec 추천 알고리즘

## 🎯 최종 승인

이 계획안은 **MVP 단계에 완벽하게 맞춘** 실용적인 계획입니다.

**시작 준비 완료!** 🚀
