# 홈플러스 → SelF 표준 카테고리 매핑 초안

> 목적: 홈플러스 원문 카테고리(`source_category_*`)를  
> SelF 표준 카테고리 12개(`docs/CATEGORY_STANDARD.md`)로 매핑하기 위한 규칙 정리

---

## 1. 매핑 개요

- **입력**: 홈플러스 원문 카테고리 경로
  - 예: `source_category_path = "수산물/건어물 > 생선 > 연어"`
- **출력**:
  - `service_category` (12개 표준 카테고리 중 1개)
  - `service_subcategory` (선택, 2depth 수준 서브카테고리)

> 실제 매핑 로직은 추후 DB 테이블(`Category`, `SourceCategory`, `CategoryMapping`)  
> 또는 JSON/YAML 룰로 구현하고, 이 문서는 그 “인간 가독성 버전”을 제공하는 것을 목표로 한다.

---

## 2. 매핑 규칙 구조(초안)

홈플러스 카테고리 구조는 실제 UI/JSON 분석을 통해 확정해야 하나,  
여기서는 **규칙 작성 포맷**과 **대표 예시**만 먼저 정의한다.

### 2-1. 규칙 테이블 포맷

| 규칙 ID | source_category_path 패턴               | rule_type | service_category           | service_subcategory | 비고                          |
| ------- | --------------------------------------- | --------- | -------------------------- | ------------------- | ----------------------------- |
| HP-001  | `^쌀/잡곡`                              | PREFIX    | GRAIN                      | NULL                | 쌀/잡곡 계열 전체             |
| HP-002  | `^채소`                                 | PREFIX    | VEGETABLE                  | NULL                | 채소 카테고리 전체            |
| HP-003  | `^과일`                                 | PREFIX    | FRUIT                      | NULL                | 과일 카테고리 전체            |
| HP-004  | `^수산물/건어물 > 생선`                 | PREFIX    | SEAFOOD                    | `생선`              | 생선류                        |
| HP-005  | `^수산물/건어물 > 해산물`               | PREFIX    | SEAFOOD                    | `해산물`            | 조개/갑각류 등                |
| HP-006  | `^수산물/건어물 > 해조류`               | PREFIX    | SEAFOOD                    | `해조류`            | 김/미역 등                    |
| HP-007  | `^우유/유제품`                          | PREFIX    | DAIRY                      | NULL                | 우유, 요거트, 치즈 등         |
| HP-008  | `^김치/반찬`                            | PREFIX    | KIMCHI_SIDE                | NULL                | 김치/밑반찬/절임류            |
| HP-009  | `^양념/오일/소스/장류`                  | PREFIX    | SEASONING_SAUCE_OIL        | NULL                | 양념/조미/소스/오일 전체      |
| HP-010  | `^정육/계란` AND path LIKE `%계란%`     | KEYWORD   | BEAN_EGG                   | `계란`              | 정육 내 계란 관련             |
| HP-011  | `^정육/계란` AND NOT path LIKE `%계란%` | KEYWORD   | MEAT                       | NULL                | 정육(육류)                    |
| HP-012  | 기타(매칭 실패)                         | FALLBACK  | NUT_DRY_ETC 또는 수동 분류 | NULL                | 로그로 남긴 후 수동 처리 대상 |

> `rule_type` 예시:
>
> - `EXACT`: 전체 경로 일치
> - `PREFIX`: 특정 prefix 로 시작
> - `KEYWORD`: 경로에 특정 키워드 포함 여부
> - `FALLBACK`: 어떤 룰에도 매칭되지 않을 때 기본값

### 2-2. 실제 홈플러스 카테고리 분석 TODO

- [ ] 홈플러스 카테고리 페이지/JSON 분석
  - [ ] `layoutResource.json` 또는 별도 카테고리 엔드포인트에서 전체 카테고리 트리 추출
  - [ ] 상위 카테고리 목록 (예: 쌀/잡곡, 채소, 과일, 정육/계란, 수산물/건어물, 우유/유제품, 김치/반찬, 양념/오일/소스/장류, 냉동, 베이커리 등) 정리
- [ ] 실제 경로 예시 수집
  - [ ] 각 상위 카테고리별로 5~10개 정도 `source_category_path` 샘플 수집
  - [ ] 샘플들을 표로 정리해 어떤 표준 카테고리에 들어가야 자연스러운지 논의
- [ ] 위 샘플을 기반으로 `HP-001 ~` 규칙 테이블을 점진적으로 채워 넣기

### 2-3. 쌀/잡곡(GRAIN) 규칙 상세

> 기준: `rcateNm`, `lcateNm`, `mcateNm`, `scateNm` 는  
> 홈플러스 상품 리스트 JSON(예: 쌀/잡곡 카테고리)에서 내려오는 값

#### 2-3-1. 기본 매핑 규칙

- 공통
  - 조건: `rcateNm == "쌀/잡곡"` AND `lcateNm == "쌀/잡곡"`
  - 매핑:
    - `service_category` = `GRAIN`
    - `service_subcategory` = `mcateNm` (중분류 이름 그대로 사용)
  - `source_category_*` 구성:
    - `source_category_l1` = `lcateNm` (예: `"쌀/잡곡"`)
    - `source_category_l2` = `mcateNm` (예: `"백미"`, `"콩/팥/보리/귀리"`)
    - `source_category_l3` = `scateNm` (예: `"10kg 이상 ~ 20kg 미만"`, `"콩류"`, `"현미"` 등)
    - `source_category_path` = `"쌀/잡곡 > {mcateNm} > {scateNm}"`

#### 2-3-2. 대표 예시 매핑

| 예시 ID | rcateNm | lcateNm | mcateNm         | scateNm               | source_category_path 예시              | service_category | service_subcategory |
| ------- | ------- | ------- | --------------- | --------------------- | -------------------------------------- | ---------------- | ------------------- |
| G-001   | 쌀/잡곡 | 쌀/잡곡 | 백미            | 10kg 이상 ~ 20kg 미만 | 쌀/잡곡 > 백미 > 10kg 이상 ~ 20kg 미만 | GRAIN            | 백미                |
| G-002   | 쌀/잡곡 | 쌀/잡곡 | 찹쌀/현미/흑미  | 현미                  | 쌀/잡곡 > 찹쌀/현미/흑미 > 현미        | GRAIN            | 찹쌀/현미/흑미      |
| G-003   | 쌀/잡곡 | 쌀/잡곡 | 찹쌀/현미/흑미  | 찹쌀                  | 쌀/잡곡 > 찹쌀/현미/흑미 > 찹쌀        | GRAIN            | 찹쌀/현미/흑미      |
| G-004   | 쌀/잡곡 | 쌀/잡곡 | 찹쌀/현미/흑미  | 흑미                  | 쌀/잡곡 > 찹쌀/현미/흑미 > 흑미        | GRAIN            | 찹쌀/현미/흑미      |
| G-005   | 쌀/잡곡 | 쌀/잡곡 | 콩/팥/보리/귀리 | 콩류                  | 쌀/잡곡 > 콩/팥/보리/귀리 > 콩류       | GRAIN            | 콩/팥/보리/귀리     |
| G-006   | 쌀/잡곡 | 쌀/잡곡 | 콩/팥/보리/귀리 | 보리류                | 쌀/잡곡 > 콩/팥/보리/귀리 > 보리류     | GRAIN            | 콩/팥/보리/귀리     |
| G-007   | 쌀/잡곡 | 쌀/잡곡 | 콩/팥/보리/귀리 | 팥류                  | 쌀/잡곡 > 콩/팥/보리/귀리 > 팥류       | GRAIN            | 콩/팥/보리/귀리     |
| G-008   | 쌀/잡곡 | 쌀/잡곡 | 수수/조/깨      | 조                    | 쌀/잡곡 > 수수/조/깨 > 조              | GRAIN            | 수수/조/깨          |
| G-009   | 쌀/잡곡 | 쌀/잡곡 | 혼합곡/수입잡곡 | 혼합곡                | 쌀/잡곡 > 혼합곡/수입잡곡 > 혼합곡     | GRAIN            | 혼합곡/수입잡곡     |

> 쌀/잡곡 계열에서는 **모든 조합이 하나의 표준 대분류(GRAIN)** 안으로 들어가며,  
> 추천·검색에서 필요한 추가 군집은 `service_subcategory`(= `mcateNm`)와 `usage_tags` 로 보완한다.

---

## 3. 구현 시 고려 사항

- **1차 구현**에서는:
  - 크롤링 JSON 의 `source_category_*` 만 신뢰하고,
  - `service_category` / `service_subcategory` 는 **없어도 동작 가능**하게 설계 (optional 필드)
- 카테고리 매핑 품질이 어느 정도 올라오면:
  - `service_category` 를 UI/추천/정렬의 기본 기준으로 사용
  - `service_subcategory` 와 `usage_tags` 로 더 정교한 필터링/추천에 활용
