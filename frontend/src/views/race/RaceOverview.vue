/**
 * RaceOverview — 赛程总览 Tab
 * 全年分站日历 + 举办状态
 */
<template>
  <div class="race-overview">
    <InfoCard title="全年赛程" :subtitle="`${year} 赛季 · ${store.raceList.length} 站`">
      <el-table :data="store.raceList" v-loading="loading" stripe>
        <el-table-column prop="round" label="分站" width="70" align="center">
          <template #default="{ row }">
            <span class="round-num">R{{ row.round }}</span>
          </template>
        </el-table-column>
        <el-table-column label="赛道">
          <template #default="{ row }">
            <div class="race-cell">
              <span class="race-name">{{ row.raceName }}</span>
              <span class="race-loc">{{ row.Circuit?.Location?.locality }}, {{ row.Circuit?.Location?.country }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="赛道名称" width="240">
          <template #default="{ row }">
            {{ row.Circuit?.circuitName }}
          </template>
        </el-table-column>
        <el-table-column prop="date" label="比赛日期" width="120" sortable />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row)" size="small" effect="dark">
              {{ statusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="viewDetail(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </InfoCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'
import InfoCard from '@/components/InfoCard.vue'

const props = defineProps({
  year: { type: Number, default: 2026 },
  round: { type: [Number, String], default: null },
})

const router = useRouter()
const store = useF1Store()
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  await store.fetchRaceList(props.year)
  loading.value = false
})

function statusType(race) {
  const status = getStatus(race)
  if (status === 'done') return 'success'
  if (status === 'upcoming') return 'warning'
  if (status === 'ongoing') return 'danger'
  return 'info'
}

function statusLabel(race) {
  const status = getStatus(race)
  if (status === 'done') return '已完成'
  if (status === 'upcoming') return '即将开始'
  if (status === 'ongoing') return '进行中'
  return '未定'
}

function getStatus(race) {
  if (!race.date) return 'unknown'
  const now = new Date()
  const d = new Date(race.date + 'T23:59:59')
  if (d < now) return 'done'
  const start = new Date(race.date + 'T00:00:00')
  if (Math.abs(start - now) < 4 * 3600 * 1000) return 'ongoing'
  return 'upcoming'
}

function viewDetail(row) {
  router.push(`/race-center?tab=detail&year=${props.year}&round=${row.round}`)
}
</script>

<style scoped>
.race-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.round-num {
  font-weight: 700;
  color: var(--f1-red);
  font-family: 'JetBrains Mono', monospace;
}

.race-cell {
  display: flex;
  flex-direction: column;
}

.race-name {
  font-weight: 600;
  color: var(--f1-text-primary);
}

.race-loc {
  font-size: 12px;
  color: var(--f1-text-muted);
}
</style>
