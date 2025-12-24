## 관리자 분석 섹션 & 지표 정의

> 목적: 관리자 통계/운영 대시보드의 각 섹션이 **어떤 역할**을 하고,  
> 어떤 지표를 “핵심/보조” 로 가져가야 하는지 정리하여 유지보수 기준을 통일합니다.

---

## 1. 핵심 지표 · Top Line (`AdminAnalyticsPage.vue`)

### 1-1. 섹션 역할

- **대상**: CEO / PM / 비즈니스 오너
- **목적**: 서비스의 전반적인 성과를 한 눈에 확인하고, 이상 징후가 있을 때 바로 Drill-down 진입.

### 1-2. 핵심 지표 (필수)

- **매출/주문**
  - `총 매출(GMV)` – 집계 기간 내 전체 결제 금액 합
  - `주문 수` – 기간 내 성공 주문 수
- **전환/효율**
  - `객단가(AOV)` – GMV / 주문 수
  - `전환율` – 세션 대비 주문 수 (Top Line 추이에서 근사 계산)
  - `장바구니→구매 전환율` – `AdminBizDaily.cart_adds` 대비 `orders` 비율
- **재구매/충성도 (샘플 기준)**
  - `재구매율(30D)` – 샘플/시연용 지표, 실제 구현 시 별도 코호트/재구매 분석으로 대체 가능

### 1-3. 보조 지표 / 시각화

- **추이 차트**
  - 축: 일/주/월 단위 (`Granularity`)  
  - 값: `revenue`, `orders`, `conversion`
- **카테고리 분해**
  - `AdminCategoryDaily` 기준 Top 카테고리들의:
    - 세션 수
    - 주문 수
    - 전환율
    - 매출

### 1-4. 리스크/To-do (Top 1)

- **Risk & Actions 섹션**:
  - 데이터 소스: `AdminOpsOverviewView` (`alerts`, `todos`)
  - 로직:
    - `alerts` 중 severity 순서(`high → medium → low`) 기준으로 Top1 선택.
    - 선택된 alert를 핵심 지표용 `RiskAlert` 포맷으로 변환해 한 줄만 노출.
    - `todos` 중 `related_alert_id` 가 Top1 alert 와 연결된 항목이 있으면 그 1건만 노출.
    - 없으면 `todos[0]` 1건만 fallback.
- **의도**:
  - 운영 페이지에서 모든 Alert/To-do/Incident 를 관리하되,  
  - 핵심 지표에서는 “가장 심각한 리스크 + 그에 대한 대표 액션 1개”만 보여주는 요약 알림.

---

## 2. 유저 행동 지표 (`AdminBehaviorPage.vue`)

### 2-1. 섹션 역할

- **대상**: Product Manager, Growth/CRM 담당자
- **목적**: 유저 풀의 활성도, 퍼널 병목, 장바구니 전환 상황을 관찰.

### 2-2. 핵심 지표 (필수)

- `구매 DAU(추정)` – 기간 내 `unique_buyers` 합을 일수로 나눈 값
- `구매 MAU(합산 기준 추정)` – 기간 내 `unique_buyers` 합
- `장바구니→구매 전환율` – 기간 내 `cart_adds` 대비 `orders` 비율

### 2-3. 보조 지표

- `장바구니 포기율(추정)` – `100 - 장바구니→구매 전환율`
  - 핵심 전환율 대비 보조 관점으로 유지.

### 2-4. 시각화/퍼널

- **추이 차트**
  - 축: 날짜
  - 값:
    - 구매자 수 (`buyers`)
    - 장바구니 담기 수 (`cart_adds`)
    - 주문 수 (`orders`)
- **퍼널**
  - 세션 → 장바구니 → 구매
  - 각 스텝별 절대값과 전 단계 대비 전환율 (`rate`).

---

## 3. 운영 건강도 지표 (`AdminOperationalPage.vue`)

### 3-1. 섹션 역할

- **대상**: 백엔드/데이터 엔지니어, 인프라/SRE
- **목적**: 크롤링/백엔드/인프라 레벨에서 서비스가 건강하게 돌아가는지 모니터링.

### 3-2. 데이터 소스

- `AdminOpsOverviewView` (`backend/analytics/views.py`)
  - 시계열: `OpsMetricPoint` 목록
    - `timestamp`
    - `crawling_success_rate`: 크롤러 성공률(또는 가용성 근사치)
    - `api_p95_ms`: **CloudWatch 모드에서는 EC2 CPU 사용률(%)** 로 사용
    - `error_rate`: **CloudWatch 모드에서는 네트워크 트래픽(평균 Bytes)** 로 사용
    - `availability`: 가용성 근사 (%)
  - 요약: `kpis[]` – 상단 카드
  - `alerts[]`, `todos[]`, `incidents[]` – 운영 리스크/작업/장애 이력

> 필드 이름은 과거 설계(응답시간/에러율)를 유지하고 있으나,  
> CloudWatch(EC2) 모드에서는 CPU/네트워크 지표를 재사용하고 있으므로  
> **레이블과 문서에서 이를 명확히 표기**합니다.

### 3-3. 운영 KPI (현재 매핑)

- **크롤링 성공률**
  - label: `"크롤링 성공률"`
  - value: `crawling_success_rate` (%)
- **EC2 CPU 사용률**
  - label: `"EC2 CPU 사용률"`
  - value: `api_p95_ms` (실제 값은 CPUUtilization, 단위 `%`)
- **네트워크 트래픽**
  - label: `"네트워크 트래픽 (In)"`
  - value: `error_rate` (실제 값은 `NetworkIn` Average Bytes)
- **서비스 가용성**
  - label: `"서비스 가용성"`
  - value: `availability` (%)

### 3-4. 시각화

- **Trend 차트**
  - 좌측 축: 성공률/가용성(%) – 크롤링 성공률, 가용성
  - 우측 축: 네트워크 활동도 (Bytes 또는 MB 단위로 표시)

### 3-5. Alert · To-do · Incident

- 공통 스키마/규칙은 `docs/Admin_Analytics_alert_incident.md` 참고.
- CloudWatch 모드에서도 동일 스키마를 사용하되, Threshold/룰은 CPU/네트워크 기반으로 조정 가능.

---

## 4. 추천 알고리즘 성과 지표 (`AdminRecommendationPage.vue`)

### 4-1. 섹션 역할

- **대상**: 추천/ML 담당자, PM
- **목적**: 홈 추천 및 개별 placement/알고리즘의 CTR·구매 전환·기여 매출을 비교.

### 4-2. 핵심 지표 (홈 기준)

- 홈 추천 CTR – `홈 추천 CTR`
- 홈 추천 구매 전환율 – `홈 추천 구매 전환율`
- 홈 추천 기여 GMV 비율 – `홈 추천 기여 GMV 비율`

데이터 소스: `AdminRecoDaily` (`placement="home"`).

### 4-3. placement/알고리즘 요약

- `price_model`, `personalized`, `gapfill` 등 placement 별:
  - 노출 수 / 클릭 수
  - CTR
  - 구매 전환율
  - 기여 GMV 비율
- Placement Summary 테이블 + 인사이트 텍스트.

### 4-4. 시각화

- CTR & 구매 전환율 추이 (기간/그라뉼러리티에 따라 집계)
- 추천 기여 GMV 비율 추이.

---

## 5. 유저 관리 (`AdminUsersPage.vue`)

### 5-1. 섹션 역할

- **대상**: 운영 관리자
- **목적**: 유저 검색/필터링 + 역할/상태 변경 + 기본 정보 수정.

### 5-2. 요약 KPI (상단 카드)

- 전체 유저 수 (`total_users`) – guest 포함
- 활성 / 비활성 유저 수 (`active_users` / `inactive_users`)
- 판매자 / 관리자 수 (`seller_count` / `admin_count`)
- 최근 7일 신규 가입자 수 (`new_users_last_7d`)

### 5-3. 관리 액션

- 리스트 검색/필터:
  - 이메일/닉네임 검색 (`q`)
  - 역할 필터 (`role`)
  - 활성/비활성 필터 (`is_active`)
- 행 단위 액션:
  - 닉네임 편집 (인라인 편집 후 `PATCH /api/admin/users/{id}/`)
  - 역할 변경 (`user/seller/admin/guest`)
  - 계정 정지/해제 (`is_active` 토글)

---

## 6. 정렬/이동 기준 요약

섹션/지표를 이동하거나 새로 추가할 때는 아래 기준을 따릅니다.

- **핵심 지표(Top Line)**:
  - 비즈니스 임팩트가 큰 숫자 (매출, 주문, 전환, 장바구니→구매 전환).
  - “전체” 관점에서 유저/서비스를 합산한 값.
- **Behavior**:
  - DAU/MAU, 퍼널, 장바구니/구매 전환 등 **유저 여정 기반 지표**.
- **Operational**:
  - 크롤링/백엔드/인프라 상태 (성공률, CPU, 네트워크, 가용성, 장애/알림/To-do).
- **Recommendation**:
  - 추천 시스템 성과 (CTR/전환/기여 매출).
- **User Management**:
  - 개별 유저 단위의 속성/권한/상태 관리.

새로운 지표를 추가할 때는:

1. **어떤 의사결정을 지원하는지** 먼저 정의하고,
2. 위 기준 중 어느 섹션에 속하는지 결정한 뒤,
3. 이 문서와 대응되는 Vue/Serializer/뷰 코드를 함께 업데이트합니다.


