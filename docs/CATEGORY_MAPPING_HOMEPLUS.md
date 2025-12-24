# 홈플러스 → SelF 표준 카테고리 매핑 규칙서

> 목적: 홈플러스 원문 카테고리(`source_category_l1~l3`, `source_category_path`)를  
> SelF 표준 카테고리 13개(`docs/CATEGORY_STANDARD.md`)로 **일관되게 매핑**하기 위한 규칙 정의

---

## 1. 매핑 규칙 테이블 (문자열/키워드 기반 보조 규칙)

### 1-1. 기본 규칙 포맷

| 규칙 ID | l1(lcateNm) 패턴                              | l2(mcateNm) 패턴/키워드                                              | l3(scateNm) 패턴/키워드 | service_category      | service_subcategory 규칙 | 비고                                                                                            |
| ------- | --------------------------------------------- | -------------------------------------------------------------------- | ----------------------- | --------------------- | ------------------------ | ----------------------------------------------------------------------------------------------- |
| HP-001  | `쌀/잡곡`                                     | `*`                                                                  | `*`                     | `GRAIN`               | `mcateNm`                | 쌀/잡곡 계열 전체 (원곡/혼합곡 포함). **Depth/ID 규칙이 없을 때 보조로 사용**                   |
| HP-010  | `채소`                                        | `*`                                                                  | `*`                     | `VEGETABLE`           | `mcateNm`                | 채소 계열 전체                                                                                  |
| HP-011  | (어떤 l1이든)                                 | `채소`,`야채`,`샐러드` 포함                                          | `*`                     | `VEGETABLE`           | `mcateNm`                | 냉동/가공 채소도 포함                                                                           |
| HP-020  | `과일`                                        | `*`                                                                  | `*`                     | `FRUIT`               | `mcateNm`                | 과일 계열 전체                                                                                  |
| HP-021  | (어떤 l1이든)                                 | `과일`,`사과`,`배`,`감귤`,`포도`,`바나나`,`베리` 등 포함             | `*`                     | `FRUIT`               | `mcateNm`                | 냉동/건조 과일도 포함                                                                           |
| HP-030  | `버섯`                                        | `*`                                                                  | `*`                     | `MUSHROOM_HERB`       | `mcateNm`                | 버섯 계열                                                                                       |
| HP-031  | `나물`                                        | `*`                                                                  | `*`                     | `MUSHROOM_HERB`       | `mcateNm`                | 나물/산채 계열                                                                                  |
| HP-032  | (어떤 l1이든)                                 | `버섯`,`표고`,`새송이`,`팽이`,`느타리` 포함                          | `*`                     | `MUSHROOM_HERB`       | `mcateNm`                | 다른 상위 카테고리(냉동 등)에 위치한 버섯도 포함                                                |
| HP-033  | (어떤 l1이든)                                 | `나물`,`시금치`,`고사리`,`고구마순` 포함                             | `*`                     | `MUSHROOM_HERB`       | `mcateNm`                | 냉동/가공 나물 포함                                                                             |
| HP-040  | `수산물/건어물`                               | `*`                                                                  | `*`                     | `SEAFOOD`             | `mcateNm`                | 수산물/건어물 전체                                                                              |
| HP-041  | (어떤 l1이든)                                 | `생선`,`연어`,`고등어`,`갈치`,`참치` 포함                            | `*`                     | `SEAFOOD`             | `mcateNm`                | 생선류                                                                                          |
| HP-042  | (어떤 l1이든)                                 | `새우`,`오징어`,`문어`,`낙지`,`게`,`조개` 포함                       | `*`                     | `SEAFOOD`             | `mcateNm`                | 갑각류/연체류                                                                                   |
| HP-043  | (어떤 l1이든)                                 | `미역`,`김`,`다시마`,`해조` 포함                                     | `*`                     | `SEAFOOD`             | `mcateNm`                | 해조류                                                                                          |
| HP-050  | `우유/유제품`                                 | `*`                                                                  | `*`                     | `DAIRY`               | `mcateNm`                | 우유/요거트/치즈/버터 등                                                                        |
| HP-051  | (어떤 l1이든)                                 | `우유`,`요거트`,`치즈`,`버터`,`크림` 포함                            | `*`                     | `DAIRY`               | `mcateNm`                | 유제품이 다른 상위 카테고리에 있는 경우 포함                                                    |
| HP-060  | `두부/김치/반찬`                              | `김치`,`장아찌`,`피클`,`반찬`,`조림` 포함                            | `*`                     | `KIMCHI_SIDE`         | `mcateNm`                | 김치/반찬/절임류                                                                                |
| HP-061  | `김치/반찬`                                   | `*`                                                                  | `*`                     | `KIMCHI_SIDE`         | `mcateNm`                | 상위 카테고리가 따로 존재하는 경우                                                              |
| HP-062  | `두부/김치/반찬`                              | `냉장장류` 또는 `장류` 포함                                          | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 두부/김치/반찬 L1 하위의 `냉장장류` 등 장류 카테고리(된장/고추장 등)                            |
| HP-063  | (어떤 l1이든)                                 | `김치` 포함                                                          | `*`                     | `KIMCHI_SIDE`         | `mcateNm`                | 모든 김치류                                                                                     |
| HP-064  | (어떤 l1이든)                                 | `장아찌`,`피클`,`절임` 포함                                          | `*`                     | `KIMCHI_SIDE`         | `mcateNm`                | 장아찌/피클/절임류                                                                              |
| HP-065  | (어떤 l1이든)                                 | `젓갈` 포함                                                          | `*`                     | `KIMCHI_SIDE`         | `mcateNm`                | 젓갈(반찬용)                                                                                    |
| HP-070  | `양념/오일/소스/장류`                         | `*`                                                                  | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 양념/조미/소스/오일 상위 카테고리 전체                                                          |
| HP-071  | `장류/양념/제빵`                              | `*`                                                                  | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 홈플러스 L1 `장류/양념/제빵` 케이스                                                             |
| HP-072  | (어떤 l1이든)                                 | `소금`,`설탕`,`식초`,`후추`,`향신료` 포함                            | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 기초 조미료                                                                                     |
| HP-073  | (어떤 l1이든)                                 | `소스`,`드레싱`,`케첩`,`마요네즈` 포함                               | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 소스/드레싱 계열                                                                                |
| HP-074  | (어떤 l1이든)                                 | `식용유`,`올리브유`,`버터오일` 포함                                  | `*`                     | `SEASONING_SAUCE_OIL` | `mcateNm`                | 오일/유지류                                                                                     |
| HP-080  | `정육/계란`                                   | `계란`,`알류`,`유정란`,`메추리알`,`가공란` 포함                      | `*`                     | `BEAN_EGG`            | `mcateNm`                | 정육/계란 L1 하위의 계란/알류                                                                   |
| HP-081  | `정육/계란`                                   | 위 HP-080 외의 모든 경우                                             | `*`                     | `MEAT`                | `mcateNm`                | 정육/계란 L1 하위의 한우/돼지/닭/가공육 등                                                      |
| HP-082  | (어떤 l1이든)                                 | `소고기`,`쇠고기`,`한우`,`수입육` 포함                               | `*`                     | `MEAT`                | `mcateNm`                | 소고기 계열                                                                                     |
| HP-083  | (어떤 l1이든)                                 | `돼지고기`,`삼겹살`,`목살`,`갈비`,`등심` 포함                        | `*`                     | `MEAT`                | `mcateNm`                | 돼지고기 계열                                                                                   |
| HP-084  | (어떤 l1이든)                                 | `닭고기`,`닭다리`,`닭가슴살`,`닭볶음탕` 포함                         | `*`                     | `MEAT`                | `mcateNm`                | 닭고기 계열                                                                                     |
| HP-085  | (어떤 l1이든)                                 | `오리고기`,`양고기` 포함                                             | `*`                     | `MEAT`                | `mcateNm`                | 기타 육류                                                                                       |
| HP-090  | `두부/김치/반찬`                              | `두부`,`유부`,`연두부` 포함                                          | `*`                     | `BEAN_EGG`            | `mcateNm`                | 두부 계열 (L1에 두부 포함)                                                                      |
| HP-091  | (어떤 l1이든)                                 | `두부`,`유부`,`연두부` 포함                                          | `*`                     | `BEAN_EGG`            | `mcateNm`                | 두부가 다른 상위 카테고리에 속한 경우 포함                                                      |
| HP-092  | (어떤 l1이든)                                 | `콩`,`두류`,`콩나물`,`건콩` 포함                                     | `*`                     | `BEAN_EGG`            | `mcateNm`                | 콩/두류 전반                                                                                    |
| HP-100  | `견과`                                        | `*`                                                                  | `*`                     | `NUT_DRY_ETC`         | `mcateNm`                | 홈플러스 L1 `견과`                                                                              |
| HP-101  | (어떤 l1이든)                                 | `견과`,`견과류`,`건과`,`건과일`,`씨앗` 포함                          | `*`                     | `NUT_DRY_ETC`         | `mcateNm`                | 견과/건과/씨앗류                                                                                |
| HP-110  | `라면/즉석식품/통조림`                        | `라면`,`컵라면` 포함                                                 | `*`                     | `NOODLE_FLOUR`        | `mcateNm`                | 라면 상위 카테고리. **Depth/ID 규칙(INSTANT_FOOD, NOODLE_FLOUR)에 매핑되지 않는 경우에만 사용** |
| HP-111  | (어떤 l1이든)                                 | `라면`,`국수`,`우동`,`소면`,`파스타`,`스파게티` 포함                 | `*`                     | `NOODLE_FLOUR`        | `mcateNm`                | 건면/생면/파스타 전반                                                                           |
| HP-112  | (어떤 l1이든)                                 | `밀가루`,`부침가루`,`튀김가루`,`핫케익믹스`,`케익믹스`,`베이킹` 포함 | `*`                     | `NOODLE_FLOUR`        | `mcateNm`                | 밀가루/가루/베이킹 기초                                                                         |
| HP-180  | (어떤 l1이든)                                 | `쌀`,`현미`,`잡곡`,`귀리`,`수수`,`조`,`깨`,`보리` 포함               | `*`                     | `GRAIN`               | `mcateNm`                | 곡물 계열 (가공 전 원곡 기준)                                                                   |
| HP-181  | (어떤 l1이든)                                 | `혼합곡`,`수입잡곡` 포함                                             | `*`                     | `GRAIN`               | `mcateNm`                | 혼합곡/수입잡곡                                                                                 |
| HP-190  | (어떤 l1이든)                                 | `과일`, `사과`,`배`,`감귤`,`만감`,`딸기`,`베리`,`바나나` 등 포함     | `*`                     | `FRUIT`               | `mcateNm`                | 세부 과일 키워드 기반                                                                           |
| HP-200  | (어떤 l1이든)                                 | `야채`,`채소`,`샐러드` 포함                                          | `*`                     | `VEGETABLE`           | `mcateNm`                | 세부 채소 키워드 기반                                                                           |
| HP-250  | (어떤 l1이든, 식품 카테고리)                  | 위 어떤 규칙에도 매칭되지 않지만 **원물/기초 식재료** 인 경우        | `*`                     | `NUT_DRY_ETC`         | `mcateNm`                | 잡곡류/건조채소 등 기타 식재료 (향후 세분화 대상)                                               |
| HP-999  | (어떤 l1이든, 비식품 또는 불명 식품 카테고리) | 위 규칙에 모두 매칭 실패                                             | `*`                     | `NULL`                | `NULL`                   | 비식품/미매핑(로그 후 수동 검토, 기본적으로 service_category=None)                              |

> 규칙 적용 순서는 위에서 아래로이며, 처음 매칭되는 규칙의  
> `service_category` / `service_subcategory` 를 사용한다.  
> 모든 규칙에 매칭되지 않는 경우(HP-999)는 `service_category=None` 으로 두고 비식품/예외로 처리한다.

---

## 2. 이후 디벨롭 계획

- [ ] **실제 카테고리 맵(JSON)과의 정합성 주기적 검증**

  - `https://mfront.homeplus.co.kr/category/map` 화면 및 내부 API(`/category/.../getMap.json` 계열)에서  
    l1/l2/l3 조합 샘플을 주기적으로 수집
  - 새로 등장한 l1/l2/l3 조합을 로그로 남기고, 이 규칙 테이블과  
    `crawler/homeplus/mappers.py::_map_service_category()` 에 함께 반영

- [ ] **정육/계란 / 두부/김치/반찬 / 냉동·밀키트 영역 정교화**

  - 현재는 키워드 기반으로 `MEAT` vs `BEAN_EGG`, `KIMCHI_SIDE`, `NOODLE_FLOUR` 등을 판별
  - 향후 실제 판매 데이터(상품 수, 매출 비중)를 보면서
    - 밀키트/간편식 중에서 “식재료”에 가깝지 않은 품목은 별도 도메인으로 분리
    - 정육/계란/두부/김치/반찬 혼합 L1 내부에서 서브코드(`service_subcategory`) 정의 검토

- [ ] **서브카테고리 코드 표준화**

  - 현재는 `service_subcategory = mcateNm` 으로 단순 매핑
  - 장기적으로는 `SEAFOOD` / `MEAT` / `VEGETABLE` 등에서  
    2depth 표준 코드(예: `생선`, `갑각류`, `근채류`, `엽채류` 등)를 정의해  
    `mcateNm` / `scateNm` 를 해당 코드로 매핑하는 별도 테이블 구축

- [ ] **멀티 소스(다른 마트/플랫폼) 통합 설계**

  - 다른 소스(예: 마켓컬리, 로켓프레시 등)도 동일 포맷의 매핑 문서를 작성
  - 모든 소스가 최종적으로 `docs/CATEGORY_STANDARD.md` 의 12개 코드로 귀결되도록 강제
  - 소스별 카테고리 변경이 발생하면, 공통 매핑 규칙서(본 문서)에서 영향 범위를 한 번에 확인

- [ ] **운영 중 피드백 루프 구축**
  - 실제 서비스/추천/검색 로그에서 “오분류된 카테고리” 케이스를 수집
  - 해당 케이스들의 `source_category_path`, l1/l2/l3, 상품 특성을 바탕으로  
    이 규칙 테이블을 주기적으로 보완
  - 규칙 변경 시, 영향 받는 `service_category` 내 상품 수·비율을 요약해  
    운영/PM 이 쉽게 검토할 수 있도록 간단한 리포트 스크립트 제공

---

## 3. categoryDepth / categoryId 기반 상위 매핑 요약 (홈플러스 전용, 1차 규칙)

> 이 절은 `list?categoryDepth=...&categoryId=...` 조합을 기준으로  
> SelF 표준 카테고리(현재 13개, `docs/CATEGORY_STANDARD.md` 참고)로  
> **상위 도메인을 1차로 결정하기 위한 “정규 규칙”** 을 요약한다.  
> 실제 크롤러 구현(`crawler/homeplus/mappers.py`)에서는
>
> 1. **먼저 이 Depth/ID 규칙을 적용**하여 `service_category` 를 결정하고,
> 2. 어떤 규칙에도 매칭되지 않는 경우에만 1장의 문자열/키워드 기반 규칙을 보조로 사용한다.
>
> “제외”로 표시된 `(categoryDepth, categoryId)` 조합은  
> 해당 도메인에서 제외하고, 아래에 명시된 다른 카테고리로 재매핑한다.

- **FRUIT – 과일 (`FRUIT`)**

  - 포함:
    - `categoryDepth=0, categoryId=1` (과일 루트 전체)
  - 제외 → `NUT_DRY_ETC`:
    - `categoryDepth=3, categoryId=300020`
    - `categoryDepth=3, categoryId=300021`

- **GRAIN – 쌀/잡곡 (`GRAIN`)**

  - 포함:
    - `categoryDepth=0, categoryId=2`

- **VEGETABLE – 채소/샐러드/버섯/나물 (`VEGETABLE`)**

  - 포함:
    - `categoryDepth=0, categoryId=3`

- **NUT_DRY_ETC – 견과/건과/간식 (`NUT_DRY_ETC`)**

  - 포함:
    - `categoryDepth=0, categoryId=4`
    - `categoryDepth=3, categoryId=300020` (FRUIT 에서 제외된 하위)
    - `categoryDepth=3, categoryId=300021` (FRUIT 에서 제외된 하위)
    - `categoryDepth=0, categoryId=14`

- **SEAFOOD – 수산물/해산물/건어물 (`SEAFOOD`)**

  - 포함:
    - `categoryDepth=0, categoryId=5`

- **MEAT – 육류 (`MEAT`)**

  - 포함:
    - `categoryDepth=0, categoryId=6`
    - `categoryDepth=2, categoryId=200068`
  - 제외 → `BEAN_EGG`:
    - `categoryDepth=2, categoryId=200048`

- **BEAN_EGG – 두부/콩/계란 (`BEAN_EGG`)**

  - 포함:
    - `categoryDepth=2, categoryId=200063`
    - `categoryDepth=2, categoryId=200048`

- **DAIRY – 우유/유제품 (`DAIRY`)**

  - 포함:
    - `categoryDepth=0, categoryId=9`

- **DRINK – 음료 (`DRINK`)**

  - 포함:
    - `categoryDepth=0, categoryId=12`
    - `categoryDepth=0, categoryId=13`

- **NOODLE_FLOUR – 면/가루/베이커리/제빵 (`NOODLE_FLOUR`)**

  - 포함:
    - `categoryDepth=0, categoryId=15`
    - `categoryDepth=2, categoryId=200077`
    - `categoryDepth=2, categoryId=200082`
  - 제외 → `SEASONING_SAUCE_OIL`:
    - `categoryDepth=2, categoryId=200125`

- **KIMCHI_SIDE – 김치/반찬/절임 (`KIMCHI_SIDE`)**

  - 포함:
    - `categoryDepth=0, categoryId=11`
  - 제외 → `BEAN_EGG`:
    - `categoryDepth=2, categoryId=200063`

- **SEASONING_SAUCE_OIL – 양념/조미/소스/오일 (`SEASONING_SAUCE_OIL`)**

  - 포함:
    - `categoryDepth=0, categoryId=17`
    - `categoryDepth=2, categoryId=200125`
  - 제외 → `NOODLE_FLOUR`:
    - `categoryDepth=2, categoryId=200077`
    - `categoryDepth=2, categoryId=200082`

- **INSTANT_FOOD – 라면/간편식품/통조림 (`INSTANT_FOOD`)**
  - 포함:
    - `categoryDepth=0, categoryId=10`
    - `categoryDepth=0, categoryId=16`

> 이 매핑은 크롤러에서 `CRAWL_SERVICE_CATEGORY_FILTER` 로  
> 도메인별 병렬 크롤링을 수행할 때 기준이 되는 상위 분할 규칙이다.
