/**
 * 年份选择 composable — 统一 yearOptions + 初始值 + store 同步
 *
 * 用法：
 *   const { yearOptions, year, syncYearToStore } = useYearSelection()
 *   const onYearChange = async () => {
 *     syncYearToStore()
 *     await store.fetchRaceList(year.value)
 *     ...
 *   }
 */
import { ref } from 'vue'
import { useF1Store } from '@/stores/f1'
import { YEAR_OPTIONS } from '@/utils/f1-constants'

export function useYearSelection(defaultYear) {
  const store = useF1Store()
  const year = ref(defaultYear || store.currentSeason || 2026)

  const syncYearToStore = () => {
    store.setSeason(year.value)
  }

  return { yearOptions: YEAR_OPTIONS, year, syncYearToStore }
}
