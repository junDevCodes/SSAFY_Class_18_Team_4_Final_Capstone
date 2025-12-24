<template>
  <div class="checkout-fail-page">
    <div class="container">
      <div class="fail-state">
        <div class="fail-icon">😞</div>
        <h1>결제에 실패했습니다</h1>
        <p class="fail-message">{{ errorMessage }}</p>

        <div v-if="errorCode" class="error-details">
          <span class="error-code">오류 코드: {{ errorCode }}</span>
        </div>

        <div class="help-text">
          <p>결제가 완료되지 않았습니다. 다음 사항을 확인해주세요:</p>
          <ul>
            <li>카드 잔액 또는 한도를 확인해주세요</li>
            <li>입력한 카드 정보가 올바른지 확인해주세요</li>
            <li>문제가 지속되면 카드사에 문의해주세요</li>
          </ul>
        </div>

        <div class="actions">
          <router-link to="/checkout" class="btn-primary">다시 결제하기</router-link>
          <router-link to="/cart" class="btn-secondary">장바구니로 돌아가기</router-link>
          <router-link to="/" class="btn-outline">홈으로 이동</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 에러 정보
const errorCode = ref('')
const errorMessage = ref('알 수 없는 오류가 발생했습니다.')

onMounted(() => {
  // URL 쿼리 파라미터에서 에러 정보 추출
  errorCode.value = (route.query.code as string) || ''
  errorMessage.value = (route.query.message as string) || '결제 처리 중 문제가 발생했습니다.'

  // 토스 에러 코드별 사용자 친화적 메시지 변환
  if (errorCode.value) {
    const friendlyMessages: Record<string, string> = {
      'PAY_PROCESS_CANCELED': '결제가 취소되었습니다.',
      'PAY_PROCESS_ABORTED': '결제가 중단되었습니다.',
      'REJECT_CARD_COMPANY': '카드사에서 결제를 거부했습니다.',
      'INVALID_CARD_EXPIRATION': '카드 유효기간이 올바르지 않습니다.',
      'INVALID_STOPPED_CARD': '정지된 카드입니다.',
      'INVALID_CARD_LOST': '분실 신고된 카드입니다.',
      'INVALID_CARD_NUMBER': '카드번호가 올바르지 않습니다.',
      'EXCEED_MAX_CARD_INSTALLMENT_PLAN': '할부 개월 수가 초과되었습니다.',
      'NOT_SUPPORTED_INSTALLMENT_PLAN_CARD': '할부가 지원되지 않는 카드입니다.',
      'EXCEED_MAX_AMOUNT': '결제 한도를 초과했습니다.',
      'NOT_AVAILABLE_BANK': '현재 사용할 수 없는 은행입니다.',
      'INVALID_PASSWORD': '비밀번호가 올바르지 않습니다.',
      'INCORRECT_BASIC_AUTH_FORMAT': '인증 정보가 올바르지 않습니다.',
      'USER_CANCEL': '사용자가 결제를 취소했습니다.',
    }

    if (friendlyMessages[errorCode.value]) {
      errorMessage.value = friendlyMessages[errorCode.value]
    }
  }
})
</script>

<style scoped>
.checkout-fail-page {
  min-height: calc(100vh - 160px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #f8f9fa;
}

.container {
  max-width: 600px;
  width: 100%;
}

.fail-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.fail-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.fail-state h1 {
  font-size: 2rem;
  color: #dc3545;
  margin-bottom: 0.5rem;
}

.fail-message {
  color: #666;
  font-size: 1.125rem;
  margin-bottom: 1rem;
}

.error-details {
  margin-bottom: 1.5rem;
}

.error-code {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: monospace;
}

.help-text {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  text-align: left;
}

.help-text p {
  font-weight: 600;
  color: #856404;
  margin-bottom: 0.75rem;
}

.help-text ul {
  margin: 0;
  padding-left: 1.25rem;
  color: #856404;
}

.help-text li {
  margin-bottom: 0.5rem;
}

.help-text li:last-child {
  margin-bottom: 0;
}

/* 액션 버튼 */
.actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-primary,
.btn-secondary,
.btn-outline {
  display: block;
  padding: 1rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  transition: all 0.2s;
}

.btn-primary {
  background: #00a86b;
  color: white;
}

.btn-primary:hover {
  background: #008c5a;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-outline {
  background: white;
  color: #333;
  border: 2px solid #ddd;
}

.btn-outline:hover {
  border-color: #00a86b;
  color: #00a86b;
}

/* 반응형 */
@media (max-width: 480px) {
  .checkout-fail-page {
    padding: 1rem;
  }

  .fail-state {
    padding: 2rem 1.5rem;
  }

  .fail-state h1 {
    font-size: 1.5rem;
  }

  .fail-icon {
    font-size: 4rem;
  }

  .help-text {
    padding: 1rem;
  }
}
</style>
