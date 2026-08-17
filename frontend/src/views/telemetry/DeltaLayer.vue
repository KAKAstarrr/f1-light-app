/**
 * DeltaLayer — 车手时间差图层
 * 以前车为基准线，后车相对时间差
 */
<template>
  <div class="delta-layer">
    <div class="layer-title">📉 时间差 (Delta)</div>
    <div ref="chartRef" class="delta-chart"></div>
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
  if (props.drivers.length < 2) return

  // 后端返回格式: { drivers: { VER: { speed: [310, ...] } }, distances: [0, 1, 2, ...] }
  const driversData = props.telemetryData?.drivers || props.telemetryData?.telemetry || {}
  const distances = props.telemetryData?.distances || []

  const baseCode = props.drivers[0]
  const baseDriver = driversData[baseCode]
  if (!baseDriver) return

  // 提取速度数组（兼容两种格式）
  const getSpeedArr = (driverTel) => {
    if (!driverTel) return []
    if (Array.isArray(driverTel.speed)) return driverTel.speed
    if (Array.isArray(driverTel.telemetry)) return driverTel.telemetry.map(p => p.Speed ?? p.speed ?? 0)
    return []
  }

  const baseSpeed = getSpeedArr(baseDriver)
  if (!baseSpeed.length) return

  // 计算基准车手在各距离点的时间（速度积分）
  // dt = distance_step / speed (m/s)
  const baseTimeAtDist = [0]
  for (let i = 1; i < baseSpeed.length; i++) {
    const dx = (distances[i] ?? 1) - (distances[i - 1] ?? 0)
    const speedMs = (baseSpeed[i] + baseSpeed[i - 1]) / 2 / 3.6 // km/h → m/s，取平均
    const dt = speedMs > 0 ? dx / speedMs : 0.1
    baseTimeAtDist.push(baseTimeAtDist[i - 1] + dt)
  }

  const series = []
  const legend = []

  // 基准线
  legend.push(baseCode)
  series.push({
    name: baseCode,
    type: 'line',
    data: distances.map((d, i) => [d, 0]),
    showSymbol: false,
    lineStyle: { color: DRIVER_CHART_COLORS[0], width: 2, type: 'dashed' },
    itemStyle: { color: DRIVER_CHART_COLORS[0] },
  })

  // 其他车手 delta
  for (let di = 1; di < props.drivers.length; di++) {
    const code = props.drivers[di]
    const drvSpeed = getSpeedArr(driversData[code])
    if (!drvSpeed.length) continue

    // 计算该车手在各距离点的时间
    const drvTimeAtDist = [0]
    for (let i = 1; i < drvSpeed.length; i++) {
      const dx = (distances[i] ?? 1) - (distances[i - 1] ?? 0)
      const speedMs = (drvSpeed[i] + drvSpeed[i - 1]) / 2 / 3.6
      const dt = speedMs > 0 ? dx / speedMs : 0.1
      drvTimeAtDist.push(drvTimeAtDist[i - 1] + dt)
    }

    // delta = drvTime - baseTime 在各距离点
    const maxLen = Math.min(baseTimeAtDist.length, drvTimeAtDist.length)
    const deltaData = []
    for (let i = 0; i < maxLen; i++) {
      deltaData.push([distances[i] ?? i, drvTimeAtDist[i] - baseTimeAtDist[i]])
    }

    legend.push(code)
    series.push({
      name: code,
      type: 'line',
      data: deltaData,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: DRIVER_CHART_COLORS[di], width: 2 },
      itemStyle: { color: DRIVER_CHART_COLORS[di] },
      emphasis: { focus: 'series' },
    })
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1a1a',
      borderColor: '#333',
      textStyle: { color: '#fff' },
      formatter: params => {
        let html = `距离: ${params[0].value[0].toFixed(0)}m<br/>`
        params.forEach(p => {
          html += `${p.marker} ${p.seriesName}: ${p.value[1] >= 0 ? '+' : ''}${p.value[1].toFixed(3)}s<br/>`
        })
        return html
      },
    },
    legend: {
      data: legend,
      textStyle: { color: '#b0b0b0' },
      top: 0,
    },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
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
      name: 'Delta (s)',
      nameTextStyle: { color: '#707070' },
      axisLabel: {
        color: '#707070',
        formatter: v => (v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1)),
      },
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
.delta-layer {
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

.delta-chart {
  flex: 1;
  min-height: 200px;
}
</style>
