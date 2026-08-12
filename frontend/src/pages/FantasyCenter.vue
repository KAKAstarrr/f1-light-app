/**
 * FantasyCenter — Fantasy 管理中心
 * Tab：我的车队 / 排行榜 / 联盟
 * 复用现有 FantasyTeam 和 League 组件
 */
<template>
  <div class="fantasy-center">
    <el-tabs v-model="activeTab" class="fantasy-tabs" @tab-change="onTabChange">
      <el-tab-pane label="🏆 我的车队" name="team">
        <FantasyTeam v-if="activeTab === 'team'" />
      </el-tab-pane>
      <el-tab-pane label="📊 排行榜" name="leaderboard">
        <FantasyLeaderboard v-if="activeTab === 'leaderboard'" />
      </el-tab-pane>
      <el-tab-pane label="👥 联盟" name="league">
        <League v-if="activeTab === 'league'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FantasyTeam from '@/pages/FantasyTeam.vue'
import League from '@/pages/League.vue'
import FantasyLeaderboard from '@/views/fantasy/FantasyLeaderboard.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref(route.query.tab || 'team')

watch(activeTab, (v) => {
  router.replace({ query: { ...route.query, tab: v } })
})

function onTabChange(tab) {
  activeTab.value = tab
}
</script>

<style scoped>
.fantasy-center {
  max-width: 1400px;
  margin: 0 auto;
}

.fantasy-tabs {
  min-height: 500px;
}
</style>
