import request from './request'

/**
 * AI 预测接口（模块 3B）
 */

/** 获取指定分站的夺冠概率预测 */
export const getPrediction = (year, round) => {
  return request.get(`/api/prediction/${year}/${round}`)
}
