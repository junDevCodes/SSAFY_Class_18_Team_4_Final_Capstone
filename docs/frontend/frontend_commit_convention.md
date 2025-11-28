# Frontend Commit Convention

## 목차
- [커밋 메시지 구조](#커밋-메시지-구조)
- [Type](#type)
- [Scope (프론트엔드)](#scope-프론트엔드)
- [커밋 메시지 예시](#커밋-메시지-예시)
- [프론트엔드 커밋 팁](#프론트엔드-커밋-팁)

## 커밋 메시지 구조

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 예시
```
feat(auth): 소셜 로그인 UI 구현

카카오, 구글 소셜 로그인 버튼을 추가했습니다.
- 소셜 로그인 버튼 컴포넌트 추가
- 로그인 페이지 레이아웃 수정
- 소셜 로그인 아이콘 추가

Resolves: #123
```

## Type

커밋의 타입을 명시합니다.

| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새로운 기능 추가 | `feat(login): 로그인 폼 컴포넌트 추가` |
| `fix` | 버그 수정 | `fix(button): 클릭 이벤트 버블링 오류 수정` |
| `design` | UI/UX 디자인 변경 | `design(header): 헤더 레이아웃 반응형 적용` |
| `style` | 코드 포맷팅, 세미콜론 누락 등 (기능 변경 없음) | `style(utils): 코드 포맷팅 적용` |
| `refactor` | 코드 리팩토링 (기능 변경 없음) | `refactor(store): 상태 관리 로직 개선` |
| `test` | 테스트 코드 추가/수정 | `test(login): 로그인 컴포넌트 테스트 추가` |
| `chore` | 빌드, 패키지 설정 등 (기능 변경 없음) | `chore(deps): vue 버전 업데이트` |
| `comment` | 주석 추가 및 변경 | `comment(utils): 유틸 함수 주석 추가` |
| `rename` | 파일/폴더명 수정 또는 이동 | `rename(components): 컴포넌트 파일명 변경` |
| `remove` | 파일 삭제 | `remove(legacy): 사용하지 않는 컴포넌트 제거` |
| `!HOTFIX` | 긴급 버그 수정 | `!HOTFIX(checkout): 결제 버튼 동작 오류 긴급 수정` |

## Scope (프론트엔드)

변경된 부분을 명시합니다. 프론트엔드 프로젝트에 맞는 scope를 사용하세요.

### 페이지/뷰
| Scope | 설명 |
|-------|------|
| `home` | 홈 페이지 |
| `login` | 로그인 페이지 |
| `signup` | 회원가입 페이지 |
| `profile` | 프로필 페이지 |
| `product` | 상품 페이지 |
| `cart` | 장바구니 페이지 |
| `checkout` | 결제 페이지 |
| `order` | 주문 페이지 |
| `search` | 검색 페이지 |
| `mypage` | 마이페이지 |

### 공통 컴포넌트
| Scope | 설명 |
|-------|------|
| `header` | 헤더 컴포넌트 |
| `footer` | 푸터 컴포넌트 |
| `nav` | 네비게이션 |
| `sidebar` | 사이드바 |
| `modal` | 모달 컴포넌트 |
| `button` | 버튼 컴포넌트 |
| `input` | 인풋 컴포넌트 |
| `form` | 폼 컴포넌트 |
| `card` | 카드 컴포넌트 |
| `table` | 테이블 컴포넌트 |
| `toast` | 토스트/알림 |
| `dropdown` | 드롭다운 |
| `tab` | 탭 컴포넌트 |

### 기능 영역
| Scope | 설명 |
|-------|------|
| `auth` | 인증/로그인 관련 |
| `store` | 상태 관리 (Pinia, Vuex, Redux 등) |
| `api` | API 호출 관련 |
| `router` | 라우터 설정 |
| `i18n` | 다국어 처리 |
| `theme` | 테마/다크모드 |
| `a11y` | 접근성 |

### 스타일/에셋
| Scope | 설명 |
|-------|------|
| `styles` | 전역 스타일 |
| `assets` | 이미지, 폰트 등 에셋 |
| `icons` | 아이콘 |

### 설정/빌드
| Scope | 설명 |
|-------|------|
| `config` | 프로젝트 설정 |
| `deps` | 의존성 관리 |
| `build` | 빌드 설정 |
| `lint` | 린트 설정 |
| `test` | 테스트 설정 |

## 커밋 메시지 예시

### 컴포넌트 관련

**feat (기능 추가)**
```
feat(login): 로그인 폼 컴포넌트 추가
feat(header): 검색 기능 추가
feat(product): 상품 필터링 컴포넌트 구현
feat(cart): 장바구니 수량 변경 기능 추가
feat(modal): 확인 모달 컴포넌트 추가
```

**fix (버그 수정)**
```
fix(button): 더블 클릭 시 중복 요청 문제 수정
fix(modal): 모달 외부 클릭 시 닫히지 않는 문제 수정
fix(form): 폼 유효성 검증 오류 수정
fix(dropdown): 드롭다운 위치 계산 오류 수정
fix(table): 페이지네이션 버튼 동작 오류 수정
```

**design (디자인 변경)**
```
design(header): 헤더 레이아웃 반응형 적용
design(button): 버튼 호버 효과 추가
design(card): 카드 그림자 효과 수정
design(footer): 푸터 디자인 리뉴얼
design(theme): 다크모드 색상 조정
```

### 상태 관리 관련

```
feat(store): 사용자 인증 상태 관리 추가
refactor(store): 장바구니 상태 로직 개선
fix(store): 로그아웃 시 상태 초기화 누락 수정
```

### 스타일 관련

```
style(button): 버튼 컴포넌트 코드 포맷팅
style(utils): ESLint 규칙 적용
style: 전체 코드 Prettier 적용
```

### API 연동 관련

```
feat(api): 상품 목록 API 연동
fix(api): API 에러 처리 로직 수정
refactor(api): API 호출 로직 axios interceptor로 통합
```

### 테스트 관련

```
test(login): 로그인 폼 유닛 테스트 추가
test(button): 버튼 컴포넌트 스냅샷 테스트 추가
test(cart): 장바구니 E2E 테스트 작성
```

### 상세 커밋 메시지 예시

```
feat(auth): 소셜 로그인 UI 구현

카카오, 구글 소셜 로그인 버튼을 추가했습니다.
- SocialLoginButton 컴포넌트 생성
- 로그인 페이지에 소셜 로그인 섹션 추가
- 카카오/구글 아이콘 SVG 추가

Resolves: #123
```

```
fix(modal): 모달 외부 클릭 시 닫히지 않는 문제 수정

이벤트 버블링으로 인해 모달 내부 클릭 시에도
닫힘 이벤트가 발생하는 문제를 수정했습니다.
- stopPropagation 추가
- 모달 오버레이 클릭 이벤트 분리

Fixes: #456
```

```
refactor(store): 상태 관리 로직 Composition API로 마이그레이션

Vue 3 Composition API 스타일로 스토어를 리팩토링했습니다.
- Options API에서 Composition API로 변환
- Pinia 스토어 모듈화
- 타입스크립트 적용

Related to: #789
```

```
design(header): 모바일 반응형 네비게이션 구현

768px 이하에서 햄버거 메뉴로 변경되도록 구현했습니다.
- 햄버거 아이콘 버튼 추가
- 슬라이드 메뉴 애니메이션 적용
- 메뉴 외부 클릭 시 닫힘 처리
```

## 프론트엔드 커밋 팁

### 1. 컴포넌트 단위로 커밋하기

```bash
# Good - 컴포넌트별로 분리
git commit -m "feat(button): 기본 버튼 컴포넌트 추가"
git commit -m "feat(button): 버튼 variants 추가 (primary, secondary)"
git commit -m "test(button): 버튼 컴포넌트 테스트 작성"

# Bad - 여러 컴포넌트를 한번에
git commit -m "feat: 버튼, 인풋, 카드 컴포넌트 추가"
```

### 2. UI 변경과 로직 변경 분리하기

```bash
# Good - UI와 로직 분리
git commit -m "design(login): 로그인 폼 UI 구현"
git commit -m "feat(login): 로그인 폼 유효성 검증 로직 추가"
git commit -m "feat(login): 로그인 API 연동"

# Bad - 모든 것을 한번에
git commit -m "feat(login): 로그인 기능 전체 구현"
```

### 3. 스타일 변경은 design 타입 사용

```bash
# CSS/스타일 관련 변경
git commit -m "design(card): 카드 호버 효과 추가"
git commit -m "design(theme): 다크모드 색상 팔레트 수정"
git commit -m "design(layout): 그리드 레이아웃 적용"
```

### 4. 반응형 작업 명시하기

```bash
git commit -m "design(header): 태블릿 반응형 레이아웃 적용"
git commit -m "design(sidebar): 모바일에서 드로어 형태로 변경"
git commit -m "fix(table): 모바일에서 가로 스크롤 추가"
```

### 5. 접근성 개선 커밋

```bash
git commit -m "feat(a11y): 키보드 네비게이션 지원 추가"
git commit -m "fix(a11y): 버튼 aria-label 누락 수정"
git commit -m "feat(a11y): 스크린 리더 지원 개선"
```

## 주의사항

### 하지 말아야 할 것

1. **의미 없는 커밋 메시지**
   ```bash
   # Bad
   git commit -m "수정"
   git commit -m "UI 변경"
   git commit -m "스타일 수정"
   ```

2. **너무 큰 커밋**
   ```bash
   # Bad - 10개 컴포넌트, 500줄 변경
   git commit -m "feat: 대시보드 페이지 전체 구현"
   ```

3. **Type 없이 커밋**
   ```bash
   # Bad
   git commit -m "로그인 버튼 추가"

   # Good
   git commit -m "feat(login): 로그인 버튼 컴포넌트 추가"
   ```

### 해야 할 것

1. **명확하고 구체적인 메시지**
   ```bash
   # Good
   git commit -m "feat(product): 상품 이미지 줌 기능 추가"
   git commit -m "fix(cart): 수량 0 미만으로 감소하는 버그 수정"
   ```

2. **작은 단위로 자주 커밋**
   ```bash
   # Good
   git commit -m "feat(form): 이메일 인풋 컴포넌트 추가"
   git commit -m "feat(form): 비밀번호 인풋 컴포넌트 추가"
   git commit -m "feat(form): 폼 유효성 검증 훅 추가"
   ```

## Issue Convention (프론트엔드)

### 이슈 라벨

| 라벨 | 설명 |
|------|------|
| `bug` | UI/기능 버그 |
| `feature` | 새로운 기능/컴포넌트 요청 |
| `design` | 디자인 변경 요청 |
| `enhancement` | 기존 기능 개선 |
| `a11y` | 접근성 관련 |
| `responsive` | 반응형 관련 |
| `performance` | 성능 개선 |

### 이슈 제목 예시

```
[Bug] 모바일에서 드롭다운 메뉴가 화면 밖으로 벗어남
[Feature] 다크모드 토글 기능 추가
[Design] 상품 카드 호버 효과 개선
[A11y] 키보드 네비게이션 지원 추가
[Performance] 이미지 레이지 로딩 적용
```

## 참고 자료

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Vue.js Style Guide](https://vuejs.org/style-guide/)
- [Atomic Design](https://bradfrost.com/blog/post/atomic-web-design/)
