/**
 * HistoryCompare — 历史对比 Tab
 * 同分站历年车手表现对比
 */
<template>
  <div class="history-compare">
    <InfoCard title="历史对比" :subtitle="selectedRaceName">
      <div v-if="!round" class="empty-hint">
        <EmptyState icon="📊" title="请选择分站" description="在上方筛选栏选择要对比的分站" />
      </div>

      <div v-else>
        <div class="year-tabs">
          <el-checkbox-group v-model="selectedYears" @change="loadCompare">
            <el-checkbox v-for="y in availableYears" :key="y" :label="y">{{ y }}</el-checkbox>
          </el-checkbox-group>
        </div>

        <el-table :data="compareData" v-loading="loading" stripe class="compare-table">
          <el-table-column prop="driver" label="车手" width="160" fixed>
            <template #default="{ row }">
              <strong>{{ row.driverCode || row.driver }}</strong>
            </template>
          </el-table-column>
          <el-table-column
            v-for="y in selectedYears"
            :key="y"
            :label="`${y}`"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <span v-if="row.results[y]" :class="positionClass(row.results[y].position)">
                {{ row.results[y].position }}
              </span>
              <span v-else class="no-data">—</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="legend">
          <span class="legend-item"><i class="pos-1"></i>冠军</span>
          <span class="legend-item"><i class="pos-2"></i>亚军</span>
          <span class="legend-item"><i class="pos-3"></i>季军</span>
          <span class="legend-item"><i class="pos-other"></i>其他名次</span>
          <span class="legend-item"><i class="pos-none"></i>未参赛</span>
        </div>
      </div>
    </InfoCard>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { getRaceResult } from '@/api/race'
import InfoCard from '@/components/InfoCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps({
  year: { type: Number, default: 2026 },
  round: { type: [Number, String], default: null },
})

const store = useF1Store()
const availableYears = [2026, 2025, 2024, 2023]
const selectedYears = ref([2026, 2025, 2024])
const compareData = ref([])
const loading = ref(false)

const selectedRaceName = computed(() => {
  const race = store.raceList.find(r => Number(r.round) === Number(props.round))
  return race ? race.raceName : ''
})

async function loadCompare() {
  if (!props.round || !selectedYears.value.length) {
    compareData.value = []
    return
  }

  loading.value = true
  const driverMap = {}

  for (const y of selectedYears.value) {
    try {
      const data = await getRaceResult(y, props.round)
      const results = data?.Races?.[0]?.Results || []
      results.forEach(r => {
        const code = r.Driver?.code || r.Driver?.driverId
        if (!code) return
        if (!driverMap[code]) {
          driverMap[code] = {
            driver: code,
            driverCode: code,
            results: {},
          }
        }
        driverMap[code].results[y] = {
          position: Number(r.position),
          points: r.points,
          grid: r.grid,
        }
      })
    } catch (e) {
      // 某年无数据跳过
    }
  }

  // 转为数组并按车手名排序
  compareData.value = Object.values(driverMap).sort((a, b) => {
    // 按最新选中年份的名次排序
    const latestYear = Math.max(...selectedYears.value)
    const aPos = a.results[latestYear]?.position || 999
    const bPos = b.results[latestYear]?.position || 999
    return aPos - bPos
  })

  loading.value = false
}

function positionClass(pos) {
  if (pos === 1) return 'pos-1'
  if (pos === 2) return 'pos-2'
  if (pos === 3) return 'pos-3'
  return 'pos-other'
}

watch(() => [props.year, props.round], () => {
  if (props.round) loadCompare()
})

onMounted(() => {
  if (props.round) loadCompare()
})
</script>

<style scoped>
.history-compare {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.year-tabs {
  margin-bottom: 16px;
}

.compare-table {
  margin-bottom: 16px;
}

.pos-1 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--f1-red);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.pos-2 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--f1-warning);
  color: #000;
  font-weight: 700;
  font-size: 13px;
}

.pos-3 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--f1-success);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.pos-other {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--f1-bg-elevated);
  color: var(--f1-text-primary);
  font-weight: 600;
  font-size: 13px;
  border: 1px solid var(--f1-border);
}

.no-data {
  color: var(--f1-text-muted);
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--f1-text-secondary);
}

.legend-item i {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.legend-item .pos-1 { background: var(--f1-red); }
.legend-item .pos-2 { background: var(--f1-warning); }
.legend-item .pos-3 { background: var(--f1-success); }
.legend-item .pos-other { background: var(--f1-bg-elevated); border: 1px solid var(--f1-border); }
.legend-item .pos-none { background: transparent; border: 1px dashed var(--f1-border); }
</style>
