# Database Migrations Guide for pred Service

이 문서는 pred 서비스의 데이터베이스 마이그레이션 관리 방법을 설명합니다.

## 개요

pred 서비스는 **Alembic**을 사용하여 PostgreSQL 데이터베이스 스키마를 관리합니다.

- **Django 마이그레이션 아님**: pred는 FastAPI + asyncpg 기반이므로 Django 마이그레이션을 사용하지 않습니다.
- **버전 관리**: 모든 스키마 변경사항은 Git으로 관리되는 마이그레이션 파일로 추적됩니다.
- **롤백 가능**: 문제 발생 시 이전 버전으로 되돌릴 수 있습니다.

## 빠른 시작

### 새로운 개발 환경 설정

```bash
# 1. 저장소 클론 후 pred 디렉토리로 이동
cd pred

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 데이터베이스 마이그레이션 실행
alembic upgrade head

# 4. 테이블 생성 확인
psql -U selfuser -d selfdb -c "\dt pred_*"

# 5. 테스트 데이터 삽입
python scripts/insert_test_recipes.py
```

### 마이그레이션 상태 확인

```bash
# 현재 적용된 마이그레이션 버전 확인
alembic current

# 마이그레이션 히스토리 확인
alembic history --verbose

# 마이그레이션 파일 목록
ls -la alembic/versions/
```

## 데이터베이스 스키마

### 테이블 구조

#### 1. pred_ingredients (재료 마스터 테이블)

```sql
CREATE TABLE pred_ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    name_normalized VARCHAR(100),
    category VARCHAR(50),
    importance_score DECIMAL(3,2),
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**용도**: 레시피 재료 마스터 데이터

#### 2. pred_recipes (레시피 메인 테이블)

```sql
CREATE TABLE pred_recipes (
    id BIGSERIAL PRIMARY KEY,
    source_site VARCHAR(50) DEFAULT '10000recipe',
    source_id VARCHAR(50),
    source_url VARCHAR(500),
    name VARCHAR(200) NOT NULL,
    name_normalized VARCHAR(200),
    description TEXT,
    thumbnail_url VARCHAR(500),
    cooking_time_min INT,
    servings INT,
    difficulty VARCHAR(50),
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 0,
    rating_count INT DEFAULT 0,
    category_main VARCHAR(50),
    category_sub VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_recipes_source UNIQUE(source_site, source_id)
);
```

**용도**: AIRScout 모델의 레시피 추천 기반 데이터

**주요 인덱스**:
- `ix_pred_recipes_name` - 레시피명 검색
- `ix_pred_recipes_name_normalized` - 정규화된 이름으로 검색
- `ix_pred_recipes_category` - 카테고리별 조회
- `ix_recipes_popularity` - 인기순 정렬
- `ix_recipes_active` - 활성화된 레시피만 조회

#### 3. pred_recipe_ingredients (레시피-재료 관계)

```sql
CREATE TABLE pred_recipe_ingredients (
    id BIGSERIAL PRIMARY KEY,
    recipe_id BIGINT NOT NULL REFERENCES pred_recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES pred_ingredients(id) ON DELETE CASCADE,
    quantity_text VARCHAR(100),
    is_required BOOLEAN DEFAULT TRUE,
    is_main BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**용도**: 레시피와 재료의 다대다 관계 매핑

#### 4. pred_ingredient_products (재료-상품 매핑)

```sql
CREATE TABLE pred_ingredient_products (
    id BIGSERIAL PRIMARY KEY,
    ingredient_id INTEGER NOT NULL REFERENCES pred_ingredients(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL,  -- products 테이블 참조 (외래키 없음)
    similarity_score DECIMAL(3,2),
    mapping_method VARCHAR(50),
    priority SMALLINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**용도**: 레시피 Gap-Filling 추천을 위한 재료-상품 매핑

**참고**: `product_id`는 메인 데이터베이스의 `products` 테이블을 참조하지만, 유연한 배포를 위해 외래키 제약조건을 추가하지 않았습니다.

## 일반적인 작업

### 마이그레이션 적용

```bash
# 모든 마이그레이션 적용
cd pred
alembic upgrade head

# 특정 버전까지만 적용
alembic upgrade <revision_id>

# 한 단계씩 적용
alembic upgrade +1
```

### 마이그레이션 롤백

```bash
# 한 단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade <revision_id>

# 모든 마이그레이션 롤백 (주의!)
alembic downgrade base
```

### 새 마이그레이션 생성

```bash
# 마이그레이션 파일 생성
alembic revision -m "add_column_to_recipes"

# 생성된 파일 편집 (예: pred/alembic/versions/20251225_1234_xxxx_add_column_to_recipes.py)
```

**마이그레이션 파일 예제**:

```python
def upgrade() -> None:
    """Add new_field column to pred_recipes."""
    op.execute("""
        ALTER TABLE pred_recipes
        ADD COLUMN new_field VARCHAR(100)
    """)

def downgrade() -> None:
    """Remove new_field column from pred_recipes."""
    op.execute("""
        ALTER TABLE pred_recipes
        DROP COLUMN IF EXISTS new_field
    """)
```

## 마이그레이션 파일 작성 패턴

### 테이블 생성

```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE my_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS my_table CASCADE")
```

### 컬럼 추가

```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE pred_recipes
        ADD COLUMN tags TEXT[]
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE pred_recipes
        DROP COLUMN IF EXISTS tags
    """)
```

### 인덱스 생성

```python
def upgrade() -> None:
    op.execute("""
        CREATE INDEX ix_recipes_tags ON pred_recipes
        USING GIN (tags)
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recipes_tags")
```

### 외래키 추가

```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE pred_recipe_steps
        ADD CONSTRAINT fk_recipe_steps_recipe_id
        FOREIGN KEY (recipe_id) REFERENCES pred_recipes(id)
        ON DELETE CASCADE
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE pred_recipe_steps
        DROP CONSTRAINT IF EXISTS fk_recipe_steps_recipe_id
    """)
```

## 환경 설정

### 데이터베이스 연결 설정

마이그레이션은 `pred/core/config.py`의 설정을 사용합니다:

```python
# .env 파일 또는 환경변수
DB_HOST=localhost
DB_PORT=5432
DB_NAME=selfdb
DB_USER=selfuser
DB_PASSWORD=selfpass
```

`alembic/env.py`에서 자동으로 로드됩니다:

```python
from core.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url_async)
# postgresql+asyncpg://selfuser:selfpass@localhost:5432/selfdb
```

### asyncpg 지원

pred 서비스는 비동기 데이터베이스 액세스를 위해 asyncpg를 사용합니다. Alembic 환경도 이에 맞춰 구성되어 있습니다:

```python
# alembic/env.py
from sqlalchemy.ext.asyncio import async_engine_from_config

async def run_async_migrations():
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
```

## 테스트 및 검증

### 로컬 테스트

```bash
# 1. 새 마이그레이션 생성
alembic revision -m "test_migration"

# 2. upgrade() 함수 작성
# 파일: pred/alembic/versions/YYYYMMDD_HHMM_xxxx_test_migration.py

# 3. 마이그레이션 적용
alembic upgrade head

# 4. 데이터베이스 확인
psql -U selfuser -d selfdb -c "\d pred_recipes"

# 5. 롤백 테스트
alembic downgrade -1

# 6. 다시 적용
alembic upgrade head
```

### 검증 쿼리

```sql
-- 테이블 존재 확인
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'pred_%';

-- 인덱스 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'pred_recipes';

-- 외래키 확인
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name LIKE 'pred_%';

-- Alembic 버전 확인
SELECT * FROM alembic_version;
```

## 프로덕션 배포

### 배포 전 체크리스트

- [ ] 로컬에서 마이그레이션 테스트 완료
- [ ] 롤백 절차 확인 및 테스트 완료
- [ ] 데이터베이스 백업 완료
- [ ] 마이그레이션 스크립트 리뷰 완료
- [ ] 다운타임 발생 가능성 검토

### 배포 절차

```bash
# 1. 데이터베이스 백업
pg_dump -U selfuser -d selfdb > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 현재 버전 확인
alembic current

# 3. 보류 중인 마이그레이션 확인
alembic history

# 4. 마이그레이션 적용
alembic upgrade head

# 5. 테이블 확인
psql -U selfuser -d selfdb -c "\dt pred_*"

# 6. 애플리케이션 테스트
# - Health check
# - 데이터 조회 테스트
# - AIRScout 모델 동작 확인

# 7. 문제 발생 시 롤백
# alembic downgrade <previous_revision>
# psql -U selfuser -d selfdb < backup_YYYYMMDD_HHMMSS.sql
```

## 트러블슈팅

### "relation 'pred_recipes' does not exist"

**원인**: 마이그레이션이 실행되지 않음

**해결**:
```bash
alembic upgrade head
```

### "Can't locate revision identified by 'xxxx'"

**원인**: 데이터베이스의 alembic_version과 코드의 마이그레이션 파일이 불일치

**해결**:
```bash
# 현재 데이터베이스 버전 확인
psql -U selfuser -d selfdb -c "SELECT * FROM alembic_version;"

# 마이그레이션 파일 확인
ls pred/alembic/versions/

# 필요시 alembic_version 테이블 수정
psql -U selfuser -d selfdb -c "UPDATE alembic_version SET version_num = '<correct_version>';"
```

### "alembic: command not found"

**원인**: Alembic이 설치되지 않음

**해결**:
```bash
pip install alembic==1.13.1
```

### 마이그레이션 충돌

**원인**: 여러 개발자가 동시에 마이그레이션 생성

**해결**:
1. 최신 코드를 pull
2. 충돌하는 마이그레이션 파일 확인
3. 필요시 마이그레이션 순서 조정 (down_revision 수정)
4. 로컬에서 테스트 후 푸시

## 베스트 프랙티스

### 1. 작은 단위로 마이그레이션 생성

❌ 나쁜 예:
```python
# 한 마이그레이션에 너무 많은 변경사항
def upgrade():
    # 3개 테이블 생성
    # 10개 컬럼 추가
    # 5개 인덱스 생성
```

✅ 좋은 예:
```python
# Migration 1: 테이블 생성
def upgrade():
    op.execute("CREATE TABLE ...")

# Migration 2: 인덱스 추가
def upgrade():
    op.execute("CREATE INDEX ...")
```

### 2. 항상 downgrade() 구현

❌ 나쁜 예:
```python
def downgrade():
    pass  # 롤백 불가능!
```

✅ 좋은 예:
```python
def downgrade():
    op.execute("DROP TABLE IF EXISTS my_table CASCADE")
```

### 3. 멱등성(Idempotency) 고려

✅ 좋은 예:
```python
def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS my_table (...)
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS my_table CASCADE")
```

### 4. 설명적인 메시지 사용

❌ 나쁜 예:
```bash
alembic revision -m "update"
```

✅ 좋은 예:
```bash
alembic revision -m "add_tags_column_to_pred_recipes"
```

### 5. 프로덕션 적용 전 테스트

```bash
# 로컬에서 반드시 테스트
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## 추가 리소스

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [pred/alembic/README](../../pred/alembic/README) - Alembic 사용법
- [pred/core/config.py](../../pred/core/config.py) - 데이터베이스 설정
- [docs/pred/COMPLETE_ERD_AND_OPTIMIZATION.md](./COMPLETE_ERD_AND_OPTIMIZATION.md) - 전체 ERD

## 문의

마이그레이션 관련 문제가 발생하면 팀 슬랙 채널 또는 이슈 트래커에 문의하세요.
