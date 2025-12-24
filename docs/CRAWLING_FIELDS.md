# 크롤링 JSON 필드 정의

- 투입 경로: `data/json/processed/{사이트}_{크롤링일시}.json`
- 처리 흐름: processed → incoming → DB 적재 → backup(`_done_{처리시각}.json`)
- 스키마 준수: `data_pipeline.schemas.CrawlBatch`, `ProductData`

## 배치 메타 (CrawlBatch)

- `batch_id` (str): `{source}_{YYYYMMDD_HHMMSS}` 형태 고유 배치 ID
- `source` (str): 크롤링 대상 구분값(예: `naver`, `homeplus`, `coupang`)
- `crawled_at` (str, ISO 8601): 배치 크롤링 시작 시각
- `total_count` (int): 포함된 상품 개수
- `products` (ProductData[]): 상품 데이터 목록
- `status` (str, 기본 `pending`): 처리 상태(`pending|processing|completed|failed`)
- `processed_at` (str, ISO 8601, optional): DB 적재 완료 시각
- `error_message` (str, optional): 배치 처리 오류 메시지

## 상품 데이터 (ProductData)

- 필수
  - `name` (str): 상품명
  - `price` (int): 판매가(숫자만)
  - `source_site` (str): 노출 사이트/브랜드 식별자
  - `source_url` (str): 상품 상세 원본 URL (중복·업데이트 키)
  - `crawled_at` (str, ISO 8601): 상품 크롤링 시각
- 선택
  - `category_name` (str): 카테고리 명
  - `unit` (str): 판매 단위·중량 정보
  - `short_description` (str): 요약 설명
  - `full_description` (str): 상세 설명
  - `images` (ProductImage[]): 이미지 리스트
  - `original_price` (int): 정상가/비교가
  - `brand_name` (str): 브랜드명 또는 사이트 내 서브 브랜드

### 이미지 (ProductImage)

d

- `image_url` (str): 이미지 URL
- `display_order` (int, 기본 0): 노출 순서

## 예시 파일명

- `homeplus_20251208_030000.json` (processed에 투입)
- 처리 후 backup: `homeplus_20251208_030000_done_20251208_031500.json`

## 참고

- JSON 인코딩: UTF-8
- 숫자형 필드(`price`, `original_price`)는 정수로 제공
- `source_url`은 중복/가격 변경 감지 키이므로 반드시 고유 URL 사용

---

## 확장 필드 (카테고리/패싯)

### 카테고리(원문) 확장 필드

- `source_category_path` (str, optional): 크롤링 사이트의 **전체 카테고리 경로 문자열**
  - 예: `"수산물/건어물 > 생선 > 연어"`
- `source_category_l1` (str, optional): 원문 1depth 카테고리 (예: `"수산물/건어물"`)
- `source_category_l2` (str, optional): 원문 2depth 카테고리 (예: `"생선"`)
- `source_category_l3` (str, optional): 원문 3depth 카테고리 (예: `"연어"`)

### 서비스 표준 카테고리 매핑 필드

- `service_category` (str, optional): SelF 서비스 표준 **상위 카테고리(예: 12개 마스터 중 1개)**
  - 예: `"수산물/해산물/건어물"`, `"채소"`, `"육류"` 등
- `service_subcategory` (str, optional): SelF 서비스 **서브카테고리(추천/검색용 2depth)**
  - 예: `"생선"`, `"소고기"`, `"잎채소"` 등

> 원칙: 원문 카테고리(`source_category_*`)는 최대한 있는 그대로 저장하고,  
> 서비스 표준 카테고리(`service_*`)는 별도의 매핑 테이블(CategoryMapping) 기반으로 결정한다.

### 추천/검색 보조 패싯 필드

- `storage_type` (str, optional): 보관 방식
  - 값 예시: `ambient`(상온) / `chilled`(냉장) / `frozen`(냉동)
- `processing_level` (str, optional): 가공 수준
  - 값 예시: `raw`(원물) / `primary`(1차 가공) / `processed`(가공식품/HMR)
- `origin_scope` (str, optional): 원산지 범주
  - 값 예시: `domestic`(국내) / `imported`(수입) / `mixed`(혼합/표기불명)
- `usage_tags` (str[], optional): 용도 태그(다중값)
  - 값 예시: `["soup", "grill"]`, `["salad"]`, `["baking"]` 등
  - 대표 태그 후보: `soup`(국/찌개), `stir_fry`(볶음), `grill`(구이), `salad`(샐러드),  
    `snack`(간식), `baking`(베이킹), `etc`(기타)
