/**
 * SpeedLayer — 速度曲线图层
 * 多车手速度对比折线图
 */
<template>
  <div class="speed-layer">
    <div class="layer-title">⚡ 速度曲线</div>
    <div ref="chartRef" class="speed-chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { DRIVER_CHART_COLORS } from '@/utils/f1-constants'

const props = defineProps({
  telemetryData: { type: Object, default: null },
  drivers: { type: Array, default: () => [] },
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

watch(() => [props.telemetryData, props.drivers], renderChart, { deep: true })

function resize() { chart?.resize() }

function renderChart() {
  if (!chart) return

  const series = []
  const legend = []

  // 后端返回格式: { drivers: { VER: { speed: [310, 305, ...] } }, distances: [0, 1, 2, ...] }
  const driversData = props.telemetryData?.drivers || props.telemetryData?.telemetry || {}
  const distances = props.telemetryData?.distances || []

  if (driversData && Object.keys(driversData).length > 0) {
    props.drivers.forEach((code, i) => {
      const driverTel = driversData[code]
      if (!driverTel) return

      // 适配两种数据格式：1) { speed: [310, ...] }  2) { telemetry: [{ Speed: 310, ... }] }
      let speedData = []
      if (Array.isArray(driverTel.speed)) {
        speedData = driverTel.speed
      } else if (Array.isArray(driverTel.telemetry)) {
        speedData = driverTel.telemetry.map(p => p.Speed ?? p.speed ?? 0)
      } else {
        return
      }

      if (!speedData.length) return

      legend.push(code)
      const data = speedData.map((v, idx) => [distances[idx] ?? idx, v])
      series.push({
        name: code,
        type: 'line',
        data,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: DRIVER_CHART_COLORS[i], width: 2 },
        itemStyle: { color: DRIVER_CHART_COLORS[i] },
        emphasis: { focus: 'series' },
      })
    })
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a1a',
      borderColor: '#333',
      textStyle: { color: '#fff' },
    },
    legend: {
      data: legend,
      textStyle: { color: '#b0b0b0' },
      top: 0,
    },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'value',
      name: '距离 (m)',
      nameTextStyle: { color: '#707070' },
      axisLabel: { color: '#707070' },
      axisLine: { lineStyle: { color: '#333' } },
      splitLine: { lineStyle: { color: '#222' } },
    },
    yAxis: {
      type: 'value',
      name: 'km/h',
      nameTextStyle: { color: '#707070' },
      axisLabel: { color: '#707070' },
      axisLine: { lineStyle: { color: '#333' } },
      splitLine: { lineStyle: { color: '#222' } },
    },
    series,
    animation: false,
  }

  chart.setOption(option, true)
}
</script>

<style scoped>
.speed-layer {
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

.speed-chart {
  flex: 1;
  min-height: 200px;
}
</style>
