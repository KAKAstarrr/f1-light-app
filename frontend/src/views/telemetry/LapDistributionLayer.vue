/**
 * LapDistributionLayer — 圈速分布箱线图图层
 */
<template>
  <div class="lap-distribution-layer">
    <div class="layer-title">📊 圈速分布</div>
    <div ref="chartRef" class="ld-chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { DRIVER_CHART_COLORS } from '@/utils/f1-constants'

const props = defineProps({
  lapData: { type: Object, default: null },
})

const chartRef = ref(null)
let chart = null

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value, 'dark')
    renderChart()
    window.addEventListener('resize', resize)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})

watch(() => props.lapData, renderChart, { deep: true })

function resize() { chart?.resize() }

function renderChart() {
  if (!chart) return

  const drivers = props.lapData?.lap_distribution || props.lapData?.drivers || []
  const categories = []
  const boxData = []
  const scatterData = []

  drivers.forEach((d, i) => {
    const laps = d.lap_times || d.laps || []
    if (!laps.length) return

    categories.push(d.driver || d.code)
    const sorted = [...laps].map(Number).sort((a, b) => a - b)
    const q1 = sorted[Math.floor(sorted.length * 0.25)]
    const median = sorted[Math.floor(sorted.length * 0.5)]
    const q3 = sorted[Math.floor(sorted.length * 0.75)]
    const min = sorted[0]
    const max = sorted[sorted.length - 1]

    boxData.push([min, q1, median, q3, max])

    // 散点
    laps.forEach(lt => {
      scatterData.push([i, Number(lt)])
    })
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a1a1a',
      borderColor: '#333',
      textStyle: { color: '#fff' },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#b0b0b0', fontSize: 11 },
      axisLine: { lineStyle: { color: '#333' } },
    },
    yAxis: {
      type: 'value',
      name: '秒',
      nameTextStyle: { color: '#707070' },
      axisLabel: { color: '#707070' },
      axisLine: { lineStyle: { color: '#333' } },
      splitLine: { lineStyle: { color: '#222' } },
    },
    series: [
      {
        name: '圈速分布',
        type: 'boxplot',
        data: boxData,
        itemStyle: { color: '#e10600', borderColor: '#e10600' },
      },
      {
        name: '单圈',
        type: 'scatter',
        data: scatterData,
        symbolSize: 4,
        itemStyle: { color: '#00a19b', opacity: 0.5 },
      },
    ],
    animation: false,
  }

  chart.setOption(option, true)
}
</script>

<style scoped>
.lap-distribution-layer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.layer-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--f1-text-secondary);
  margin-bottom: 8px;
}

.ld-chart {
  flex: 1;
  min-height: 200px;
}
</style>
