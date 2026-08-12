/**
 * FantasyLeaderboard — Fantasy 排行榜 Tab
 */
<template>
  <div class="fantasy-leaderboard">
    <InfoCard title="赛季排行榜" :subtitle="`${season} 赛季`">
      <el-table :data="leaderboard" v-loading="loading" stripe>
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="rankTagType(row.rank)" effect="dark" round>
              {{ row.rank }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.username }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="team_name" label="车队名" min-width="140" />
        <el-table-column label="总积分" width="100" align="center">
          <template #default="{ row }">
            <strong class="points mono">{{ row.total_points }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="本轮积分" width="100" align="center">
          <template #default="{ row }">
            <span class="mono">{{ row.last_round_points || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !leaderboard.length" description="暂无排行榜数据" />
    </InfoCard>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useF1Store } from '@/stores/f1'
import { getLeaderboard } from '@/api/fantasy'
import { rankTagType } from '@/utils/f1-constants'
import InfoCard from '@/components/InfoCard.vue'

const store = useF1Store()
const season = computed(() => store.currentSeason)
const leaderboard = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const data = await getLeaderboard(season.value)
    leaderboard.value = data?.leaderboard || []
  } catch (e) {
    leaderboard.value = []
  }
  loading.value = false
})
</script>

<style scoped>
.fantasy-leaderboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.points {
  color: var(--f1-red);
  font-size: 16px;
  font-weight: 700;
}
</style>
