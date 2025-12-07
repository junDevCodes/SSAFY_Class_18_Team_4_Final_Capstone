import { reactive, onMounted, onUnmounted } from 'vue'

// 타이머 컴포저블
export function useTimer() {
  const timer = reactive({ hours: '00', minutes: '00', seconds: '00' })

  let intervalId: ReturnType<typeof setInterval> | null = null


  const tick = () => {
    const now = new Date()
    const target = new Date()
    target.setHours(24, 0, 0, 0)

    const totalSeconds = Math.max(0, Math.floor((target.getTime() - now.getTime()) / 1000))
    timer.hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0')
    timer.minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0')
    timer.seconds = String(totalSeconds % 60).padStart(2, '0')

    if (totalSeconds === 0 && intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  const startTimer = () => {
    if (intervalId) return
    tick()
    intervalId = setInterval(tick, 1000)
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

