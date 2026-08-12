import request from './request'

/**
 * 车手 / 车队相关接口（模块 A3）
 * 所有函数支持传入 { silent: true } 来抑制错误弹窗（用于 store 层有兜底逻辑的调用）
 */

// 获取当前赛季车手名单
export const getCurrentDrivers = (options = {}) => {
  return request.get('/api/current/drivers', options)
}

// 获取指定年份车手名单
export const getDriversByYear = (year, options = {}) => {
  return request.get(`/api/${year}/drivers`, options)
}

// 获取当前赛季车手积分榜
export const getDriverStandings = (options = {}) => {
  return request.get('/api/current/driverstandings', options)
}

// 获取当前赛季车队积分榜
export const getConstructorStandings = (options = {}) => {
  return request.get('/api/current/constructorstandings', options)
}
