import { defineStore } from 'pinia'
import { getCurrentSeason, getSeasonByYear } from '@/api/race'
import { getCurrentDrivers, getDriversByYear, getDriverStandings, getConstructorStandings } from '@/api/driver'
import { MOCK_2026_DRIVERS } from '@/utils/f1-constants'

const CACHE_TTL = 10 * 60 * 1000 // 10 分钟

/**
 * 全局状态仓库
 * 管理：当前赛季、选中的分站、赛程列表、车手/车队积分榜、车手名单缓存
 */
export const useF1Store = defineStore('f1', {
  state() {
    return {
      currentSeason: 2026,
      selectedRound: null,
      raceList: [],
      driverStandings: [],
      constructorStandings: [],
      // 缓存层
      _driverCache: {},       // { 2025: [...], 2024: [...] }
      _raceListCache: {},     // { 2025: [...], 2024: [...] }
      _fetchTime: {},         // { 'drivers_2025': timestamp, 'races_2025': timestamp }
    }
  },

  getters: {
    roundCount: (state) => state.raceList.length,
    selectedRace: (state) =>
      state.raceList.find((r) => Number(r.round) === Number(state.selectedRound)) || null,
  },

  actions: {
    setSeason(year) {
      this.currentSeason = Number(year)
    },
    setSelectedRound(round) {
      this.selectedRound = round ? Number(round) : null
    },
    setRaceList(list) {
      this.raceList = list
    },

    // 拉取赛程（带缓存，10 分钟过期）
    async fetchRaceList(year) {
      const y = year ?? this.currentSeason
      const cacheKey = `races_${y}`

      // 命中缓存
      if (this._raceListCache[y]?.length && Date.now() - (this._fetchTime[cacheKey] || 0) < CACHE_TTL) {
        this.raceList = this._raceListCache[y]
        return
      }

      try {
        const currentYear = new Date().getFullYear()
        const data = y === currentYear ? await getCurrentSeason({ silent: true }) : await getSeasonByYear(y, { silent: true })
        this.raceList = data.Races || []
        this._raceListCache[y] = this.raceList
        this._fetchTime[cacheKey] = Date.now()
      } catch (e) {
        this.raceList = this._raceListCache[y] || []
        console.error('赛程拉取失败:', e)
      }
    },

    // 拉取车手名单（2026 用 Ergast 真实数据，其他年份带缓存 + 兜底）
    async fetchDrivers(year) {
      const y = year ?? this.currentSeason
      const cacheKey = `drivers_${y}`

      // 命中缓存
      if (this._driverCache[y]?.length && Date.now() - (this._fetchTime[cacheKey] || 0) < CACHE_TTL) {
        return this._driverCache[y]
      }

      try {
        const currentYear = new Date().getFullYear()
        const data = y === currentYear ? await getCurrentDrivers({ silent: true }) : await getDriversByYear(y, { silent: true })
        let drivers = (data?.Drivers || []).map((d) => ({
          code: d.code || '',
          givenName: d.givenName || '',
          familyName: d.familyName || '',
          driverId: d.driverId || '',
        })).filter((d) => d.code)

        // 兜底：某年 Ergast 空数据（典型如 2025），用当前赛季（2026）真实车手兜底
        if (drivers.length === 0 && y !== currentYear) {
          const fallback = await getCurrentDrivers({ silent: true })
          drivers = (fallback?.Drivers || []).map((d) => ({
            code: d.code || '',
            givenName: d.givenName || '',
            familyName: d.familyName || '',
            driverId: d.driverId || '',
          })).filter((d) => d.code)
        }

        this._driverCache[y] = drivers
        this._fetchTime[cacheKey] = Date.now()
        return drivers
      } catch (e) {
        console.error('车手名单拉取失败:', e)
        return this._driverCache[y] || MOCK_2026_DRIVERS
      }
    },

    async fetchDriverStandings() {
      try {
        const data = await getDriverStandings()
        this.driverStandings = data.StandingsLists?.[0]?.DriverStandings || []
      } catch (e) {
        this.driverStandings = []
        console.error('车手积分榜拉取失败:', e)
      }
    },

    async fetchConstructorStandings() {
      try {
        const data = await getConstructorStandings()
        this.constructorStandings = data.StandingsLists?.[0]?.ConstructorStandings || []
      } catch (e) {
        this.constructorStandings = []
        console.error('车队积分榜拉取失败:', e)
      }
    },

    // 清除指定年份缓存（或全部）
    clearCache(key) {
      if (key) {
        delete this._driverCache[key]
        delete this._raceListCache[key]
        delete this._fetchTime[`drivers_${key}`]
        delete this._fetchTime[`races_${key}`]
      } else {
        this._driverCache = {}
        this._raceListCache = {}
        this._fetchTime = {}
      }
    },
  },
})
