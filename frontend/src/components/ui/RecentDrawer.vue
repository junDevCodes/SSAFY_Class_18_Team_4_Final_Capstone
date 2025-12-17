<template>
  <teleport to="body">
    <Transition name="fade">
      <div v-if="uiStore.isRecentOpen" class="backdrop" @click="uiStore.closeRecent">
        <aside class="drawer" @click.stop>
          <header class="drawer-header">
            <div class="title">최근 본 상품</div>
            <button class="close" type="button" aria-label="닫기" @click="uiStore.closeRecent">×</button>
          </header>

          <div class="drawer-body">
            <RecentProductsRail :limit="20" wrapper-class="p-0" />
          </div>
        </aside>
      </div>
    </Transition>
  </teleport>
</template>

<script setup lang="ts">
import RecentProductsRail from '@/components/sections/RecentProductsRail.vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()
</script>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  justify-content: flex-end;
  z-index: 1200;
}

.drawer {
  width: min(440px, 90vw);
  height: 100vh;
  background: #fff;
  box-shadow: -6px 0 18px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.title {
  font-weight: 800;
  font-size: 16px;
  color: #111827;
}

.close {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}

.close:hover {
  color: #111827;
}

.drawer-body {
  padding: 12px 16px 20px;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
