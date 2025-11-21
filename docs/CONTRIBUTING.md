# Contributing Guide

프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트 기여 방법을 안내합니다.

## 📋 목차
- [시작하기](#시작하기)
- [개발 환경 설정](#개발-환경-설정)
- [기여 프로세스](#기여-프로세스)
- [코드 리뷰](#코드-리뷰)
- [버그 리포트](#버그-리포트)
- [기능 제안](#기능-제안)

## 🚀 시작하기

### 기여 전 확인사항

프로젝트에 기여하기 전에 다음 문서들을 확인해주세요:
- [README.md](../README.md) - 프로젝트 개요
- [Code Convention](./CODE_CONVENTION.md) - 코드 작성 규칙
- [Git Convention](./GIT_CONVENTION.md) - Git 사용 규칙
- [Branch Strategy](./BRANCH_STRATEGY.md) - 브랜치 전략

### 기여 가능한 영역

다음과 같은 방법으로 프로젝트에 기여할 수 있습니다:
- 🐛 버그 수정
- ✨ 새로운 기능 추가
- 📝 문서 개선
- 🎨 UI/UX 개선
- ⚡️ 성능 최적화
- ✅ 테스트 코드 작성
- 🔧 리팩토링

## 🛠 개발 환경 설정

### 1. 저장소 Fork 및 Clone

```bash
# 1. GitHub에서 저장소 Fork

# 2. Fork한 저장소 Clone
git clone https://github.com/YOUR_USERNAME/project-name.git
cd project-name

# 3. 원본 저장소를 origin으로 추가
git remote add origin https://github.com/ORIGINAL_OWNER/project-name.git

# 4. upstream 확인
git remote -v
```

### 2. 의존성 설치

**Backend (Django)**
```bash
# 백엔드 디렉토리 이동
cd backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate
# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements/development.txt

# 마이그레이션
python manage.py migrate
```

**Frontend (Vue)**
```bash
# 프론트엔드 디렉토리 이동
cd frontend

# 의존성 설치
npm install
```

### 3. 환경 변수 설정

**Backend (Django)**
```bash
# backend/.env.example을 복사
cd backend
cp .env.example .env

# .env 파일 내용 수정 (DB 정보, SECRET_KEY 등)
```

**Frontend (Vue)**
```bash
# frontend/.env.example을 복사
cd frontend
cp .env.example .env

# .env 파일 내용 수정 (API URL 등)
```

### 4. 개발 서버 실행

**Backend (Django)**
```bash
cd backend
python manage.py runserver
# 서버 주소: http://127.0.0.1:8000/
```

**Frontend (Vue)**
```bash
cd frontend
npm run dev
# 서버 주소: http://localhost:5173/ (Vite 기본값)
```

### 5. 테스트 실행

**Backend (Django)**
```bash
cd backend

# 전체 테스트
python manage.py test

# 특정 앱 테스트
python manage.py test apps.users

# 테스트 커버리지
coverage run --source='.' manage.py test
coverage report
```

**Frontend (Vue)**
```bash
cd frontend

# 전체 테스트
npm test

# 특정 테스트
npm test -- <test-name>

# 테스트 커버리지
npm run test:coverage
```

## 🔄 기여 프로세스

### 1. 이슈 확인 또는 생성

기여하기 전에 항상 이슈를 먼저 확인하세요.

```bash
# 기존 이슈 확인
# GitHub Issues 탭에서 관련 이슈 검색

# 새로운 이슈 생성
# 버그: Bug Report 템플릿 사용
# 기능: Feature Request 템플릿 사용
```

### 2. 브랜치 생성
```bash
# dev 브랜치에서 최신 코드 pull
git checkout dev
git pull origin dev

# 새 브랜치 생성
git checkout -b feature/123-new-feature
```

### 3. 코드 작성

#### 코딩 규칙 준수
- [Code Convention](./CODE_CONVENTION.md) 따르기
- ESLint, Prettier 규칙 준수
- 주석 적절히 작성
- 의미 있는 변수/함수명 사용

#### 커밋 규칙
- [Git Convention](./GIT_CONVENTION.md) 따르기
- 작은 단위로 자주 커밋
- 의미 있는 커밋 메시지 작성

```bash
# 예시
git add .
git commit -m "feat(auth): 소셜 로그인 기능 추가"
git commit -m "test(auth): 로그인 테스트 케이스 추가"
git commit -m "docs(readme): 설치 가이드 업데이트"
```

### 4. 테스트 작성

새로운 기능을 추가하거나 버그를 수정할 때는 반드시 테스트를 작성하세요.

```javascript
// 예시: user.test.js
describe('User Login', () => {
  test('should login successfully with valid credentials', () => {
    // 테스트 코드
  });

  test('should fail login with invalid credentials', () => {
    // 테스트 코드
  });
});
```

### 5. 코드 검증

푸시하기 전에 다음을 확인하세요:

### 5. 코드 검증

푸시하기 전에 다음을 확인하세요:

**Backend (Django)**
```bash
# 코드 스타일 검사
flake8 .

# 자동 포맷팅
black .

# Import 정렬
isort .

# 테스트 실행
python manage.py test
```

**Frontend (Vue)**
```bash
# 린트 검사
npm run lint

# 린트 자동 수정
npm run lint:fix

# 테스트 실행
npm test

# 빌드 확인
npm run build
```

### 6. Push 및 Pull Request 생성

```bash
# 원격 저장소에 푸시
git push origin feature/123-new-feature

# GitHub에서 Pull Request 생성
# base: dev ← compare: feature/123-new-feature
```

### 7. Pull Request 작성

PR을 생성할 때 다음 템플릿을 사용하세요:

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

## 스크린샷
<!-- UI 변경이 있는 경우 스크린샷 첨부 -->

## 관련 이슈
Closes #123

## 체크리스트
- [ ] 코드 컨벤션을 준수했습니다
- [ ] 테스트를 작성했습니다
- [ ] 문서를 업데이트했습니다
- [ ] 충돌을 해결했습니다
- [ ] 모든 테스트가 통과했습니다
- [ ] 린트 검사를 통과했습니다
```

## 👀 코드 리뷰

### 리뷰 받기

1. **리뷰어 지정**: 최소 1명 이상의 팀원을 리뷰어로 지정
2. **리뷰 대기**: 리뷰어의 의견을 기다림
3. **피드백 반영**: 리뷰 의견을 성실히 반영
4. **재요청**: 수정 완료 후 재리뷰 요청

### 리뷰 할 때

코드 리뷰 시 다음 사항을 확인하세요:

#### 기능성
- [ ] 요구사항을 충족하는가?
- [ ] 예상대로 동작하는가?
- [ ] 엣지 케이스를 처리하는가?

#### 코드 품질
- [ ] 코드 컨벤션을 따르는가?
- [ ] 가독성이 좋은가?
- [ ] 중복 코드가 없는가?
- [ ] 적절히 모듈화되어 있는가?

#### 테스트
- [ ] 테스트 코드가 작성되었는가?
- [ ] 테스트가 충분한가?
- [ ] 모든 테스트가 통과하는가?

#### 문서
- [ ] 주석이 적절한가?
- [ ] README나 문서가 업데이트되었는가?

#### 성능 및 보안
- [ ] 성능 이슈가 없는가?
- [ ] 보안 취약점이 없는가?

### 리뷰 코멘트 작성

**건설적인 피드백**
```
✅ Good: "이 부분은 함수로 분리하면 재사용성이 높아질 것 같습니다."
❌ Bad: "이 코드는 별로네요."
```

**구체적인 제안**
```
✅ Good: "변수명을 userData보다는 currentUser가 더 명확할 것 같습니다."
❌ Bad: "변수명이 이상합니다."
```

**긍정적인 피드백도 함께**
```
✅ "에러 처리를 꼼꼼하게 하셨네요! 👍"
✅ "테스트 케이스가 잘 작성되었습니다!"
```

## 🐛 버그 리포트

버그를 발견하면 다음 절차를 따라주세요:

### 1. 이슈 검색
먼저 동일한 버그가 이미 보고되었는지 확인하세요.

### 2. 버그 리포트 작성
새로운 이슈를 생성하고 Bug Report 템플릿을 사용하세요.

```markdown
## 버그 설명
로그인 시 토큰이 저장되지 않는 문제

## 재현 방법
1. 로그인 페이지 접속
2. 유효한 계정으로 로그인
3. 페이지 새로고침
4. 로그인 상태가 유지되지 않음

## 예상 동작
로그인 후 토큰이 localStorage에 저장되어야 함

## 실제 동작
토큰이 저장되지 않고 페이지 새로고침 시 로그아웃됨

## 환경
- OS: macOS Sonoma 14.0
- Browser: Chrome 119
- Version: 1.0.0

## 추가 정보
콘솔에 에러 메시지 없음
```

### 3. 버그 수정
이슈가 승인되면 브랜치를 생성하고 수정을 진행하세요.

```bash
git checkout -b fix/125-token-storage-bug
```

## 💡 기능 제안

새로운 기능을 제안하려면:

### 1. 이슈 생성
Feature Request 템플릿을 사용하여 이슈를 생성하세요.

```markdown
## 기능 설명
다크 모드 지원 기능

## 동기
사용자들이 다크 모드를 선호하며, 눈의 피로를 줄일 수 있습니다.

## 제안하는 해결 방법
1. 테마 토글 버튼 추가
2. 로컬 스토리지에 테마 설정 저장
3. CSS 변수를 사용한 테마 시스템 구현

## 대안
- 시스템 설정을 따르는 자동 테마 변경
- 여러 테마 옵션 제공

## 추가 정보
Figma 디자인: [링크]
```

### 2. 논의
팀과 기능에 대해 논의하고 승인을 받으세요.

### 3. 구현
승인되면 기능을 구현하고 PR을 생성하세요.

## ⚠️ 주의사항

### 하지 말아야 할 것

1. ❌ main 또는 dev 브랜치에 직접 푸시
2. ❌ 코드 리뷰 없이 병합
3. ❌ 테스트 없이 코드 작성
4. ❌ 대용량 파일 커밋 (이미지, 비디오 등)
5. ❌ 민감 정보 커밋 (API 키, 비밀번호 등)
6. ❌ 여러 기능을 한 PR에 포함
7. ❌ force push (특히 공유 브랜치)

### 해야 할 것

1. ✅ 작은 단위로 자주 커밋
2. ✅ 의미 있는 커밋 메시지 작성
3. ✅ 테스트 코드 작성
4. ✅ 코드 리뷰에 적극 참여
5. ✅ 문서 업데이트
6. ✅ 컨벤션 준수
7. ✅ 충돌 발생 시 빠르게 해결

## 🎯 좋은 기여자 되기

### 커뮤니케이션
- 질문이 있으면 주저하지 말고 물어보세요
- 이슈와 PR에서 적극적으로 소통하세요
- 건설적인 피드백을 주고받으세요

### 코드 품질
- 항상 최선의 코드를 작성하려 노력하세요
- 리팩토링을 두려워하지 마세요
- 테스트를 중요하게 생각하세요

### 협업
- 다른 사람의 시간을 존중하세요
- 코드 리뷰는 빠르게 진행하세요
- 도움이 필요한 팀원을 적극 도와주세요

### 학습
- 실수를 두려워하지 마세요
- 피드백을 통해 성장하세요
- 새로운 기술을 배우는 것을 즐기세요

## 📚 참고 자료

- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Code Review Best Practices](https://google.github.io/eng-practices/review/)

## 💬 질문 및 지원

기여 관련 질문이 있으면:
- GitHub Issues에 질문 이슈 생성
- 팀 Slack 채널에 문의
- [jundevcodes@gmail.com] 로 연락

## 🙏 감사합니다

프로젝트에 기여해주셔서 진심으로 감사드립니다!
여러분의 기여가 프로젝트를 더 좋게 만듭니다. 🚀