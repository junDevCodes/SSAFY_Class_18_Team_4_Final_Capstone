# Fixtures 데이터 로드 가이드

이 폴더는 심사용 초기 데이터를 포함하고 있습니다.

## 데이터 구성

| 파일 | 설명 | 레코드 수 |
|------|------|----------|
| `categories_*.csv` | 상품 카테고리 | 13개 |
| `products_*.csv` | 상품 기본 정보 | 7,276개 |
| `product_details_*.csv` | 상품 상세 설명 | 7,276개 |
| `product_images_*.csv` | 상품 이미지 | 19,828개 |
| `product_inventories_*.csv` | 재고 정보 | 7,276개 |
| `product_price_histories_*.csv` | 가격 변동 이력 | 11,051개 |
| `product_stats_*.csv` | 상품 통계 | 7,276개 |

## 사용 방법 (Docker 환경)

### 1. Docker Compose로 서비스 시작

```bash
# 프로젝트 루트로 이동
cd SSAFY_Class_18_Team_4_Final_Capstone

# Docker Compose로 전체 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps
```

### 2. Fixtures 데이터 로드

#### 심사용 (기존 데이터 삭제 후 로드) - 권장

```bash
docker exec self-backend python manage.py load_fixtures --clear
```

#### 기존 데이터 유지하며 로드 (안전 모드)

```bash
docker exec self-backend python manage.py load_fixtures
```

#### 데이터 존재 시 스킵

```bash
docker exec self-backend python manage.py load_fixtures --skip-if-exists
```

#### 검증만 수행 (실제 DB 변경 없음)

```bash
docker exec self-backend python manage.py load_fixtures --dry-run
```

### 3. 커맨드 옵션

| 옵션 | 설명 |
|------|------|
| `--clear` | 기존 상품 관련 데이터 삭제 후 로드 |
| `--skip-if-exists` | 상품 데이터가 이미 존재하면 로드 스킵 |
| `--dry-run` | 실제 DB 변경 없이 검증만 수행 |
| `--fixtures-dir <경로>` | fixtures 폴더 경로 직접 지정 |

### 4. 예상 실행 시간

- 전체 데이터 로드: 약 30초 ~ 1분
- `--clear` 옵션 사용 시: 약 1분

### 5. 로드 후 확인

```bash
# Django shell에서 확인
docker exec -it self-backend python manage.py shell

>>> from products.models import Product, Category
>>> Product.objects.count()
7276
>>> Category.objects.count()
13
```

## 주의사항

1. **프로덕션 환경에서는 `--clear` 옵션 사용 주의**
   - 기존 데이터가 모두 삭제됩니다

2. **Docker 서비스 실행 필수**
   - `docker-compose up -d` 로 서비스가 실행 중이어야 합니다

3. **판매자 자동 생성**
   - fixtures 로드 시 기본 판매자 (홈플러스, id=1)가 자동 생성됩니다

4. **ID 유지**
   - CSV의 ID 값이 그대로 사용되므로 기존 데이터와 충돌할 수 있습니다
   - 심사용으로 `--clear` 옵션 사용을 권장합니다

## 문제 해결

### "fixtures 폴더를 찾을 수 없습니다" 오류

Docker 환경에서는 자동으로 `/app/data/fixtures` 경로를 사용합니다.
수동 지정이 필요한 경우:

```bash
docker exec self-backend python manage.py load_fixtures --fixtures-dir /app/data/fixtures/
```

### "products CSV 파일이 필수입니다" 오류

- `data/fixtures/` 폴더에 `products_*.csv` 파일이 있는지 확인하세요

### 외래키 오류 발생 시

```bash
# 기존 데이터 삭제 후 재시도
docker exec self-backend python manage.py load_fixtures --clear
```

### 컨테이너가 실행 중이 아닌 경우

```bash
# 서비스 시작
docker-compose up -d

# 상태 확인
docker-compose ps
```
