/**
 * AppHeader — 顶部水平导航
 * 5 个一级入口：赛事数据中心 / 遥测分析 / AI预测 / Fantasy / 投票
 * GP Tempo 风格：暗色背景 + F1 品牌红高亮
 */
<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <span class="logo-icon">🏎️</span>
        <span class="logo-text">F1 <span class="logo-accent">DATA</span></span>
      </router-link>
    </div>

    <nav class="header-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item) }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="header-right">
      <span class="season-badge">{{ store.currentSeason }} 赛季</span>
    </div>
  </header>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useF1Store } from '@/stores/f1'

const route = useRoute()
const store = useF1Store()

const navItems = [
  { path: '/race-center', label: '赛事数据中心', icon: '📅', match: ['/race-center', '/'] },
  { path: '/telemetry', label: '遥测分析', icon: '📈', match: ['/telemetry'] },
  { path: '/prediction', label: 'AI 预测', icon: '🤖', match: ['/prediction'] },
  { path: '/fantasy', label: 'Fantasy', icon: '🏆', match: ['/fantasy'] },
  { path: '/vote', label: '车手投票', icon: '🗳️', match: ['/vote'] },
]

function isActive(item) {
  return item.match.some(m => route.path === m || route.path.startsWith(m + '/'))
}
</script>

<style scoped>
.app-header {
  height: 56px;
  background: var(--f1-bg-dark);
  border-bottom: 1px solid var(--f1-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.header-left {
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--f1-text-primary);
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1px;
}

.logo-accent {
  color: var(--f1-red);
  font-weight: 900;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  text-decoration: none;
  color: var(--f1-text-secondary);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--f1-bg-hover);
  color: var(--f1-text-primary);
}

.nav-item.active {
  background: rgba(225, 6, 0, 0.12);
  color: var(--f1-red);
}

.nav-icon {
  font-size: 16px;
}

.nav-label {
  line-height: 1;
}

.header-right {
  flex-shrink: 0;
}

.season-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 4px;
  background: var(--f1-bg-elevated);
  border: 1px solid var(--f1-border);
  color: var(--f1-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .nav-label {
    display: none;
  }
  .nav-item {
    padding: 8px 10px;
  }
  .nav-icon {
    font-size: 20px;
  }
}
</style>
