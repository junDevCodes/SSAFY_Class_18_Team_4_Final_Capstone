<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <button class="logo" type="button" @click="goHome">
        <span class="logo-main">Sel</span>
        <span class="logo-accent">F</span>
      </button>

      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          class="nav-link"
          :class="{ active: isActive(item) }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <main class="admin-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

const navItems = [
  {
    name: 'admin-analytics-topline',
    label: '핵심 지표',
    to: { name: 'admin-analytics-topline' },
  },
  {
    name: 'admin-analytics-recommendation',
    label: '추천 성과',
    to: { name: 'admin-analytics-recommendation' },
  },
  {
    name: 'admin-analytics-behavior',
    label: '유저 행동',
    to: { name: 'admin-analytics-behavior' },
  },
  {
    name: 'admin-analytics-operational',
    label: '운영 지표',
    to: { name: 'admin-analytics-operational' },
  },
  {
    name: 'admin-users',
    label: '유저 관리',
    to: { name: 'admin-users' },
  },
] as const

const goHome = () => {
  router.push({ name: 'home' })
}

const isActive = (item: (typeof navItems)[number]) => {
  if (route.name === item.name) return true
  return false
}
</script>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: #0f172a;
}

.admin-sidebar {
  width: 240px;
  padding: 20px 16px;
  background: radial-gradient(circle at top left, #1e293b 0, #020617 55%);
  border-right: 1px solid rgba(148, 163, 184, 0.3);
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: sticky;
  top: 0;
  align-self: flex-start;
  height: 100vh;
}

.logo {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.logo-main {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 800;
  font-size: 50px;
  letter-spacing: -0.04em;
  color: #f9fafb;
}

.logo-accent {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-weight: 800;
  font-size: 50px;
  font-style: italic;
  letter-spacing: -0.04em;
  color: #38bdf8;
}

.nav {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-link {
  display: block;
  padding: 9px 12px;
  border-radius: 999px;
  font-size: 20px;
  font-weight: 600;
  color: #cbd5f5;
  text-decoration: none;
  border: 1px solid transparent;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.nav-link:hover {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(148, 163, 184, 0.6);
}

.nav-link.active {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #f9fafb;
  border-color: transparent;
}

.admin-main {
  flex: 1;
  background: #f6f7fb;
  min-height: 100vh;
}

@media (max-width: 960px) {
  .admin-shell {
    flex-direction: column;
  }

  .admin-sidebar {
    position: static;
    height: auto;
    width: 100%;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
  }

  .nav {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .nav-link {
    font-size: 12px;
    padding: 6px 10px;
  }
}
</style>


