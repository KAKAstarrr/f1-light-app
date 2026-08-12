<!--
  TrackMap.vue — 赛道地图分段着色页（模块 B5）
  SVG 渲染赛道轮廓 + Sector 1/2/3 最快车手着色（Purple/Green/Yellow）
-->
<template>
  <div class="track-map-page">
    <div class="filter-bar">
      <el-select v-model="year" style="width: 110px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="`${y}`" :value="y" />
      </el-select>

      <el-select v-model="round" placeholder="选择分站" style="width: 220px" @change="fetchData">
        <el-option
          v-for="r in store.raceList"
          :key="r.round"
          :label="`第${r.round}站 ${r.raceName}`"
          :value="Number(r.round)"
        />
      </el-select>

      <el-select v-model="sessionType" style="width: 130px" @change="fetchData">
        <el-option label="正赛 R" value="R" />
        <el-option label="排位 Q" value="Q" />
        <el-option label="冲刺赛 S" value="S" />
      </el-select>

      <el-button type="primary" @click="fetchData" :loading="loading" :disabled="!round">
        加载赛道数据
      </el-button>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：赛道地图 SVG -->
      <el-col :span="16">
        <el-card shadow="never" class="block">
          <template #header>
            <span>{{ trackData?.circuit_name || '赛道地图' }}</span>
          </template>

          <el-empty v-if="!trackData && !loading" description="选择分站后加载赛道地图" />
          <el-empty v-if="trackData && !trackData.track_points?.length" description="该赛道暂无坐标数据" />

          <div v-if="trackData?.track_points?.length" class="track-svg-container">
            <svg viewBox="0 0 100 100" class="track-svg" preserveAspectRatio="xMidYMid meet">
              <!-- 赛道轮廓 -->
              <polyline
                :points="trackPointsStr"
                fill="none"
                stroke="#c0c0c0"
                stroke-width="3"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
              <!-- 分段着色（每段用不同颜色覆盖） -->
              <polyline
                v-for="(seg, i) in trackSegments"
                :key="i"
                :points="seg.points"
                fill="none"
                :stroke="seg.color"
                stroke-width="4"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
              <!-- 起点/终点标记 -->
              <circle
                v-if="trackData.track_points.length"
                :cx="trackData.track_points[0].x"
                :cy="trackData.track_points[0].y"
                r="1.5"
                fill="#333"
                stroke="#fff"
                stroke-width="0.5"
              />
              <text
                v-if="trackData.track_points.length"
                :x="trackData.track_points[0].x + 2"
                :y="trackData.track_points[0].y + 1"
                font-size="4"
                fill="#333"
              >Start/Finish</text>
            </svg>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：分段信息 -->
      <el-col :span="8">
        <el-card shadow="never" class="block">
          <template #header><span>分段最快（Sector）</span></template>

          <div v-if="trackData?.sectors?.length">
            <div
              v-for="s in trackData.sectors"
              :key="s.sector"
              class="sector-card"
              :class="`sector-${s.color}`"
            >
              <div class="sector-header">
                <span class="sector-name">Sector {{ s.sector }}</span>
                <span class="sector-color-tag" :class="`tag-${s.color}`">
                  {{ s.color === 'purple' ? '紫' : s.color === 'green' ? '绿' : '黄' }}
                </span>
              </div>
              <div class="sector-driver">
                <span class="driver-code">{{ s.fastest_driver || 'N/A' }}</span>
                <span class="driver-time">{{ s.fastest_time_str || '-' }}</span>
              </div>
            </div>

            <div class="overall-fastest" v-if="trackData.overall_fastest_driver">
              全场最快: <strong>{{ trackData.overall_fastest_driver }}</strong>
            </div>
          </div>

          <el-empty v-else description="无分段数据" :image-size="80" />
        </el-card>

        <!-- 颜色说明 -->
        <el-card shadow="never" class="block">
          <template #header><span>颜色说明</span></template>
          <div class="legend">
            <div class="legend-item">
              <span class="legend-color purple"></span>
              <span>Purple — 全场最快</span>
            </div>
            <div class="legend-item">
              <span class="legend-color green"></span>
              <span>Green — 个人最快</span>
            </div>
            <div class="legend-item">
              <span class="legend-color yellow"></span>
              <span>Yellow — 非个人最快</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { useYearSelection } from '@/composables/useYearSelection'
import { getTrackMap } from '@/api/telemetry'

const store = useF1Store()
const { yearOptions, year, syncYearToStore } = useYearSelection()

const round = ref(null)
const sessionType = ref('R')
const loading = ref(false)
const trackData = ref(null)

const trackPointsStr = computed(() => {
  if (!trackData.value?.track_points) return ''
  return trackData.value.track_points.map(p => `${p.x},${p.y}`).join(' ')
})

const trackSegments = computed(() => {
  if (!trackData.value?.track_points?.length) return []
  const pts = trackData.value.track_points
  const total = pts.length
  const perSeg = Math.ceil(total / 3)

  const colorMap = { purple: '#a020f0', green: '#00aa00', yellow: '#ffaa00' }
  const sectors = trackData.value.sectors || []

  const segments = []
  for (let i = 0; i < 3; i++) {
    const start = i * perSeg
    const end = i === 2 ? total : (i + 1) * perSeg + 1 // +1 连接点
    const segPts = pts.slice(start, end)
    if (segPts.length > 1) {
      const sectorInfo = sectors.find(s => s.sector === i + 1)
      const color = sectorInfo ? colorMap[sectorInfo.color] || '#c0c0c0' : '#c0c0c0'
      segments.push({
        points: segPts.map(p => `${p.x},${p.y}`).join(' '),
        color,
      })
    }
  }
  return segments
})

const onYearChange = async () => {
  syncYearToStore()
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
  }
}

const fetchData = async () => {
  if (!round.value) return
  loading.value = true
  try {
    const res = await getTrackMap(year.value, round.value, sessionType.value)
    if (res.code === 200) {
      trackData.value = res
    } else {
      trackData.value = null
    }
  } catch {
    trackData.value = null
  }
  loading.value = false
}

onMounted(async () => {
  await store.fetchRaceList(year.value)
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    await fetchData()
  }
})
</script>

<style scoped>
.track-map-page { padding: 16px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.block { margin-bottom: 20px; }
.track-svg-container { display: flex; justify-content: center; }
.track-svg { width: 100%; max-width: 500px; height: 400px; background: #f8f8f8; border-radius: 8px; }

.sector-card {
  padding: 10px; margin-bottom: 10px; border-radius: 6px;
  border-left: 4px solid #ccc; background: #fafafa;
}
.sector-card.sector-purple { border-left-color: #a020f0; }
.sector-card.sector-green { border-left-color: #00aa00; }
.sector-card.sector-yellow { border-left-color: #ffaa00; }

.sector-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.sector-name { font-weight: bold; font-size: 14px; }
.sector-color-tag {
  padding: 2px 8px; border-radius: 4px; font-size: 11px; color: #fff;
}
.tag-purple { background: #a020f0; }
.tag-green { background: #00aa00; }
.tag-yellow { background: #ffaa00; }

.sector-driver { display: flex; justify-content: space-between; align-items: center; }
.driver-code { font-size: 18px; font-weight: bold; }
.driver-time { font-size: 14px; color: #606266; }

.overall-fastest {
  margin-top: 12px; padding: 8px; text-align: center;
  background: #f0f0f0; border-radius: 6px; font-size: 14px;
}

.legend { display: flex; flex-direction: column; gap: 10px; }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.legend-color { width: 20px; height: 4px; border-radius: 2px; }
.legend-color.purple { background: #a020f0; }
.legend-color.green { background: #00aa00; }
.legend-color.yellow { background: #ffaa00; }
</style>
