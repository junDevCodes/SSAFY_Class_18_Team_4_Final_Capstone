# 백엔드 빠른 시작 가이드

## ⚠️ 중요: 가상환경 활성화 필수!

백엔드를 실행하기 전에 **반드시 가상환경을 활성화**해야 합니다.

### Windows (Git Bash 또는 PowerShell)
```bash
# 프로젝트 루트로 이동
cd C:\Users\SSAFY\Desktop\final_pjt

# 가상환경 활성화
. venv/Scripts/activate

# 또는 PowerShell의 경우
venv\Scripts\Activate.ps1

# 백엔드 디렉토리로 이동
cd backend

# 서버 실행
python manage.py runserver 8000
```

### Linux/Mac
```bash
# 프로젝트 루트로 이동
cd ~/Desktop/final_pjt

# 가상환경 활성화
source venv/bin/activate

# 백엔드 디렉토리로 이동
cd backend

# 서버 실행
python manage.py runserver 8000
```

## ✅ 설치 확인

가상환경이 활성화되면 터미널 프롬프트 앞에 `(venv)`가 표시됩니다.

```bash
(venv) C:\Users\SSAFY\Desktop\final_pjt\backend>
```

## 🔍 문제 해결

### 오류: `ModuleNotFoundError: No module named 'corsheaders'`
**해결 방법:**
```bash
# 가상환경 활성화 후
pip install django-cors-headers
```

### 오류: `No module named 'django'`
**해결 방법:**
```bash
# 가상환경 활성화 후
pip install -r requirements.txt
```

### 포트 8000이 이미 사용 중인 경우
```bash
# 다른 포트 사용
python manage.py runserver 8001
```

그리고 프론트엔드의 `.env.development` 파일에서도 포트를 변경:
```env
VITE_API_BASE_URL=http://localhost:8001
```

## 📝 서버 실행 확인

서버가 정상적으로 실행되면 다음과 같은 메시지가 표시됩니다:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

브라우저에서 `http://localhost:8000/admin/`에 접속하여 Django 관리자 페이지가 로드되는지 확인할 수 있습니다.

## 🎯 다음 단계

1. 백엔드 서버 실행 확인
2. 프론트엔드 서버 실행 (`cd frontend && npm run dev`)
3. 브라우저에서 `http://localhost:3000` 접속
4. 회원가입/로그인 테스트

