<template>
  <div class="page-wrap">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">全场最快圈速排行</span>
          <div class="header-controls">
            <el-select v-model="year" style="width: 100px" @change="onYearChange">
              <el-option v-for="y in yearOptions" :key="y" :label="`${y}`" :value="y" />
            </el-select>
            <el-select v-model="round" placeholder="选择分站" style="width: 200px" @change="loadData">
              <el-option
                v-for="r in store.raceList"
                :key="r.round"
                :label="`第${r.round}站 ${r.raceName}`"
                :value="Number(r.round)"
              />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="lapTableData" border stripe v-loading="loading" @sort-change="handleSort">
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="rankType(row.Rank)" effect="dark" round>{{ row.Rank }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="Driver" label="车手代码" width="120" />
        <el-table-column prop="LapTimeStr" label="最快圈速" width="140" sortable="custom" />
        <el-table-column label="用时(秒)" sortable="custom" prop="LapTimeSeconds">
          <template #default="{ row }">
            <span>{{ row.LapTimeSeconds }}s</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getFastestLap } from '@/api/telemetry'

const store = useF1Store()
const { yearOptions, year, syncYearToStore } = useYearSelection()

const round = ref(null)
const loading = ref(false)
const lapTableData = ref([])

const rankType = (pos) => {
  const p = Number(pos)
  if (p === 1) return 'danger'
  if (p === 2) return 'warning'
  if (p === 3) return 'success'
  return 'info'
}

const handleSort = ({ prop, order }) => {
  if (!lapTableData.value.length) return
  if (order === 'ascending') {
    lapTableData.value.sort((a, b) => a[prop] - b[prop])
  } else if (order === 'descending') {
    lapTableData.value.sort((a, b) => b[prop] - a[prop])
  }
}

const onYearChange = async () => {
  syncYearToStore()
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    await loadData()
  }
}

const loadData = async () => {
  if (!round.value) return
  loading.value = true
  try {
    const data = await getFastestLap(year.value, round.value, 'R')
    lapTableData.value = data?.fastest_lap_ranking || []
  } catch {
    lapTableData.value = []
  }
  loading.value = false
}

onMounted(async () => {
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    await loadData()
  }
})
</script>

<style scoped>
.page-wrap { margin: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 18px; font-weight: bold; }
.header-controls { display: flex; gap: 10px; }
</style>
