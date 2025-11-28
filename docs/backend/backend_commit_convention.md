# Backend Commit Convention

## 목차
- [커밋 메시지 구조](#커밋-메시지-구조)
- [Type](#type)
- [Scope (백엔드)](#scope-백엔드)
- [커밋 메시지 예시](#커밋-메시지-예시)
- [백엔드 커밋 팁](#백엔드-커밋-팁)

## 커밋 메시지 구조

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 예시
```
feat(auth): JWT 기반 인증 시스템 구현

Access Token과 Refresh Token을 발급하는 인증 시스템을 구현했습니다.
- JWT 토큰 생성 및 검증 로직 추가
- Redis 기반 Refresh Token 저장
- 토큰 갱신 API 구현

Resolves: #123
```

## Type

커밋의 타입을 명시합니다.

| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새로운 기능 추가 | `feat(auth): 로그인 API 구현` |
| `fix` | 버그 수정 | `fix(user): 이메일 중복 검사 오류 수정` |
| `refactor` | 코드 리팩토링 (기능 변경 없음) | `refactor(order): 주문 처리 로직 개선` |
| `test` | 테스트 코드 추가/수정 | `test(user): 사용자 등록 테스트 추가` |
| `docs` | 문서 수정 | `docs(api): Swagger 문서 업데이트` |
| `style` | 코드 포맷팅 (기능 변경 없음) | `style(service): 코드 포맷팅 적용` |
| `chore` | 빌드, 설정 등 (기능 변경 없음) | `chore(deps): Spring Boot 버전 업데이트` |
| `perf` | 성능 개선 | `perf(query): 상품 조회 쿼리 최적화` |
| `comment` | 주석 추가 및 변경 | `comment(service): 서비스 로직 주석 추가` |
| `rename` | 파일/폴더명 수정 또는 이동 | `rename(domain): 엔티티 패키지 구조 변경` |
| `remove` | 파일 삭제 | `remove(legacy): 사용하지 않는 API 제거` |
| `!HOTFIX` | 긴급 버그 수정 | `!HOTFIX(payment): 결제 금액 계산 오류 긴급 수정` |

## Scope (백엔드)

변경된 부분을 명시합니다. 백엔드 프로젝트에 맞는 scope를 사용하세요.

### 도메인 영역
| Scope | 설명 |
|-------|------|
| `user` | 사용자 도메인 |
| `auth` | 인증/인가 |
| `product` | 상품 도메인 |
| `order` | 주문 도메인 |
| `payment` | 결제 도메인 |
| `cart` | 장바구니 도메인 |
| `review` | 리뷰 도메인 |
| `coupon` | 쿠폰 도메인 |
| `notification` | 알림 도메인 |
| `search` | 검색 도메인 |

### 인프라/기술 영역
| Scope | 설명 |
|-------|------|
| `api` | API 공통 |
| `db` | 데이터베이스 |
| `cache` | 캐싱 (Redis 등) |
| `queue` | 메시지 큐 (Kafka, RabbitMQ 등) |
| `batch` | 배치 작업 |
| `scheduler` | 스케줄러 |
| `security` | 보안 설정 |
| `logging` | 로깅 |
| `monitoring` | 모니터링 |

### 레이어 영역
| Scope | 설명 |
|-------|------|
| `controller` | 컨트롤러 레이어 |
| `service` | 서비스 레이어 |
| `repository` | 리포지토리 레이어 |
| `domain` | 도메인/엔티티 |
| `dto` | DTO 클래스 |
| `mapper` | 매퍼 (MyBatis 등) |

### 설정/빌드
| Scope | 설명 |
|-------|------|
| `config` | 애플리케이션 설정 |
| `deps` | 의존성 관리 |
| `docker` | Docker 설정 |
| `ci` | CI/CD 설정 |
| `test` | 테스트 설정 |

## 커밋 메시지 예시

### API 관련

**feat (기능 추가)**
```
feat(auth): 로그인 API 구현
feat(user): 회원가입 API 구현
feat(product): 상품 검색 API 추가
feat(order): 주문 생성 API 구현
feat(payment): 결제 처리 API 추가
```

**fix (버그 수정)**
```
fix(auth): 토큰 만료 검증 오류 수정
fix(user): 이메일 중복 검사 누락 수정
fix(order): 주문 금액 계산 오류 수정
fix(payment): 결제 취소 시 환불 금액 오류 수정
fix(api): API 응답 상태 코드 수정
```

### 데이터베이스 관련

```
feat(db): users 테이블 마이그레이션 추가
fix(db): 인덱스 누락으로 인한 조회 성능 저하 수정
refactor(repository): JPA 쿼리 최적화
feat(domain): Order 엔티티 연관관계 수정
chore(db): 테스트 데이터 시드 스크립트 추가
```

### 성능 관련

```
perf(query): 상품 목록 조회 쿼리 최적화
perf(cache): 인기 상품 캐싱 적용
perf(batch): 대량 데이터 처리 배치 사이즈 조정
refactor(service): N+1 문제 해결을 위한 fetch join 적용
```

### 보안 관련

```
feat(security): API Rate Limiting 적용
fix(security): SQL Injection 취약점 수정
feat(auth): OAuth2 소셜 로그인 추가
fix(auth): 비밀번호 해싱 알고리즘 변경 (bcrypt)
chore(security): 보안 헤더 설정 추가
```

### 테스트 관련

```
test(auth): 로그인 API 통합 테스트 추가
test(user): 회원가입 서비스 유닛 테스트 작성
test(order): 주문 생성 E2E 테스트 추가
test(repository): 상품 조회 쿼리 테스트 작성
```

### 상세 커밋 메시지 예시

```
feat(auth): JWT 기반 인증 시스템 구현

Access Token과 Refresh Token을 발급하는 인증 시스템을 구현했습니다.
- JwtTokenProvider: 토큰 생성 및 검증
- JwtAuthenticationFilter: 요청 인증 필터
- Redis를 활용한 Refresh Token 저장
- 토큰 갱신 API (POST /api/auth/refresh)

Resolves: #123
Ref: #100
```

```
fix(order): 동시성 이슈로 인한 재고 감소 오류 수정

여러 사용자가 동시에 주문할 때 재고가 정확히 차감되지 않는
문제를 수정했습니다.
- 비관적 락(Pessimistic Lock) 적용
- 재고 차감 로직 트랜잭션 범위 조정
- 동시성 테스트 케이스 추가

Fixes: #456
```

```
perf(product): 상품 목록 조회 성능 개선

대용량 상품 데이터 조회 시 응답 시간이 느린 문제를 개선했습니다.
- 커버링 인덱스 추가
- 불필요한 JOIN 제거
- 페이지네이션 쿼리 최적화
- 응답 시간: 2000ms → 150ms

Related to: #789
```

```
refactor(service): 주문 서비스 로직 리팩토링

주문 서비스의 책임을 분리하고 테스트 가능성을 높였습니다.
- OrderService → OrderCommandService, OrderQueryService 분리
- 결제 처리 로직을 PaymentService로 위임
- 도메인 이벤트 적용 (OrderCreatedEvent)
- 단위 테스트 커버리지 45% → 85%
```

## 백엔드 커밋 팁

### 1. 레이어별로 커밋하기

```bash
# Good - 레이어별 분리
git commit -m "feat(domain): Order 엔티티 추가"
git commit -m "feat(repository): OrderRepository 구현"
git commit -m "feat(service): 주문 생성 비즈니스 로직 구현"
git commit -m "feat(controller): 주문 생성 API 엔드포인트 추가"

# Bad - 모든 레이어를 한번에
git commit -m "feat(order): 주문 기능 전체 구현"
```

### 2. 마이그레이션은 별도 커밋

```bash
# Good - 마이그레이션 분리
git commit -m "feat(db): orders 테이블 마이그레이션 추가"
git commit -m "feat(order): 주문 도메인 로직 구현"

# Bad - 마이그레이션과 로직 혼합
git commit -m "feat(order): 주문 기능 구현 및 테이블 생성"
```

### 3. 성능 개선은 perf 타입 사용

```bash
# 성능 관련 변경
git commit -m "perf(query): 상품 조회 쿼리에 인덱스 추가"
git commit -m "perf(cache): 카테고리 목록 Redis 캐싱 적용"
git commit -m "perf(batch): 배치 처리 chunk 사이즈 최적화"
```

### 4. 보안 수정은 명확하게

```bash
git commit -m "fix(security): SQL Injection 취약점 수정"
git commit -m "fix(auth): 비밀번호 평문 저장 문제 수정"
git commit -m "feat(security): CSRF 토큰 검증 추가"
```

### 5. API 변경사항 명시

```bash
# API 추가
git commit -m "feat(api): GET /api/products/{id} 상품 상세 조회 API 추가"

# API 수정
git commit -m "refactor(api): GET /api/products 페이지네이션 파라미터 추가"

# API 삭제
git commit -m "remove(api): DELETE /api/legacy/users 레거시 API 제거"
```

### 6. 트랜잭션 관련 변경

```bash
git commit -m "fix(service): 주문 취소 트랜잭션 롤백 처리 수정"
git commit -m "refactor(service): 외부 API 호출을 트랜잭션 외부로 분리"
git commit -m "feat(event): 주문 완료 이벤트 발행 추가"
```

## 주의사항

### 하지 말아야 할 것

1. **의미 없는 커밋 메시지**
   ```bash
   # Bad
   git commit -m "수정"
   git commit -m "fix bug"
   git commit -m "update"
   ```

2. **너무 큰 커밋**
   ```bash
   # Bad - 여러 도메인, 500줄 변경
   git commit -m "feat: 주문, 결제, 배송 기능 구현"
   ```

3. **Type 없이 커밋**
   ```bash
   # Bad
   git commit -m "로그인 API 추가"

   # Good
   git commit -m "feat(auth): 로그인 API 구현"
   ```

4. **마이그레이션과 코드 변경 혼합**
   ```bash
   # Bad
   git commit -m "feat(user): 사용자 테이블 생성 및 CRUD 구현"

   # Good
   git commit -m "feat(db): users 테이블 마이그레이션 추가"
   git commit -m "feat(user): 사용자 CRUD API 구현"
   ```

### 해야 할 것

1. **명확하고 구체적인 메시지**
   ```bash
   # Good
   git commit -m "feat(auth): JWT Access Token 발급 로직 구현"
   git commit -m "fix(order): 주문 금액 소수점 반올림 오류 수정"
   ```

2. **작은 단위로 자주 커밋**
   ```bash
   # Good
   git commit -m "feat(domain): Product 엔티티 추가"
   git commit -m "feat(repository): ProductRepository 인터페이스 정의"
   git commit -m "feat(service): 상품 조회 비즈니스 로직 구현"
   git commit -m "test(service): 상품 조회 유닛 테스트 작성"
   ```

3. **영향 범위 명시**
   ```bash
   # 성능 영향이 있는 경우
   git commit -m "perf(query): 상품 조회 쿼리 최적화 (2s → 100ms)"

   # Breaking Change인 경우
   git commit -m "feat(api)!: 인증 방식 변경 (세션 → JWT)"
   ```

## Issue Convention (백엔드)

### 이슈 라벨

| 라벨 | 설명 |
|------|------|
| `bug` | 서버/API 버그 |
| `feature` | 새로운 API/기능 요청 |
| `enhancement` | 기존 기능 개선 |
| `performance` | 성능 개선 |
| `security` | 보안 관련 |
| `database` | DB 관련 |
| `refactor` | 리팩토링 |

### 이슈 제목 예시

```
[Bug] 로그인 시 토큰이 발급되지 않음
[Feature] 소셜 로그인 API 추가 요청
[Performance] 상품 목록 조회 API 응답 시간 개선
[Security] API Rate Limiting 적용 필요
[Database] 주문 테이블 인덱스 최적화 필요
```

## 참고 자료

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Commit Guidelines](https://github.com/angular/angular/blob/main/CONTRIBUTING.md)
- [Spring Boot Best Practices](https://spring.io/guides)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
