# SelF 데이터 파이프라인 명세서

> **문서 버전**: v1.0.0
> **작성일**: 2025년 12월 01일
> **프로젝트명**: SelF (Special Selection All For You)

---

## 목차

1. [개요](#1-개요)
2. [아키텍처](#2-아키텍처)
3. [데이터 흐름](#3-데이터-흐름)
4. [JSON 스키마](#4-json-스키마)
5. [처리 로직](#5-처리-로직)
6. [사용 방법](#6-사용-방법)
7. [v2.1 분리 테이블 처리](#7-v21-분리-테이블-처리)

---

## 1. 개요

### 1.1 목적

데이터 파이프라인은 외부 크롤링 데이터를 표준화된 JSON 포맷으로 받아서 데이터베이스에 적재하는 모듈입니다.

### 1.2 주요 기능

- **JSON 데이터 파싱**: 크롤링 배치 데이터를 파싱하고 검증
- **중복 처리**: `source_url` 기준으로 기존 상품 식별
- **가격 변동 추적**: 기존 상품의 가격이 변경되면 `product_price_histories` 테이블에 기록
- **v2.1 분리 테이블 생성**: 신규 상품 등록 시 `ProductDetail`, `ProductInventory`, `ProductStats` 자동 생성
- **백업 관리**: 처리 완료된 JSON 파일을 백업 폴더로 이동

### 1.3 모듈 위치

```
backend/
├── data_pipeline/
│   ├── __init__.py
│   ├── schemas.py        # Pydantic 스키마 정의
│   └── processor.py      # 데이터 처리 로직
└── data/
    └── json/
        ├── incoming/     # 처리 대기 JSON 파일
        ├── processed/    # (예약, 미사용)
        └── backup/       # 처리 완료 백업
```

---

## 2. 아키텍처

### 2.1 컴포넌트 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Pipeline                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   schemas    │ -> │  processor   │ -> │   Django     │   │
│  │  (Pydantic)  │    │ (DataProcessor) │   │   Models     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  입력: data/json/incoming/*.json                             │
│  출력: data/json/backup/*_done_*.json                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 클래스 구조

| 클래스/모듈 | 설명 |
|------------|------|
| `CrawlBatch` | 크롤링 배치 전체 데이터를 나타내는 Pydantic 모델 |
| `ProductData` | 개별 상품 데이터를 나타내는 Pydantic 모델 |
| `ImageData` | 상품 이미지 데이터를 나타내는 Pydantic 모델 |
| `DataProcessor` | JSON 파일 처리 및 DB 적재 담당 클래스 |
| `PriceTracker` | 가격 변동 추적 유틸리티 클래스 |

---

## 3. 데이터 흐름

### 3.1 전체 흐름

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   크롤러     │ -> │  incoming   │ -> │  processor  │ -> │   Database  │
│   (외부)     │    │   폴더      │    │   처리      │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │                   │
                          │                   v
                          │           ┌─────────────┐
                          └---------->│   backup    │
                                      │   폴더      │
                                      └─────────────┘
```

### 3.2 상품 처리 흐름

```
상품 데이터 수신
       │
       v
┌──────────────────┐
│  source_url로    │
│  기존 상품 조회   │
└──────────────────┘
       │
       ├── 기존 상품 있음 ──────────────────┐
       │                                    │
       v                                    v
┌──────────────────┐              ┌──────────────────┐
│  신규 상품 생성   │              │  가격 비교       │
│                  │              │                  │
│  - Product       │              ├── 가격 동일 ─> skip
│  - ProductDetail │              │
│  - ProductInventory│            └── 가격 변동 ──┐
│  - ProductStats  │                              │
│  - ProductImage  │                              v
└──────────────────┘              ┌──────────────────┐
                                  │ ProductPriceHistory │
                                  │ 기록 + 가격 업데이트 │
                                  └──────────────────┘
```

---

## 4. JSON 스키마

### 4.1 CrawlBatch (배치 루트)

```typescript
interface CrawlBatch {
  batch_id: string;              // 배치 고유 ID (예: "curly_20251201_001")
  source: string;                // 데이터 출처 (예: "curly", "coupang")
  crawled_at: string;            // 크롤링 시각 (ISO 8601)
  status: "pending" | "completed" | "failed";  // 처리 상태
  processed_at: string | null;   // 처리 완료 시각
  products: ProductData[];       // 상품 배열
}
```

### 4.2 ProductData (상품)

```typescript
interface ProductData {
  // 필수 필드
  name: string;                  // 상품명 (최대 500자)
  price: number;                 // 판매가 (정수)
  source_site: string;           // 출처 사이트명 (예: "컬리", "쿠팡")
  source_url: string;            // 원본 상품 URL (중복 판단 기준)

  // 선택 필드
  brand_name: string | null;     // 브랜드명
  category_name: string | null;  // 카테고리명 (없으면 자동 생성)
  original_price: number | null; // 정상가/비교가
  short_description: string | null; // 짧은 설명
  full_description: string | null;  // 상세 설명 (HTML 가능)
  crawled_at: string | null;     // 크롤링 시각

  // 이미지
  images: ImageData[];           // 이미지 배열
}
```

### 4.3 ImageData (이미지)

```typescript
interface ImageData {
  image_url: string;             // 이미지 URL (필수)
  alt_text: string | null;       // 대체 텍스트
  display_order: number | null;  // 표시 순서 (기본: 인덱스)
}
```

### 4.4 예시 JSON 파일

```json
{
  "batch_id": "curly_20251201_001",
  "source": "curly",
  "crawled_at": "2025-12-01 10:30:00",
  "status": "pending",
  "processed_at": null,
  "products": [
    {
      "name": "[KF365] 유기농 시금치 200g",
      "price": 4900,
      "original_price": 5900,
      "source_site": "컬리",
      "source_url": "https://www.kurly.com/goods/12345",
      "brand_name": "KF365",
      "category_name": "채소",
      "short_description": "싱싱한 유기농 시금치",
      "full_description": "<p>국내산 유기농 시금치입니다...</p>",
      "crawled_at": "2025-12-01 10:25:00",
      "images": [
        {
          "image_url": "https://img.kurly.com/goods/12345_main.jpg",
          "alt_text": "유기농 시금치 메인 이미지",
          "display_order": 0
        },
        {
          "image_url": "https://img.kurly.com/goods/12345_detail.jpg",
          "alt_text": "유기농 시금치 상세 이미지",
          "display_order": 1
        }
      ]
    }
  ]
}
```

---

## 5. 처리 로직

### 5.1 DataProcessor 클래스

```python
class DataProcessor:
    """JSON 크롤링 데이터를 DB로 처리하는 클래스"""

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: 데이터 폴더 기본 경로 (기본: 프로젝트루트/data/json)
        """
        ...

    def get_pending_files(self) -> List[Path]:
        """처리 대기 중인 JSON 파일 목록 조회 (파일명 기준 시간순 정렬)"""
        ...

    def process_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """모든 대기 파일 처리

        Returns:
            처리 결과 요약 {
                total_files: int,
                processed_files: int,
                failed_files: int,
                total_products: int,
                new_products: int,
                updated_products: int,
                skipped_products: int,
                errors: List[Dict]
            }
        """
        ...

    def process_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, int]:
        """단일 JSON 파일 처리

        Returns:
            처리 결과 {total: int, new: int, updated: int, skipped: int}
        """
        ...
```

### 5.2 상품 처리 규칙

| 상황 | 처리 | 결과 |
|------|------|------|
| 새 상품 (`source_url` 없음) | 신규 생성 + v2.1 테이블 생성 | `new` |
| 기존 상품, 가격 변동 | 가격 업데이트 + 이력 기록 | `updated` |
| 기존 상품, 가격 동일 | 스킵 | `skipped` |
| 처리 실패 | 에러 로그 + 스킵 | `skipped` |

### 5.3 중복 판단 기준

- **Primary Key**: `source_url` (원본 상품 URL)
- **Fallback**: 없음 (source_url이 없으면 항상 신규 생성)

### 5.4 슬러그 생성 규칙

```python
def _make_slug(self, text: str) -> str:
    """한글을 포함한 텍스트에서 슬러그 생성

    1. 소문자 변환
    2. 특수문자 제거 (한글, 영문, 숫자, 공백 제외)
    3. 공백을 하이픈으로 변환
    4. 연속 하이픈 제거
    5. 앞뒤 하이픈 제거
    6. 최대 450자 제한
    """
    ...

def _get_unique_slug(self, base_slug: str, model_class) -> str:
    """고유한 슬러그 생성 (중복 시 숫자 추가)

    예: "유기농-시금치" -> "유기농-시금치-1" -> "유기농-시금치-2"
    """
    ...
```

---

## 6. 사용 방법

### 6.1 Django Management Command

```bash
# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 디렉토리 이동
cd backend

# 시뮬레이션 모드 (DB 변경 없음)
python manage.py process_crawl_data --dry-run

# 실제 처리
python manage.py process_crawl_data
```

### 6.2 Python 스크립트 직접 실행

```bash
# 시뮬레이션 모드
cd backend
python -m data_pipeline.processor

# 실제 처리 (dry_run=False로 수정 필요)
```

### 6.3 결과 예시

```
[정보] 처리 대기 파일: 3개
  - curly_20251201_001.json
  - coupang_20251201_001.json
  - ssg_20251201_001.json

=== 처리 결과 ===
총 파일: 3개
성공: 3개
실패: 0개
총 상품: 150개
  - 신규: 120개
  - 업데이트: 25개
  - 건너뜀: 5개
```

---

## 7. v2.1 분리 테이블 처리

### 7.1 신규 상품 생성 시 자동 생성되는 테이블

신규 상품이 등록되면 다음 테이블들이 함께 생성됩니다:

| 테이블 | 초기값 | 설명 |
|--------|--------|------|
| `Product` | (상품 데이터) | 메인 상품 정보 |
| `ProductDetail` | short_description, full_description | 상세 설명 |
| `ProductInventory` | stock_quantity=0, safe_stock_level=10 | 재고 정보 |
| `ProductStats` | view_count=0, quality_score=50.00 | 통계 정보 |
| `ProductImage` | (이미지 데이터) | 상품 이미지 |

### 7.2 가격 변동 시 처리

기존 상품의 가격이 변동되면:

1. `ProductPriceHistory` 테이블에 이력 추가
   - `old_price`: 이전 가격
   - `new_price`: 새 가격
   - `change_rate`: 자동 계산 `((new - old) / old * 100)`
   - `recorded_at`: 현재 시각

2. `Product.price` 업데이트

### 7.3 처리 코드 예시 (processor.py)

```python
# v2.1: 분리 테이블 생성
from products.models import ProductDetail as ProductDetailModel
from products.models import ProductInventory, ProductStats

# ProductDetail 생성
ProductDetailModel.objects.create(
    product=new_product,
    short_description=product.short_description,
    full_description=product.full_description,
)

# ProductInventory 생성
ProductInventory.objects.create(
    product=new_product,
    stock_quantity=0,
    safe_stock_level=10,
)

# ProductStats 생성
ProductStats.objects.create(
    product=new_product,
    view_count=0,
    quality_score=50.00,
)
```

---

## 부록: 에러 처리

### 일반 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `JSONDecodeError` | 잘못된 JSON 형식 | JSON 파일 검증 |
| `ValidationError` | Pydantic 스키마 불일치 | 필수 필드 확인 |
| `IntegrityError` | DB 제약 조건 위반 | 데이터 중복/형식 확인 |

### 로그 확인

```bash
# Django 로그 확인
tail -f logs/django.log

# 파이프라인 직접 실행 시 콘솔 출력 확인
```

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2025-12-01 | 최초 작성 |
