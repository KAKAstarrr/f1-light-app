import request from './request'

/**
 * Fantasy 接口（模块 3C）
 */

/** 创建/更新 Fantasy 阵容 */
export const saveFantasyTeam = (data) => {
  return request.post('/api/fantasy/team', data)
}

/** 查看我的阵容 */
export const getMyTeam = (season, round) => {
  return request.get(`/api/fantasy/team/${season}/${round}`)
}

/** 结算 Fantasy 积分 */
export const scoreFantasy = (season, round) => {
  return request.post(`/api/fantasy/score/${season}/${round}`)
}

/** 获取赛季排行榜 */
export const getLeaderboard = (season) => {
  return request.get(`/api/fantasy/leaderboard/${season}`)
}

/** 获取动态定价 */
export const getPrices = (season) => {
  return request.get('/api/fantasy/prices', {
    params: { season }
  })
}

/** 查看历史阵容记录 */
export const getHistory = (season) => {
  return request.get('/api/fantasy/history', {
    params: { season }
  })
}

/** 使用芯片 */
export const useChip = (season, chip) => {
  return request.post('/api/fantasy/chip', { season, chip })
}

/** 查看芯片使用状态 */
export const getChipStatus = (season) => {
  return request.get('/api/fantasy/chip-status', {
    params: { season }
  })
}

/** 创建联盟 */
export const createLeague = (name, season) => {
  return request.post('/api/fantasy/leagues', { name, season })
}

/** 加入联盟 */
export const joinLeague = (leagueId, inviteCode) => {
  return request.post(`/api/fantasy/leagues/${leagueId}/join`, { invite_code: inviteCode })
}

/** 获取联盟内排行榜 */
export const getLeagueLeaderboard = (leagueId) => {
  return request.get(`/api/fantasy/leagues/${leagueId}/leaderboard`)
}

/** 查看我加入的联盟列表 */
export const getMyLeagues = () => {
  return request.get('/api/fantasy/my-leagues')
}
