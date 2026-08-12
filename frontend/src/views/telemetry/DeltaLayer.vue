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
  if (!chart || !props.telemetryData?.telemetry) return
  if (props.drivers.length < 2) return

  // 第一名车手作为基准
  const baseCode = props.drivers[0]
  const baseTel = props.telemetryData.telemetry[baseCode]
  if (!baseTel?.telemetry?.length) return

  // 基准车手的距离-时间积分
  const baseData = baseTel.telemetry
  const baseDistance = [0]
  for (let i = 1; i < baseData.length; i++) {
    const dt = 1 / 240 // 假设 240Hz 采样
    const speed = (baseData[i].Speed || baseData[i].speed || 0) / 3.6 // km/h → m/s
    baseDistance.push(baseDistance[i - 1] + speed * dt)
  }

  const series = []
  const legend = []

  // 基准线
  legend.push(baseCode)
  series.push({
    name: baseCode,
    type: 'line',
    data: baseData.map((_, i) => [baseDistance[i], 0]),
    showSymbol: false,
    lineStyle: { color: DRIVER_CHART_COLORS[0], width: 2, type: 'dashed' },
    itemStyle: { color: DRIVER_CHART_COLORS[0] },
  })

  // 其他车手 delta
  for (let di = 1; di < props.drivers.length; di++) {
    const code = props.drivers[di]
    const tel = props.telemetryData.telemetry[code]
    if (!tel?.telemetry?.length) continue

    const driverData = tel.telemetry
    const driverDistance = [0]
    for (let i = 1; i < driverData.length; i++) {
      const dt = 1 / 240
      const speed = (driverData[i].Speed || driverData[i].speed || 0) / 3.6
      driverDistance.push(driverDistance[i - 1] + speed * dt)
    }

    // 在相同距离点计算时间差
    const deltaData = []
    const maxLen = Math.min(baseData.length, driverData.length)
    let baseTime = 0
    let driverTime = 0

    for (let i = 0; i < maxLen; i++) {
      if (i > 0) {
        const baseSpeed = (baseData[i].Speed || baseData[i].speed || 0) / 3.6
        const driverSpeed = (driverData[i].Speed || driverData[i].speed || 0) / 3.6
        baseTime += 1 / 240
        driverTime += 1 / 240
      }
      deltaData.push([baseDistance[i], driverTime - baseTime])
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
