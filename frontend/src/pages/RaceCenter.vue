/**
 * RaceCenter — 赛事数据中心主页
 * 筛选栏 + Tab 切换 + 侧边栏
 */
<template>
  <div class="race-center">
    <FilterBar
      v-model:modelYear="year"
      v-model:modelRound="round"
      :showDrivers="false"
      :showJump="true"
      @load="onLoad"
    />

    <div class="center-body">
      <div class="center-main">
        <el-tabs v-model="activeTab" @tab-change="onTabChange" class="race-tabs">
          <el-tab-pane label="赛程总览" name="overview">
            <RaceOverview v-if="activeTab === 'overview'" :key="'ov' + tabKey" :year="year" :round="round" />
          </el-tab-pane>
          <el-tab-pane label="分站详情" name="detail">
            <RaceDetail v-if="activeTab === 'detail'" :key="'dt' + tabKey" :year="year" :round="round" />
          </el-tab-pane>
          <el-tab-pane label="实时积分" name="standings">
            <StandingsLive v-if="activeTab === 'standings'" :key="'st' + tabKey" />
          </el-tab-pane>
          <el-tab-pane label="历史对比" name="history">
            <HistoryCompare v-if="activeTab === 'history'" :key="'hi' + tabKey" :year="year" :round="round" />
          </el-tab-pane>
        </el-tabs>
      </div>

      <SideRail ref="sideRail" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'
import FilterBar from '@/components/FilterBar.vue'
import SideRail from '@/components/SideRail.vue'
import RaceOverview from '@/views/race/RaceOverview.vue'
import RaceDetail from '@/views/race/RaceDetail.vue'
import StandingsLive from '@/views/race/StandingsLive.vue'
import HistoryCompare from '@/views/race/HistoryCompare.vue'

const route = useRoute()
const router = useRouter()
const store = useF1Store()

const year = ref(Number(route.query.year) || store.currentSeason)
const round = ref(route.query.round ? Number(route.query.round) : null)
const activeTab = ref(route.query.tab || 'overview')
const sideRail = ref(null)
const tabKey = ref(0)

watch(year, (v) => {
  store.setSeason(v)
  updateQuery()
})

watch(round, () => {
  updateQuery()
})

watch(activeTab, () => {
  updateQuery()
})

// 修复：监听 URL query —— 查看按钮 / SideRail 收藏跳转都是 router.push 改 URL，
// 停留在页面内时若不同步 ref，Tab 和数据都不会切换。
// 值相同则跳过（防循环：updateQuery 的 router.replace 会再次触发本 watch）。
watch(() => route.query, (q) => {
  const qYear = q.year ? Number(q.year) : store.currentSeason
  const qRound = q.round ? Number(q.round) : null
  const qTab = q.tab || 'overview'
  if (qYear !== year.value) year.value = qYear
  if (qRound !== round.value) round.value = qRound
  if (qTab !== activeTab.value) activeTab.value = qTab
})

function updateQuery() {
  const query = { tab: activeTab.value }
  if (year.value) query.year = year.value
  if (round.value) query.round = round.value
  router.replace({ query })
}

function onTabChange(tab) {
  activeTab.value = tab
}

function onLoad() {
  // 强制当前 Tab 组件重新挂载（重新请求数据），替代原来的空函数
  tabKey.value += 1
}

onMounted(async () => {
  await store.fetchRaceList(year.value)
})
</script>

<style scoped>
.race-center {
  max-width: 1600px;
  margin: 0 auto;
}

.center-body {
  display: flex;
  gap: 16px;
}

.center-main {
  flex: 1;
  min-width: 0;
}

.race-tabs {
  min-height: 500px;
}
</style>
