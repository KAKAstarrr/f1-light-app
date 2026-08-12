<template>
  <div class="prediction-page">
    <!-- 锁定分站栏 -->
    <div class="race-lock-bar" v-if="upcomingRace">
      <span class="lock-icon">🔒</span>
      <span class="lock-label">预测目标</span>
      <span class="race-name">{{ upcomingRace.raceName }}</span>
      <span class="race-date">{{ upcomingRace.date }}</span>
      <el-tag type="success" size="small">即将开始</el-tag>
    </div>

    <!-- 无即将开始的分站 -->
    <el-card v-if="!upcomingRace && !loadingRaces" shadow="never">
      <el-empty description="暂无即将开始的分站，无法进行预测" />
    </el-card>

    <!-- 预测内容 -->
    <el-card v-if="upcomingRace" shadow="never" class="block" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>夺冠概率分布</span>
          <el-tag size="small" type="info">{{ modelVersion }}</el-tag>
        </div>
      </template>

      <!-- Top3 高亮 -->
      <div v-if="predictions.length" class="top3-row">
        <div
          v-for="(p, i) in predictions.slice(0, 3)"
          :key="p.driver_code"
          class="top3-card"
          :style="{ borderColor: top3Color(i) }"
        >
          <div class="top3-rank">{{ i + 1 }}</div>
          <div class="top3-code">{{ p.driver_code }}</div>
          <div class="top3-name">{{ p.driver_name }}</div>
          <div class="top3-prob">{{ (p.probability * 100).toFixed(1) }}%</div>
          <div class="top3-team">{{ p.constructor }}</div>
        </div>
      </div>

      <!-- 全部车手概率柱状图 -->
      <div v-if="predictions.length" class="chart" ref="chartRef"></div>

      <!-- 特征权重说明 -->
      <el-collapse v-if="featureWeights">
        <el-collapse-item title="特征权重说明（模型决策依据）">
          <el-descriptions :column="1" border>
            <el-descriptions-item
              v-for="(weight, name) in featureWeights"
              :key="name"
              :label="featureLabel(name)"
            >
              {{ (weight * 100).toFixed(0) }}%
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>

      <el-empty v-if="!loading && !predictions.length" description="暂无预测数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useF1Store } from '@/stores/f1'
import { useNextRace } from '@/composables/useNextRace'
import { getPrediction } from '@/api/prediction'

const store = useF1Store()
const { upcomingRace } = useNextRace()

const loading = ref(false)
const loadingRaces = ref(true)
const predictions = ref([])
const modelVersion = ref('')
const featureWeights = ref(null)
const chartRef = ref(null)
let chartInstance = null

// 从 upcomingRace 派生 year 和 round
const year = computed(() => Number(upcomingRace.value?.season) || store.currentSeason)
const round = computed(() => Number(upcomingRace.value?.round) || null)

const top3Color = (i) => {
  const colors = ['#e10600', '#ff9800', '#4caf50']
  return colors[i] || '#999'
}

const featureLabel = (name) => ({
  championship_ratio: '赛季积分占比',
  recent_avg_pos: '近5场平均位次',
  qualifying_pos: '排位赛位次',
  win_rate: '历史胜率',
  dnf_rate: '近期退赛率'
})[name] || name

const renderChart = () => {
  if (!chartRef.value || !predictions.value.length) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const data = predictions.value.slice(0, 15)
  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = data[params[0].dataIndex]
        return `${p.driver_code} - ${p.driver_name}<br/>
          概率: ${(p.probability * 100).toFixed(1)}%<br/>
          预测排名: ${p.rank_pred}<br/>
          车队: ${p.constructor}`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(p => p.driver_code),
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '夺冠概率',
      axisLabel: { formatter: v => (v * 100).toFixed(0) + '%' }
    },
    series: [{
      type: 'bar',
      data: data.map((p, i) => ({
        value: p.probability,
        itemStyle: { color: i < 3 ? ['#e10600', '#ff9800', '#4caf50'][i] : '#409eff' }
      })),
      label: { show: true, position: 'top', formatter: p => (p.value * 100).toFixed(1) + '%' }
    }]
  })
}

const loadPrediction = async () => {
  if (!round.value) return
  loading.value = true
  try {
    const data = await getPrediction(year.value, round.value)
    if (data.code === 200) {
      predictions.value = data.predictions || []
      modelVersion.value = data.model_version || ''
      featureWeights.value = data.feature_weights || null
      await nextTick()
      renderChart()
    } else {
      predictions.value = []
    }
  } catch {
    predictions.value = []
  }
  loading.value = false
}

onMounted(async () => {
  await store.fetchRaceList(store.currentSeason)
  loadingRaces.value = false
  if (upcomingRace.value) {
    await loadPrediction()
  }
})
</script>

<style scoped>
.prediction-page { padding: 16px; }
.race-lock-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; margin-bottom: 16px;
  background: #f0f9eb; border: 1px solid #e1f3d8; border-radius: 8px;
}
.lock-icon { font-size: 18px; }
.lock-label { font-size: 14px; color: #67c23a; font-weight: 600; }
.race-name { font-size: 18px; font-weight: bold; }
.race-date { font-size: 14px; color: #909399; }
.block { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.top3-row { display: flex; gap: 16px; margin-bottom: 24px; }
.top3-card {
  flex: 1; text-align: center; padding: 16px; border-radius: 8px;
  border: 2px solid #ddd; background: #f9f9f9;
}
.top3-rank { font-size: 28px; font-weight: bold; color: #666; }
.top3-code { font-size: 24px; font-weight: bold; margin: 4px 0; }
.top3-name { font-size: 12px; color: #999; }
.top3-prob { font-size: 20px; font-weight: bold; color: #333; margin: 4px 0; }
.top3-team { font-size: 12px; color: #999; }
.chart { width: 100%; height: 350px; }
</style>
