<template>
  <div class="race-list">
    <div class="page-header">
      <h2>赛程列表</h2>
      <!-- 2A.6 年份选择 -->
      <el-select v-model="year" placeholder="选择赛季" style="width: 140px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="`${y} 赛季`" :value="y" />
      </el-select>
    </div>

    <!-- 2A.4 el-table + v-for 列表渲染 -->
    <el-table :data="store.raceList" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="round" label="分站" width="80" align="center" />
      <el-table-column label="赛道">
        <template #default="{ row }">
          <div class="race-cell">
            <span class="race-name">{{ row.raceName }}</span>
            <span class="race-loc">{{ row.Circuit?.Location?.locality }}, {{ row.Circuit?.Location?.country }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="赛道名称" width="220">
        <template #default="{ row }">
          {{ row.Circuit?.circuitName }}
        </template>
      </el-table-column>
      <el-table-column prop="date" label="比赛日期" width="130" sortable />
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="viewDetail(row)">
            查看结果
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'

const router = useRouter()
const store = useF1Store()

// ref 响应式数据
const year = ref(2026)
const loading = ref(false)
const yearOptions = [2026, 2025, 2024, 2023]

// 赛季切换
const onYearChange = async (val) => {
  store.setSeason(val)
  await loadRaces()
}

// 拉取赛程
const loadRaces = async () => {
  loading.value = true
  await store.fetchRaceList(year.value)
  loading.value = false
}

// 跳转分站结果页：动态路由 /results/:year/:round
const viewDetail = (row) => {
  store.setSelectedRound(row.round)
  router.push(`/results/${year.value}/${row.round}`)
}

// onMounted 生命周期：页面加载时自动请求
onMounted(loadRaces)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
}
.race-cell {
  display: flex;
  flex-direction: column;
}
.race-name {
  font-weight: 600;
}
.race-loc {
  font-size: 12px;
  color: #999;
}
</style>
