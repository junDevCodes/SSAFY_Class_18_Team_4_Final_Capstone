# Git Convention

## 📋 목차
- [Commit Message Convention](#commit-message-convention)
- [Branch Naming Convention](#branch-naming-convention)
- [Pull Request Convention](#pull-request-convention)
- [Issue Convention](#issue-convention)

## 💬 Commit Message Convention

### 커밋 메시지 구조
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
커밋의 타입을 명시합니다.

| Type | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 (README, 주석 등) |
| `style` | 코드 포맷팅, 세미콜론 누락 등 (기능 변경 없음) |
| `refactor` | 코드 리팩토링 (기능 변경 없음) |
| `test` | 테스트 코드 추가/수정 |
| `chore` | 빌드 업무, 패키지 매니저 설정 등 (기능 변경 없음) |
| `design` | CSS 등 사용자 UI 디자인 변경 |
| `comment` | 주석 추가 및 변경 |
| `rename` | 파일/폴더명 수정 또는 이동 |
| `remove` | 파일 삭제 |
| `!HOTFIX` | 급하게 치명적인 버그 수정 |

### Scope (선택사항)
변경된 부분을 명시합니다.
- `auth`, `user`, `product`, `api` 등

### Subject
- 50자 이내로 작성
- 마침표 생략
- 과거형 사용 금지
- 명령문 형태로 작성
- 첫 글자는 소문자

### Body (선택사항)
- 72자마다 줄바꿈
- 무엇을, 왜 변경했는지 작성
- 어떻게는 코드에서 확인 가능하므로 생략

### Footer (선택사항)
- 이슈 트래커 ID 참조
- `Fixes`: 이슈 수정 중 (미완료)
- `Resolves`: 이슈 해결
- `Ref`: 참고할 이슈
- `Related to`: 관련 이슈

### 커밋 메시지 예시

#### 기본 형태
```
feat(auth): 로그인 기능 추가
```

#### 상세 형태
```
feat(auth): 소셜 로그인 기능 추가

카카오, 구글 소셜 로그인 기능을 구현했습니다.
- 카카오 OAuth 2.0 인증 추가
- 구글 OAuth 2.0 인증 추가
- 소셜 로그인 후 JWT 토큰 발급

Resolves: #123
Ref: #456
```

#### 다양한 예시
```
fix(user): 회원가입 유효성 검증 오류 수정

docs(readme): 설치 방법 업데이트

style(button): 버튼 컴포넌트 코드 포맷팅

refactor(api): API 호출 로직 개선

test(user): 사용자 등록 테스트 추가

chore(deps): axios 버전 업데이트

design(header): 헤더 레이아웃 변경

!HOTFIX(payment): 결제 모듈 치명적 오류 수정
```

## 🌿 Branch Naming Convention

### 브랜치 유형

| 브랜치 | 설명 |
|--------|------|
| `main` | 배포 가능한 안정 버전 |
| `dev` | 개발 중인 최신 버전 |
| `feature/*` | 새로운 기능 개발 |
| `fix/*` | 버그 수정 |
| `hotfix/*` | 긴급 버그 수정 (main에서 분기) |
| `release/*` | 배포 준비 |
| `docs/*` | 문서 작업 |

### 브랜치 네이밍 규칙
```
<type>/<issue-number>-<short-description>
```

### 브랜치명 예시
```
feature/123-user-login
feature/124-social-login
fix/125-login-validation
hotfix/126-payment-error
docs/127-update-readme
```

### 브랜치 사용 규칙

1. **브랜치 생성**
```bash
# dev에서 최신 코드 pull
git checkout dev
git pull origin dev

# 새 브랜치 생성
git checkout -b feature/123-user-login
```

2. **브랜치 푸시**
```bash
git push origin feature/123-user-login
```

3. **브랜치 삭제**
```bash
# 로컬 브랜치 삭제
git branch -d feature/123-user-login

# 원격 브랜치 삭제
git push origin --delete feature/123-user-login
```

## 🔀 Pull Request Convention

### PR 제목
```
[Type] 작업 내용 요약
```

예시:
```
[Feat] 사용자 로그인 기능 구현
[Fix] 회원가입 유효성 검증 오류 수정
[Docs] README 설치 가이드 추가
```

### PR 설명 템플릿
```markdown
## 작업 내용
이 PR에서 수행한 작업을 간단히 설명합니다.

## 변경 사항
- 변경 사항 1
- 변경 사항 2
- 변경 사항 3

## 테스트 방법
1. 테스트 단계 1
2. 테스트 단계 2
3. 예상 결과

## 스크린샷 (선택사항)
UI 변경이 있는 경우 스크린샷을 첨부합니다.

## 관련 이슈
Closes #123
Related to #456

## 체크리스트
- [ ] 코드 컨벤션을 준수했나요?
- [ ] 테스트를 작성했나요?
- [ ] 문서를 업데이트했나요?
- [ ] 충돌을 해결했나요?
```

### PR 작성 규칙

1. **작은 단위로 작성**: 한 PR에는 하나의 기능/수정만
2. **Self Review**: PR 생성 전 스스로 코드 리뷰
3. **Reviewer 지정**: 최소 1명 이상의 리뷰어 지정
4. **리뷰 반영**: 리뷰 의견은 성실히 반영
5. **Merge 전 확인**: CI/CD 통과 여부 확인

## 🐛 Issue Convention

### 이슈 제목
```
[Label] 이슈 내용 요약
```

### 이슈 라벨

| 라벨 | 설명 |
|------|------|
| `bug` | 버그 |
| `feature` | 새로운 기능 요청 |
| `docs` | 문서 관련 |
| `question` | 질문 |
| `help wanted` | 도움 요청 |
| `duplicate` | 중복된 이슈 |
| `wontfix` | 수정하지 않을 이슈 |

### 이슈 템플릿

#### 버그 리포트
```markdown
## 버그 설명
버그에 대한 명확하고 간결한 설명

## 재현 방법
1. 첫 번째 단계
2. 두 번째 단계
3. 세 번째 단계

## 예상 동작
어떤 동작을 예상했는지 설명

## 실제 동작
실제로 어떤 동작이 발생했는지 설명

## 스크린샷
가능하다면 스크린샷 첨부

## 환경
- OS: [예: Windows 10]
- Browser: [예: Chrome 95]
- Version: [예: 1.0.0]

## 추가 정보
기타 추가적인 컨텍스트
```

#### 기능 요청
```markdown
## 기능 설명
새로운 기능에 대한 명확하고 간결한 설명

## 동기
이 기능이 왜 필요한지 설명

## 제안하는 해결 방법
어떻게 구현하면 좋을지 제안

## 대안
고려한 다른 대안이 있다면 설명

## 추가 정보
기타 추가적인 컨텍스트나 스크린샷
```

## 📌 Git 사용 팁

### 자주 사용하는 명령어
```bash
# 상태 확인
git status

# 변경 사항 추가
git add .

# 커밋
git commit -m "feat: 로그인 기능 추가"

# 푸시
git push origin feature/123-user-login

# 최신 코드 받기
git pull origin dev

# 브랜치 확인
git branch

# 브랜치 전환
git checkout dev

# 브랜치 생성 및 전환
git checkout -b feature/124-new-feature
```

### Commit 수정
```bash
# 마지막 커밋 메시지 수정
git commit --amend

# 여러 커밋 합치기 (최근 3개)
git rebase -i HEAD~3
```

### 충돌 해결
```bash
# 현재 브랜치에 dev 내용 가져오기
git pull origin dev

# 충돌 파일 수정 후
git add .
git commit -m "fix: merge conflict 해결"
```

## ⚠️ 주의사항

1. **main, dev 브랜치에 직접 푸시 금지**
2. **Force Push 금지** (`git push -f` 사용하지 않기)
3. **개인 브랜치는 자유롭게 커밋** (Squash 후 PR)
4. **대용량 파일 커밋 금지** (.gitignore 활용)
5. **민감 정보 커밋 금지** (API 키, 비밀번호 등)