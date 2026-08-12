<!--
  League.vue — Fantasy 联盟系统页面
  功能：创建联盟 / 加入联盟 / 查看联盟排行榜
-->
<template>
  <div class="league-page">
    <div class="page-header">
      <h2>Fantasy 联盟</h2>
    </div>

    <!-- 未登录提示 -->
    <el-card v-if="!token" shadow="never" class="block">
      <el-alert title="请先登录后使用联盟功能" type="warning" :closable="false" />
    </el-card>

    <template v-if="token">
      <!-- 创建/加入联盟 -->
      <el-card shadow="never" class="block">
        <template #header><span>创建 / 加入联盟</span></template>
        <el-row :gutter="20">
          <el-col :span="12">
            <h4>创建新联盟</h4>
            <el-input v-model="newLeagueName" placeholder="联盟名称" style="margin-bottom: 8px" />
            <el-button type="primary" @click="createLeague" :loading="creating" :disabled="!newLeagueName">
              创建联盟
            </el-button>
          </el-col>
          <el-col :span="12">
            <h4>加入联盟</h4>
            <el-input v-model="joinLeagueId" placeholder="联盟 ID" style="margin-bottom: 8px" />
            <el-input v-model="joinInviteCode" placeholder="邀请码" style="margin-bottom: 8px" />
            <el-button type="success" @click="joinLeague" :loading="joining" :disabled="!joinLeagueId || !joinInviteCode">
              加入联盟
            </el-button>
          </el-col>
        </el-row>
      </el-card>

      <!-- 我的联盟列表 -->
      <el-card shadow="never" class="block">
        <template #header><span>我的联盟</span></template>
        <el-table :data="leagues" stripe v-loading="loadingLeagues">
          <el-table-column prop="name" label="联盟名称" />
          <el-table-column prop="season" label="赛季" width="80" align="center" />
          <el-table-column prop="member_count" label="成员数" width="80" align="center" />
          <el-table-column label="邀请码" width="120">
            <template #default="{ row }">
              <span v-if="row.is_creator" class="invite-code">{{ row.invite_code }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button size="small" @click="viewLeaderboard(row.id)">排行榜</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 联盟排行榜弹窗 -->
      <el-dialog v-model="showLeaderboard" title="联盟排行榜" width="600px">
        <el-table :data="leagueLeaderboard" stripe v-loading="loadingBoard">
          <el-table-column label="排名" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="rankType(row.rank)" effect="dark" round>{{ row.rank }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="username" label="用户" />
          <el-table-column prop="season_points" label="赛季积分" width="120" align="center" />
          <el-table-column prop="rounds_scored" label="已结算" width="80" align="center" />
        </el-table>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import * as fantasyApi from '@/api/fantasy'
import { ElMessage } from 'element-plus'

const store = useF1Store()
const token = ref(localStorage.getItem('f1_token') || '')
const newLeagueName = ref('')
const joinLeagueId = ref('')
const joinInviteCode = ref('')
const creating = ref(false)
const joining = ref(false)
const leagues = ref([])
const loadingLeagues = ref(false)

const showLeaderboard = ref(false)
const leagueLeaderboard = ref([])
const loadingBoard = ref(false)

const rankType = (pos) => {
  if (pos === 1) return 'danger'
  if (pos === 2) return 'warning'
  if (pos === 3) return 'success'
  return 'info'
}

const loadLeagues = async () => {
  if (!token.value) return
  loadingLeagues.value = true
  try {
    const data = await fantasyApi.getMyLeagues()
    leagues.value = data.leagues || []
  } catch {
    leagues.value = []
  }
  loadingLeagues.value = false
}

const createLeague = async () => {
  creating.value = true
  try {
    const res = await fantasyApi.createLeague(newLeagueName.value, store.currentSeason)
    ElMessage.success(`联盟创建成功！邀请码: ${res.invite_code}`)
    newLeagueName.value = ''
    await loadLeagues()
  } catch { /* 拦截器处理 */ }
  creating.value = false
}

const joinLeague = async () => {
  joining.value = true
  try {
    const res = await fantasyApi.joinLeague(Number(joinLeagueId.value), joinInviteCode.value)
    ElMessage.success(res.message)
    joinLeagueId.value = ''
    joinInviteCode.value = ''
    await loadLeagues()
  } catch { /* 拦截器处理 */ }
  joining.value = false
}

const viewLeaderboard = async (leagueId) => {
  showLeaderboard.value = true
  loadingBoard.value = true
  try {
    const data = await fantasyApi.getLeagueLeaderboard(leagueId)
    leagueLeaderboard.value = data.leaderboard || []
  } catch {
    leagueLeaderboard.value = []
  }
  loadingBoard.value = false
}

onMounted(() => {
  loadLeagues()
})
</script>

<style scoped>
.league-page { padding: 16px; }
.page-header { margin-bottom: 16px; }
.block { margin-bottom: 20px; }
h4 { margin: 0 0 10px; }
.invite-code { font-family: monospace; font-weight: bold; color: #e10600; }
</style>
