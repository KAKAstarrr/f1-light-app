<!--
  TeleCompare.vue — 车手遥测对比页（对标 GP Tempo 布局）
  布局：顶部筛选栏(100%) + 左栏(15%) + 中栏(70%) + 右栏(15%)
  图表：速度曲线 / 油门刹车叠加 / Delta时间差，三图 axisPointer 联动
  2026适配：DRS隐藏、mock车手、未举办分站提示
-->
<template>
  <div class="telemetry-page">
    <!-- ==================== 顶部筛选栏 ==================== -->
    <div class="filter-bar">
      <el-select v-model="year" style="width: 110px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="`${y}`" :value="y" />
      </el-select>

      <el-select
        v-model="round"
        placeholder="选择分站"
        style="width: 220px"
        @change="onRoundChange"
      >
        <el-option
          v-for="r in store.raceList"
          :key="r.round"
          :label="`第${r.round}站 ${r.raceName}`"
          :value="Number(r.round)"
        />
      </el-select>

      <el-select v-model="sessionType" style="width: 130px">
        <el-option
          v-for="s in sessionTypeOptions"
          :key="s.value"
          :label="s.label"
          :value="s.value"
        />
      </el-select>

      <el-button
        type="primary"
        @click="fetchTelemetryData"
        :loading="loading"
        :disabled="!round || selectedDrivers.length === 0"
      >
        加载遥测数据
      </el-button>
    </div>

    <!-- ==================== 三栏主体 ==================== -->
    <el-row :gutter="12" class="main-row">
      <!-- ========== 左侧窄栏 15% ========== -->
      <el-col :span="4">
        <div class="side-panel">
          <!-- 车手多选 -->
          <div class="panel-section">
            <div class="panel-title">车手选择（最多 3 人）</div>
            <el-select
              v-model="selectedDrivers"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择车手"
              style="width: 100%"
              @change="handleDriverChange"
            >
              <el-option
                v-for="driver in driverOptions"
                :key="driver.code"
                :label="`${driver.code} - ${driver.givenName} ${driver.familyName}`"
                :value="driver.code"
              />
            </el-select>
          </div>

          <!-- 数据通道 -->
          <div class="panel-section">
            <div class="panel-title">数据通道</div>
            <el-checkbox-group v-model="selectedChannels" @change="handleChannelChange">
              <el-checkbox
                v-for="ch in availableChannels"
                :key="ch.key"
                :value="ch.key"
              >{{ ch.label }}</el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-col>

      <!-- ========== 中间主区域 70% ========== -->
      <el-col :span="16">
        <div class="center-area">
          <!-- 分站未开始 -->
          <el-empty v-if="raceNotStarted" description="分站暂未开始" />

          <!-- 图表区 -->
          <template v-else-if="telemetryData">
            <div v-if="showSpeedChart" class="chart-card">
              <div class="chart-title">速度曲线 (km/h)</div>
              <div ref="speedChartRef" class="chart-box"></div>
            </div>

            <div v-if="showThrottleBrakeChart" class="chart-card">
              <div class="chart-title">油门 / 刹车叠加</div>
              <div ref="throttleBrakeChartRef" class="chart-box"></div>
            </div>

            <div v-if="selectedDrivers.length >= 2" class="chart-card">
              <div class="chart-title">车手时间差 (Delta)</div>
              <div ref="deltaChartRef" class="chart-box"></div>
            </div>
          </template>

          <!-- 空状态 -->
          <el-empty v-else description="选择车手和通道后点击加载" />

          <!-- 最快圈速排行表格 -->
          <div v-if="fastestLapData && fastestLapData.length" class="table-card">
            <div class="chart-title">最快圈速排行</div>
            <el-table :data="fastestLapData" stripe size="small" style="width: 100%">
              <el-table-column prop="Rank" label="排名" width="70" align="center" />
              <el-table-column label="车手" width="100">
                <template #default="{ row }">
                  <span
                    :class="{ 'driver-highlight': selectedDrivers.includes(row.Driver) }"
                  >{{ row.Driver }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="LapTimeStr" label="圈速" width="120" />
            </el-table>
          </div>
        </div>
      </el-col>

      <!-- ========== 右侧窄栏 15% ========== -->
      <el-col :span="4">
        <div class="side-panel">
          <!-- 选中车手卡片 -->
          <div class="panel-section">
            <div class="panel-title">选中车手</div>
            <div v-if="selectedDrivers.length === 0" class="empty-hint">未选择车手</div>
            <div
              v-for="(code, idx) in selectedDrivers"
              :key="code"
              class="driver-card"
              :class="{ 'driver-hidden': hiddenDrivers.includes(code) }"
              @click="toggleDriverVisible(code)"
            >
              <div
                class="driver-avatar"
                :style="{ background: getDriverColor(code, idx) }"
              >{{ code.charAt(0) }}</div>
              <div class="driver-meta">
                <div class="driver-code">{{ code }}</div>
                <div class="driver-fullname">{{ getDriverName(code) }}</div>
              </div>
            </div>
          </div>

          <!-- 操作提示 -->
          <div class="panel-section">
            <div class="panel-title">操作提示</div>
            <p class="hint-text">点击车手卡片可隐藏 / 显示该车手的全部数据</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getTelemetryCompare, getFastestLap } from '@/api/telemetry'
import { getCurrentDrivers, getDriversByYear } from '@/api/driver'
import { MOCK_2026_DRIVERS } from '@/utils/f1-constants'
import { ElMessage } from 'element-plus'

const store = useF1Store()

// ============================================================
// 常量
// ============================================================

// 车队颜色映射（用于车手卡片和图表线条，按车手代码映射）
const teamColors = {
  VER: '#3671C6', PER: '#3671C6',
  HAM: '#E8002D', LEC: '#E8002D', SAI: '#E8002D',
  NOR: '#FF8000', PIA: '#FF8000',
  RUS: '#27F4D2', ANT: '#27F4D2',
  ALO: '#229971', STR: '#229971',
  ALB: '#37BEDD', COL: '#37BEDD',
  GAS: '#0093CC', OCO: '#0093CC',
  HUL: '#52E252', MAG: '#52E252', BEA: '#52E252',
  TSU: '#666666', RIC: '#666666',
  BOT: '#52E252', ZHO: '#52E252',
}
const defaultPalette = ['#DC143C', '#00A8E8', '#FF8000', '#8E44AD', '#2ECC71', '#F1C40F']

// 年份选择（使用全局 composable）
const { yearOptions, year, syncYearToStore } = useYearSelection()

// 会话类型（Q1/Q2/Q3 映射到 Q，FastF1 排位赛为整体 session）
const sessionTypeOptions = [
  { label: 'FP1', value: 'FP1' },
  { label: 'FP2', value: 'FP2' },
  { label: 'FP3', value: 'FP3' },
  { label: 'Q1', value: 'Q1' },
  { label: 'Q2', value: 'Q2' },
  { label: 'Q3', value: 'Q3' },
  { label: '冲刺赛', value: 'S' },
  { label: '正赛', value: 'R' },
]

// 全部通道定义
const allChannelDefs = [
  { key: 'speed', label: '速度' },
  { key: 'throttle', label: '油门' },
  { key: 'brake', label: '刹车' },
  { key: 'rpm', label: '转速' },
  { key: 'gear', label: '挡位' },
  { key: 'drs', label: 'DRS' },
]

// ============================================================
// 响应式状态
// ============================================================

// year 由 useYearSelection composable 提供
const round = ref(null)
const sessionType = ref('R')
const selectedDrivers = ref([])
const selectedChannels = ref(['speed', 'throttle', 'brake'])
const driverOptions = ref([])
const hiddenDrivers = ref([])

const loading = ref(false)
const telemetryData = ref(null)
const fastestLapData = ref(null)
const raceNotStarted = ref(false)

// 图表 DOM 引用 & 实例
const speedChartRef = ref(null)
const throttleBrakeChartRef = ref(null)
const deltaChartRef = ref(null)
let speedChart = null
let throttleBrakeChart = null
let deltaChart = null
const chartGroup = 'telemetry-group'

// ============================================================
// 计算属性
// ============================================================

// 2026 年过滤掉 DRS 通道
const availableChannels = computed(() => {
  return allChannelDefs.filter(ch => year.value !== 2026 || ch.key !== 'drs')
})

// 速度图是否显示
const showSpeedChart = computed(() => selectedChannels.value.includes('speed'))

// 油门/刹车图是否显示
const showThrottleBrakeChart = computed(() =>
  selectedChannels.value.includes('throttle') || selectedChannels.value.includes('brake')
)

// 发给后端的通道列表（始终包含 speed 用于 Delta 计算）
const channelsForAPI = computed(() => {
  const set = new Set(selectedChannels.value)
  set.add('speed') // Delta 计算需要 speed
  if (year.value === 2026) set.delete('drs')
  return Array.from(set)
})

// 实际用于 API 的 session_type（Q1/Q2/Q3 统一映射为 Q）
const sessionTypeForAPI = computed(() => {
  const v = sessionType.value
  if (v === 'Q1' || v === 'Q2' || v === 'Q3') return 'Q'
  return v
})

// ============================================================
// 生命周期
// ============================================================

onMounted(async () => {
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
  }
  await loadDriverOptions()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  disposeAllCharts()
  window.removeEventListener('resize', handleResize)
})

// ============================================================
// 工具函数
// ============================================================

function getDriverColor(code, index) {
  return teamColors[code] || defaultPalette[index % defaultPalette.length]
}

function getDriverName(code) {
  const d = driverOptions.value.find(d => d.code === code)
  if (!d) return ''
  return `${d.givenName} ${d.familyName}`
}

// Q1/Q2/Q3 → Q 的 session 映射已在 sessionTypeForAPI 中处理

// ============================================================
// 数据加载
// ============================================================

async function loadDriverOptions() {
  try {
    // 2026 用 getCurrentDrivers（Ergast current=2026，30 人）
    // 其他年份用 getDriversByYear（Ergast 历史数据）
    // 失败时 fallback 到 MOCK_2026_DRIVERS
    const apiFn = year.value === 2026 ? getCurrentDrivers : () => getDriversByYear(year.value)
    const res = await apiFn()
    const rawDrivers = res?.Drivers || (Array.isArray(res) ? res : [])
    driverOptions.value = rawDrivers.map(d => ({
      code: d.code || d.driver_code || '',
      givenName: d.givenName || (d.full_name ? d.full_name.split(' ')[0] : ''),
      familyName: d.familyName || (d.full_name ? d.full_name.split(' ').slice(1).join(' ') : ''),
    })).filter(d => d.code)

    // 兜底：如果没拉到任何车手，用 MOCK
    if (driverOptions.value.length === 0) {
      driverOptions.value = [...MOCK_2026_DRIVERS]
    }
  } catch (error) {
    console.error('加载车手数据失败:', error)
    driverOptions.value = [...MOCK_2026_DRIVERS]
  }
}

async function fetchTelemetryData() {
  if (!round.value) {
    ElMessage.warning('请先选择分站')
    return
  }
  if (selectedDrivers.value.length === 0) {
    ElMessage.warning('请至少选择一个车手')
    return
  }
  if (channelsForAPI.value.length === 0) {
    ElMessage.warning('请至少选择一个数据通道')
    return
  }

  loading.value = true
  raceNotStarted.value = false
  telemetryData.value = null
  fastestLapData.value = null
  hiddenDrivers.value = []

  try {
    const res = await getTelemetryCompare({
      year: Number(year.value),
      round: Number(round.value),
      drivers: selectedDrivers.value.join(','),
      channels: channelsForAPI.value.join(','),
      sessionType: sessionTypeForAPI.value,
    })

    if (res && typeof res.code === 'number' && res.code !== 200) {
      // 后端软错误（如数据不存在）
      if (year.value === 2026) {
        raceNotStarted.value = true
      } else {
        ElMessage.warning(res.msg || '未获取到遥测数据')
      }
      return
    }

    if (res && res.distances && res.drivers) {
      telemetryData.value = res
      await nextTick()
      renderAllCharts()
      fetchFastestLapData()
    } else {
      if (year.value === 2026) {
        raceNotStarted.value = true
      } else {
        ElMessage.warning('未获取到遥测数据')
      }
    }
  } catch (error) {
    console.error('获取遥测数据失败:', error)
    if (year.value === 2026) {
      raceNotStarted.value = true
    }
  } finally {
    loading.value = false
  }
}

async function fetchFastestLapData() {
  try {
    const res = await getFastestLap(
      Number(year.value),
      Number(round.value),
      sessionTypeForAPI.value
    )
    if (res && res.code === 200 && res.fastest_lap_ranking) {
      fastestLapData.value = res.fastest_lap_ranking
    }
  } catch (error) {
    console.error('获取最快圈速失败:', error)
  }
}

// ============================================================
// 事件处理
// ============================================================

async function onYearChange() {
  syncYearToStore()
  // 2026 年移除 DRS
  if (year.value === 2026 && selectedChannels.value.includes('drs')) {
    selectedChannels.value = selectedChannels.value.filter(ch => ch !== 'drs')
    ElMessage.info('2026 年 DRS 数据暂不可用，已自动移除')
  }
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
  } else {
    round.value = null
  }
  telemetryData.value = null
  raceNotStarted.value = false
  fastestLapData.value = null
  await loadDriverOptions()
}

function onRoundChange() {
  telemetryData.value = null
  raceNotStarted.value = false
  fastestLapData.value = null
}

function handleDriverChange(value) {
  if (value.length > 3) {
    selectedDrivers.value = value.slice(0, 3)
    ElMessage.warning('最多只能选择 3 个车手进行对比')
  }
  // 移除已取消选择的车手的隐藏状态
  hiddenDrivers.value = hiddenDrivers.value.filter(c => selectedDrivers.value.includes(c))
}

function handleChannelChange(value) {
  // 2026 年 DRS 不可选
  if (year.value === 2026 && value.includes('drs')) {
    selectedChannels.value = value.filter(ch => ch !== 'drs')
    ElMessage.warning('2026 年 DRS 数据暂不可用')
  }
}

function toggleDriverVisible(code) {
  const idx = hiddenDrivers.value.indexOf(code)
  if (idx > -1) {
    hiddenDrivers.value.splice(idx, 1)
  } else {
    hiddenDrivers.value.push(code)
  }
  updateChartsVisibility()
}

// ============================================================
// 图表渲染
// ============================================================

function renderAllCharts() {
  if (!telemetryData.value) return

  disposeAllCharts()

  const visibleDrivers = selectedDrivers.value.filter(c => !hiddenDrivers.value.includes(c))

  // 速度图
  if (speedChartRef.value && showSpeedChart.value) {
    speedChart = echarts.init(speedChartRef.value)
    speedChart.group = chartGroup
    speedChart.setOption(generateSpeedOption(visibleDrivers))
  }

  // 油门/刹车图
  if (throttleBrakeChartRef.value && showThrottleBrakeChart.value) {
    throttleBrakeChart = echarts.init(throttleBrakeChartRef.value)
    throttleBrakeChart.group = chartGroup
    throttleBrakeChart.setOption(generateThrottleBrakeOption(visibleDrivers))
  }

  // Delta 图（至少 2 名车手）
  if (deltaChartRef.value && selectedDrivers.value.length >= 2) {
    deltaChart = echarts.init(deltaChartRef.value)
    deltaChart.group = chartGroup
    deltaChart.setOption(generateDeltaOption(visibleDrivers))
  }

  // 三图联动
  echarts.connect(chartGroup)
}

function disposeAllCharts() {
  ;[speedChart, throttleBrakeChart, deltaChart].forEach(chart => {
    if (chart && chart.dispose) chart.dispose()
  })
  speedChart = null
  throttleBrakeChart = null
  deltaChart = null
}

function handleResize() {
  ;[speedChart, throttleBrakeChart, deltaChart].forEach(chart => {
    if (chart) chart.resize()
  })
}

// 切换车手可见性时更新图表
function updateChartsVisibility() {
  if (!telemetryData.value) return
  renderAllCharts()
}

// ============================================================
// ECharts Option 生成
// ============================================================

// 公共 Tooltip Formatter — 显示距离 + 各车手多通道数据
function makeTooltipFormatter(chartType) {
  return function (params) {
    if (!params || params.length === 0) return ''
    const dataIndex = params[0].dataIndex
    const distances = telemetryData.value.distances || []
    const distance = distances[dataIndex] !== undefined
      ? distances[dataIndex].toFixed(1)
      : (params[0].value[0] !== undefined ? params[0].value[0].toFixed(1) : '-')
    let html = `<b>距离: ${distance} m</b><br/>`

    const visibleDrivers = selectedDrivers.value.filter(c => !hiddenDrivers.value.includes(c))
    visibleDrivers.forEach(code => {
      const drvData = telemetryData.value.drivers[code]
      if (!drvData) return
      html += `<b style="color:${getDriverColor(code, selectedDrivers.value.indexOf(code))}">${code}</b><br/>`

      if (chartType === 'speed' && drvData.speed && drvData.speed[dataIndex] != null) {
        html += `&nbsp;&nbsp;速度: ${drvData.speed[dataIndex].toFixed(1)} km/h<br/>`
      }
      if (chartType === 'throttleBrake') {
        if (drvData.throttle && drvData.throttle[dataIndex] != null) {
          html += `&nbsp;&nbsp;油门: ${drvData.throttle[dataIndex].toFixed(1)}%<br/>`
        }
        if (drvData.brake && drvData.brake[dataIndex] != null) {
          html += `&nbsp;&nbsp;刹车: ${(drvData.brake[dataIndex] * 100).toFixed(0)}%<br/>`
        }
      }
      // 所有图表的 Tooltip 都附带挡位和 DRS（2026 年隐藏 DRS）
      if (drvData.gear && drvData.gear[dataIndex] != null) {
        html += `&nbsp;&nbsp;挡位: ${drvData.gear[dataIndex]}<br/>`
      }
      if (year.value !== 2026 && drvData.drs && drvData.drs[dataIndex] != null) {
        html += `&nbsp;&nbsp;DRS: ${formatDRS(drvData.drs[dataIndex])}<br/>`
      }
    })
    return html
  }
}

function formatDRS(val) {
  if (val === 0 || val === 0.0) return '关闭'
  if (val === 1 || val === 1.0) return '启用'
  if (val === 2 || val === 2.0) return '检测区'
  return String(val)
}

// 通用 grid / xAxis 配置
const commonGrid = { left: 60, right: 30, top: 20, bottom: 40 }
const commonXAxis = {
  type: 'value',
  name: '距离 (m)',
  nameTextStyle: { fontSize: 11 },
  scale: true,
}

// ---- 图表 1：速度曲线 ----
function generateSpeedOption(visibleDrivers) {
  const distances = telemetryData.value.distances || []
  const drivers = telemetryData.value.drivers || {}

  const series = visibleDrivers.map(code => {
    const idx = selectedDrivers.value.indexOf(code)
    const color = getDriverColor(code, idx)
    const speedData = drivers[code]?.speed || []
    return {
      name: code,
      type: 'line',
      showSymbol: false,
      smooth: true,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      data: speedData.map((v, i) => [distances[i] ?? i * 10, v]),
    }
  })

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: makeTooltipFormatter('speed') },
    legend: { show: false, data: visibleDrivers, selected: makeSelectedMap(visibleDrivers) },
    grid: commonGrid,
    xAxis: commonXAxis,
    yAxis: { type: 'value', name: 'km/h', min: 0, max: 350 },
    series,
  }
}

// ---- 图表 2：油门 / 刹车叠加 ----
function generateThrottleBrakeOption(visibleDrivers) {
  const distances = telemetryData.value.distances || []
  const drivers = telemetryData.value.drivers || {}

  const series = []
  visibleDrivers.forEach(code => {
    const idx = selectedDrivers.value.indexOf(code)
    const color = getDriverColor(code, idx)
    const drvData = drivers[code] || {}

    // 油门：line + 半透明面积
    if (drvData.throttle) {
      series.push({
        name: `${code} - 油门`,
        type: 'line',
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 1.5, color },
        areaStyle: { opacity: 0.15, color },
        itemStyle: { color },
        data: drvData.throttle.map((v, i) => [distances[i] ?? i * 10, v]),
      })
    }
    // 刹车：line + 半透明红色面积（FastF1 brake 是 0~1，转换为 0~100）
    if (drvData.brake) {
      series.push({
        name: `${code} - 刹车`,
        type: 'line',
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1.5, color: '#E83838' },
        areaStyle: { opacity: 0.2, color: '#E83838' },
        itemStyle: { color: '#E83838' },
        data: drvData.brake.map((v, i) => [distances[i] ?? i * 10, v * 100]),
      })
    }
  })

  const legendData = series.map(s => s.name)

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, formatter: makeTooltipFormatter('throttleBrake') },
    legend: { show: false, data: legendData, selected: makeSelectedMap(visibleDrivers, [' - 油门', ' - 刹车']) },
    grid: commonGrid,
    xAxis: commonXAxis,
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series,
  }
}

// ---- 图表 3：Delta 时间差 ----
function generateDeltaOption(visibleDrivers) {
  const distances = telemetryData.value.distances || []
  const drivers = telemetryData.value.drivers || {}

  if (visibleDrivers.length < 2) {
    return {
      tooltip: { trigger: 'axis' },
      grid: commonGrid,
      xAxis: commonXAxis,
      yAxis: { type: 'value', name: 'Delta (s)' },
      series: [],
    }
  }

  // 以第一个可见车手为基准
  const refCode = visibleDrivers[0]
  const refSpeed = drivers[refCode]?.speed || []
  const refCumTime = calculateCumulativeTime(distances, refSpeed)

  const series = visibleDrivers.slice(1).map(code => {
    const idx = selectedDrivers.value.indexOf(code)
    const color = getDriverColor(code, idx)
    const drvSpeed = drivers[code]?.speed || []
    const drvCumTime = calculateCumulativeTime(distances, drvSpeed)
    // delta > 0 表示该车手比基准慢
    const deltaData = distances.map((d, i) => [d, drvCumTime[i] - refCumTime[i]])
    return {
      name: `${code} vs ${refCode}`,
      type: 'line',
      showSymbol: false,
      smooth: true,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      data: deltaData,
    }
  })

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: function (params) {
        if (!params || params.length === 0) return ''
        const dataIndex = params[0].dataIndex
        const distance = (distances[dataIndex] ?? params[0].value[0] ?? 0).toFixed(1)
        let html = `<b>距离: ${distance} m</b><br/>`
        params.forEach(item => {
          const delta = item.value[1]
          const sign = delta >= 0 ? '+' : ''
          const color = delta > 0 ? '#E83838' : '#22C55E'
          html += `${item.seriesName}: <span style="color:${color}">${sign}${delta.toFixed(3)}s</span><br/>`
        })
        return html
      },
    },
    legend: { show: false, data: series.map(s => s.name), selected: makeSelectedMap(visibleDrivers.slice(1)) },
    grid: commonGrid,
    xAxis: commonXAxis,
    yAxis: { type: 'value', name: 'Delta (s)', axisLine: { show: true } },
    series,
  }
}

// ============================================================
// 辅助计算
// ============================================================

// 根据距离和速度数组计算累积时间（秒）
// v 单位 km/h → m/s，dt = ds / v
function calculateCumulativeTime(distances, speeds) {
  if (!distances.length || !speeds.length) return []
  const cumTimes = [0]
  for (let i = 1; i < distances.length; i++) {
    const ds = distances[i] - distances[i - 1]
    const v_kmh = speeds[i] || speeds[i - 1] || 1 // 防止除零
    const v_ms = v_kmh / 3.6
    const dt = v_ms > 0 ? ds / v_ms : 0
    cumTimes.push(cumTimes[i - 1] + dt)
  }
  return cumTimes
}

// 生成 legend.selected 映射（控制车手可见性）
function makeSelectedMap(drivers, suffixes = ['']) {
  const selected = {}
  drivers.forEach(code => {
    const hidden = hiddenDrivers.value.includes(code)
    suffixes.forEach(suffix => {
      if (suffix === '') {
        selected[code] = !hidden
      } else {
        selected[`${code}${suffix}`] = !hidden
      }
    })
  })
  return selected
}

// ============================================================
// Watch — 通道变化时如果已有数据则重新渲染
// ============================================================

watch(selectedChannels, () => {
  if (telemetryData.value) {
    nextTick(() => renderAllCharts())
  }
})
</script>

<style scoped>
.telemetry-page {
  padding: 16px;
}

/* ========== 顶部筛选栏 ========== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

/* ========== 三栏布局 ========== */
.main-row {
  margin: 0 !important;
}

.side-panel {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  min-height: 400px;
}

.panel-section {
  margin-bottom: 20px;
}

.panel-section:last-child {
  margin-bottom: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #ebeef5;
}

.empty-hint {
  font-size: 12px;
  color: #c0c4cc;
  text-align: center;
  padding: 12px 0;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin: 0;
}

/* ========== 车手卡片 ========== */
.driver-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 6px;
}

.driver-card:hover {
  background: #f5f7fa;
}

.driver-card.driver-hidden {
  opacity: 0.4;
}

.driver-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.driver-meta {
  overflow: hidden;
}

.driver-code {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.driver-fullname {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========== 中间图表区 ========== */
.center-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.chart-box {
  width: 100%;
  height: 300px;
}

.table-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.driver-highlight {
  color: #409eff;
  font-weight: 700;
}
</style>
