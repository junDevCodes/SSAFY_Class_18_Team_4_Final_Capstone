<template>
  <div class="flex items-center justify-center min-h-screen px-4 py-12 bg-gray-50">
    <div class="w-full max-w-md">
      <!-- 카드 -->
      <div class="p-8 bg-white shadow-xl rounded-2xl">
        <!-- 로고 -->
        <div class="mb-6 text-center">
          <div class="text-3xl font-bold font-display text-brand-900">
            Sel<span class="inline-block transform italic text-brand-500 ml-0.5">F</span>
          </div>
        </div>

        <!-- 아이콘 -->
        <div class="flex items-center justify-center w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100">
          <KeyRound :size="32" class="text-amber-600" />
        </div>

        <!-- 제목 -->
        <div class="mb-8 text-center">
          <h1 class="mb-2 text-xl font-bold text-gray-900">비밀번호 변경 필요</h1>
          <p class="text-sm text-gray-500">
            임시 비밀번호로 로그인하셨습니다.<br>
            보안을 위해 새 비밀번호를 설정해주세요.
          </p>
        </div>

        <!-- 폼 -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label class="block mb-1 text-sm font-medium text-gray-700">새 비밀번호</label>
            <input
              v-model="newPassword"
              type="password"
              placeholder="영문, 숫자, 특수문자 포함 8자 이상"
              class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
              :class="{ 'border-red-500 focus:ring-red-500': passwordError }"
            >
            <p v-if="passwordError" class="mt-1 text-xs text-red-500">{{ passwordError }}</p>
          </div>

          <div>
            <label class="block mb-1 text-sm font-medium text-gray-700">새 비밀번호 확인</label>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="비밀번호를 다시 입력해주세요"
              class="w-full px-4 py-3 text-sm transition-all border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
              :class="{ 'border-red-500 focus:ring-red-500': confirmError }"
            >
            <p v-if="confirmError" class="mt-1 text-xs text-red-500">{{ confirmError }}</p>
          </div>

          <!-- 비밀번호 요구사항 -->
          <div class="p-3 rounded-lg bg-gray-50">
            <p class="mb-2 text-xs font-medium text-gray-700">비밀번호 요구사항</p>
            <ul class="space-y-1 text-xs text-gray-500">
              <li :class="{ 'text-green-600': hasMinLength }">
                <span class="mr-1">{{ hasMinLength ? '✓' : '○' }}</span>
                8자 이상
              </li>
              <li :class="{ 'text-green-600': hasLetter }">
                <span class="mr-1">{{ hasLetter ? '✓' : '○' }}</span>
                영문자 포함
              </li>
              <li :class="{ 'text-green-600': hasNumber }">
                <span class="mr-1">{{ hasNumber ? '✓' : '○' }}</span>
                숫자 포함
              </li>
              <li :class="{ 'text-green-600': hasSpecial }">
                <span class="mr-1">{{ hasSpecial ? '✓' : '○' }}</span>
                특수문자 포함 (!@#$%^&* 등)
              </li>
            </ul>
          </div>

          <button
            type="submit"
            :disabled="isSubmitting || !isPasswordValid"
            class="w-full bg-brand-500 hover:bg-brand-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-3.5 rounded-lg transition-colors text-sm shadow-lg shadow-brand-500/20"
          >
            {{ isSubmitting ? '처리 중...' : '비밀번호 변경' }}
          </button>
        </form>

        <!-- 로그아웃 링크 -->
        <div class="mt-6 text-center">
          <button
            @click="handleLogout"
            class="text-sm text-gray-500 hover:text-gray-700 hover:underline"
          >
            다른 계정으로 로그인
          </button>
        </div>
      </div>

      <!-- 안내 문구 -->
      <p class="mt-4 text-xs text-center text-gray-400">
        비밀번호를 변경하지 않으면 서비스를 이용할 수 없습니다.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { KeyRound } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const newPassword = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)

// 비밀번호 유효성 검사
const hasMinLength = computed(() => newPassword.value.length >= 8)
const hasLetter = computed(() => /[a-zA-Z]/.test(newPassword.value))
const hasNumber = computed(() => /\d/.test(newPassword.value))
const hasSpecial = computed(() => /[!@#$%^&*(),.?":{}|<>]/.test(newPassword.value))

const isPasswordValid = computed(() =>
  hasMinLength.value && hasLetter.value && hasNumber.value && hasSpecial.value
)

const passwordError = computed(() => {
  if (!newPassword.value) return ''
  if (!hasMinLength.value) return '비밀번호는 8자 이상이어야 합니다.'
  if (!hasLetter.value) return '영문자를 포함해야 합니다.'
  if (!hasNumber.value) return '숫자를 포함해야 합니다.'
  if (!hasSpecial.value) return '특수문자를 포함해야 합니다.'
  return ''
})

const confirmError = computed(() => {
  if (!confirmPassword.value) return ''
  if (newPassword.value !== confirmPassword.value) return '비밀번호가 일치하지 않습니다.'
  return ''
})

// 비밀번호 변경 처리
const handleSubmit = async () => {
  if (!isPasswordValid.value) {
    uiStore.showToast('비밀번호 요구사항을 충족해주세요.')
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    uiStore.showToast('비밀번호가 일치하지 않습니다.')
    return
  }

  isSubmitting.value = true
  try {
    await authStore.forceChangePassword(newPassword.value)
    uiStore.showToast('비밀번호가 변경되었습니다.')

    // 권한에 따른 리다이렉트
    if (authStore.isAdmin) {
      router.push('/admin/analytics')
    } else if (authStore.isSeller) {
      router.push('/seller/dashboard')
    } else {
      router.push('/mypage/profile')
    }
  } catch (error: any) {
    uiStore.showToast(error.message || '비밀번호 변경에 실패했습니다.')
  } finally {
    isSubmitting.value = false
  }
}

// 로그아웃 처리
const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
  uiStore.showToast('로그아웃되었습니다.')
}
</script>
