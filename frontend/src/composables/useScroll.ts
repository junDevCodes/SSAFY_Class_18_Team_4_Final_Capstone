import { onMounted, onUnmounted } from 'vue'
import { useUIStore } from '@/stores/ui'

// 스크롤 컴포저블
export function useScroll() {
  const uiStore = useUIStore()

  const handleScroll = () => {
    uiStore.setScrolled(window.scrollY > 50)
  }

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const scrollToContent = () => {
    const nav = document.getElementById('sticky-nav')
    if (nav) {
      nav.scrollIntoView({ behavior: 'smooth' })
      return
    }
    // 폴백: 화면 하단으로 한 화면 정도 스크롤
    const target = window.innerHeight - 80
    window.scrollTo({ top: target > 0 ? target : 0, behavior: 'smooth' })
  }

  onMounted(() => {
    window.addEventListener('scroll', handleScroll)
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll)
  })

  return {
    scrollToTop,
    scrollToContent
  }
}

