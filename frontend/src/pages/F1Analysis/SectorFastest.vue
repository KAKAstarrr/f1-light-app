<template>
  <div class="page-wrap">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">赛道分段最快（Sector Fastest）</span>
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
            <el-select v-model="sessionType" style="width: 120px" @change="loadData">
              <el-option label="正赛" value="R" />
              <el-option label="排位赛" value="Q" />
              <el-option label="冲刺赛" value="S" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-if="overallDriver" class="overall-banner">
        <el-tag type="danger" effect="dark" size="large">
          全场分段总和最快: {{ overallDriver }}
        </el-tag>
      </div>

      <el-row :gutter="20" v-loading="loading">
        <el-col v-for="sector in sectorData" :key="sector.sector" :span="8">
          <el-card shadow="never" class="sector-card">
            <template #header>
              <div class="sector-header">
                <span>Sector {{ sector.sector }}</span>
                <el-tag v-if="sector.fastest_driver" type="danger" effect="dark" size="small">
                  {{ sector.fastest_driver }} {{ sector.fastest_time_str }}s
                </el-tag>
              </div>
            </template>
            <el-table :data="sector.ranking.slice(0, 10)" border stripe size="small">
              <el-table-column label="#" width="50" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column prop="driver" label="车手" width="80" />
              <el-table-column label="分段用时" width="120">
                <template #default="{ row }">{{ row.time_str }}s</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && !sectorData.length" description="暂无分段数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getSectorFastest } from '@/api/telemetry'
import { ElMessage } from 'element-plus'

const store = useF1Store()
const { yearOptions, year, syncYearToStore } = useYearSelection()

const round = ref(null)
const sessionType = ref('R')
const loading = ref(false)
const sectorData = ref([])
const overallDriver = ref(null)

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
    const data = await getSectorFastest(year.value, round.value, sessionType.value)
    if (data?.code === 200) {
      sectorData.value = data.sectors || []
      overallDriver.value = data.overall_fastest_driver || null
    } else {
      sectorData.value = []
      overallDriver.value = null
      ElMessage.warning(data?.msg || '暂无数据')
    }
  } catch (e) {
    sectorData.value = []
    overallDriver.value = null
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
.overall-banner { margin-bottom: 16px; text-align: center; }
.sector-card { margin-bottom: 20px; }
.sector-header { display: flex; justify-content: space-between; align-items: center; font-weight: bold; }
</style>
