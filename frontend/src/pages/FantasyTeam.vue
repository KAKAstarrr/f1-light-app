<template>
  <div class="fantasy-page">
    <!-- 锁定分站栏 -->
    <div class="race-lock-bar" v-if="upcomingRace">
      <span class="lock-icon">🔒</span>
      <span class="lock-label">Fantasy 目标</span>
      <span class="race-name">{{ upcomingRace.raceName }}</span>
      <span class="race-date">{{ upcomingRace.date }}</span>
      <el-tag type="success" size="small">即将开始</el-tag>
    </div>

    <!-- 无即将开始的分站 -->
    <el-card v-if="!upcomingRace && !loadingRaces" shadow="never" class="block">
      <el-empty description="暂无即将开始的分站">
        <template #description>
          <p>当前赛季暂无即将开始的分站</p>
          <p style="font-size: 13px; color: #909399;">下方可查看本赛季排行榜</p>
        </template>
      </el-empty>
    </el-card>

    <!-- 未登录时显示登录/注册 -->
    <el-card v-if="upcomingRace && !token" shadow="never" class="block">
      <el-alert title="请先登录或注册后使用 Fantasy 功能" type="warning" :closable="false" />
      <div class="auth-form">
        <el-tabs v-model="authTab">
          <el-tab-pane label="登录" name="login">
            <el-form label-width="80px" @submit.prevent="doLogin">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="用户名或邮箱" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" show-password />
              </el-form-item>
              <el-button type="primary" @click="doLogin" :loading="authLoading">登录</el-button>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="注册" name="register">
            <el-form label-width="80px" @submit.prevent="doRegister">
              <el-form-item label="用户名">
                <el-input v-model="regForm.username" placeholder="至少3位" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="regForm.email" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="regForm.password" type="password" show-password placeholder="至少6位" />
              </el-form-item>
              <el-button type="primary" @click="doRegister" :loading="authLoading">注册</el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>

    <!-- 已登录 + 有 upcoming：阵容管理 -->
    <template v-if="upcomingRace && token">
      <el-card shadow="never" class="block">
        <template #header>
          <div class="card-header">
            <span>我的阵容</span>
            <div class="budget-info">
              <span>预算: </span>
              <strong :class="{ over: totalCost > 100 }">¥{{ totalCost.toFixed(1) }}M</strong>
              <span> / ¥100M</span>
              <el-tag :type="totalCost <= 100 ? 'success' : 'danger'" size="small">
                {{ totalCost <= 100 ? '预算内' : '超标!' }}
              </el-tag>
            </div>
          </div>
        </template>

        <!-- 车手选择 -->
        <h4>选择车手（最多5个）</h4>
        <div class="driver-grid">
          <div
            v-for="d in driverList"
            :key="d.code"
            class="driver-card"
            :class="{ selected: isDriverSelected(d.code) }"
            @click="toggleDriver(d)"
          >
            <div class="d-code">{{ d.code }}</div>
            <div class="d-name">{{ d.name }}</div>
            <div class="d-team">{{ d.constructor }}</div>
            <div class="d-price">¥{{ d.price.toFixed(1) }}M</div>
            <el-tag v-if="isCaptain(d.code)" type="danger" size="small">队长 x2</el-tag>
          </div>
        </div>

        <!-- 队长选择 -->
        <div v-if="selectedDrivers.length" class="captain-select">
          <span>设置队长（x2 Boost）：</span>
          <el-select v-model="captainCode" placeholder="选择队长" style="width: 160px">
            <el-option
              v-for="d in selectedDrivers"
              :key="d.code"
              :label="d.code"
              :value="d.code"
            />
          </el-select>
        </div>

        <!-- 车队选择 -->
        <h4>选择车队（最多2个）</h4>
        <div class="driver-grid">
          <div
            v-for="c in constructorList"
            :key="c.ref"
            class="driver-card"
            :class="{ selected: isConstructorSelected(c.ref) }"
            @click="toggleConstructor(c)"
          >
            <div class="d-name">{{ c.name }}</div>
            <div class="d-price">¥{{ c.price.toFixed(1) }}M</div>
          </div>
        </div>

        <!-- 芯片选择 -->
        <h4>芯片</h4>
        <div class="chip-section">
          <el-select v-model="chip" style="width: 220px">
            <el-option label="无芯片" value="none" />
            <el-option label="Limitless（无视预算）" value="limitless" :disabled="chipStatus.limitless?.remaining <= 0" />
            <el-option label="Wildcard（无限转会）" value="wildcard" :disabled="chipStatus.wildcard?.remaining <= 0" />
            <el-option label="No Negative（不扣退赛分）" value="no_negative" :disabled="chipStatus.no_negative?.remaining <= 0" />
          </el-select>
          <div class="chip-status">
            <el-tag v-if="chipStatus.limitless" size="small" :type="chipStatus.limitless.remaining > 0 ? 'success' : 'info'">
              Limitless: {{ chipStatus.limitless.remaining }}/{{ chipStatus.limitless.max }}
            </el-tag>
            <el-tag v-if="chipStatus.wildcard" size="small" :type="chipStatus.wildcard.remaining > 0 ? 'success' : 'info'">
              Wildcard: {{ chipStatus.wildcard.remaining }}/{{ chipStatus.wildcard.max }}
            </el-tag>
            <el-tag v-if="chipStatus.no_negative" size="small" :type="chipStatus.no_negative.remaining > 0 ? 'success' : 'info'">
              No Negative: {{ chipStatus.no_negative.remaining }}/{{ chipStatus.no_negative.max }}
            </el-tag>
          </div>
        </div>

        <!-- 转会信息 -->
        <div class="transfer-info">
          <span>本站转会次数: {{ transfersUsed }} / 2（免费）</span>
          <el-tag v-if="transfersUsed >= 2 && chip !== 'wildcard'" type="warning" size="small">
            超出免费次数将扣分
          </el-tag>
        </div>

        <div class="save-bar">
          <el-button type="primary" @click="saveTeam" :loading="saving" :disabled="totalCost > 100 && chip !== 'limitless'">
            保存阵容
          </el-button>
          <el-button @click="loadExisting">读取已有阵容</el-button>
          <el-button @click="loadHistory">查看历史记录</el-button>
        </div>
      </el-card>

      <!-- 历史阵容弹窗 -->
      <el-dialog v-model="showHistory" title="历史阵容记录" width="700px">
        <div v-if="historyData">
          <div class="history-summary">
            <span>赛季: {{ historyData.season }}</span>
            <span>参与分站: {{ historyData.total_rounds }}</span>
            <span>总积分: {{ historyData.total_points }}</span>
          </div>
          <el-table :data="historyData.history" stripe size="small">
            <el-table-column prop="round" label="分站" width="60" align="center" />
            <el-table-column label="车手" min-width="200">
              <template #default="{ row }">
                <span v-for="(d, i) in row.drivers" :key="i">
                  {{ d.code }}{{ d.is_captain ? '(C)' : '' }}{{ i < row.drivers.length - 1 ? ', ' : '' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="total_cost" label="花费" width="80" align="center">
              <template #default="{ row }">¥{{ row.total_cost?.toFixed(1) }}M</template>
            </el-table-column>
            <el-table-column prop="total_points" label="积分" width="80" align="center" />
            <el-table-column label="芯片" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.chip_used !== 'none'" size="small">{{ row.chip_used }}</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_scored ? 'success' : 'info'" size="small">
                  {{ row.is_scored ? '已结算' : '未结算' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-dialog>
    </template>

    <!-- 排行榜（始终显示） -->
    <el-card shadow="never" class="block">
      <template #header><span>赛季排行榜</span></template>
      <el-table :data="leaderboard" stripe v-loading="loadingBoard">
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="rankType(row.rank)" effect="dark" round>{{ row.rank }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户" />
        <el-table-column prop="season_points" label="赛季积分" width="120" align="center" />
        <el-table-column prop="rounds_scored" label="已结算分站" width="120" align="center" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { useNextRace } from '@/composables/useNextRace'
import { getDriverStandings, getConstructorStandings } from '@/api/driver'
import * as authApi from '@/api/auth'
import * as fantasyApi from '@/api/fantasy'
import { ElMessage } from 'element-plus'
import { rankTagType } from '@/utils/f1-constants'

const store = useF1Store()
const { upcomingRace } = useNextRace()

const loadingRaces = ref(true)

// 从 upcomingRace 派生 year 和 round（与 Prediction 完全独立）
const year = computed(() => Number(upcomingRace.value?.season) || store.currentSeason)
const round = computed(() => Number(upcomingRace.value?.round) || null)

// 鉴权
const token = ref(localStorage.getItem('f1_token') || '')
const authTab = ref('login')
const authLoading = ref(false)
const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', email: '', password: '' })

const doLogin = async () => {
  authLoading.value = true
  try {
    const res = await authApi.login(loginForm.value)
    token.value = res.access_token
    localStorage.setItem('f1_token', res.access_token)
    ElMessage.success('登录成功')
    loadExisting()
  } catch { /* 拦截器已弹错误 */ }
  authLoading.value = false
}

const doRegister = async () => {
  authLoading.value = true
  try {
    const res = await authApi.register(regForm.value)
    token.value = res.access_token
    localStorage.setItem('f1_token', res.access_token)
    ElMessage.success('注册成功')
    loadExisting()
  } catch {}
  authLoading.value = false
}

// 车手/车队列表
const driverList = ref([])
const constructorList = ref([])
const selectedDrivers = ref([])
const selectedConstructors = ref([])
const captainCode = ref('')
const chip = ref('none')
const saving = ref(false)
const leaderboard = ref([])
const loadingBoard = ref(false)
const chipStatus = ref({})
const transfersUsed = ref(0)
const historyData = ref(null)
const showHistory = ref(false)

const totalCost = computed(() => {
  return [...selectedDrivers.value, ...selectedConstructors.value]
    .reduce((sum, d) => sum + (d.price || 0), 0)
})

const isDriverSelected = (code) => selectedDrivers.value.some(d => d.code === code)
const isCaptain = (code) => captainCode.value === code
const isConstructorSelected = (ref) => selectedConstructors.value.some(c => c.ref === ref)

const toggleDriver = (d) => {
  if (isDriverSelected(d.code)) {
    selectedDrivers.value = selectedDrivers.value.filter(x => x.code !== d.code)
    if (captainCode.value === d.code) captainCode.value = ''
  } else {
    if (selectedDrivers.value.length >= 5) {
      ElMessage.warning('最多选 5 个车手')
      return
    }
    selectedDrivers.value.push({ code: d.code, name: d.name, price: d.price })
  }
}

const toggleConstructor = (c) => {
  if (isConstructorSelected(c.ref)) {
    selectedConstructors.value = selectedConstructors.value.filter(x => x.ref !== c.ref)
  } else {
    if (selectedConstructors.value.length >= 2) {
      ElMessage.warning('最多选 2 个车队')
      return
    }
    selectedConstructors.value.push({ ref: c.ref, name: c.name, price: c.price })
  }
}

const rankType = rankTagType

const loadDriverList = async () => {
  try {
    const standings = await getDriverStandings()
    const drivers = standings?.StandingsLists?.[0]?.DriverStandings || []
    driverList.value = drivers.map((d) => {
      const code = d.Driver?.code || ''
      const name = `${d.Driver?.givenName || ''} ${d.Driver?.familyName || ''}`
      const constructor = d.Constructors?.[0]?.name || 'Unknown'
      const pos = Number(d.position)
      let price = 15
      if (pos <= 3) price = 30
      else if (pos <= 5) price = 25
      else if (pos <= 10) price = 20
      return { code, name, constructor, price }
    })
  } catch {
    driverList.value = []
  }
}

const loadConstructorList = async () => {
  try {
    const data = await getConstructorStandings()
    const list = data?.StandingsLists?.[0]?.ConstructorStandings || []
    constructorList.value = list.map((c) => {
      const pos = Number(c.position)
      let price = 15
      if (pos <= 2) price = 25
      else if (pos <= 4) price = 20
      else if (pos <= 6) price = 15
      return {
        ref: c.Constructor?.constructorId || '',
        name: c.Constructor?.name || 'Unknown',
        price
      }
    })
  } catch {
    constructorList.value = []
  }
}

const saveTeam = async () => {
  if (!round.value) return
  saving.value = true
  try {
    await fantasyApi.saveFantasyTeam({
      season: year.value,
      round: round.value,
      drivers: selectedDrivers.value.map(d => ({
        driver_code: d.code,
        is_captain: d.code === captainCode.value,
        price: d.price
      })),
      constructors: selectedConstructors.value.map(c => ({
        constructor_ref: c.ref,
        price: c.price
      })),
      chip: chip.value
    })
    ElMessage.success('阵容保存成功')
  } catch {}
  saving.value = false
}

const loadExisting = async () => {
  if (!round.value || !token.value) return
  try {
    const data = await fantasyApi.getMyTeam(year.value, round.value)
    selectedDrivers.value = (data.drivers || []).map(d => ({
      code: d.code, name: d.code, price: d.price
    }))
    selectedConstructors.value = (data.constructors || []).map(c => ({
      ref: c.ref, name: c.ref, price: c.price
    }))
    chip.value = data.chip_used || 'none'
    const cap = (data.drivers || []).find(d => d.is_captain)
    captainCode.value = cap?.code || ''
  } catch {
    // 404 = 还没建阵容，正常情况
  }
}

const loadLeaderboard = async () => {
  loadingBoard.value = true
  try {
    const data = await fantasyApi.getLeaderboard(year.value)
    leaderboard.value = data.leaderboard || []
  } catch {
    leaderboard.value = []
  }
  loadingBoard.value = false
}

const loadChipStatus = async () => {
  if (!token.value) return
  try {
    const data = await fantasyApi.getChipStatus(year.value)
    chipStatus.value = {
      limitless: { used: data.limitless?.used || 0, max: data.limitless?.max || 2, remaining: (data.limitless?.max || 2) - (data.limitless?.used || 0) },
      wildcard: { used: data.wildcard?.used || 0, max: data.wildcard?.max || 2, remaining: (data.wildcard?.max || 2) - (data.wildcard?.used || 0) },
      no_negative: { used: data.no_negative?.used || 0, max: data.no_negative?.max || 1, remaining: (data.no_negative?.max || 1) - (data.no_negative?.used || 0) },
    }
  } catch {
    chipStatus.value = {}
  }
}

const loadHistory = async () => {
  try {
    const data = await fantasyApi.getHistory(year.value)
    historyData.value = data
    showHistory.value = true
  } catch { /* 拦截器处理 */ }
}

onMounted(async () => {
  await store.fetchRaceList(store.currentSeason)
  loadingRaces.value = false
  await loadDriverList()
  await loadConstructorList()
  // 排行榜始终加载（即使无 upcoming）
  loadLeaderboard()
  if (upcomingRace.value && token.value) {
    loadExisting()
    loadChipStatus()
  }
})
</script>

<style scoped>
.fantasy-page { padding: 16px; }
.race-lock-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; margin-bottom: 16px;
  background: #f0f9eb; border: 1px solid #e1f3d8; border-radius: 8px;
}
.lock-icon { font-size: 18px; }
.lock-label { font-size: 14px; color: #67c23a; font-weight: 600; }
.race-name { font-size: 18px; font-weight: bold; }
.race-date { font-size: 14px; color: #909399; }
.block { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.budget-info { display: flex; align-items: center; gap: 6px; }
.budget-info .over { color: #f56c6c; }
.auth-form { margin-top: 16px; }
.driver-grid { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.driver-card {
  width: 140px; padding: 10px; border: 2px solid #ddd; border-radius: 8px;
  cursor: pointer; text-align: center; transition: all 0.2s;
}
.driver-card:hover { border-color: #409eff; transform: translateY(-2px); }
.driver-card.selected { border-color: #e10600; background: #fff5f5; }
.d-code { font-size: 18px; font-weight: bold; }
.d-name { font-size: 12px; color: #666; }
.d-team { font-size: 11px; color: #999; }
.d-price { font-size: 14px; color: #e10600; font-weight: bold; margin: 4px 0; }
.captain-select { margin: 12px 0; }
.save-bar { margin-top: 16px; display: flex; gap: 10px; }
h4 { margin: 16px 0 8px; }
.chip-section { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.chip-status { display: flex; gap: 6px; flex-wrap: wrap; }
.transfer-info { margin: 10px 0; font-size: 13px; color: #606266; display: flex; align-items: center; gap: 8px; }
.history-summary { display: flex; gap: 24px; margin-bottom: 16px; font-size: 14px; }
</style>
