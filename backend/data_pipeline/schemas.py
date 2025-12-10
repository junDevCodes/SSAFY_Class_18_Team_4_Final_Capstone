"""
데이터 파이프라인 JSON 스키마 정의

크롤링된 상품 데이터의 JSON 구조를 정의합니다.
신규 ERD (SelF_ERD_V2.1)와 호환되는 구조입니다.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
import json


@dataclass
class ProductImage:
    """상품 이미지 스키마"""
    image_url: str
    display_order: int = 0


@dataclass
class ProductData:
    """크롤링된 상품 데이터 스키마

    CSV 컬럼 매핑:
    - site_name → source_site
    - category → category_name
    - product_name → name
    - price → price
    - unit → unit
    - description → short_description
    - product_url → source_url
    - image_url → images[0].image_url
    - detail_info → full_description
    - crawled_at → crawled_at
    """

    # 필수 필드
    name: str
    price: int
    source_site: str
    source_url: str
    crawled_at: str  # ISO 8601 형식

    # 선택 필드
    category_name: Optional[str] = None
    unit: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None

    # 이미지 (리스트)
    images: List[ProductImage] = field(default_factory=list)

    # 가격 관련 (향후 확장)
    original_price: Optional[int] = None

    # 고유 식별자 (브랜드 + 상품명 조합으로 중복 체크)
    brand_name: Optional[str] = None  # source_site에서 추출 가능

    # 확장 필드 (원문 카테고리/서비스 카테고리/패싯)
    source_category_path: Optional[str] = None
    source_category_l1: Optional[str] = None
    source_category_l2: Optional[str] = None
    source_category_l3: Optional[str] = None
    service_category: Optional[str] = None
    service_subcategory: Optional[str] = None
    storage_type: Optional[str] = None
    processing_level: Optional[str] = None

    # 상세 설명 분리
    full_image_description: Optional[str] = None
    full_text_description: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        # 이미지 객체를 딕셔너리로 변환
        data['images'] = [asdict(img) if isinstance(img, ProductImage) else img for img in self.images]
        return data

    @classmethod
    def from_csv_row(cls, row: dict) -> 'ProductData':
        """CSV 행에서 ProductData 생성

        Args:
            row: CSV DictReader의 행 데이터

        Returns:
            ProductData 인스턴스
        """
        # 가격 파싱 (숫자만 추출)
        price_str = row.get('price', '0')
        price = int(''.join(filter(str.isdigit, str(price_str))) or '0')

        # 이미지 URL 처리
        images = []
        image_url = row.get('image_url', '').strip()
        if image_url:
            images.append(ProductImage(image_url=image_url, display_order=0))

        # 브랜드명 추출 (site_name에서)
        site_name = row.get('site_name', '')
        brand_name = cls._extract_brand_name(site_name)

        return cls(
            name=row.get('product_name', '').strip(),
            price=price,
            source_site=site_name,
            source_url=row.get('product_url', '').strip(),
            crawled_at=row.get('crawled_at', datetime.now().isoformat()),
            category_name=row.get('category', '').strip() or None,
            unit=row.get('unit', '').strip() or None,
            short_description=row.get('description', '').strip() or None,
            full_description=row.get('detail_info', '').strip() or None,
            images=images,
            brand_name=brand_name,
        )

    @staticmethod
    def _extract_brand_name(site_name: str) -> Optional[str]:
        """site_name에서 브랜드명 추출

        예: '네이버쇼핑_컬리N마트' → '컬리N마트'
        """
        if not site_name:
            return None

        # 언더스코어로 분리하여 마지막 부분 반환
        parts = site_name.split('_')
        if len(parts) > 1:
            return parts[-1]
        return site_name


@dataclass
class CrawlBatch:
    """크롤링 배치 스키마

    하나의 JSON 파일에 저장되는 크롤링 배치 데이터입니다.
    """

    # 배치 메타데이터
    batch_id: str  # 예: "naver_20251123_052455"
    source: str  # 데이터 소스 (예: "naver", "coupang")
    crawled_at: str  # 배치 크롤링 시작 시각
    total_count: int

    # 상품 데이터 리스트
    products: List[ProductData] = field(default_factory=list)

    # 배치 상태
    status: str = "pending"  # pending, processing, completed, failed
    processed_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'batch_id': self.batch_id,
            'source': self.source,
            'crawled_at': self.crawled_at,
            'total_count': self.total_count,
            'products': [p.to_dict() for p in self.products],
            'status': self.status,
            'processed_at': self.processed_at,
            'error_message': self.error_message,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> 'CrawlBatch':
        """딕셔너리에서 CrawlBatch 생성"""
        products = []
        for p in data.get('products', []):
            images = [ProductImage(**img) for img in p.get('images', [])]
            p['images'] = images
            products.append(ProductData(**{k: v for k, v in p.items() if k in ProductData.__dataclass_fields__}))

        return cls(
            batch_id=data['batch_id'],
            source=data['source'],
            crawled_at=data['crawled_at'],
            total_count=data['total_count'],
            products=products,
            status=data.get('status', 'pending'),
            processed_at=data.get('processed_at'),
            error_message=data.get('error_message'),
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'CrawlBatch':
        """JSON 문자열에서 CrawlBatch 생성"""
        return cls.from_dict(json.loads(json_str))
