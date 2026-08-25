<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="logo-icon">🏎️</span>
        <span class="logo-text">F1 <span class="logo-accent">DATA</span></span>
      </div>
      <p class="login-sub">F1 数据平台 · 用户登录</p>

      <el-tabs v-model="authTab" stretch>
        <!-- 登录 -->
        <el-tab-pane label="登录" name="login">
          <el-form label-width="0" @submit.prevent="doLogin">
            <el-form-item>
              <el-input
                v-model="loginForm.username"
                placeholder="用户名或邮箱"
                size="large"
                :prefix-icon="User"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="loginForm.password"
                type="password"
                show-password
                placeholder="密码"
                size="large"
                :prefix-icon="Lock"
                @keyup.enter="doLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="authLoading"
              @click="doLogin"
            >
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form label-width="0" @submit.prevent="doRegister">
            <el-form-item>
              <el-input
                v-model="regForm.username"
                placeholder="用户名（至少 3 位）"
                size="large"
                :prefix-icon="User"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.email"
                placeholder="邮箱"
                size="large"
                :prefix-icon="Message"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.password"
                type="password"
                show-password
                placeholder="密码（至少 6 位）"
                size="large"
                :prefix-icon="Lock"
                @keyup.enter="doRegister"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="authLoading"
              @click="doRegister"
            >
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="login-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>未登录也可浏览全部数据，登录后解锁 Fantasy / 投票等个性化功能</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, InfoFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const authTab = ref('login')
const authLoading = ref(false)
const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', email: '', password: '' })

// 登录成功后跳转：优先回来源页，其次首页
const redirectAfterAuth = () => {
  const redirect = route.query.redirect
  router.replace(typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/')
}

const doLogin = async () => {
  if (!loginForm.value.username.trim()) {
    ElMessage.error('请输入用户名或邮箱')
    return
  }
  if (!loginForm.value.password) {
    ElMessage.error('请输入密码')
    return
  }
  authLoading.value = true
  try {
    await userStore.login(loginForm.value)
    ElMessage.success('登录成功')
    redirectAfterAuth()
  } catch { /* 拦截器已弹错误 */ }
  authLoading.value = false
}

const doRegister = async () => {
  // 与后端 UserRegister schema 规则保持一致，避免 422
  if (!regForm.value.username || regForm.value.username.trim().length < 3) {
    ElMessage.error('用户名至少 3 位')
    return
  }
  if (!regForm.value.email || !regForm.value.email.includes('@') || !regForm.value.email.includes('.')) {
    ElMessage.error('请输入正确的邮箱地址')
    return
  }
  if (!regForm.value.password || regForm.value.password.length < 6) {
    ElMessage.error('密码至少 6 位')
    return
  }
  authLoading.value = true
  try {
    await userStore.register(regForm.value)
    ElMessage.success('注册成功，已自动登录')
    redirectAfterAuth()
  } catch { /* 拦截器已弹错误 */ }
  authLoading.value = false
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 56px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(160deg, #f5f7fa 0%, #eef1f6 100%);
}

.login-card {
  width: 380px;
  padding: 32px 36px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 6px;
}

.logo-icon { font-size: 28px; }

.logo-text {
  font-size: 22px;
  font-weight: 800;
  color: #1f2329;
  letter-spacing: 1px;
}

.logo-accent { color: #e10600; font-weight: 900; }

.login-sub {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin: 0 0 20px;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.login-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 18px;
  padding: 10px 12px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 6px;
  color: #67c23a;
  font-size: 12px;
  line-height: 1.6;
}

.login-tip .el-icon { margin-top: 2px; flex-shrink: 0; }
</style>
