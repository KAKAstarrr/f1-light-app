/**
 * SectorFastestLayer — 分段最快图层
 * 各赛段最快车手柱状图
 */
<template>
  <div class="sector-fastest-layer">
    <div class="layer-title">⏱️ 分段最快</div>
    <div ref="chartRef" class="sf-chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { DRIVER_CHART_COLORS } from '@/utils/f1-constants'

const props = defineProps({
  sectorData: { type: Object, default: null },
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

watch(() => props.sectorData, renderChart, { deep: true })

function resize() { chart?.resize() }

function renderChart() {
  if (!chart) return

  const sectors = props.sectorData?.sector_fastest || props.sectorData?.sectors || []
  if (!sectors.length) {
    chart.clear()
    return
  }

  const categories = sectors.map(s => `S${s.sector || s.Sector}`)
  const times = sectors.map(s => Number(s.time || s.Time || s.LapTimeSeconds || 0))
  const drivers = sectors.map(s => s.driver || s.Driver || '?')

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a1a',
      borderColor: '#333',
      textStyle: { color: '#fff' },
      formatter: params => {
        const p = params[0]
        return `${categories[p.dataIndex]}<br/>${drivers[p.dataIndex]}: ${p.value.toFixed(3)}s`
      },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#b0b0b0' },
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
        type: 'bar',
        data: times.map((t, i) => ({
          value: t,
          itemStyle: { color: DRIVER_CHART_COLORS[i % DRIVER_CHART_COLORS.length] },
        })),
        barWidth: '50%',
        label: {
          show: true,
          position: 'top',
          formatter: params => drivers[params.dataIndex],
          color: '#b0b0b0',
          fontSize: 11,
        },
      },
    ],
    animation: false,
  }

  chart.setOption(option, true)
}
</script>

<style scoped>
.sector-fastest-layer {
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

.sf-chart {
  flex: 1;
  min-height: 200px;
}
</style>
