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

    <!-- Fallback 警告 -->
    <el-alert
      v-if="modelVersion === 'rule_v1_fallback'"
      title="XGBoost 推理失败，已降级到规则模型"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 12px"
    />

    <!-- 预测内容 -->
    <el-card v-if="upcomingRace" shadow="never" class="block" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>夺冠概率分布</span>
          <div class="header-tags">
            <el-tag size="small" :type="modelTagType">{{ modelVersionLabel }}</el-tag>
            <el-tag v-if="featureCount" size="small" type="info">{{ featureCount }} 特征</el-tag>
          </div>
        </div>
      </template>

      <!-- Top3 高亮 -->
      <div v-if="predictions.length" class="top3-row">
        <div
          v-for="(p, i) in predictions.slice(0, 3)"
          :key="p.driver_code"
          class="top3-card"
          :style="{ borderColor: top3Color(i) }"
          @click="toggleExpand(p.driver_code)"
        >
          <div class="top3-rank">{{ i + 1 }}</div>
          <div class="top3-code">{{ p.driver_code }}</div>
          <div class="top3-name">{{ p.driver_name }}</div>
          <div class="top3-prob">{{ (p.probability * 100).toFixed(1) }}%</div>
          <div class="top3-team">{{ p.constructor }}</div>

          <!-- XGBoost: SHAP 特征贡献 -->
          <div v-if="p.shap_top3 && isXgb" class="shap-bars">
            <div class="shap-title">SHAP 特征贡献</div>
            <div
              v-for="s in p.shap_top3"
              :key="s.feature"
              class="shap-bar-item"
            >
              <div class="shap-bar-label" :title="featureLabel(s.feature)">
                {{ featureShort(s.feature) }}
              </div>
              <div class="shap-bar-track">
                <div
                  class="shap-bar-fill"
                  :style="{
                    width: shapBarWidth(s.contribution) + '%',
                    background: s.contribution >= 0 ? '#67c23a' : '#f56c6c'
                  }"
                ></div>
              </div>
              <div class="shap-bar-value" :class="s.contribution >= 0 ? 'pos' : 'neg'">
                {{ s.contribution > 0 ? '+' : '' }}{{ s.contribution.toFixed(3) }}
              </div>
            </div>
          </div>

          <!-- rule_v1: 特征值 mini bar -->
          <div v-if="p.features && !isXgb" class="feature-mini-bars">
            <div
              v-for="(val, fname) in p.features"
              :key="fname"
              class="mini-bar-item"
            >
              <div class="mini-bar-label" :title="featureLabel(fname)">
                {{ featureShort(fname) }}
              </div>
              <div class="mini-bar-track">
                <div
                  class="mini-bar-fill"
                  :style="{ width: featurePercent(fname, val) + '%', background: top3Color(i) }"
                ></div>
              </div>
              <div class="mini-bar-value">{{ formatFeatureVal(fname, val) }}</div>
            </div>
          </div>

          <!-- 展开详情 -->
          <transition name="expand">
            <div v-if="expandedDriver === p.driver_code" class="feature-detail">
              <!-- XGBoost: SHAP 详情 -->
              <template v-if="isXgb">
                <div class="detail-title">SHAP 特征贡献 Top 3</div>
                <div
                  v-for="s in (p.shap_top3 || [])"
                  :key="s.feature"
                  class="detail-row"
                >
                  <div class="detail-label" :title="featureDesc(s.feature)">
                    {{ featureLabel(s.feature) }}
                  </div>
                  <div class="detail-shap" :class="s.contribution >= 0 ? 'pos' : 'neg'">
                    {{ s.contribution > 0 ? '+' : '' }}{{ s.contribution.toFixed(4) }}
                  </div>
                </div>
                <div class="detail-title" style="margin-top: 8px">全部特征值</div>
                <div
                  v-for="(val, fname) in p.features"
                  :key="fname"
                  class="detail-row"
                >
                  <div class="detail-label" :title="featureDesc(fname)">
                    {{ featureLabel(fname) }}
                  </div>
                  <div class="detail-value">{{ formatFeatureVal(fname, val) }}</div>
                </div>
                <div class="detail-score">
                  模型概率: {{ p.model_proba?.toFixed(6) || '-' }}
                </div>
              </template>

              <!-- rule_v1: 权重详情 -->
              <template v-else>
                <div class="detail-title">特征详情 (权重)</div>
                <div
                  v-for="(val, fname) in p.features"
                  :key="fname"
                  class="detail-row"
                >
                  <div class="detail-label" :title="featureDesc(fname)">
                    {{ featureLabel(fname) }}
                  </div>
                  <div class="detail-value">{{ formatFeatureVal(fname, val) }}</div>
                  <div class="detail-weight">
                    {{ featureWeights ? ((featureWeights[fname] || 0) * 100).toFixed(0) + '%' : '' }}
                  </div>
                </div>
                <div class="detail-score">
                  原始得分: {{ p.raw_score?.toFixed(4) || '-' }}
                </div>
              </template>
            </div>
          </transition>
        </div>
      </div>

      <!-- 全部车手概率柱状图 -->
      <div v-if="predictions.length" class="chart" ref="chartRef"></div>

      <!-- XGBoost: 特征重要性 -->
      <el-collapse v-if="isXgb && featureImportance.length">
        <el-collapse-item title="模型特征重要性 Top 5（XGBoost Gain）">
          <el-descriptions :column="1" border>
            <el-descriptions-item
              v-for="(item, idx) in featureImportance"
              :key="item.feature"
              :label="`${idx + 1}. ${featureLabel(item.feature)}`"
            >
              {{ (item.importance * 100).toFixed(2) }}%
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>

      <!-- rule_v1: 特征权重说明 -->
      <el-collapse v-if="!isXgb && featureWeights">
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
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
const featureCount = ref(null)
const featureWeights = ref(null)
const featureImportance = ref([])
const chartRef = ref(null)
const expandedDriver = ref(null)
let chartInstance = null

// 从 upcomingRace 派生 year 和 round
const year = computed(() => Number(upcomingRace.value?.season) || store.currentSeason)
const round = computed(() => Number(upcomingRace.value?.round) || null)

const isXgb = computed(() => modelVersion.value === 'xgb_v1')
const modelVersionLabel = computed(() => {
  const map = { xgb_v1: 'XGBoost v1', rule_v1: '规则模型 v1', rule_v1_fallback: '规则模型 (降级)' }
  return map[modelVersion.value] || modelVersion.value
})
const modelTagType = computed(() => {
  if (modelVersion.value === 'xgb_v1') return 'success'
  if (modelVersion.value === 'rule_v1_fallback') return 'warning'
  return 'info'
})

const top3Color = (i) => {
  const colors = ['#e10600', '#ff9800', '#4caf50']
  return colors[i] || '#999'
}

// ── 特征标签映射（19 个 XGBoost + 5 个 rule_v1）──
const featureLabel = (name) => ({
  // XGBoost 19 特征
  qualifying_pos: '排位赛位次',
  grid: '发车位次',
  qualifying_pos_inv: '排位位次(反转)',
  grid_inv: '发车位次(反转)',
  driver_season_points_before: '赛季积分',
  driver_season_races_before: '赛季完赛场次',
  driver_season_wins_before: '赛季胜场',
  driver_season_dnfs_before: '赛季退赛数',
  driver_season_avg_pos_before: '赛季平均位次',
  driver_last5_avg_pos: '近5场平均位次',
  driver_last5_dnfs: '近5场退赛数',
  driver_circuit_avg_pos: '赛道平均位次',
  driver_circuit_races: '赛道场次',
  driver_circuit_dnfs: '赛道退赛数',
  constructor_season_points_before: '车队赛季积分',
  constructor_season_avg_pos_before: '车队平均位次',
  constructor_season_dnfs_before: '车队退赛数',
  regulation_era: '规则时代',
  round_normalized: '赛季进度',
  // rule_v1 5 特征
  championship_ratio: '赛季积分占比',
  recent_avg_pos: '近5场平均位次',
  win_rate: '历史胜率',
  dnf_rate: '近期退赛率',
})[name] || name

const featureShort = (name) => ({
  qualifying_pos: '排位',
  grid: '发车',
  qualifying_pos_inv: '排位⁻¹',
  grid_inv: '发车⁻¹',
  driver_season_points_before: '积分',
  driver_season_races_before: '场次',
  driver_season_wins_before: '胜场',
  driver_season_dnfs_before: '退赛',
  driver_season_avg_pos_before: '均位',
  driver_last5_avg_pos: '近5场',
  driver_last5_dnfs: '近5退',
  driver_circuit_avg_pos: '赛道均位',
  driver_circuit_races: '赛道次',
  driver_circuit_dnfs: '赛道退',
  constructor_season_points_before: '队积分',
  constructor_season_avg_pos_before: '队均位',
  constructor_season_dnfs_before: '队退赛',
  regulation_era: '时代',
  round_normalized: '进度',
  championship_ratio: '积分',
  win_rate: '胜率',
  dnf_rate: 'DNF',
})[name] || name

const featureDesc = (name) => ({
  qualifying_pos: '本场排位赛位次 (越低越好)',
  grid: '发车位次 (越低越好)',
  qualifying_pos_inv: '排位位次反转值 21-pos (越高越好)',
  grid_inv: '发车位次反转值 21-grid (越高越好)',
  driver_season_points_before: '本赛季截至上轮的累计积分',
  driver_season_races_before: '本赛季截至上轮的完赛场次',
  driver_season_wins_before: '本赛季截至上轮的胜场数',
  driver_season_dnfs_before: '本赛季截至上轮的退赛数',
  driver_season_avg_pos_before: '本赛季截至上轮的平均完赛位次',
  driver_last5_avg_pos: '跨赛季最近5场的平均完赛位次',
  driver_last5_dnfs: '跨赛季最近5场的退赛次数',
  driver_circuit_avg_pos: '该车手在该赛道的历史平均位次',
  driver_circuit_races: '该车手在该赛道的历史参赛次数',
  driver_circuit_dnfs: '该车手在该赛道的历史退赛次数',
  constructor_season_points_before: '车队本赛季截至上轮的累计积分',
  constructor_season_avg_pos_before: '车队本赛季截至上轮的平均完赛位次',
  constructor_season_dnfs_before: '车队本赛季截至上轮的退赛数',
  regulation_era: '规则时代: 0=2018-2021, 1=2022+',
  round_normalized: '赛季进度 round/total_rounds (0-1)',
  championship_ratio: '当前赛季积分占榜首比例 (0-1)',
  win_rate: '本赛季胜率 (越高越好)',
  dnf_rate: '近期退赛率 (越低越好)',
})[name] || ''

const formatFeatureVal = (name, val) => {
  if (val === null || val === undefined) return '-'
  if (name === 'recent_avg_pos' || name === 'qualifying_pos' ||
      name === 'driver_season_avg_pos_before' || name === 'driver_last5_avg_pos' ||
      name === 'driver_circuit_avg_pos' || name === 'constructor_season_avg_pos_before' ||
      name === 'driver_season_races_before' || name === 'driver_season_wins_before' ||
      name === 'driver_season_dnfs_before' || name === 'driver_last5_dnfs' ||
      name === 'driver_circuit_races' || name === 'driver_circuit_dnfs' ||
      name === 'constructor_season_dnfs_before' || name === 'grid') {
    return Number.isInteger(val) ? val : val.toFixed(1)
  }
  if (name === 'championship_ratio' || name === 'win_rate' || name === 'dnf_rate') {
    return (val * 100).toFixed(1) + '%'
  }
  if (name === 'round_normalized') {
    return (val * 100).toFixed(1) + '%'
  }
  if (name === 'regulation_era') {
    return val >= 1 ? '2022+新规' : '2018-2021'
  }
  if (name === 'driver_season_points_before' || name === 'constructor_season_points_before') {
    return val.toFixed(0)
  }
  return val
}

// rule_v1: 特征值归一化为 0-100%
const featurePercent = (name, val) => {
  if (name === 'championship_ratio' || name === 'win_rate') return Math.min(100, val * 100)
  if (name === 'dnf_rate') return Math.min(100, (1 - val) * 100)
  if (name === 'recent_avg_pos' || name === 'qualifying_pos') return Math.max(5, (1 - (val - 1) / 19) * 100)
  return 50
}

// SHAP 贡献值 → bar 宽度 (0-100%)
const shapBarWidth = (contribution) => {
  const absVal = Math.abs(contribution)
  // SHAP 值通常在 -3 ~ +3 范围，映射到 0-100%
  return Math.min(100, absVal * 50)
}

const toggleExpand = (code) => {
  expandedDriver.value = expandedDriver.value === code ? null : code
}

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
        let html = `<b>${p.driver_code}</b> - ${p.driver_name}<br/>
          概率: ${(p.probability * 100).toFixed(1)}%<br/>
          预测排名: ${p.rank_pred}<br/>
          车队: ${p.constructor}`
        if (p.model_proba !== undefined) {
          html += `<br/>模型概率: ${p.model_proba.toFixed(6)}`
        }
        if (p.raw_score) {
          html += `<br/>原始得分: ${p.raw_score.toFixed(4)}`
        }
        // SHAP top-3
        if (p.shap_top3 && p.shap_top3.length) {
          html += '<br/><br/><b>SHAP 特征贡献:</b>'
          for (const s of p.shap_top3) {
            const sign = s.contribution > 0 ? '+' : ''
            const color = s.contribution >= 0 ? '#67c23a' : '#f56c6c'
            html += `<br/><span style="color:${color}">${featureShort(s.feature)}: ${sign}${s.contribution.toFixed(3)}</span>`
          }
        }
        return html
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
      featureCount.value = data.feature_count || null
      featureWeights.value = data.feature_weights || null
      featureImportance.value = data.feature_importance || []
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

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
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
.header-tags { display: flex; gap: 6px; }
.top3-row { display: flex; gap: 16px; margin-bottom: 24px; }
.top3-card {
  flex: 1; text-align: center; padding: 16px; border-radius: 8px;
  border: 2px solid #ddd; background: #f9f9f9;
  cursor: pointer; transition: all 0.2s;
}
.top3-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}
.top3-rank { font-size: 28px; font-weight: bold; color: #666; }
.top3-code { font-size: 24px; font-weight: bold; margin: 4px 0; }
.top3-name { font-size: 12px; color: #999; }
.top3-prob { font-size: 20px; font-weight: bold; color: #333; margin: 4px 0; }
.top3-team { font-size: 12px; color: #999; }

/* SHAP bars */
.shap-bars {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}
.shap-title {
  font-size: 10px;
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.shap-bar-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
}
.shap-bar-label {
  width: 48px;
  color: #888;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.shap-bar-track {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}
.shap-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
.shap-bar-value {
  width: 44px;
  text-align: right;
  font-weight: 600;
  flex-shrink: 0;
}
.shap-bar-value.pos { color: #67c23a; }
.shap-bar-value.neg { color: #f56c6c; }

/* rule_v1 mini bars */
.feature-mini-bars {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}
.mini-bar-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
}
.mini-bar-label {
  width: 40px;
  color: #888;
  cursor: help;
  flex-shrink: 0;
}
.mini-bar-track {
  flex: 1;
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}
.mini-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}
.mini-bar-value {
  width: 36px;
  text-align: right;
  color: #555;
  font-weight: 600;
  flex-shrink: 0;
}

/* Expand detail */
.feature-detail {
  margin-top: 12px;
  padding: 10px;
  background: rgba(0,0,0,0.03);
  border-radius: 6px;
  text-align: left;
}
.detail-title {
  font-size: 11px;
  font-weight: 700;
  color: #666;
  margin-bottom: 6px;
  text-transform: uppercase;
}
.detail-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 2px 0;
  border-bottom: 1px solid #eee;
}
.detail-label {
  flex: 1;
  color: #555;
  cursor: help;
}
.detail-value {
  width: 60px;
  text-align: right;
  font-weight: 600;
  color: #333;
}
.detail-weight {
  width: 36px;
  text-align: right;
  color: #999;
}
.detail-shap {
  width: 60px;
  text-align: right;
  font-weight: 600;
}
.detail-shap.pos { color: #67c23a; }
.detail-shap.neg { color: #f56c6c; }
.detail-score {
  margin-top: 6px;
  font-size: 11px;
  color: #999;
  text-align: right;
}

.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to, .expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
.chart { width: 100%; height: 350px; }
</style>
