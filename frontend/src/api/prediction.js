import request from './request'

/**
 * AI 预测接口（模块 3B）
 */

/** 获取指定分站的夺冠概率预测（无记录时 save=true 会计算并保存到历史库） */
export const getPrediction = (year, round, config = {}) => {
  return request.get(`/api/prediction/${year}/${round}`, config)
}

/** 获取赛季预测历史（各站 Top3 摘要） */
export const getPredictionHistory = (season, config = {}) => {
  return request.get('/api/prediction/history', { params: { season }, ...config })
}
