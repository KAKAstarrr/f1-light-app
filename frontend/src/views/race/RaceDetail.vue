/**
 * RaceDetail — 分站详情 Tab
 * 排位/正赛结果 + 最快圈 + 轮胎策略
 */
<template>
  <div class="race-detail" v-if="round">
    <!-- 比赛结果 Top10 -->
    <InfoCard title="比赛结果 · Top10" class="block">
      <el-table :data="resultList" v-loading="loading.result" stripe>
        <el-table-column label="名次" width="80" align="center">
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
        <el-table-column prop="grid" label="发车位" width="80" align="center" />
        <el-table-column prop="laps" label="圈数" width="70" align="center" />
        <el-table-column prop="points" label="积分" width="70" align="center" />
        <el-table-column label="完赛状态" min-width="120">
          <template #default="{ row }">
            <span :class="row.status === 'Finished' ? 'status-ok' : 'status-ng'">
              {{ row.status }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </InfoCard>

    <!-- 最快圈排行 -->
    <InfoCard title="最快圈速排行" class="block">
      <el-table :data="fastLapList" v-loading="loading.fastLap" stripe>
        <el-table-column label="排名" width="70" align="center">
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
    </InfoCard>

    <!-- 轮胎策略 -->
    <InfoCard title="轮胎进站策略" class="block">
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
                background: getCompoundColor(s.compound)
              }"
              :title="`${s.compound} · 第${s.start_lap}-${s.end_lap}圈 · ${s.laps}圈`"
            >
              <span class="seg-label">{{ s.laps }}</span>
            </div>
          </div>
        </div>
        <div class="legend">
          <span v-for="c in legendCompounds" :key="c" class="legend-item">
            <i :style="{ background: getCompoundColor(c) }"></i>{{ compoundLabel(c) }}
          </span>
        </div>
      </div>
    </InfoCard>
  </div>

  <EmptyState
    v-else
    icon="🏁"
    title="请选择分站"
    description="在上方筛选栏选择要查看的分站"
  />
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useF1Store } from '@/stores/f1'
import { getRaceResult } from '@/api/race'
import { getFastestLap, getTyreStrategy } from '@/api/telemetry'
import { rankTagType, driverName, getCompoundColor, COMPOUND_LABELS } from '@/utils/f1-constants'
import InfoCard from '@/components/InfoCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps({
  year: { type: Number, default: 2026 },
  round: { type: [Number, String], default: null },
})

const store = useF1Store()

const resultList = ref([])
const fastLapList = ref([])
const tyreList = ref([])
const loading = reactive({ result: false, fastLap: false, tyre: false })

const compoundLabel = (c) => COMPOUND_LABELS[c] || c

const fastLapPercent = (sec) => {
  if (!fastLapList.value.length) return 0
  const fastest = fastLapList.value[0].LapTimeSeconds
  if (!fastest || !sec) return 0
  return Math.max(20, Math.round((fastest / sec) * 100))
}

const totalLaps = () => tyreList.value.reduce((m, d) => Math.max(m, ...d.stints.map(s => s.end_lap)), 1)
const segWidth = (s) => {
  const total = totalLaps()
  return Math.max(4, (s.laps / total) * 100)
}
const legendCompounds = () => {
  const set = new Set()
  tyreList.value.forEach(d => d.stints.forEach(s => set.add(s.compound)))
  return [...set]
}

async function loadAll() {
  if (!props.round) return
  loadResults()
  loadFastLap()
  loadTyre()
}

async function loadResults() {
  if (!props.round) return
  loading.result = true
  try {
    const data = await getRaceResult(props.year, props.round)
    const all = data?.Races?.[0]?.Results || []
    resultList.value = all.filter(r => Number(r.position) <= 10)
  } catch (e) {
    resultList.value = []
  }
  loading.result = false
}

async function loadFastLap() {
  if (!props.round) return
  loading.fastLap = true
  try {
    const data = await getFastestLap(props.year, props.round, 'R')
    fastLapList.value = data?.fastest_lap_ranking || []
  } catch (e) {
    fastLapList.value = []
  }
  loading.fastLap = false
}

async function loadTyre() {
  if (!props.round) return
  loading.tyre = true
  try {
    const data = await getTyreStrategy(props.year, props.round)
    tyreList.value = data?.tyre_strategy || []
  } catch (e) {
    tyreList.value = []
  }
  loading.tyre = false
}

watch(() => [props.year, props.round], () => {
  loadAll()
})

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.race-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.block {
  margin-bottom: 0;
}

.sub {
  display: block;
  font-size: 12px;
  color: var(--f1-text-muted);
}

.status-ok { color: var(--f1-success); }
.status-ng { color: var(--f1-red); }

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
  color: var(--f1-text-primary);
}

.tyre-bar {
  flex: 1;
  display: flex;
  height: 22px;
  background: var(--f1-bg-elevated);
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
  border-right: 1px solid rgba(255, 255, 255, 0.3);
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
  color: var(--f1-text-secondary);
}

.legend-item i {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}
</style>
