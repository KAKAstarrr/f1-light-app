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
            <RaceOverview v-if="activeTab === 'overview'" :year="year" :round="round" />
          </el-tab-pane>
          <el-tab-pane label="分站详情" name="detail">
            <RaceDetail v-if="activeTab === 'detail'" :year="year" :round="round" />
          </el-tab-pane>
          <el-tab-pane label="实时积分" name="standings">
            <StandingsLive v-if="activeTab === 'standings'" />
          </el-tab-pane>
          <el-tab-pane label="历史对比" name="history">
            <HistoryCompare v-if="activeTab === 'history'" :year="year" :round="round" />
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
  // 触发当前 Tab 组件重新加载（通过 key 机制）
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
