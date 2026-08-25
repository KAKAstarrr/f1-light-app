import { defineStore } from 'pinia'
import * as authApi from '@/api/auth'

const TOKEN_KEY = 'f1_token' // 保持与历史散点读取的键名一致

/**
 * 用户状态仓库（模块 3A 前端配套）
 * 管理：登录 token、用户信息、登录/注册/退出
 * 策略：可选登录 —— 未登录仍可浏览，登录后解锁个性化功能
 */
export const useUserStore = defineStore('user', {
  state() {
    return {
      token: localStorage.getItem(TOKEN_KEY) || '',
      userInfo: null, // { id, username, email, display_name, role }
      initialized: false,
    }
  },

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    displayName: (state) =>
      state.userInfo?.display_name || state.userInfo?.username || '',
  },

  actions: {
    // 初始化：已有 token 时拉取用户信息（token 失效则自动清理）
    async init() {
      if (this.initialized) return
      this.initialized = true
      if (!this.token) return
      try {
        const me = await authApi.getMe({ silent: true })
        this.userInfo = me
      } catch {
        // token 无效/过期 → 静默清理，不打扰浏览
        this.clearAuth()
      }
    },

    async login(payload) {
      const res = await authApi.login(payload)
      this.setAuth(res.access_token)
      try {
        this.userInfo = await authApi.getMe({ silent: true })
      } catch { /* me 拉取失败不阻断登录 */ }
      return res
    },

    async register(payload) {
      const res = await authApi.register(payload)
      this.setAuth(res.access_token)
      try {
        this.userInfo = await authApi.getMe({ silent: true })
      } catch { /* 同上 */ }
      return res
    },

    setAuth(token) {
      this.token = token
      localStorage.setItem(TOKEN_KEY, token)
    },

    // 退出登录：清 token + 用户信息
    logout() {
      this.clearAuth()
    },

    clearAuth() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
