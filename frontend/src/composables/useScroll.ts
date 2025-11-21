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
    }
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

