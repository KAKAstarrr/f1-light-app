/**
 * F1 全局常量 — 车手 mock / 车队颜色 / 年份选项 / 通道过滤
 */

// 统一年份选项（2026 排最前）
export const YEAR_OPTIONS = [2026, 2025, 2024, 2023]

// 2026 赛季 mock 车手（Ergast 未覆盖 2026，前端预置）
export const MOCK_2026_DRIVERS = [
  { code: 'VER', givenName: 'Max', familyName: 'Verstappen', driverId: 'verstappen' },
  { code: 'HAM', givenName: 'Lewis', familyName: 'Hamilton', driverId: 'hamilton' },
  { code: 'LEC', givenName: 'Charles', familyName: 'Leclerc', driverId: 'leclerc' },
  { code: 'NOR', givenName: 'Lando', familyName: 'Norris', driverId: 'norris' },
  { code: 'PIA', givenName: 'Oscar', familyName: 'Piastri', driverId: 'piastri' },
  { code: 'ALB', givenName: 'Alexander', familyName: 'Albon', driverId: 'albon' },
]

// 车队官方主题色
export const TEAM_COLORS = {
  red_bull: '#3671C6',
  ferrari: '#E8002D',
  mercedes: '#27F4D2',
  mclaren: '#FF8000',
  alpine: '#0093CC',
  aston_martin: '#229971',
  williams: '#64C4FF',
  rb: '#6692FF',
  sauber: '#52E252',
  haas: '#B6BABD',
}

// 轮胎统一配色（F1 官方惯例）
export const COMPOUND_COLORS = {
  SOFT: '#f44336',
  MEDIUM: '#ffd600',
  HARD: '#bdbdbd',
  INTERMEDIATE: '#4caf50',
  WET: '#2196f3',
  UNKNOWN: '#9e9e9e',
}

export const COMPOUND_LABELS = {
  SOFT: '软胎',
  MEDIUM: '中性',
  HARD: '硬胎',
  INTERMEDIATE: '半雨',
  WET: '全雨',
}

// 图表车手配色（按选择顺序）
export const DRIVER_CHART_COLORS = [
  '#e10600', '#00a19b', '#0600ef', '#ff8700', '#0090ff', '#229971',
]

/**
 * 判断是否 2026 赛季
 */
export function isYear2026(year) {
  return Number(year) === 2026
}

/**
 * 按年份过滤遥测通道（2026 年移除 DRS）
 */
export function filterChannelsForYear(channels, year) {
  if (isYear2026(year)) {
    return channels.filter((ch) => ch !== 'drs')
  }
  return channels
}

/**
 * 轮胎配色取值
 */
export function getCompoundColor(compound) {
  return COMPOUND_COLORS[compound] || '#9e9e9e'
}

/**
 * 排名徽标类型（Element Plus tag type）
 */
export function rankTagType(pos) {
  const p = Number(pos)
  if (p === 1) return 'danger'
  if (p === 2) return 'warning'
  if (p === 3) return 'success'
  return 'info'
}

/**
 * 车手全名拼接（兼容 Ergast 字段）
 */
export function driverName(d) {
  if (!d) return ''
  return `${d.givenName || ''} ${d.familyName || ''}`.trim()
}
