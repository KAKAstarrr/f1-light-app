<template>
  <div class="vote-page">
    <!-- 锁定分站栏（进行中） -->
    <div class="race-lock-bar" v-if="ongoingRace">
      <span class="lock-icon">🔴</span>
      <span class="lock-label">投票对象</span>
      <span class="race-name">{{ ongoingRace.raceName }}</span>
      <el-tag type="danger" size="small">进行中</el-tag>
    </div>

    <!-- 无进行中的比赛 -->
    <el-alert
      v-if="!ongoingRace && !loadingRaces"
      title="当前无进行中的比赛"
      type="info"
      :closable="false"
      show-icon
    >
      <template #default>
        下方可查看上一场最佳车手投票结果
      </template>
    </el-alert>

    <!-- 未登录 + 有进行中比赛 -->
    <el-card v-if="!token && ongoingRace" shadow="never" class="block">
      <el-alert title="请先登录后投票" type="warning" :closable="false" />
      <p style="margin-top: 8px;">登录后可以为你心中的最佳车手投票，每人每站只能投一次。</p>
    </el-card>

    <!-- 已登录 + 有进行中比赛：投票区 -->
    <template v-if="token && ongoingRace">
      <el-card shadow="never" class="block">
        <template #header><span>投票给最佳车手</span></template>
        <div class="vote-form">
          <el-select v-model="selectedDriver" placeholder="选择车手" style="width: 300px">
            <el-option
              v-for="d in driverList"
              :key="d.code"
              :label="`${d.code} - ${d.name}`"
              :value="d.code"
            />
          </el-select>
          <el-button type="primary" @click="submitVote" :loading="voting" :disabled="!selectedDriver">
            提交投票
          </el-button>
        </div>
      </el-card>

      <!-- 本场投票结果 -->
      <el-card shadow="never" class="block">
        <template #header>
          <div class="card-header">
            <span>本场投票结果统计</span>
            <el-tag size="small">{{ totalVotes }} 票</el-tag>
          </div>
        </template>
        <div v-loading="loadingResults" class="results-container">
          <div v-for="r in voteResults" :key="r.driver_code" class="result-row">
            <span class="r-code">{{ r.driver_code }}</span>
            <div class="r-bar-wrap">
              <div class="r-bar" :style="{ width: r.percentage + '%', background: barColor(r.percentage) }">
                <span class="r-pct">{{ r.percentage }}%</span>
              </div>
            </div>
            <span class="r-votes">{{ r.votes }} 票</span>
          </div>
          <el-empty v-if="!loadingResults && !voteResults.length" description="暂无投票数据" />
        </div>
      </el-card>
    </template>

    <!-- 上一场最佳车手投票结果 -->
    <el-card v-if="lastCompletedRace" shadow="never" class="block">
      <template #header>
        <div class="card-header">
          <span>上一场最佳车手投票结果 — {{ lastCompletedRace.raceName }}</span>
          <el-tag size="small" type="info">{{ lastCompletedRace.date }}</el-tag>
        </div>
      </template>
      <div v-loading="loadingLastResults" class="results-container">
        <div v-for="r in lastVoteResults" :key="r.driver_code" class="result-row">
          <span class="r-code" :class="{ winner: r.driver_code === lastWinner }">{{ r.driver_code }}</span>
          <div class="r-bar-wrap">
            <div class="r-bar" :style="{ width: r.percentage + '%', background: barColor(r.percentage) }">
              <span class="r-pct">{{ r.percentage }}%</span>
            </div>
          </div>
          <span class="r-votes">{{ r.votes }} 票</span>
        </div>
        <el-empty v-if="!loadingLastResults && !lastVoteResults.length" description="暂无上一场投票数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { useNextRace } from '@/composables/useNextRace'
import { getDriverStandings } from '@/api/driver'
import * as voteApi from '@/api/vote'
import { ElMessage } from 'element-plus'

const store = useF1Store()
const { ongoingRace, lastCompletedRace } = useNextRace()

const loadingRaces = ref(true)
const token = ref(localStorage.getItem('f1_token') || '')
const selectedDriver = ref('')
const voting = ref(false)
const loadingResults = ref(false)
const loadingLastResults = ref(false)
const driverList = ref([])
const voteResults = ref([])
const lastVoteResults = ref([])
const totalVotes = ref(0)

// 从 ongoingRace 派生
const voteYear = computed(() => Number(ongoingRace.value?.season) || store.currentSeason)
const voteRound = computed(() => Number(ongoingRace.value?.round) || null)

// 从 lastCompletedRace 派生
const lastYear = computed(() => Number(lastCompletedRace.value?.season) || null)
const lastRound = computed(() => Number(lastCompletedRace.value?.round) || null)

// 上一场获胜车手（得票最多）
const lastWinner = computed(() => {
  if (!lastVoteResults.value.length) return null
  return lastVoteResults.value.reduce((max, r) => r.votes > max.votes ? r : max).driver_code
})

const barColor = (pct) => {
  if (pct >= 50) return '#e10600'
  if (pct >= 25) return '#ff9800'
  return '#409eff'
}

const submitVote = async () => {
  if (!voteRound.value) return
  voting.value = true
  try {
    await voteApi.castVote({
      season: voteYear.value,
      round: voteRound.value,
      driver_code: selectedDriver.value
    })
    ElMessage.success('投票成功！')
    loadResults()
  } catch {}
  voting.value = false
}

const loadResults = async () => {
  if (!voteRound.value) return
  loadingResults.value = true
  try {
    const data = await voteApi.getVoteResults(voteYear.value, voteRound.value)
    voteResults.value = data.results || []
    totalVotes.value = data.total_votes || 0
  } catch {
    voteResults.value = []
  }
  loadingResults.value = false
}

const loadLastResults = async () => {
  if (!lastRound.value) return
  loadingLastResults.value = true
  try {
    const data = await voteApi.getVoteResults(lastYear.value, lastRound.value)
    lastVoteResults.value = data.results || []
  } catch {
    lastVoteResults.value = []
  }
  loadingLastResults.value = false
}

const loadDrivers = async () => {
  try {
    const data = await getDriverStandings()
    const list = data?.StandingsLists?.[0]?.DriverStandings || []
    driverList.value = list.map(d => ({
      code: d.Driver?.code || '',
      name: `${d.Driver?.givenName || ''} ${d.Driver?.familyName || ''}`
    }))
  } catch {
    driverList.value = []
  }
}

onMounted(async () => {
  await store.fetchRaceList(store.currentSeason)
  loadingRaces.value = false
  await loadDrivers()
  if (ongoingRace.value) {
    loadResults()
  }
  if (lastCompletedRace.value) {
    loadLastResults()
  }
})
</script>

<style scoped>
.vote-page { padding: 16px; }
.race-lock-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; margin-bottom: 16px;
  background: #fef0f0; border: 1px solid #fde2e2; border-radius: 8px;
}
.lock-icon { font-size: 18px; }
.lock-label { font-size: 14px; color: #f56c6c; font-weight: 600; }
.race-name { font-size: 18px; font-weight: bold; }
.block { margin-bottom: 20px; }
.vote-form { display: flex; gap: 12px; align-items: center; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.results-container { display: flex; flex-direction: column; gap: 10px; }
.result-row { display: flex; align-items: center; gap: 12px; }
.r-code { width: 60px; font-weight: bold; font-size: 16px; }
.r-code.winner { color: #e10600; }
.r-bar-wrap { flex: 1; height: 30px; background: #f5f5f5; border-radius: 15px; overflow: hidden; }
.r-bar { height: 100%; display: flex; align-items: center; padding-left: 10px; color: #fff; font-size: 12px; font-weight: bold; border-radius: 15px; transition: width 0.3s; }
.r-pct { text-shadow: 0 0 3px rgba(0,0,0,0.3); }
.r-votes { width: 60px; font-size: 13px; color: #666; }
</style>
