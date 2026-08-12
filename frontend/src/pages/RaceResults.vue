<template>
  <div class="race-results">
    <div class="page-header">
      <h2>分站结果</h2>
      <div class="selectors">
        <!-- 2A.6 年份 + 分站选择 -->
        <el-select v-model="year" style="width: 120px" @change="onYearChange">
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
      </div>
    </div>

    <!-- A2：比赛结果 Top10 -->
    <el-card shadow="never" class="block">
      <template #header>
        <span>比赛结果 · Top10</span>
      </template>
      <el-table :data="resultList" v-loading="loading.result" stripe>
        <el-table-column label="名次" width="90" align="center">
          <!-- 2A.5 排名徽标：Top3 高亮 -->
          <template #default="{ row }">
            <el-tag :type="rankTagType(row.position)" effect="dark" round>
              {{ row.position }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="车手" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.Driver?.code || driverName(row.Driver) }}</strong>
            <span class="sub">{{ driverName(row.Driver) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="车队" min-width="140">
          <template #default="{ row }">{{ row.Constructor?.name }}</template>
        </el-table-column>
        <el-table-column prop="grid" label="发车位" width="90" align="center" />
        <el-table-column prop="laps" label="圈数" width="80" align="center" />
        <el-table-column prop="points" label="积分" width="80" align="center" />
        <el-table-column label="完赛状态" min-width="140">
          <template #default="{ row }">
            <span :class="row.status === 'Finished' ? 'status-ok' : 'status-ng'">
              {{ row.status }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- A4-1：最快圈排行 -->
    <el-card shadow="never" class="block">
      <template #header>
        <span>最快圈速排行</span>
      </template>
      <el-table :data="fastLapList" v-loading="loading.fastLap" stripe>
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="rankTagType(row.Rank)" effect="dark" round>{{ row.Rank }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="Driver" label="车手" width="100" />
        <el-table-column prop="LapTimeStr" label="最快圈速" width="140" />
        <el-table-column label="用时(秒)">
          <template #default="{ row }">
            <el-progress
              :percentage="fastLapPercent(row.LapTimeSeconds)"
              :show-text="false"
              :stroke-width="10"
              color="#e10600"
            />
            <span class="sub">{{ row.LapTimeSeconds }}s</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- A4-2：轮胎策略条带图 -->
    <el-card shadow="never" class="block">
      <template #header>
        <span>轮胎进站策略</span>
      </template>
      <div v-loading="loading.tyre" class="tyre-chart">
        <div v-for="d in tyreList" :key="d.driver" class="tyre-row">
          <span class="tyre-driver">{{ d.driver }}</span>
          <div class="tyre-bar">
            <div
              v-for="s in d.stints"
              :key="s.stint"
              class="tyre-seg"
              :style="{
                width: segWidth(s) + '%',
                background: compoundColor(s.compound)
              }"
              :title="`${s.compound} · 第${s.start_lap}-${s.end_lap}圈 · ${s.laps}圈`"
            >
              <span class="seg-label">{{ s.laps }}</span>
            </div>
          </div>
        </div>
        <!-- 图例 -->
        <div class="legend">
          <span v-for="c in legendCompounds" :key="c" class="legend-item">
            <i :style="{ background: compoundColor(c) }"></i>{{ compoundLabel(c) }}
          </span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'
import { getRaceResult } from '@/api/race'
import { getFastestLap, getTyreStrategy } from '@/api/telemetry'

const route = useRoute()
const router = useRouter()
const store = useF1Store()

const yearOptions = [2026, 2025, 2024, 2023]
const year = ref(Number(route.params.year) || store.currentSeason)
const round = ref(route.params.round ? Number(route.params.round) : null)

const resultList = ref([])
const fastLapList = ref([])
const tyreList = ref([])

const loading = reactive({ result: false, fastLap: false, tyre: false })

// 轮胎配色（F1 官方惯例：软红/中黄/硬白/半雨绿/全雨蓝）
const compoundColorMap = {
  SOFT: '#f44336',
  MEDIUM: '#ffd600',
  HARD: '#bdbdbd',
  'INTERMEDIATE': '#4caf50',
  WET: '#2196f3',
  UNKNOWN: '#9e9e9e'
}
const compoundColor = (c) => compoundColorMap[c] || '#9e9e9e'
const compoundLabel = (c) => ({ SOFT: '软胎', MEDIUM: '中性', HARD: '硬胎', INTERMEDIATE: '半雨', WET: '全雨' }[c] || c)

const driverName = (d) => (d ? `${d.givenName || ''} ${d.familyName || ''}`.trim() : '')
const rankTagType = (pos) => {
  const p = Number(pos)
  if (p === 1) return 'danger' // 红
  if (p === 2) return 'warning' // 黄
  if (p === 3) return 'success' // 绿
  return 'info'
}

// 计算最快圈进度百分比（相对最快者）
const fastLapPercent = (sec) => {
  if (!fastLapList.value.length) return 0
  const fastest = fastLapList.value[0].LapTimeSeconds
  if (!fastest || !sec) return 0
  // 越慢百分比越低，最快=100%
  return Math.max(20, Math.round((fastest / sec) * 100))
}

// 轮胎分段宽度：按该站总圈数占比
const totalLaps = () => tyreList.value.reduce((m, d) => Math.max(m, ...d.stints.map((s) => s.end_lap)), 1)
const segWidth = (s) => {
  const total = totalLaps()
  return Math.max(4, (s.laps / total) * 100)
}
const legendCompounds = () => {
  const set = new Set()
  tyreList.value.forEach((d) => d.stints.forEach((s) => set.add(s.compound)))
  return [...set]
}

// ---- 数据加载 ----
const loadResults = async () => {
  if (!round.value) return
  loading.result = true
  try {
    const data = await getRaceResult(year.value, round.value)
    // Ergast: Races[0].Results
    const all = data?.Races?.[0]?.Results || []
    // 取 Top10
    resultList.value = all.filter((r) => Number(r.position) <= 10)
  } catch (e) {
    resultList.value = []
  }
  loading.result = false
}

const loadFastLap = async () => {
  if (!round.value) return
  loading.fastLap = true
  try {
    const data = await getFastestLap(year.value, round.value, 'R')
    // 拦截器已保证 code===200，这里直接取业务字段
    fastLapList.value = data?.fastest_lap_ranking || []
  } catch (e) {
    fastLapList.value = []
  }
  loading.fastLap = false
}

const loadTyre = async () => {
  if (!round.value) return
  loading.tyre = true
  try {
    const data = await getTyreStrategy(year.value, round.value)
    tyreList.value = data?.tyre_strategy || []
  } catch (e) {
    tyreList.value = []
  }
  loading.tyre = false
}

const loadAll = () => {
  loadResults()
  loadFastLap()
  loadTyre()
}

// ---- 事件 ----
const onYearChange = async (val) => {
  store.setSeason(val)
  await store.fetchRaceList(val)
  // 年份切换后重置分站为第一站
  if (store.raceList.length) {
    round.value = Number(store.raceList[0].round)
    onRoundChange(round.value)
  }
}

const onRoundChange = (val) => {
  store.setSelectedRound(val)
  // 同步到 URL（动态路由）
  router.replace(`/results/${year.value}/${val}`)
  loadAll()
}

// 监听路由参数变化（侧边栏/浏览器前进后退）
watch(
  () => [route.params.year, route.params.round],
  ([y, r]) => {
    if (y) year.value = Number(y)
    if (r) round.value = Number(r)
    if (year.value && round.value) loadAll()
  }
)

onMounted(async () => {
  // 先确保赛程列表已加载（用于分站下拉）
  if (!store.raceList.length) await store.fetchRaceList(year.value)
  if (!round.value && store.raceList.length) {
    round.value = Number(store.raceList[0].round)
  }
  if (round.value) loadAll()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.selectors {
  display: flex;
  gap: 12px;
}
.block {
  margin-bottom: 20px;
}
.sub {
  display: block;
  font-size: 12px;
  color: #999;
}
.status-ok {
  color: #67c23a;
}
.status-ng {
  color: #f56c6c;
}
/* 轮胎策略条带 */
.tyre-chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tyre-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tyre-driver {
  width: 50px;
  font-weight: 600;
  font-size: 13px;
  text-align: right;
}
.tyre-bar {
  flex: 1;
  display: flex;
  height: 22px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}
.tyre-seg {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  font-size: 11px;
  font-weight: 600;
  border-right: 1px solid rgba(255, 255, 255, 0.5);
}
.seg-label {
  text-shadow: 0 0 2px rgba(255, 255, 255, 0.6);
}
.legend {
  margin-top: 12px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}
.legend-item i {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}
</style>
