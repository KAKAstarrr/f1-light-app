/**
 * ThrottleBrakeLayer — 油门/刹车图层
 * 面积图：油门（绿）+ 刹车（红）
 */
<template>
  <div class="throttle-brake-layer">
    <div class="layer-title">🏎️ 油门 / 刹车</div>
    <div ref="chartRef" class="tb-chart"></div>
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

  // 后端返回格式: { drivers: { VER: { throttle: [100, ...], brake: [0, ...] } }, distances: [...] }
  const driversData = props.telemetryData?.drivers || props.telemetryData?.telemetry || {}
  const distances = props.telemetryData?.distances || []

  if (driversData && Object.keys(driversData).length > 0) {
    props.drivers.forEach((code, i) => {
      const driverTel = driversData[code]
      if (!driverTel) return

      // 适配两种格式：1) { throttle: [...], brake: [...] }  2) { telemetry: [{ Throttle, Brake }] }
      let throttleArr = []
      let brakeArr = []
      if (Array.isArray(driverTel.throttle)) {
        throttleArr = driverTel.throttle
        brakeArr = driverTel.brake || []
      } else if (Array.isArray(driverTel.telemetry)) {
        throttleArr = driverTel.telemetry.map(p => p.Throttle ?? p.throttle ?? 0)
        brakeArr = driverTel.telemetry.map(p => p.Brake ?? p.brake ?? 0)
      } else {
        return
      }

      if (!throttleArr.length) return

      legend.push(`${code} 油门`)
      legend.push(`${code} 刹车`)

      const throttleData = throttleArr.map((v, idx) => [distances[idx] ?? idx, v])
      const brakeData = brakeArr.map((v, idx) => [distances[idx] ?? idx, v])

      series.push({
        name: `${code} 油门`,
        type: 'line',
        data: throttleData,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: DRIVER_CHART_COLORS[i], width: 1.5 },
        areaStyle: { color: DRIVER_CHART_COLORS[i], opacity: 0.2 },
        itemStyle: { color: DRIVER_CHART_COLORS[i] },
      })

      series.push({
        name: `${code} 刹车`,
        type: 'line',
        data: brakeData,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: DRIVER_CHART_COLORS[i], width: 1.5, type: 'dashed' },
        areaStyle: { color: '#e10600', opacity: 0.15 },
        itemStyle: { color: '#e10600' },
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
      textStyle: { color: '#b0b0b0', fontSize: 10 },
      top: 0,
      type: 'scroll',
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
      name: '%',
      min: 0,
      max: 100,
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
.throttle-brake-layer {
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

.tb-chart {
  flex: 1;
  min-height: 200px;
}
</style>
