import axios from 'axios'
import { ElLoading, ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  baseURL: '', // 通过 Vite proxy 代理 /api → http://localhost:8010（避免 CORS）
  timeout: 15000 // 15 秒超时（FastF1 首次加载可能较慢）
})

let loadingInstance = null
// 简易计数：多个并发请求只弹一次 Loading
let requestCount = 0

function showLoading() {
  if (requestCount === 0) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '加载数据中，首次加载可能较慢...',
      background: 'rgba(0, 0, 0, 0.5)'
    })
  }
  requestCount++
}

function hideLoading() {
  requestCount = Math.max(0, requestCount - 1)
  if (requestCount === 0) {
    loadingInstance?.close()
    loadingInstance = null
  }
}

// 请求拦截器：附加 Authorization + 统一显示 Loading
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('f1_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    showLoading()
    return config
  },
  (error) => {
    hideLoading()
    return Promise.reject(error)
  }
)

// 响应拦截器：兼容后端两种返回格式
//   1) Ergast 接口：直接返回数据本体（RaceTable / StandingsTable），无 code 字段
//   2) FastF1 接口：返回 { code: 200/500, msg, ... }，code===500 为"软错误"
// 请求时可传 config.silent = true 来抑制错误弹窗（用于探测性请求）
service.interceptors.response.use(
  (response) => {
    hideLoading()
    const res = response.data

    // 只在后端显式带 code 字段（FastF1）且不为 200 时，才当作业务错误
    if (res && typeof res.code === 'number' && res.code !== 200) {
      if (!response.config?.silent) {
        ElMessage.error(res.msg || '数据加载失败')
      }
      return Promise.reject(new Error(res.msg || 'Error'))
    }
    // 正常返回数据本体，组件里无需再 .data.data
    return res
  },
  (error) => {
    hideLoading()
    // 如果请求时设了 silent，不弹任何错误提示
    if (error.config?.silent) {
      return Promise.reject(error)
    }
    // HTTP 层错误（4xx/5xx/超时/断网）
    if (error.code === 'ECONNABORTED') {
      // 遥测类接口数据量大（50-100MB 原始数据），给出针对性提示
      const url = error.config?.url || ''
      const isHeavy = url.includes('/telemetry') || url.includes('/speed-overlay') || url.includes('/track-map')
      ElMessage.error(isHeavy
        ? '遥测数据量较大，加载超时。请稍后重试（第二次会走缓存，快很多）'
        : '请求超时，请稍后重试')
    } else if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || '服务器异常'
      ElMessage.error(`[${status}] ${detail}`)
    } else {
      ElMessage.error('网络错误或服务器未启动')
    }
    return Promise.reject(error)
  }
)

export default service
