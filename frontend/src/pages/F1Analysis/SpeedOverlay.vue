<!--
  SpeedOverlay.vue — 速度叠加对比页（模块 B4）
  基于赛道距离归一化的多车手速度曲线叠加，精确对比弯道速度差异
-->
<template>
  <div class="speed-overlay-page">
    <div class="filter-bar">
      <el-select v-model="year" style="width: 110px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="`${y}`" :value="y" />
      </el-select>

      <el-select v-model="round" placeholder="选择分站" style="width: 220px" @change="onRoundChange">
        <el-option
          v-for="r in store.raceList"
          :key="r.round"
          :label="`第${r.round}站 ${r.raceName}`"
          :value="Number(r.round)"
        />
      </el-select>

      <el-select v-model="sessionType" style="width: 130px">
        <el-option label="正赛 R" value="R" />
        <el-option label="排位 Q" value="Q" />
        <el-option label="冲刺赛 S" value="S" />
      </el-select>

      <el-select
        v-model="selectedDrivers"
        multiple
        collapse-tags
        collapse-tags-tooltip
        placeholder="选择车手（最多4人）"
        style="width: 300px"
        :multiple-limit="4"
      >
        <el-option
          v-for="d in driverOptions"
          :key="d.code"
          :label="`${d.code} - ${d.givenName} ${d.familyName}`"
          :value="d.code"
        />
      </el-select>

      <el-button
        type="primary"
        @click="fetchData"
        :loading="loading"
        :disabled="!round || selectedDrivers.length === 0"
      >
        加载速度数据
      </el-button>
    </div>

    <el-card shadow="never" class="block">
      <template #header>
        <div class="card-header">
          <span>速度叠加对比</span>
          <span v-if="trackLength" class="track-info">赛道长度: {{ trackLength }}m</span>
        </div>
      </template>

      <el-empty v-if="!overlayData && !loading" description="选择车手后点击加载" />

      <div v-if="overlayData" ref="chartRef" class="chart-box"></div>

      <!-- 车手速度汇总 -->
      <div v-if="overlayData" class="driver-summary">
        <div v-for="(data, code) in overlayData.drivers" :key="code" class="summary-card">
          <span class="driver-code" :style="{ color: getDriverColor(code) }">{{ code }}</span>
          <span class="max-speed">最高: {{ data.max_speed }} km/h</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getDriversByYear } from '@/api/driver'
import { getSpeedOverlay } from '@/api/telemetry'

const store = useF1Store()
const { yearOptions, year, syncYearToStore } = useYearSelection()

const round = ref(null)
const sessionType = ref('R')
const selectedDrivers = ref([])
const driverOptions = ref([])
const loading = ref(false)
const overlayData = ref(null)
const trackLength = ref(0)
const chartRef = ref(null)
let chartInstance = null

const driverColors = ['#e10600', '#00a19b', '#0600ef', '#ff8700', '#0090ff', '#229971']

const getDriverColor = (code) => {
  const idx = Object.keys(overlayData.value?.drivers || {}).indexOf(code)
  return driverColors[idx] || driverColors[0]
}

const onYearChange = async () => {
  syncYearToStore()
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
  }
}

const onRoundChange = async () => {
  overlayData.value = null
  await loadDrivers()
}

const loadDrivers = async () => {
  if (!round.value) return
  try {
    const data = await getDriversByYear(year.value)
    const drivers = data?.Drivers || []
    driverOptions.value = drivers.map(d => ({
      code: d.code || '',
      givenName: d.givenName || '',
      familyName: d.familyName || '',
      driverId: d.driverId || ''
    })).filter(d => d.code)
  } catch {
    driverOptions.value = []
  }
}

const fetchData = async () => {
  if (!round.value || selectedDrivers.value.length === 0) return
  loading.value = true
  try {
    const res = await getSpeedOverlay({
      year: year.value,
      round: round.value,
      drivers: selectedDrivers.value.join(','),
      sessionType: sessionType.value
    })
    if (res.code === 200) {
      overlayData.value = res
      trackLength.value = res.track_length
      await nextTick()
      renderChart()
    }
  } catch { /* 拦截器处理 */ }
  loading.value = false
}

const renderChart = () => {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)

  const data = overlayData.value
  const distances = data.grid_distances

  const series = Object.entries(data.drivers).map(([code, d], idx) => ({
    name: code,
    type: 'line',
    data: d.speed,
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 2, color: driverColors[idx] },
    itemStyle: { color: driverColors[idx] },
    emphasis: { focus: 'series' },
  }))

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `距离: ${params[0].axisValue}m<br/>`
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${p.value} km/h<br/>`
        })
        return html
      }
    },
    legend: {
      data: Object.keys(data.drivers),
      top: 5,
    },
    grid: { left: 60, right: 30, top: 50, bottom: 60 },
    xAxis: {
      type: 'category',
      data: distances,
      name: '赛道距离 (m)',
      nameLocation: 'middle',
      nameGap: 35,
    },
    yAxis: {
      type: 'value',
      name: '速度 (km/h)',
      min: 0,
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 },
    ],
    series,
  })
}

onMounted(async () => {
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    await loadDrivers()
  }
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.speed-overlay-page { padding: 16px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.block { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.track-info { font-size: 13px; color: #909399; }
.chart-box { width: 100%; height: 500px; }
.driver-summary { display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
.summary-card {
  padding: 8px 16px; border: 1px solid #ebeef5; border-radius: 6px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.driver-code { font-size: 18px; font-weight: bold; }
.max-speed { font-size: 13px; color: #606266; }
</style>
