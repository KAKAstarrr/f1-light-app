/**
 * 下一场比赛 composable — 计算 upcoming / ongoing / lastCompleted
 *
 * 状态判定规则：
 *   upcoming      → date > now 的第一站
 *   ongoing       → |date - now| < 4h（比赛窗口期）
 *   lastCompleted → date < now 的最后一站
 *
 * 用法：
 *   const { upcomingRace, ongoingRace, lastCompletedRace } = useNextRace()
 *   // 需先确保 store.raceList 已加载
 */
import { computed } from 'vue'
import { useF1Store } from '@/stores/f1'

function parseRaceDate(race) {
  if (!race?.date) return null
  const timeStr = race.time || '00:00:00Z'
  return new Date(`${race.date}T${timeStr}`)
}

export function useNextRace() {
  const store = useF1Store()

  const upcomingRace = computed(() => {
    const now = new Date()
    return (
      store.raceList.find((r) => {
        const d = parseRaceDate(r)
        return d && d > now
      }) || null
    )
  })

  const ongoingRace = computed(() => {
    const now = new Date()
    return (
      store.raceList.find((r) => {
        const d = parseRaceDate(r)
        if (!d) return false
        const diff = Math.abs(d - now)
        return diff < 4 * 3600 * 1000 // ±4小时
      }) || null
    )
  })

  const lastCompletedRace = computed(() => {
    const now = new Date()
    const completed = store.raceList.filter((r) => {
      const d = parseRaceDate(r)
      return d && d < now
    })
    return completed[completed.length - 1] || null
  })

  return { upcomingRace, ongoingRace, lastCompletedRace }
}
