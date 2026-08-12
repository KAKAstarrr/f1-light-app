/**
 * StandingsLive — 实时积分 Tab
 * 车手/车队积分榜 + 趋势图
 */
<template>
  <div class="standings-live">
    <el-form :inline="true" :model="filterForm" class="filter">
      <el-form-item label="排序方式">
        <el-select v-model="filterForm.sortBy" style="width: 160px">
          <el-option label="积分降序" value="points_desc" />
          <el-option label="胜场降序" value="wins_desc" />
        </el-select>
      </el-form-item>
      <el-form-item label="关键词">
        <el-input
          v-model="filterForm.keyword"
          placeholder="车手/车队名"
          clearable
          style="width: 180px"
        />
      </el-form-item>
    </el-form>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="车手榜" name="driver">
        <InfoCard :noPadding="true">
          <el-table :data="sortedDriverList" v-loading="loading.driver" stripe>
            <el-table-column label="排名" width="70" align="center">
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
            <el-table-column label="车队">
              <template #default="{ row }">{{ row.Constructors?.[0]?.name }}</template>
            </el-table-column>
            <el-table-column label="国籍" width="100">
              <template #default="{ row }">{{ row.Driver?.nationality }}</template>
            </el-table-column>
            <el-table-column label="胜场" width="70" align="center" prop="wins" />
            <el-table-column label="积分" width="90" align="center">
              <template #default="{ row }">
                <strong class="points mono">{{ row.points }}</strong>
              </template>
            </el-table-column>
          </el-table>
        </InfoCard>
      </el-tab-pane>

      <el-tab-pane label="车队榜" name="constructor">
        <InfoCard :noPadding="true">
          <el-table :data="sortedConstructorList" v-loading="loading.constructor" stripe>
            <el-table-column label="排名" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="rankTagType(row.position)" effect="dark" round>
                  {{ row.position }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="车队" min-width="200">
              <template #default="{ row }">
                <strong>{{ row.Constructor?.name }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="国籍" width="120">
              <template #default="{ row }">{{ row.Constructor?.nationality }}</template>
            </el-table-column>
            <el-table-column label="胜场" width="70" align="center" prop="wins" />
            <el-table-column label="积分" width="90" align="center">
              <template #default="{ row }">
                <strong class="points mono">{{ row.points }}</strong>
              </template>
            </el-table-column>
          </el-table>
        </InfoCard>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'
import { rankTagType, driverName } from '@/utils/f1-constants'
import InfoCard from '@/components/InfoCard.vue'

const store = useF1Store()

const activeTab = ref('driver')
const filterForm = reactive({ sortBy: 'points_desc', keyword: '' })
const loading = reactive({ driver: false, constructor: false })

const sortedDriverList = computed(() => {
  let list = [...store.driverStandings]
  const kw = filterForm.keyword.trim().toLowerCase()
  if (kw) {
    list = list.filter(r =>
      (r.Driver?.code || '').toLowerCase().includes(kw) ||
      driverName(r.Driver).toLowerCase().includes(kw) ||
      (r.Constructors?.[0]?.name || '').toLowerCase().includes(kw)
    )
  }
  if (filterForm.sortBy === 'wins_desc') {
    list.sort((a, b) => Number(b.wins) - Number(a.wins))
  } else {
    list.sort((a, b) => Number(b.points) - Number(a.points))
  }
  return list
})

const sortedConstructorList = computed(() => {
  let list = [...store.constructorStandings]
  const kw = filterForm.keyword.trim().toLowerCase()
  if (kw) {
    list = list.filter(r => (r.Constructor?.name || '').toLowerCase().includes(kw))
  }
  if (filterForm.sortBy === 'wins_desc') {
    list.sort((a, b) => Number(b.wins) - Number(a.wins))
  } else {
    list.sort((a, b) => Number(b.points) - Number(a.points))
  }
  return list
})

async function onTabChange(tab) {
  if (tab === 'constructor' && !store.constructorStandings.length) {
    loading.constructor = true
    await store.fetchConstructorStandings()
    loading.constructor = false
  }
}

onMounted(async () => {
  loading.driver = true
  await store.fetchDriverStandings()
  loading.driver = false
})
</script>

<style scoped>
.filter {
  margin-bottom: 12px;
}

.sub {
  display: block;
  font-size: 12px;
  color: var(--f1-text-muted);
}

.points {
  color: var(--f1-red);
  font-size: 16px;
  font-weight: 700;
}
</style>
