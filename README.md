
﻿# SelF

> 소비자가 원하는 상품을 추천하고, 가장 저렴하게 찾을 수 있는 전자상거래 플랫폼.

<img src="https://i.postimg.cc/FsR1X5cv/Self_로고.png" alt="SelF-Logo" width="200">

## 📌 프로젝트 소개

프로젝트의 목적과 배경, 주요 특징을 설명합니다.

- **1차 개발 기간**: 2025.11.10 ~ 2025.12.28
- **추가 개발 기간**: 2025.12.28 ~ YYYY.MM.DD
- **팀 구성**: 3명

## 👥 팀원 소개

| 이름 | 역할 | GitHub | 담당 기능 |
|------|------|--------|-----------|
| 이준영 | 팀장/Data/AI/Embeded/DevOps | [@junDevCodes](@https://github.com/junDevCodes) | Data 분석 & 인사이트 도출, CI/CD 파이프라인 구축 |
| 배용건 | Frontend | [@dragun8](@https://github.com/dragun8) | MVP 설계, UI/UX 구현 |
| 송준서 | Backend/DevOps/AI Agent | [@Junseo5](@https://github.com/Junseo5) | API 개발, DB 설계, 기능 개발 |

## 🛠 기술 스택

### Frontend
![VUE](https://img.shields.io/badge/Vue.js-35495E?&logo=vuedotjs&logoColor=FFF&style=flat-square)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![TypeScript](https://shields.io/badge/TypeScript-3178C6?logo=TypeScript&logoColor=FFF&style=flat-square)

### Backend
![Django](https://img.shields.io/badge/Django-092E20?&style=flat-square&logo=django&logoColor=green)
![DRF](https://img.shields.io/badge/django--rest--framework-3.12.4-blue?style=flat-square&labelColor=333333&logo=django&logoColor=white&color=blue)

### Database
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white&style=flat-square)![Redis:Database](https://img.shields.io/badge/Database-Redis-informational?style=flat-square&logo=redis&logoColor=white&color=red)

### Crawling / Scraping
![Playwright]()

### Data Processing & ML/DL
![Pandas](https://img.shields.io/badge/-Pandas-333333?style=flat-square&logo=pandas)
![Numpy](https://img.shields.io/badge/-Numpy-013243?&logo=NumPy&style=flat-square)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![Keras](https://img.shields.io/badge/-Keras-D00000?style=flat-sqaure&logo=Keras)
![Prophet]()
![Sentence-Transformers]()
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)

### Cloud & Infra
![Docker](https://img.shields.io/badge/docker-257bd6?style=flat-square&logo=docker&logoColor=white)
![Docker-compose](https://img.shields.io/badge/Docker%20Compose-061D2F?logo=docker&style=flat-square)
![AWS-Lightsail-Container]()
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white&style=flat-square)
![Github-Actions](https://img.shields.io/badge/-GitHub%20Actions-333333?style=flat-square&logo=github-actions)

### Storage
![AWS-S3]()
![Nginx](https://img.shields.io/badge/Nginx-009639?logo=nginx&logoColor=white&style=flat-square)


### Authentication
![OAuth2](https://img.shields.io/badge/OAuth_2.0-Bearer-000000?style=flat-square)
<!-- ### Tools
![REDIS](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?style=for-the-badge&logo=apache-kafka&logoColor=white) -->

### Communicate
![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-Join?logo=Slack&style=flat-square)
![Discord](https://shields.io/discord/1442794136955654144?style=flat-square&label=discord&logo=discord&labelColor=black&color=5865F2)


## ✨ 주요 기능

> 🚧 개발 중 - 주요 기능은 개발 완료 후 업데이트 예정

````markdown
FORMAT
### 1. 기능명
- 기능에 대한 간단한 설명
- 스크린샷 또는 GIF 추가 권장

### 2. 기능명
- 기능에 대한 간단한 설명

### 3. 기능명
- 기능에 대한 간단한 설명

## 🏗 프로젝트 구조

```
project-root/
├── backend/            # Django 백엔드 (REST API)
├── frontend/           # Vue.js 프론트엔드
├── data/               # 데이터 분석, Jupyter Notebook, 인사이트
├── storage/            # 데이터 저장 및 DB
├── docs/               # 프로젝트 문서
│   ├── GIT_CONVENTION.md
│   ├── CODE_CONVENTION.md
│   ├── BRANCH_STRATEGY.md
│   ├── CODE_REVIEW.md
│   └── CONTRIBUTING.md
└── README.md
```
````

## 🚀 설치 및 실행

### 요구사항

**Backend**
- Python 3.9 이상
- pip

**Frontend**
- Node.js 18.x 이상
- npm 또는 yarn

### Backend 설치 및 실행
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

# 개발 서버 실행
python manage.py runserver

# 테스트 실행
python manage.py test
```

### Frontend 설치 및 실행
```bash
# 프론트엔드 디렉토리 이동
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버 실행
npm start
```

## 📝 협업 규칙

- [Git Convention](docs/GIT_CONVENTION.md)
- [Code Convention](docs/CODE_CONVENTION.md)
- [Branch Strategy](docs/BRANCH_STRATEGY.md)
- [Code Review](docs/CODE_REVIEW.md)

## 🔗 링크

- [프로젝트 기획 노션 페이지](https://www.notion.so/SSAFY-SEOUL-CLASS-18-TEAM-4-FINAL-CAPSTONE-PROJECT-2a67359b60688023991cef2fa72846f1?source=copy_link)
- [배포 URL](https://example.com)
- [API 문서](https://api.example.com/docs)

## 📄 라이센스

MIT License

## 🤝 기여

이 프로젝트에 기여하고 싶으시다면 [CONTRIBUTING.md](docs/CONTRIBUTING.md)를 참고해주세요.