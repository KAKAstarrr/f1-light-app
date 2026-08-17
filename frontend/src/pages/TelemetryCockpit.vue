/**
 * TelemetryCockpit — 遥测分析 GP Tempo 风格大屏
 * 顶部筛选 + 主区(80%) + 底部图层控制+播放(20%)
 * 三种模式：地图 / 图表 / 分屏
 * 6 个图层独立开关
 */
<template>
  <div class="telemetry-cockpit">
    <!-- 顶部筛选栏 -->
    <div class="cockpit-header">
      <div class="filter-left">
        <el-select v-model="year" style="width: 110px" @change="onYearChange">
          <el-option v-for="y in yearOptions" :key="y" :label="`${y}`" :value="y" />
        </el-select>
        <el-select
          v-model="round"
          placeholder="选择分站"
          style="width: 200px"
          filterable
          @change="onRoundChange"
        >
          <el-option
            v-for="r in store.raceList"
            :key="r.round"
            :label="`R${r.round} ${r.raceName}`"
            :value="Number(r.round)"
          />
        </el-select>
        <el-select
          v-model="selectedDrivers"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="选择车手 (最多4人)"
          style="min-width: 220px; max-width: 400px"
          :max="4"
        >
          <el-option
            v-for="d in driverOptions"
            :key="d.code"
            :label="`${d.code} - ${d.givenName} ${d.familyName}`"
            :value="d.code"
          />
        </el-select>
        <el-select v-model="sessionType" style="width: 100px">
          <el-option label="正赛 R" value="R" />
          <el-option label="排位 Q" value="Q" />
          <el-option label="Q1" value="Q1" />
          <el-option label="Q2" value="Q2" />
          <el-option label="Q3" value="Q3" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="loadAll">
          📊 加载数据
        </el-button>
      </div>

      <div class="filter-right">
        <!-- 模式切换器 -->
        <el-segmented v-model="layerStore.viewMode" :options="viewModeOptions" />
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="cockpit-main" v-loading="loading" element-loading-text="加载遥测数据中...">
      <div v-if="!hasData" class="no-data-state">
        <EmptyState
          icon="📈"
          title="遥测分析大屏"
          description="选择年份、分站和车手后点击「加载数据」开始分析"
        />
        <div v-if="loadError" class="load-error-msg">
          {{ loadError }}
        </div>
        <el-button class="demo-btn" type="primary" plain size="small" @click="loadDemoData">
          试用示例数据 (2024 R1 VER vs NOR)
        </el-button>
      </div>

      <div v-else class="main-content" :class="`mode-${layerStore.viewMode}`">
        <!-- 左上角车手对比卡片 -->
        <DriverCompareCard :drivers="compareDrivers" :lapInfo="currentLap" />

        <!-- 地图模式 -->
        <div v-if="layerStore.viewMode === 'map'" class="map-view">
          <TrackLayer
            v-if="layerStore.trackMap"
            :trackData="trackData"
            :telemetryData="telemetryData"
            :drivers="selectedDrivers"
            :currentTime="playerStore.currentTime"
            :cornerSegments="cornerSegments"
            :driverColorMap="driverColorMap"
          />
          <div v-else class="layer-disabled">
            <EmptyState icon="🗺️" title="赛道底图已关闭" description="在下方图层控制中开启" />
          </div>
        </div>

        <!-- 图表模式 -->
        <div v-if="layerStore.viewMode === 'chart'" class="chart-view">
          <div class="chart-grid">
            <div v-if="layerStore.speed" class="chart-item">
              <SpeedLayer :telemetryData="telemetryData" :drivers="selectedDrivers" />
            </div>
            <div v-if="layerStore.throttleBrake" class="chart-item">
              <ThrottleBrakeLayer :telemetryData="telemetryData" :drivers="selectedDrivers" />
            </div>
            <div v-if="layerStore.lapDistribution" class="chart-item">
              <LapDistributionLayer :lapData="lapDistData" />
            </div>
            <div v-if="layerStore.sectorFastest" class="chart-item">
              <SectorFastestLayer :sectorData="sectorData" />
            </div>
            <div v-if="layerStore.delta && selectedDrivers.length >= 2" class="chart-item">
              <DeltaLayer :telemetryData="telemetryData" :drivers="selectedDrivers" />
            </div>
          </div>
        </div>

        <!-- 分屏模式 -->
        <div v-if="layerStore.viewMode === 'split'" class="split-view">
          <div class="split-left">
            <TrackLayer
              v-if="layerStore.trackMap"
              :trackData="trackData"
              :telemetryData="telemetryData"
              :drivers="selectedDrivers"
              :currentTime="playerStore.currentTime"
              :cornerSegments="cornerSegments"
              :driverColorMap="driverColorMap"
            />
          </div>
          <div class="split-right">
            <div class="chart-grid">
              <div v-if="layerStore.speed" class="chart-item">
                <SpeedLayer :telemetryData="telemetryData" :drivers="selectedDrivers" />
              </div>
              <div v-if="layerStore.throttleBrake" class="chart-item">
                <ThrottleBrakeLayer :telemetryData="telemetryData" :drivers="selectedDrivers" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部控制区 -->
    <div class="cockpit-footer">
      <!-- 图层开关面板 -->
      <div class="layer-panel">
        <span class="panel-title">图层</span>
        <div class="layer-toggles">
          <div
            v-for="layer in layers"
            :key="layer.key"
            class="layer-toggle"
            :class="{
              active: layerStore[layer.key],
              disabled: !layerStore.layerAvailability[layer.key]
            }"
            @click="layerStore.toggle(layer.key)"
          >
            <span class="layer-icon">{{ layer.icon }}</span>
            <span class="layer-name">{{ layer.name }}</span>
            <span v-if="!layerStore.layerAvailability[layer.key]" class="layer-unavailable">
              不可用
            </span>
          </div>
        </div>
      </div>

      <!-- 播放控件 -->
      <div class="player-panel">
        <div class="player-controls">
          <el-button
            circle
            size="small"
            @click="playerStore.reset()"
            type="default"
          >
            ⏮
          </el-button>
          <el-button
            circle
            @click="playerStore.toggle()"
            :type="playerStore.isPlaying ? 'danger' : 'primary'"
          >
            {{ playerStore.isPlaying ? '⏸' : '▶' }}
          </el-button>
          <div class="speed-selector">
            <el-button
              v-for="s in playerStore.speedOptions"
              :key="s"
              size="small"
              :type="playerStore.speed === s ? 'primary' : 'default'"
              @click="playerStore.setSpeed(s)"
            >
              {{ s }}x
            </el-button>
          </div>
        </div>

        <!-- 时间轴 -->
        <div class="timeline">
          <span class="time-label mono">{{ playerStore.formattedCurrent }}</span>
          <el-slider
            v-model="sliderValue"
            :max="100"
            :step="0.1"
            :show-tooltip="false"
            class="timeline-slider"
            @change="onSeek"
          />
          <span class="time-label mono">{{ playerStore.formattedTotal }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useF1Store } from '@/stores/f1'
import { useLayerStore } from '@/stores/layer'
import { usePlayerStore } from '@/stores/player'
import { YEAR_OPTIONS, DRIVER_CHART_COLORS, filterChannelsForYear } from '@/utils/f1-constants'
import { getTelemetryCompare, getTrackMap, getLapDistribution, getSectorFastest } from '@/api/telemetry'
import EmptyState from '@/components/EmptyState.vue'
import DriverCompareCard from '@/components/DriverCompareCard.vue'
import TrackLayer from '@/views/telemetry/TrackLayer.vue'
import SpeedLayer from '@/views/telemetry/SpeedLayer.vue'
import ThrottleBrakeLayer from '@/views/telemetry/ThrottleBrakeLayer.vue'
import LapDistributionLayer from '@/views/telemetry/LapDistributionLayer.vue'
import SectorFastestLayer from '@/views/telemetry/SectorFastestLayer.vue'
import DeltaLayer from '@/views/telemetry/DeltaLayer.vue'

const route = useRoute()
const store = useF1Store()
const layerStore = useLayerStore()
const playerStore = usePlayerStore()

const yearOptions = YEAR_OPTIONS
const year = ref(Number(route.query.year) || store.currentSeason)
const round = ref(route.query.round ? Number(route.query.round) : null)
const selectedDrivers = ref(route.query.drivers ? route.query.drivers.split(',') : [])
const sessionType = ref(route.query.sessionType || 'R')
const driverOptions = ref([])
const loading = ref(false)
const hasData = ref(false)
const loadError = ref(null) // 错误信息

// 数据
const telemetryData = ref(null)
const trackData = ref(null)
const lapDistData = ref(null)
const sectorData = ref(null)

// 播放进度滑块
const sliderValue = ref(0)

const currentLap = computed(() => {
  if (!playerStore.totalTime) return ''
  const lapDuration = playerStore.totalTime
  const currentLapNum = Math.floor(playerStore.currentTime / lapDuration) + 1
  return currentLapNum
})

const compareDrivers = computed(() => {
  if (!telemetryData.value?.drivers && !telemetryData.value?.telemetry) return []
  const driversData = telemetryData.value.drivers || telemetryData.value.telemetry || {}
  return selectedDrivers.value.map((code, i) => {
    const driverData = driversData[code]
    if (!driverData) return { code, color: DRIVER_CHART_COLORS[i], name: code }

    // 从 speed 数组中估算最快圈速（用距离/平均速度）
    let lapTime = null
    const distances = telemetryData.value?.distances || []
    const speedArr = driverData.speed || (driverData.telemetry || []).map(p => p.Speed ?? p.speed ?? 0)
    if (speedArr.length > 0 && distances.length > 0) {
      const totalDist = distances[distances.length - 1] - distances[0]
      const avgSpeed = speedArr.reduce((a, b) => a + b, 0) / speedArr.length
      if (avgSpeed > 0) {
        lapTime = totalDist / (avgSpeed / 3.6) // m / (km/h → m/s)
      }
    }

    return {
      code,
      color: DRIVER_CHART_COLORS[i],
      name: code,
      lapTime: lapTime ? formatLapTime(lapTime) : null,
      delta: i === 0 ? 0 : null,
    }
  })
})

// 弯角最快段（来自 telemetry 接口的 corner_segments 字段）
// 把 telemetry 接口返回的 corner_segments 传给 TrackLayer 用于赛道分段染色
const cornerSegments = computed(() => {
  return telemetryData.value?.corner_segments || []
})

// 车手 → 颜色映射（用于 TrackLayer 把每段染色为最快车手的车队色）
const driverColorMap = computed(() => {
  const map = {}
  selectedDrivers.value.forEach((code, i) => {
    map[code] = DRIVER_CHART_COLORS[i % DRIVER_CHART_COLORS.length]
  })
  return map
})

const layers = [
  { key: 'trackMap', name: '赛道底图', icon: '🗺️' },
  { key: 'speed', name: '速度曲线', icon: '⚡' },
  { key: 'throttleBrake', name: '油门/刹车', icon: '🏎️' },
  { key: 'lapDistribution', name: '圈速分布', icon: '📊' },
  { key: 'sectorFastest', name: '分段最快', icon: '⏱️' },
  { key: 'delta', name: '时间差', icon: '📉' },
]

const viewModeOptions = [
  { label: '地图', value: 'map' },
  { label: '图表', value: 'chart' },
  { label: '分屏', value: 'split' },
]

function formatLapTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = (seconds % 60).toFixed(3)
  return `${m}:${s.padStart(6, '0')}`
}

async function onYearChange() {
  await store.fetchRaceList(year.value)
  driverOptions.value = await store.fetchDrivers(year.value)
  round.value = null
  hasData.value = false
}

async function onRoundChange() {
  hasData.value = false
}

async function loadAll() {
  if (!round.value || selectedDrivers.value.length === 0) return

  loading.value = true
  loadError.value = null
  layerStore.reset()
  hasData.value = false

  // 清空旧数据
  telemetryData.value = null
  trackData.value = null
  lapDistData.value = null
  sectorData.value = null

  try {
    // 检测图层可用性
    layerStore.setAvailability({
      trackMap: true,
      speed: true,
      throttleBrake: true,
      lapDistribution: true,
      sectorFastest: true,
      delta: selectedDrivers.value.length >= 2,
    })

    // 并行加载所有图层数据
    const channels = filterChannelsForYear(['speed', 'throttle', 'brake', 'drs'], year.value)
    const driversStr = selectedDrivers.value.join(',')

    const promises = []
    const errors = []

    // 遥测数据
    promises.push(
      getTelemetryCompare({
        year: year.value,
        round: round.value,
        drivers: driversStr,
        channels: channels.join(','),
        sessionType: sessionTypeForAPI(),
      }).then(data => {
        // 后端返回 {code, drivers, distances} 或 {code:500, msg}
        if (data && data.code === 500) {
          errors.push(`遥测: ${data.msg || '加载失败'}`)
          layerStore.setAvailability({ speed: false, throttleBrake: false, delta: false })
        } else if (data && data.drivers) {
          telemetryData.value = data
        } else if (data && data.telemetry) {
          // 兼容旧格式
          telemetryData.value = data
        }
      }).catch(e => {
        errors.push(`遥测加载失败: ${e.message || e}`)
        layerStore.setAvailability({ speed: false, throttleBrake: false, delta: false })
      })
    )

    // 赛道地图
    if (layerStore.trackMap) {
      promises.push(
        getTrackMap(year.value, round.value, sessionTypeForAPI())
          .then(data => {
            if (data && data.code === 500) {
              errors.push(`赛道图: ${data.msg || '加载失败'}`)
              layerStore.setAvailability({ trackMap: false })
            } else if (data) {
              trackData.value = data
            }
          })
          .catch(e => {
            errors.push(`赛道图加载失败: ${e.message || e}`)
            layerStore.setAvailability({ trackMap: false })
          })
      )
    }

    // 圈速分布
    if (layerStore.lapDistribution) {
      promises.push(
        getLapDistribution(year.value, round.value, sessionTypeForAPI())
          .then(data => {
            if (data && data.code === 500) {
              errors.push(`圈速分布: ${data.msg || '加载失败'}`)
              layerStore.setAvailability({ lapDistribution: false })
            } else if (data) {
              lapDistData.value = data
            }
          })
          .catch(e => {
            errors.push(`圈速分布加载失败: ${e.message || e}`)
            layerStore.setAvailability({ lapDistribution: false })
          })
      )
    }

    // 分段最快
    if (layerStore.sectorFastest) {
      promises.push(
        getSectorFastest(year.value, round.value, sessionTypeForAPI())
          .then(data => {
            if (data && data.code === 500) {
              errors.push(`分段最快: ${data.msg || '加载失败'}`)
              layerStore.setAvailability({ sectorFastest: false })
            } else if (data) {
              sectorData.value = data
            }
          })
          .catch(e => {
            errors.push(`分段最快加载失败: ${e.message || e}`)
            layerStore.setAvailability({ sectorFastest: false })
          })
      )
    }

    await Promise.allSettled(promises)

    // 设置播放总时长（从遥测数据估算）
    if (telemetryData.value?.drivers) {
      const firstDriver = selectedDrivers.value[0]
      const driverData = telemetryData.value.drivers[firstDriver]
      if (driverData?.speed?.length && telemetryData.value.distances?.length) {
        const totalDist = telemetryData.value.distances[telemetryData.value.distances.length - 1] - telemetryData.value.distances[0]
        const avgSpeed = driverData.speed.reduce((a, b) => a + b, 0) / driverData.speed.length
        if (avgSpeed > 0) {
          playerStore.setTotalTime(totalDist / (avgSpeed / 3.6))
        }
      }
    }

    // 判断是否有有效数据
    const hasAnyData = telemetryData.value || trackData.value || lapDistData.value || sectorData.value
    if (hasAnyData) {
      hasData.value = true
      if (errors.length > 0) {
        loadError.value = errors.join('; ')
      }
    } else {
      loadError.value = errors.join('; ') || '所有数据源加载失败'
    }
  } finally {
    loading.value = false
  }
}

function sessionTypeForAPI() {
  // Q1/Q2/Q3 都映射到 Q
  if (['Q1', 'Q2', 'Q3'].includes(sessionType.value)) return 'Q'
  return sessionType.value
}

function loadDemoData() {
  year.value = 2024
  round.value = 1
  selectedDrivers.value = ['VER', 'NOR']
  sessionType.value = 'R'
  loadAll()
}

function onSeek(val) {
  playerStore.seek((val / 100) * playerStore.totalTime)
}

// 监听播放进度同步滑块
watch(() => playerStore.currentTime, () => {
  if (playerStore.totalTime) {
    sliderValue.value = (playerStore.currentTime / playerStore.totalTime) * 100
  }
})

onMounted(async () => {
  await store.fetchRaceList(year.value)
  driverOptions.value = await store.fetchDrivers(year.value)

  // 如果 URL 带了参数，自动加载
  if (round.value && selectedDrivers.value.length) {
    loadAll()
  }
})

onUnmounted(() => {
  playerStore.pause()
})
</script>

<style scoped>
.telemetry-cockpit {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 48px);
  max-width: 1800px;
  margin: 0 auto;
  gap: 12px;
}

.cockpit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  padding: 10px 16px;
  flex-wrap: wrap;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cockpit-main {
  flex: 1;
  background: var(--f1-bg-dark);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  min-height: 400px;
}

.no-data-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.load-error-msg {
  color: var(--f1-red, #e10600);
  font-size: 13px;
  max-width: 500px;
  text-align: center;
  padding: 8px 16px;
  background: rgba(225, 6, 0, 0.1);
  border-radius: 6px;
}

.demo-btn {
  margin-top: 8px;
}

.main-content {
  width: 100%;
  height: 100%;
  position: relative;
}

.main-content.mode-map {
  display: flex;
}

.main-content.mode-chart {
  padding: 12px;
  overflow-y: auto;
}

.main-content.mode-split {
  display: flex;
  gap: 8px;
  padding: 8px;
}

.map-view {
  width: 100%;
  height: 100%;
  position: relative;
}

.chart-view {
  width: 100%;
  height: 100%;
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  height: 100%;
}

.chart-item {
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  padding: 12px;
  min-height: 300px;
}

.split-view {
  width: 100%;
  display: flex;
  gap: 8px;
}

.split-left {
  flex: 1;
  position: relative;
}

.split-right {
  flex: 1;
}

.split-right .chart-grid {
  grid-template-columns: 1fr;
}

.layer-disabled {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 底部控制区 */
.cockpit-footer {
  display: flex;
  gap: 12px;
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  padding: 10px 16px;
}

.layer-panel {
  flex: 1;
}

.panel-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--f1-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 6px;
}

.layer-toggles {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.layer-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 4px;
  background: var(--f1-bg-elevated);
  border: 1px solid var(--f1-border);
  cursor: pointer;
  font-size: 12px;
  color: var(--f1-text-secondary);
  transition: all 0.15s;
  user-select: none;
}

.layer-toggle:hover:not(.disabled) {
  background: var(--f1-bg-hover);
  color: var(--f1-text-primary);
}

.layer-toggle.active {
  background: rgba(225, 6, 0, 0.15);
  border-color: var(--f1-red);
  color: var(--f1-red);
}

.layer-toggle.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.layer-icon {
  font-size: 14px;
}

.layer-name {
  font-weight: 500;
}

.layer-unavailable {
  font-size: 10px;
  color: var(--f1-text-muted);
  margin-left: 2px;
}

.player-panel {
  flex-shrink: 0;
  min-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.speed-selector {
  display: flex;
  gap: 4px;
}

.timeline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 12px;
  color: var(--f1-text-secondary);
  min-width: 50px;
  text-align: center;
}

.timeline-slider {
  flex: 1;
}

:deep(.timeline-slider .el-slider__runway) {
  background: var(--f1-bg-elevated);
}

:deep(.timeline-slider .el-slider__bar) {
  background: var(--f1-red);
}

:deep(.timeline-slider .el-slider__button) {
  border-color: var(--f1-red);
}

:deep(.el-segmented) {
  background: var(--f1-bg-elevated) !important;
}

:deep(.el-segmented .el-segmented__item.is-selected) {
  background: var(--f1-red) !important;
  color: #fff !important;
}

@media (max-width: 1024px) {
  .cockpit-footer {
    flex-direction: column;
  }
  .player-panel {
    min-width: 100%;
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
