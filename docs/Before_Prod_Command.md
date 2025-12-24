## 개요

SelF 서비스를 **로컬/개발 환경**과 **프로덕션(EC2)** 에서 처음 구동할 때 실행해야 하는 대표 명령어를 정리합니다.  
아래 순서를 따르면:

- DB 마이그레이션
- 슈퍼유저 생성
- 샘플/시나리오 기반 테스트 데이터 적재
- Admin Analytics 통계 대시보드 점검

까지 한 번에 준비할 수 있습니다.

---

## 1. 공통 사전 준비

- `.env` 파일 준비
  - 로컬 개발: `backend/.env`
  - 프로덕션: 리포지토리 루트의 `.env` (`docker-compose.prod.yml` 에서 참조)
- 필수 값
  - `DB_ENGINE=django.db.backends.postgresql`
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - 기타 이메일/도메인 관련 환경 변수는 기존 템플릿 참고

---

## 2. 로컬 개발 환경 (docker-compose.yml)

### 2-1. 첫 실행 (전체 스택 기동)

```bash
# 프로젝트 루트
docker compose up --build
```

- `backend` 컨테이너는 다음을 자동으로 수행:
  - `python manage.py migrate --noinput`
  - `django.contrib.sites.Site` 기본 도메인 `localhost:8000` 설정
  - `python manage.py process_json_data --show-details` (실패 시에도 서버 구동 계속)
  - `gunicorn project_self.wsgi:application --bind 0.0.0.0:8000`

### 2-2. Django 슈퍼유저 생성

```bash
docker compose exec backend python manage.py createsuperuser
```

### 2-3. Admin Analytics용 샘플 + 시나리오 데이터 생성

> 이 데이터는 **실제 DB에 저장되지만 `is_test=True`로 마킹**되며,  
> 통계 화면에서 “테스트 데이터 + 실데이터 / 실데이터만” 모드로 구분해 볼 수 있습니다.

```bash
# 14일치 기본 샘플 + 일간 집계 + 추천/카테고리 샘플
docker compose exec backend python manage.py seed_admin_analytics_sample --days 14

# Behavior 시나리오(프로모션/장바구니 증가 등)까지 반영한 고급 샘플
docker compose exec backend python manage.py seed_admin_analytics_scenarios --days 14
```

- `seed_admin_analytics_sample`
  - admin-demo용 유저/주문/결제 생성
  - 비즈니스 집계(`AdminBizDaily`), 추천 집계(`AdminRecoDaily`), 카테고리 집계(`AdminCategoryDaily`) 생성
  - 생성된 집계는 모두 `is_test=True`
- `seed_admin_analytics_scenarios`
  - `AdminBizDaily.sessions`, `cart_adds` 에 시나리오별 패턴 적용
  - `is_test=True`, `scenario=baseline/promo/high_abandon/loyal` 으로 저장

### 2-4. Admin Analytics 집계 재생성 (필요 시)

실제 주문/결제가 쌓인 뒤 Admin Analytics용 집계를 다시 쌓고 싶을 때:

```bash
# 특정 날짜 범위 집계
docker compose exec backend python manage.py aggregate_biz_daily --start-date 2025-03-01 --end-date 2025-03-07

# 어제 날짜 집계 (인자 생략 시)
docker compose exec backend python manage.py aggregate_biz_daily
```

---

## 3. 프로덕션 환경 (docker-compose.prod.yml, EC2)

### 3-1. 첫 배포/시작

```bash
# .env, docker-compose.prod.yml 이 있는 디렉터리
docker compose -f docker-compose.prod.yml up -d
```

- `backend` 컨테이너는 다음을 자동으로 수행:
  - `python manage.py migrate --noinput`
  - `python manage.py collectstatic --noinput`
  - `django.contrib.sites.Site` 도메인: `${EC2_PUBLIC_IP:-localhost}`
  - `gunicorn project_self.wsgi:application --bind 0.0.0.0:8000 --workers 2`

### 3-2. 프로덕션 슈퍼유저 생성

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### 3-3. (선택) Admin Analytics용 테스트 시나리오 데이터 적재

운영 DB에 **데모용 테스트 시나리오 데이터**를 추가하고 싶을 때만 사용합니다.  
운영 정책에 따라 **스테이징/테스트 환경에만 사용하는 것을 권장**합니다.

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_admin_analytics_sample --days 14

docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_admin_analytics_scenarios --days 14
```

- 이미 실데이터가 쌓인 운영 환경에서는:
  - Admin Analytics 화면의 “데이터 범위” 필터에서
    - `테스트 데이터 + 실데이터` (기본)  
    - `실데이터만`
    를 선택해서 운영 데이터만 보는 것을 추천.

---

## 4. 크롤러 / 예측 서버 batch 확인 (선택)

### 4-1. 크롤러 메인 엔트리 실행 (로컬)

```bash
cd crawler
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 4-2. 예측 서버(pred) 단독 기동 (로컬 도커)

```bash
docker compose up pred
```

> pred 컨테이너는 PostgreSQL `products` 테이블이 준비될 때까지 대기 후  
> `uvicorn main:app --host 0.0.0.0 --port 8001` 로 기동됩니다.

---

## 5. Admin 통계 페이지 확인 체크리스트

1. `http://localhost:8000/admin` 접속 후 Django admin 로그인 (슈퍼유저).
2. 프론트엔드: `http://localhost:8080/admin` 진입.
3. 다음 페이지에서 샘플/시나리오 기반 통계가 정상 노출되는지 확인:
   - `핵심 지표`: Top Line + 리스크 알림/To-do
   - `유저 행동 지표`: DAU/MAU, 장바구니→구매 전환율, 퍼널
   - `운영 건강도 지표`: 크롤링 성공률, 에러율, 가용성, Alerts/To-do/Incidents
   - `추천 알고리즘 성과 지표`: 홈 추천 CTR/전환율, placement 요약

테스트 데이터는 언제든 Admin 페이지 상단 필터에서  
**“데이터 범위: 테스트 데이터 + 실데이터 / 실데이터만”** 으로 구분해서 볼 수 있습니다.


