import request from './request'

/**
 * 单站圈速 / 轮胎策略接口（模块 A4，FastF1）
 * 后端路由：/api/fastf1/{year}/{round}/fast-lap
 *           /api/fastf1/{year}/{round}/tyre-strategy
 */

/**
 * 获取单站最快圈速排行
 * @param {number} year 赛季
 * @param {number} round 分站序号
 * @param {string} session 会话类型 R=正赛 Q=排位 FP1/FP2/FP3=练习赛
 */
export const getFastestLap = (year, round, session = 'R') => {
  return request.get(`/api/fastf1/${year}/${round}/fast-lap`, {
    params: { session_type: session }
  })
}

/**
 * 获取单站轮胎进站策略
 * @param {number} year 赛季
 * @param {number} round 分站序号
 */
export const getTyreStrategy = (year, round) => {
  return request.get(`/api/fastf1/${year}/${round}/tyre-strategy`)
}

/**
 * 获取车手遥测对比数据（模块 B2）
 * 后端路由：/api/fastf1/{year}/{round}/telemetry
 * @param {object} params { year, round, drivers, channels, sessionType }
 */
export const getTelemetryCompare = (params) => {
  return request.get(`/api/fastf1/${params.year}/${params.round}/telemetry`, {
    params: {
      drivers: params.drivers,
      channels: params.channels,
      session_type: params.sessionType || 'R'
    },
    timeout: 60000  // FastF1 遥测首次加载可能需要 30-60s
  })
}

/**
 * 获取赛道分段最快（模块 B1）
 * 后端路由：/api/fastf1/{year}/{round}/sector-fastest
 * @param {number} year 赛季
 * @param {number} round 分站序号
 * @param {string} session 会话类型，默认 R
 */
export const getSectorFastest = (year, round, session = 'R') => {
  return request.get(`/api/fastf1/${year}/${round}/sector-fastest`, {
    params: { session_type: session }
  })
}

/**
 * 获取圈速分布数据（模块 B3）
 * 后端路由：/api/fastf1/{year}/{round}/lap-distribution
 * @param {number} year 赛季
 * @param {number} round 分站序号
 * @param {string} session 会话类型，默认 R
 */
export const getLapDistribution = (year, round, session = 'R') => {
  return request.get(`/api/fastf1/${year}/${round}/lap-distribution`, {
    params: { session_type: session }
  })
}

/**
 * 获取速度叠加对比数据（模块 B4）
 * 后端路由：/api/fastf1/{year}/{round}/speed-overlay
 * @param {object} params { year, round, drivers, sessionType }
 */
export const getSpeedOverlay = (params) => {
  return request.get(`/api/fastf1/${params.year}/${params.round}/speed-overlay`, {
    params: {
      drivers: params.drivers,
      session_type: params.sessionType || 'R'
    },
    timeout: 60000
  })
}

/**
 * 获取赛道地图分段着色数据（模块 B5）
 * 后端路由：/api/fastf1/{year}/{round}/track-map
 * @param {number} year 赛季
 * @param {number} round 分站序号
 * @param {string} session 会话类型，默认 R
 */
export const getTrackMap = (year, round, session = 'R') => {
  return request.get(`/api/fastf1/${year}/${round}/track-map`, {
    params: { session_type: session },
    timeout: 60000
  })
}

/**
 * 获取天气数据（模块 B6）
 * 后端路由：/api/fastf1/{year}/{round}/weather
 * @param {number} year 赛季
 * @param {number} round 分站序号
 * @param {string} session 会话类型，默认 R
 */
export const getWeather = (year, round, session = 'R') => {
  return request.get(`/api/fastf1/${year}/${round}/weather`, {
    params: { session_type: session }
  })
}
