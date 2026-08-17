/**
 * TrackLayer — 赛道底图图层
 * 模式 A：track_points + corner_segments 同时存在 → 按 corner_segments 把赛道线切成彩色段
 *         每段颜色 = 该段最快车手的车队色（GP Tempo 风格）
 * 模式 B：无 corner_segments（赛道轮廓 + 车手位置动画）
 * 模式 C：无 track_points → 退化为柱状图展示全场分段最快
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
  // 新增：telemetry 接口返回的分段最快车手（每个段 {segment_index, start_dist, end_dist, fastest_driver}）
  cornerSegments: { type: Array, default: () => [] },
  // 新增：车手 -> 颜色映射（来自父组件 store，避免重复定义）
  driverColorMap: { type: Object, default: () => ({}) },
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

watch(() => [props.trackData, props.drivers, props.currentTime, props.cornerSegments, props.driverColorMap], renderChart, { deep: true })

function resize() {
  chart?.resize()
}

// 解析车手颜色：优先用父组件传入的 driverColorMap，否则用 DRIVER_COLORS 兜底
function resolveColor(code, idx) {
  if (props.driverColorMap && props.driverColorMap[code]) return props.driverColorMap[code]
  return DRIVER_COLORS[idx % DRIVER_COLORS.length]
}

function renderChart() {
  if (!chart) return

  const trackPoints = props.trackData?.track_points || props.trackData?.circuit_points || []
  const sectors = props.trackData?.sectors || []
  const circuitName = props.trackData?.circuit_name || ''
  const overallFastest = props.trackData?.overall_fastest_driver || ''
  const cornerSegments = props.cornerSegments || []

  // 如果有赛道坐标点，绘制赛道线 + 弯道最快段染色
  if (trackPoints.length > 0) {
    const trackLine = trackPoints.map(p => [p.x ?? p[0], p.y ?? p[1]])
    const N = trackPoints.length

    // 车手位置（与 corner_segments 染色无关，保留原有动画）
    const driverPositions = []
    const driversData = props.telemetryData?.drivers || props.telemetryData?.telemetry || {}
    if (driversData && props.drivers.length) {
      props.drivers.forEach((code, i) => {
        const driverTel = driversData[code]
        if (!driverTel) return

        // 从遥测数据中找 X/Y 坐标
        let xVal = null, yVal = null
        if (Array.isArray(driverTel.telemetry)) {
          const tel = driverTel.telemetry
          const totalTime = driverTel.laps?.[0]?.LapTimeSeconds || 90
          const timeIdx = Math.floor((props.currentTime / totalTime) * tel.length)
          const point = tel[Math.min(timeIdx, tel.length - 1)]
          xVal = point?.X ?? point?.x ?? null
          yVal = point?.Y ?? point?.y ?? null
        }

        if (xVal != null && yVal != null) {
          driverPositions.push({
            name: code,
            value: [xVal, yVal],
            itemStyle: { color: resolveColor(code, i) },
          })
        }
      })
    }

    // ----- 构造系列：每段一个独立 series，颜色 = 该段最快车手 ----
    const series = []

    if (cornerSegments.length > 0 && props.drivers.length > 0) {
      const segCount = cornerSegments.length
      const driverIdxMap = {}
      props.drivers.forEach((code, i) => { driverIdxMap[code] = i })

      // 按 corner_segments 等分切点索引
      const segSeriesList = []
      for (let i = 0; i < segCount; i++) {
        const seg = cornerSegments[i]
        const startIdx = Math.floor((i / segCount) * N)
        const endIdx = Math.max(startIdx + 1, Math.floor(((i + 1) / segCount) * N))
        const slice = trackLine.slice(startIdx, endIdx)
        if (!slice.length) continue
        const code = seg.fastest_driver
        const color = code && driverIdxMap[code] !== undefined
          ? resolveColor(code, driverIdxMap[code])
          : '#444'
        segSeriesList.push({ data: slice, color, segInfo: seg })
      }

      // 底层灰色（兜底显示，让曲线连成一条）
      series.push({
        name: 'TrackBase',
        type: 'line',
        data: trackLine,
        showSymbol: false,
        lineStyle: { color: '#2a2a2a', width: 6, cap: 'round' },
        z: 1,
      })

      // 每段彩色 line
      segSeriesList.forEach((s, i) => {
        series.push({
          name: `Seg${i}`,
          type: 'line',
          data: s.data,
          showSymbol: false,
          lineStyle: { color: s.color, width: 5, cap: 'round' },
          z: 2,
          emphasis: { lineStyle: { width: 6 } },
          // tooltip 信息
          tooltip: {
            formatter: () => {
              const info = s.segInfo
              if (!info.fastest_driver) return `段 ${i + 1}/${segCount}<br/>无遥测数据`
              return `<b>段 ${i + 1}/${segCount}</b><br/>` +
                `最快: <b style="color:${s.color}">${info.fastest_driver}</b><br/>` +
                `距离: ${info.start_dist} ~ ${info.end_dist}<br/>` +
                `平均速度: ${info.fastest_avg_speed_kmh ?? '-'} km/h`
            },
          },
        })
      })

      // 起点标记
      if (trackLine.length > 0) {
        const [sx, sy] = trackLine[0]
        series.push({
          name: 'Start',
          type: 'scatter',
          data: [{ value: [sx, sy], name: '起点' }],
          symbolSize: 10,
          itemStyle: { color: '#fff', borderColor: '#000', borderWidth: 1 },
          label: {
            show: true,
            formatter: 'S',
            position: 'top',
            color: '#fff',
            fontSize: 9,
            fontWeight: 'bold',
          },
          z: 5,
        })
      }

      // 图例：每位车手赢的段数 + 颜色
      const legendCounts = {}
      cornerSegments.forEach(s => {
        if (s.fastest_driver) legendCounts[s.fastest_driver] = (legendCounts[s.fastest_driver] || 0) + 1
      })
      const legendData = props.drivers
        .filter(c => legendCounts[c])
        .map((code, i) => ({
          name: `${code} · ${legendCounts[code]}段`,
          icon: 'rect',
          textStyle: { color: resolveColor(code, driverIdxMap[code] ?? i), fontSize: 11 },
        }))

      // 拼接 driverPositions 作为最后一个 series
      series.push({
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
      })

      chart.setOption({
        backgroundColor: 'transparent',
        title: circuitName ? {
          text: circuitName,
          subtext: '分段最快车手着色（沿赛道 30 段）',
          left: 'center',
          top: 10,
          textStyle: { color: '#aaa', fontSize: 13, fontWeight: 'normal' },
          subtextStyle: { color: '#666', fontSize: 11 },
        } : undefined,
        tooltip: {
          trigger: 'item',
          backgroundColor: '#1a1a1a',
          borderColor: '#333',
          textStyle: { color: '#fff' },
        },
        legend: {
          data: legendData,
          bottom: 10,
          left: 'center',
          textStyle: { color: '#ccc' },
          itemWidth: 14,
          itemHeight: 10,
        },
        xAxis: { type: 'value', show: false, scale: true },
        yAxis: { type: 'value', show: false, scale: true, inverse: true },
        grid: { left: 0, right: 0, top: 50, bottom: 50 },
        animation: false,
        series,
      }, true)
      return
    }

    // 没有 corner_segments 的回退逻辑（保留原有 Track + Drivers 渲染）
    const option = {
      backgroundColor: 'transparent',
      title: circuitName ? {
        text: circuitName,
        left: 'center',
        top: 10,
        textStyle: { color: '#888', fontSize: 13, fontWeight: 'normal' },
      } : undefined,
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
  } else {
    // 无赛道坐标 — 显示分段最快着色信息
    const sectorLabels = sectors.map(s => `S${s.sector}`)
    const sectorData = sectors.map((s, i) => ({
      value: s.fastest_time || 0,
      name: `S${s.sector}`,
      driver: s.fastest_driver || '?',
      color: s.color === 'purple' ? '#a020f0' : '#00cc66',
    }))

    const option = {
      backgroundColor: 'transparent',
      title: {
        text: circuitName || '赛道地图',
        subtext: overallFastest ? `全场最快: ${overallFastest}` : '坐标数据暂不可用',
        left: 'center',
        top: '15%',
        textStyle: { color: '#aaa', fontSize: 16 },
        subtextStyle: { color: '#666', fontSize: 12 },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: '#1a1a1a',
        borderColor: '#333',
        textStyle: { color: '#fff' },
        formatter: params => {
          const d = sectorData[params.dataIndex]
          return d ? `${d.name}<br/>最快: ${d.driver}<br/>时间: ${d.value.toFixed(3)}s` : ''
        },
      },
      xAxis: {
        type: 'category',
        data: sectorLabels,
        axisLabel: { color: '#888', fontSize: 14 },
        axisLine: { lineStyle: { color: '#333' } },
      },
      yAxis: {
        type: 'value',
        name: '秒',
        nameTextStyle: { color: '#666' },
        axisLabel: { color: '#666' },
        splitLine: { lineStyle: { color: '#222' } },
        axisLine: { lineStyle: { color: '#333' } },
      },
      grid: { left: '10%', right: '10%', top: '35%', bottom: '20%' },
      series: [{
        type: 'bar',
        data: sectorData.map(d => ({
          value: d.value,
          itemStyle: { color: d.color, borderRadius: [4, 4, 0, 0] },
        })),
        barWidth: '40%',
        label: {
          show: true,
          position: 'top',
          formatter: params => sectorData[params.dataIndex]?.driver || '',
          color: '#aaa',
          fontSize: 12,
          fontWeight: 'bold',
        },
      }],
      animation: false,
    }

    chart.setOption(option, true)
  }
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
