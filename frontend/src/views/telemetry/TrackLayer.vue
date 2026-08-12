/**
 * TrackLayer — 赛道底图图层
 * SVG 赛道线 + 弯道编号 + 车手位置圆点
 */
<template>
  <div class="track-layer">
    <div ref="chartRef" class="track-chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  trackData: { type: Object, default: null },
  telemetryData: { type: Object, default: null },
  drivers: { type: Array, default: () => [] },
  currentTime: { type: Number, default: 0 },
})

const chartRef = ref(null)
let chart = null

const DRIVER_COLORS = ['#e10600', '#00a19b', '#0600ef', '#ff8700', '#0090ff', '#229971']

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

watch(() => [props.trackData, props.drivers, props.currentTime], renderChart, { deep: true })

function resize() {
  chart?.resize()
}

function renderChart() {
  if (!chart || !props.trackData) return

  const trackPoints = props.trackData?.track_points || props.trackData?.circuit_points || []
  if (!trackPoints.length) return

  // 赛道线数据
  const trackLine = trackPoints.map(p => [p.x || p[0], p.y || p[1]])

  // 车手位置（如果有遥测数据 + 播放时间）
  const driverPositions = []
  if (props.telemetryData?.telemetry && props.drivers.length) {
    props.drivers.forEach((code, i) => {
      const driverTel = props.telemetryData.telemetry[code]
      if (!driverTel?.telemetry?.length) return
      // 找到最接近 currentTime 的数据点
      const tel = driverTel.telemetry
      const timeIdx = Math.floor((props.currentTime / (driverTel.laps?.[0]?.LapTimeSeconds || 90)) * tel.length)
      const point = tel[Math.min(timeIdx, tel.length - 1)]
      if (point?.X != null && point?.Y != null) {
        driverPositions.push({
          name: code,
          value: [point.X, point.Y],
          itemStyle: { color: DRIVER_COLORS[i] },
        })
      }
    })
  }

  const option = {
    backgroundColor: 'transparent',
    xAxis: { type: 'value', show: false, scale: true },
    yAxis: { type: 'value', show: false, scale: true, inverse: true },
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    series: [
      {
        name: 'Track',
        type: 'line',
        data: trackLine,
        showSymbol: false,
        lineStyle: { color: '#444', width: 8, cap: 'round' },
        emphasis: { lineStyle: { color: '#666' } },
      },
      {
        name: 'Drivers',
        type: 'scatter',
        data: driverPositions,
        symbolSize: 16,
        label: {
          show: true,
          formatter: params => params.name,
          fontSize: 10,
          fontWeight: 'bold',
          color: '#fff',
          position: 'top',
        },
        z: 10,
      },
    ],
    animation: false,
  }

  chart.setOption(option, true)
}
</script>

<style scoped>
.track-layer {
  width: 100%;
  height: 100%;
  position: relative;
}

.track-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
