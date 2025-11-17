# Code Convention

## 📋 목차
- [기본 원칙](#기본-원칙)
- [Backend (Django)](#backend-django)
- [Frontend (Vue)](#frontend-vue)
- [공통 규칙](#공통-규칙)
- [코드 검토 도구](#코드-검토-도구)

## 🎯 기본 원칙

1. **가독성**: 코드는 다른 사람이 읽기 쉽게 작성합니다
2. **일관성**: 정해진 규칙을 모든 코드에 일관되게 적용합니다
3. **단순성**: 불필요하게 복잡한 코드는 지양합니다
4. **의미 있는 이름**: 변수, 함수명은 그 역할을 명확히 표현합니다

---

## 🐍 Backend (Django)

### Python 스타일 가이드
**PEP 8** 스타일 가이드를 따릅니다.

### 명명 규칙

#### 변수 및 함수
- **snake_case** 사용
- 의미를 명확히 알 수 있는 이름

```python
# Good
user_name = "John"
is_active = True
def get_user_profile():
    pass

# Bad
userName = "John"
active = True
def getUserProfile():
    pass
```

#### 클래스명
- **PascalCase** 사용

```python
class UserProfile:
    pass

class ProductManager:
    pass
```

#### 상수
- **UPPER_SNAKE_CASE** 사용

```python
MAX_UPLOAD_SIZE = 5242880  # 5MB
API_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 10
```

#### 모듈 및 패키지
- **snake_case** 사용
- 짧고 명확한 이름

```python
# Good
user_management/
    __init__.py
    models.py
    views.py
    serializers.py
```

### Django 프로젝트 구조

```
backend/
├── config/                 # 프로젝트 설정
│   ├── settings/
│   │   ├── base.py        # 공통 설정
│   │   ├── development.py # 개발 환경
│   │   └── production.py  # 프로덕션 환경
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # 앱들
│   ├── users/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests.py
│   └── products/
├── requirements/           # 의존성
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── manage.py
```

### Models

```python
from django.db import models

class User(models.Model):
    """사용자 모델"""
    
    email = models.EmailField(unique=True, verbose_name="이메일")
    username = models.CharField(max_length=50, verbose_name="사용자명")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자들"
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """전체 이름 반환"""
        return f"{self.first_name} {self.last_name}"
```

**규칙:**
- Docstring 작성
- `verbose_name` 지정
- `Meta` 클래스에 `db_table`, `ordering` 명시
- `__str__` 메서드 구현

### Views (Django REST Framework)

```python
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class UserProfileView(APIView):
    """사용자 프로필 API"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """프로필 조회"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """프로필 수정"""
        serializer = UserSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(
            serializer.errors, 
            status=status.HTTP_400_BAD_REQUEST
        )
```

**규칙:**
- 각 메서드에 Docstring 작성
- 적절한 HTTP 상태 코드 사용
- 에러 처리 명시

### Serializers

```python
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """사용자 Serializer"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["id", "email", "username", "full_name", "created_at"]
        read_only_fields = ["id", "created_at"]
    
    def get_full_name(self, obj):
        """전체 이름 반환"""
        return obj.get_full_name()
    
    def validate_email(self, value):
        """이메일 유효성 검증"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value
```

### Import 순서

```python
# 1. 표준 라이브러리
import json
from datetime import datetime

# 2. Django 관련
from django.db import models
from django.contrib.auth.models import AbstractUser

# 3. 서드파티 라이브러리
from rest_framework import serializers
from rest_framework.views import APIView

# 4. 로컬 앱
from apps.users.models import User
from apps.users.serializers import UserSerializer
```

### 코드 스타일

```python
# 들여쓰기: 스페이스 4칸
def example_function():
    if condition:
        do_something()

# 줄 길이: 최대 79자 (PEP 8)
# 긴 줄은 적절히 줄바꿈
long_variable_name = some_function(
    parameter1, 
    parameter2,
    parameter3
)

# 공백
# 함수 정의 사이: 2줄
# 클래스 정의 사이: 2줄
# 메서드 정의 사이: 1줄

# 주석
# 한 줄 주석은 # 뒤 공백 하나
def function():
    # 이렇게 작성
    pass
```

---

## 🖼 Frontend (Vue)

### Vue 3 Composition API 사용

### 명명 규칙

#### 컴포넌트명
- **PascalCase** 사용 (multi-word)

```vue
<!-- Good -->
<template>
  <UserProfile />
  <ProductCard />
</template>

<!-- Bad -->
<template>
  <user-profile />  <!-- kebab-case는 템플릿에서만 -->
  <profile />       <!-- single-word 금지 -->
</template>
```

#### 변수 및 함수
- **camelCase** 사용

```javascript
// Good
const userName = ref('');
const isLoading = ref(false);
const fetchUserData = async () => {};

// Bad
const user_name = ref('');
const FetchUserData = async () => {};
```

#### 상수
- **UPPER_SNAKE_CASE** 사용

```javascript
const MAX_FILE_SIZE = 5242880;
const API_BASE_URL = 'http://localhost:8000/api';
```

### Vue 프로젝트 구조

```
frontend/
├── src/
│   ├── assets/           # 정적 파일
│   ├── components/       # 재사용 컴포넌트
│   │   ├── common/       # 공통 컴포넌트
│   │   └── features/     # 기능별 컴포넌트
│   ├── views/            # 페이지 컴포넌트
│   ├── router/           # 라우터 설정
│   ├── stores/           # Pinia 스토어
│   ├── composables/      # Composition 함수
│   ├── utils/            # 유틸리티 함수
│   ├── api/              # API 호출 함수
│   ├── styles/           # 글로벌 스타일
│   ├── App.vue
│   └── main.js
├── public/
└── package.json
```

### 컴포넌트 작성 순서

```vue
<script setup>
// 1. Import
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import UserCard from '@/components/UserCard.vue';

// 2. Props & Emits
const props = defineProps({
  userId: {
    type: Number,
    required: true
  }
});

const emit = defineEmits(['update', 'delete']);

// 3. Reactive Data
const user = ref(null);
const isLoading = ref(false);

// 4. Computed
const fullName = computed(() => {
  return `${user.value?.firstName} ${user.value?.lastName}`;
});

// 5. Methods
const fetchUser = async () => {
  isLoading.value = true;
  try {
    // API 호출
  } catch (error) {
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

// 6. Lifecycle Hooks
onMounted(() => {
  fetchUser();
});
</script>

<template>
  <!-- 템플릿 -->
</template>

<style scoped>
/* 스타일 */
</style>
```

### 컴포넌트 규칙

```vue
<script setup>
// Props는 객체 형식으로 상세하게 정의
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  count: {
    type: Number,
    default: 0
  },
  items: {
    type: Array,
    default: () => []
  }
});

// v-for에는 항상 :key 사용
</script>

<template>
  <div>
    <h1>{{ title }}</h1>
    <ul>
      <li v-for="item in items" :key="item.id">
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
/* scoped 스타일 사용 */
</style>
```

### API 호출 (Axios)

```javascript
// api/users.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const userAPI = {
  // 사용자 목록 조회
  getUsers: async (params) => {
    const response = await axios.get(`${API_BASE_URL}/users/`, { params });
    return response.data;
  },
  
  // 사용자 상세 조회
  getUser: async (userId) => {
    const response = await axios.get(`${API_BASE_URL}/users/${userId}/`);
    return response.data;
  },
  
  // 사용자 생성
  createUser: async (data) => {
    const response = await axios.post(`${API_BASE_URL}/users/`, data);
    return response.data;
  },
  
  // 사용자 수정
  updateUser: async (userId, data) => {
    const response = await axios.put(`${API_BASE_URL}/users/${userId}/`, data);
    return response.data;
  },
  
  // 사용자 삭제
  deleteUser: async (userId) => {
    const response = await axios.delete(`${API_BASE_URL}/users/${userId}/`);
    return response.data;
  }
};
```

### Pinia Store

```javascript
// stores/user.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { userAPI } from '@/api/users';

export const useUserStore = defineStore('user', () => {
  // State
  const user = ref(null);
  const isAuthenticated = ref(false);
  
  // Getters
  const fullName = computed(() => {
    return user.value ? `${user.value.firstName} ${user.value.lastName}` : '';
  });
  
  // Actions
  const login = async (credentials) => {
    try {
      const data = await userAPI.login(credentials);
      user.value = data.user;
      isAuthenticated.value = true;
      localStorage.setItem('token', data.token);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };
  
  const logout = () => {
    user.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem('token');
  };
  
  return {
    user,
    isAuthenticated,
    fullName,
    login,
    logout
  };
});
```

### 템플릿 규칙

```vue
<template>
  <!-- 여러 속성은 줄바꿈 -->
  <button
    type="button"
    class="btn-primary"
    :disabled="isLoading"
    @click="handleClick"
  >
    클릭
  </button>
  
  <!-- v-if와 v-for 같이 사용 금지 -->
  <!-- Bad -->
  <div v-if="isActive" v-for="item in items" :key="item.id">
    {{ item.name }}
  </div>
  
  <!-- Good -->
  <div v-if="isActive">
    <div v-for="item in items" :key="item.id">
      {{ item.name }}
    </div>
  </div>
  
  <!-- 복잡한 표현식은 computed 사용 -->
  <!-- Bad -->
  <div>{{ user.firstName + ' ' + user.lastName }}</div>
  
  <!-- Good -->
  <div>{{ fullName }}</div>
</template>
```

---

## 🔧 공통 규칙

### 파일명

```
Backend (Django):
- snake_case
- models.py, views.py, serializers.py

Frontend (Vue):
- PascalCase (컴포넌트)
- camelCase (유틸리티)
- UserProfile.vue
- formatDate.js
```

### 주석

```python
# Python
def get_user_profile(user_id):
    """
    사용자 프로필을 조회합니다.
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 사용자 프로필 정보
    """
    pass
```

```javascript
// JavaScript
/**
 * 사용자 프로필을 조회합니다
 * @param {number} userId - 사용자 ID
 * @returns {Promise<Object>} 사용자 프로필 정보
 */
const getUserProfile = async (userId) => {
  // 구현
};
```

---

## 🔍 코드 검토 도구

### Backend (Django)

#### 1. Flake8 (코드 스타일 검사)

**설치**
```bash
pip install flake8
```

**설정 파일 (.flake8)**
```ini
[flake8]
max-line-length = 88
exclude = 
    .git,
    __pycache__,
    */migrations/*,
    venv,
    env
ignore = E203, W503
```

**사용**
```bash
# 전체 검사
flake8 .

# 특정 디렉토리
flake8 apps/
```

#### 2. Black (자동 포맷팅)

**설치**
```bash
pip install black
```

**설정 파일 (pyproject.toml)**
```toml
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | migrations
)/
'''
```

**사용**
```bash
# 자동 포맷팅
black .

# 확인만 하기
black --check .
```

#### 3. isort (Import 정렬)

**설치**
```bash
pip install isort
```

**설정 파일 (pyproject.toml)**
```toml
[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88
skip_gitignore = true
```

**사용**
```bash
# Import 정렬
isort .

# 확인만 하기
isort --check-only .
```

#### 4. pylint (정적 분석)

**설치**
```bash
pip install pylint
```

**사용**
```bash
pylint apps/
```

### Frontend (Vue)

#### 1. ESLint (코드 검사)

**설치**
```bash
npm install -D eslint eslint-plugin-vue
```

**설정 파일 (.eslintrc.cjs)**
```javascript
module.exports = {
  root: true,
  env: {
    node: true,
    browser: true
  },
  extends: [
    'plugin:vue/vue3-recommended',
    'eslint:recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'vue/multi-word-component-names': 'error',
    'vue/component-name-in-template-casing': ['error', 'PascalCase'],
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'quotes': ['error', 'single'],
    'semi': ['error', 'always']
  }
};
```

**사용**
```bash
# 검사
npm run lint

# 자동 수정
npm run lint -- --fix
```

#### 2. Prettier (자동 포맷팅)

**설치**
```bash
npm install -D prettier eslint-config-prettier eslint-plugin-prettier
```

**설정 파일 (.prettierrc.json)**
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

**사용**
```bash
# 포맷팅
npx prettier --write "src/**/*.{js,vue,json}"

# 확인만
npx prettier --check "src/**/*.{js,vue,json}"
```

### VS Code 설정

**settings.json**
```json
{
  // Python
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  
  // Vue
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[vue]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact",
    "vue"
  ]
}
```

### Pre-commit Hook

**.pre-commit-config.yaml** (Backend)
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

**설치 및 사용**
```bash
pip install pre-commit
pre-commit install

# 수동 실행
pre-commit run --all-files
```

**package.json** (Frontend)
```json
{
  "scripts": {
    "lint": "eslint --ext .js,.vue src",
    "lint:fix": "eslint --ext .js,.vue src --fix",
    "format": "prettier --write \"src/**/*.{js,vue,json}\""
  },
  "husky": {
    "hooks": {
      "pre-commit": "npm run lint"
    }
  }
}
```

### GitHub Actions (자동 검사)

**.github/workflows/code-quality.yml**
```yaml
name: Code Quality Check

on: [pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install flake8 black isort
      - name: Run flake8
        run: flake8 .
      - name: Run black
        run: black --check .
      - name: Run isort
        run: isort --check-only .
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run ESLint
        run: npm run lint
      - name: Run Prettier
        run: npx prettier --check "src/**/*.{js,vue,json}"
```

## ✅ 체크리스트

### 코드 작성 전
- [ ] 컨벤션 문서 확인
- [ ] 린터 설정 완료

### 코드 작성 중
- [ ] 명명 규칙 준수
- [ ] 주석 적절히 작성
- [ ] 코드 포맷팅 자동 적용

### PR 생성 전
- [ ] `flake8`, `black`, `isort` 통과 (Backend)
- [ ] `npm run lint` 통과 (Frontend)
- [ ] 테스트 코드 작성
- [ ] 불필요한 console.log 제거