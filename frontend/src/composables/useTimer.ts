import { reactive, onMounted, onUnmounted } from 'vue'

// 타이머 컴포저블
export function useTimer() {
  const timer = reactive({ hours: '12', minutes: '34', seconds: '56' })

  let intervalId: ReturnType<typeof setInterval> | null = null

  const startTimer = () => {
    intervalId = setInterval(() => {
      const now = new Date()
      timer.hours = String(23 - now.getHours()).padStart(2, '0')
      timer.minutes = String(59 - now.getMinutes()).padStart(2, '0')
      timer.seconds = String(59 - now.getSeconds()).padStart(2, '0')
    }, 1000)
  }

  const stopTimer = () => {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  onMounted(() => {
    startTimer()
  })

  onUnmounted(() => {
    stopTimer()
  })

  return {
    timer,
    startTimer,
    stopTimer
  }
}

