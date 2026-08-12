<template>
  <div class="standings">
    <div class="page-header">
      <h2>车队 / 车手排行榜</h2>
    </div>

    <!-- 2A.3 + 2A.6：筛选表单 -->
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
      <el-form-item>
        <el-button @click="resetFilter">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 2A.3：车手/车队 Tab -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="车手榜" name="driver">
        <el-table :data="sortedDriverList" v-loading="loading.driver" stripe>
          <el-table-column label="排名" width="80" align="center">
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
          <el-table-column label="胜场" width="80" align="center" prop="wins" />
          <el-table-column label="积分" width="100" align="center">
            <template #default="{ row }">
              <strong class="points">{{ row.points }}</strong>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="车队榜" name="constructor">
        <el-table :data="sortedConstructorList" v-loading="loading.constructor" stripe>
          <el-table-column label="排名" width="80" align="center">
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
          <el-table-column label="胜场" width="80" align="center" prop="wins" />
          <el-table-column label="积分" width="100" align="center">
            <template #default="{ row }">
              <strong class="points">{{ row.points }}</strong>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useF1Store } from '@/stores/f1'

const store = useF1Store()

const activeTab = ref('driver')
const filterForm = reactive({ sortBy: 'points_desc', keyword: '' })
const loading = reactive({ driver: false, constructor: false })

const driverName = (d) => (d ? `${d.givenName || ''} ${d.familyName || ''}`.trim() : '')
const rankTagType = (pos) => {
  const p = Number(pos)
  if (p === 1) return 'danger'
  if (p === 2) return 'warning'
  if (p === 3) return 'success'
  return 'info'
}

// 2A.6 computed 计算属性：排序 + 筛选
const sortedDriverList = computed(() => {
  let list = [...store.driverStandings]
  // 关键词过滤
  const kw = filterForm.keyword.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (r) =>
        (r.Driver?.code || '').toLowerCase().includes(kw) ||
        driverName(r.Driver).toLowerCase().includes(kw) ||
        (r.Constructors?.[0]?.name || '').toLowerCase().includes(kw)
    )
  }
  // 排序
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
    list = list.filter(
      (r) => (r.Constructor?.name || '').toLowerCase().includes(kw)
    )
  }
  if (filterForm.sortBy === 'wins_desc') {
    list.sort((a, b) => Number(b.wins) - Number(a.wins))
  } else {
    list.sort((a, b) => Number(b.points) - Number(a.points))
  }
  return list
})

const resetFilter = () => {
  filterForm.sortBy = 'points_desc'
  filterForm.keyword = ''
}

const onTabChange = async (tab) => {
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
.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
}
.filter {
  margin-bottom: 12px;
}
.sub {
  display: block;
  font-size: 12px;
  color: #999;
}
.points {
  color: #e10600;
  font-size: 16px;
}
</style>
