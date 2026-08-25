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

      <!-- 未登录：登录入口 -->
      <el-button
        v-if="!userStore.isLoggedIn"
        class="login-btn"
        size="small"
        round
        @click="router.push('/login')"
      >
        <el-icon style="margin-right: 4px"><User /></el-icon>
        登录 / 注册
      </el-button>

      <!-- 已登录：用户下拉 -->
      <el-dropdown v-else trigger="click" @command="onUserCommand">
        <span class="user-chip">
          <el-avatar :size="24" class="user-avatar">{{ avatarChar }}</el-avatar>
          <span class="user-name">{{ userStore.displayName || userStore.userInfo?.username }}</span>
          <el-icon class="user-caret"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              角色：{{ roleLabel }}
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useF1Store } from '@/stores/f1'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const store = useF1Store()
const userStore = useUserStore()

const avatarChar = computed(() => {
  const name = userStore.displayName || userStore.userInfo?.username || '?'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const role = userStore.userInfo?.role
  const map = { admin: '管理员', user: '普通用户' }
  return map[role] || role || '普通用户'
})

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

function onUserCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  }
}

onMounted(() => {
  // 已有 token 时拉取用户信息（静默，失败自动清理）
  userStore.init()
})
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
  display: flex;
  align-items: center;
  gap: 10px;
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

/* 用户区 */
.login-btn {
  background: var(--f1-red);
  border-color: var(--f1-red);
  color: #fff;
  font-weight: 600;
}

.login-btn:hover {
  opacity: 0.9;
  color: #fff;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 12px 3px 4px;
  border-radius: 20px;
  background: var(--f1-bg-elevated);
  border: 1px solid var(--f1-border);
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
}

.user-chip:hover {
  border-color: var(--f1-red);
}

.user-avatar {
  background: var(--f1-red);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.user-name {
  color: var(--f1-text-primary);
  font-size: 13px;
  font-weight: 600;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-caret {
  color: var(--f1-text-secondary);
  font-size: 12px;
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
