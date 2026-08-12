import request from './request'

/**
 * 赛程 / 分站结果相关接口（模块 A1 / A2）
 * 所有函数支持传入 { silent: true } 来抑制错误弹窗（用于 store 层有兜底逻辑的调用）
 */

// 获取当前赛季赛程
export const getCurrentSeason = (options = {}) => {
  return request.get('/api/current-season', options)
}

// 获取指定年份赛程
export const getSeasonByYear = (year, options = {}) => {
  return request.get(`/api/season/${year}`, options)
}

// 获取单站比赛结果（返回完整 RaceTable，前端自行取 Top10）
export const getRaceResult = (year, round, options = {}) => {
  return request.get(`/api/race-result/${year}/${round}`, options)
}

// 获取全部赛道信息
export const getAllCircuits = (options = {}) => {
  return request.get('/api/circuits', options)
}

// 获取当前赛季分站排位赛结果
export const getCurrentQualifying = (round, options = {}) => {
  return request.get(`/api/current/${round}/qualifying`, options)
}

// 获取历史赛季分站排位赛结果
export const getQualifyingByYear = (year, round, options = {}) => {
  return request.get(`/api/${year}/${round}/qualifying`, options)
}
