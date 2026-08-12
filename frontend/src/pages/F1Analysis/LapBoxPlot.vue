<template>
  <div class="page-wrap">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">圈速分布（Box Plot）</span>
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
            </el-select>
          </div>
        </div>
      </template>

      <div ref="chartRef" class="chart"></div>
      <el-empty v-if="!loading && !hasData" description="暂无圈速分布数据" />
    </el-card>

    <el-card shadow="hover" style="margin-top: 20px" v-if="hasData">
      <template #header><span class="card-title">统计明细</span></template>
      <el-table :data="tableData" border stripe size="small">
        <el-table-column label="排名" width="60" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="driver" label="车手" width="80" />
        <el-table-column prop="compound" label="轮胎" width="100" />
        <el-table-column prop="lap_count" label="圈数" width="80" align="center" />
        <el-table-column prop="min" label="最快圈" width="100">
          <template #default="{ row }">{{ row.min }}s</template>
        </el-table-column>
        <el-table-column prop="median" label="中位数" width="100">
          <template #default="{ row }">{{ row.median }}s</template>
        </el-table-column>
        <el-table-column prop="mean" label="平均" width="100">
          <template #default="{ row }">{{ row.mean }}s</template>
        </el-table-column>
        <el-table-column prop="max" label="最慢圈" width="100">
          <template #default="{ row }">{{ row.max }}s</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getLapDistribution } from '@/api/telemetry'
import { ElMessage } from 'element-plus'

const store = useF1Store()
const { yearOptions, year, syncYearToStore } = useYearSelection()

const round = ref(null)
const sessionType = ref('R')
const loading = ref(false)
const distribution = ref([])
const chartRef = ref(null)
let chartInstance = null

const hasData = computed(() => distribution.value.length > 0)
const tableData = computed(() => distribution.value)

const compoundColor = (compound) => {
  const map = {
    SOFT: '#e74c3c',
    MEDIUM: '#f39c12',
    HARD: '#95a5a6',
    INTERMEDIATE: '#3498db',
    WET: '#2c3e50',
  }
  return map[compound] || '#409eff'
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
    const data = await getLapDistribution(year.value, round.value, sessionType.value)
    if (data?.code === 200) {
      distribution.value = data.distribution || []
    } else {
      distribution.value = []
      ElMessage.warning(data?.msg || '暂无数据')
    }
  } catch (e) {
    distribution.value = []
  }
  loading.value = false
  await nextTick()
  renderChart()
}

const renderChart = () => {
  if (!chartRef.value || !hasData.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)

  const data = distribution.value
  const categories = data.map(d => d.driver)

  // ECharts boxplot: [min, Q1, median, Q3, max]
  const boxData = data.map(d => {
    const times = d.lap_times
    if (!times.length) return [0, 0, 0, 0, 0]
    const n = times.length
    const q1 = times[Math.floor(n * 0.25)] || times[0]
    const median = d.median
    const q3 = times[Math.floor(n * 0.75)] || times[n - 1]
    return [d.min, q1, median, q3, d.max]
  })

  // Outliers: individual lap times outside the box
  const outliers = []
  data.forEach((d, i) => {
    const q1 = d.lap_times[Math.floor(d.lap_times.length * 0.25)] || d.min
    const q3 = d.lap_times[Math.floor(d.lap_times.length * 0.75)] || d.max
    const iqr = q3 - q1
    const lower = q1 - 1.5 * iqr
    const upper = q3 + 1.5 * iqr
    d.lap_times.forEach(t => {
      if (t < lower || t > upper) {
        outliers.push([i, t])
      }
    })
  })

  const option = {
    title: {
      text: `${year.value} 第${round.value}站 圈速分布`,
      left: 'center',
      textStyle: { fontSize: 16 },
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        if (params.componentType === 'series' && params.seriesType === 'boxplot') {
          const d = params.value
          return `${categories[params.dataIndex]}<br/>` +
            `最快: ${d[0]}s<br/>` +
            `Q1: ${d[1]}s<br/>` +
            `中位: ${d[2]}s<br/>` +
            `Q3: ${d[3]}s<br/>` +
            `最慢: ${d[4]}s`
        }
        return ''
      },
    },
    grid: {
      left: '5%',
      right: '5%',
      bottom: '15%',
      top: '12%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: 45, fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: '圈速 (秒)',
      scale: true,
    },
    series: [
      {
        name: '圈速分布',
        type: 'boxplot',
        data: boxData,
        itemStyle: {
          color: function(params) {
            const idx = params.dataIndex
            if (data[idx]) {
              return compoundColor(data[idx].compound)
            }
            return '#409eff'
          },
        },
      },
      {
        name: '异常值',
        type: 'scatter',
        data: outliers,
        symbolSize: 6,
        itemStyle: { color: '#e74c3c' },
      },
    ],
  }

  chartInstance.setOption(option)
}

const onResize = () => chartInstance?.resize()

onMounted(async () => {
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    await loadData()
  }
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.page-wrap { margin: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 18px; font-weight: bold; }
.header-controls { display: flex; gap: 10px; }
.chart { width: 100%; height: 500px; }
</style>
