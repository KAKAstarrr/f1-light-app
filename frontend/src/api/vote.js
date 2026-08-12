import request from './request'

/**
 * 投票接口（模块 E）
 */

/** 提交最佳车手投票 */
export const castVote = (data) => {
  return request.post('/api/vote', data)
}

/** 获取投票结果统计 */
export const getVoteResults = (season, round) => {
  return request.get(`/api/vote/results/${season}/${round}`)
}
