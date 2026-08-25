<template>
  <div class="prediction-page">
    <!-- 工具条：分站选择 + 视图切换 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedRound"
          :loading="loadingRaces"
          placeholder="选择分站"
          style="width: 260px"
          @change="onRoundChange"
        >
          <el-option
            v-for="r in raceOptions"
            :key="r.round"
            :label="`R${String(r.round).padStart(2, '0')} · ${r.raceName}${r.isPast ? '（已结束）' : ''}`"
            :value="r.round"
          />
        </el-select>
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!selectedRound"
          @click="loadPrediction(true)"
        >
          查看预测
        </el-button>
      </div>

      <div class="toolbar-right">
        <el-button
          :type="viewMode === 'history' ? 'primary' : 'default'"
          :plain="viewMode !== 'history'"
          @click="switchView('history')"
        >
          📋 本赛季预测历史
        </el-button>
      </div>
    </div>

    <!-- ========== 详情视图 ========== -->
    <template v-if="viewMode === 'detail'">
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
      <el-card v-if="selectedRace" shadow="never" class="block" v-loading="loading">
        <template #header>
          <div class="card-header">
            <div>
              <span class="race-title">R{{ pad(selectedRace.round) }} {{ selectedRace.raceName }}</span>
              <span class="race-date">{{ selectedRace.date }}</span>
            </div>
            <div class="header-tags">
              <el-tag size="small" :type="modelTagType">{{ modelVersionLabel }}</el-tag>
              <el-tag v-if="featureCount" size="small" type="info">{{ featureCount }} 特征</el-tag>
              <!-- 数据来源标注 -->
              <el-tag v-if="predSource" size="small" :type="predSource === 'backfill' ? 'warning' : 'success'">
                {{ predSource === 'backfill' ? '回算生成' : '在线预测' }}
              </el-tag>
              <el-tag v-if="predTime" size="small" type="info">{{ predTime }}</el-tag>
            </div>
          </div>
        </template>

        <!-- 天气影响摘要（正赛实际天气，来自 FastF1） -->
        <div v-if="weatherInfo" class="weather-bar" :class="{ 'is-neutral': weatherInfo.is_neutral }">
          <span class="weather-emoji">{{ weatherInfo.is_wet ? '🌧️' : '☀️' }}</span>
          <span class="weather-cond">{{ weatherInfo.is_wet ? '湿地正赛 · 雨战' : '干地正赛' }}</span>
          <span class="weather-sep">|</span>
          <span class="weather-item">🌡️ 气温 {{ weatherInfo.air_temp.toFixed(1) }}°C</span>
          <span class="weather-item">🏁 赛道温度 {{ weatherInfo.track_temp.toFixed(1) }}°C</span>
          <span class="weather-item">💧 最大降雨 {{ weatherInfo.rainfall.toFixed(1) }}mm</span>
          <span class="weather-item">💨 湿度 {{ weatherInfo.humidity.toFixed(0) }}%</span>
          <el-tooltip
            v-if="weatherInfo.is_neutral"
            content="该分站天气数据暂未收录（未来分站或数据缺失），预测使用中性值参与计算：干地 / 20°C / 30°C / 0mm / 60%"
            placement="top"
          >
            <span class="weather-neutral-tag">⚠️ 中性值（天气未收录）</span>
          </el-tooltip>
        </div>

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
                  <div class="detail-title" style="margin-top: 8px">
                    特征维度（{{ activeFeatureGroups.length }} 组 · 点击展开）
                  </div>
                  <el-collapse class="feature-groups">
                    <el-collapse-item
                      v-for="g in activeFeatureGroups"
                      :key="g.key"
                      :name="g.key"
                      :title="`${g.icon} ${g.title}（${g.visibleFeatures.length}）`"
                    >
                      <div class="group-desc">{{ g.desc }}</div>
                      <div
                        v-for="fname in g.visibleFeatures"
                        :key="fname"
                        class="detail-row"
                      >
                        <div class="detail-label" :title="featureDesc(fname)">
                          {{ featureLabel(fname) }}
                        </div>
                        <div class="detail-value">{{ formatFeatureVal(fname, (expandedPrediction.features || {})[fname]) }}</div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                  <div class="detail-score">
                    模型概率: {{ p.model_proba?.toFixed(6) || '-' }}
                  </div>
                </template>

                <!-- rule_v1: 权重详情 -->
                <template v-else>
                  <div class="detail-title">特征详情（权重）</div>
                  <el-collapse class="feature-groups">
                    <el-collapse-item
                      v-for="g in activeFeatureGroups"
                      :key="g.key"
                      :name="g.key"
                      :title="`${g.icon} ${g.title}（${g.visibleFeatures.length}）`"
                    >
                      <div class="group-desc">{{ g.desc }}</div>
                      <div
                        v-for="fname in g.visibleFeatures"
                        :key="fname"
                        class="detail-row"
                      >
                        <div class="detail-label" :title="featureDesc(fname)">
                          {{ featureLabel(fname) }}
                        </div>
                        <div class="detail-value">{{ formatFeatureVal(fname, (expandedPrediction.features || {})[fname]) }}</div>
                        <div class="detail-weight">
                          {{ featureWeights ? ((featureWeights[fname] || 0) * 100).toFixed(0) + '%' : '' }}
                        </div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
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

      <el-card v-if="!selectedRace" shadow="never" class="block">
        <el-empty description="暂无分站数据，无法进行预测" />
      </el-card>
    </template>

    <!-- ========== 历史视图 ========== -->
    <el-card v-else shadow="never" class="block" v-loading="loadingHistory">
      <template #header>
        <div class="card-header">
          <span>{{ season }} 赛季预测历史</span>
          <el-tag size="small" type="info">{{ historyRounds.length }} 站有记录</el-tag>
        </div>
      </template>

      <el-table :data="historyRows" stripe size="small" @row-click="onHistoryRowClick" class="history-table">
        <el-table-column label="分站" width="90" align="center">
          <template #default="{ row }">
            <span class="round-badge">R{{ pad(row.round) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="raceName" label="大奖赛" min-width="160" />
        <el-table-column label="预测 Top3" min-width="220">
          <template #default="{ row }">
            <span class="top3-mini">
              <template v-for="(t, i) in row.top3" :key="t.driver_code">
                <span class="mini-rank">{{ i + 1 }}</span>{{ t.driver_code }}
                <span class="mini-prob">{{ (t.probability * 100).toFixed(1) }}%</span>
                <span v-if="i < row.top3.length - 1" class="mini-sep">·</span>
              </template>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="模型" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="['xgb_v1', 'xgb_v2'].includes(row.model_version) ? 'success' : 'info'">
              {{ modelShort(row.model_version) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source === 'backfill' ? 'warning' : 'success'">
              {{ row.source === 'backfill' ? '回算' : '在线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="timeText" label="预测时间" width="170" align="center" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click.stop="viewRound(row.round)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="本赛季暂无预测记录，先去「查看预测」生成一次吧" :image-size="80" />
        </template>
      </el-table>

      <div v-if="historyRounds.length" class="history-tip">
        💡 点击任意行可查看该站完整预测详情；「回算」标记表示对已结束分站的补算结果
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useF1Store } from '@/stores/f1'
import { useNextRace } from '@/composables/useNextRace'
import { getPrediction, getPredictionHistory } from '@/api/prediction'

const store = useF1Store()
const { upcomingRace } = useNextRace()

const season = computed(() => store.currentSeason)

// ── 视图与分站选择 ──
const viewMode = ref('detail') // detail | history
const selectedRound = ref(null)
const raceOptions = ref([])
const loadingRaces = ref(true)

const loading = ref(false)
const loadingHistory = ref(false)
const predictions = ref([])
const modelVersion = ref('')
const featureCount = ref(null)
const featureWeights = ref(null)
const featureImportance = ref([])
const predSource = ref('') // backfill | live
const predTime = ref('')
const chartRef = ref(null)
const expandedDriver = ref(null)
let chartInstance = null

// ── 历史记录 ──
const historyRounds = ref([])
const historyRows = computed(() => {
  const nameMap = {}
  for (const r of raceOptions.value) nameMap[r.round] = r.raceName
  return historyRounds.value.map((h) => ({
    ...h,
    raceName: nameMap[h.round] || `R${h.round}`,
    timeText: h.created_at ? h.created_at.replace('T', ' ').slice(0, 16) : '-',
  }))
})

const selectedRace = computed(() =>
  raceOptions.value.find((r) => r.round === selectedRound.value) || null
)

const pad = (n) => String(n).padStart(2, '0')

const isXgb = computed(() => ['xgb_v1', 'xgb_v2'].includes(modelVersion.value))
const modelVersionLabel = computed(() => {
  const map = { xgb_v1: 'XGBoost v1', xgb_v2: 'XGBoost v2', rule_v1: '规则模型 v1', rule_v1_fallback: '规则模型 (降级)' }
  return map[modelVersion.value] || modelVersion.value
})
const modelTagType = computed(() => {
  if (['xgb_v1', 'xgb_v2'].includes(modelVersion.value)) return 'success'
  if (modelVersion.value === 'rule_v1_fallback') return 'warning'
  return 'info'
})
const modelShort = (v) => ({
  xgb_v1: 'XGBoost',
  xgb_v2: 'XGBoost v2',
  rule_v1: '规则模型',
  rule_v1_fallback: '规则(降级)',
}[v] || v)

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
  // 环境/天气特征 (xgb_v2)
  weather_is_wet: '干湿状态',
  weather_air_temp: '气温',
  weather_track_temp: '赛道温度',
  weather_max_rainfall: '最大降雨',
  weather_humidity: '湿度',
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
  weather_is_wet: '干湿',
  weather_air_temp: '气温',
  weather_track_temp: '赛道温',
  weather_max_rainfall: '降雨',
  weather_humidity: '湿度',
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
  weather_is_wet: '正赛是否湿地 (1=雨战, 0=干地)。来自 FastF1 正赛实际天气记录',
  weather_air_temp: '正赛平均气温 (°C)。气温影响轮胎工作窗口与引擎散热',
  weather_track_temp: '正赛平均赛道温度 (°C)。高温加速轮胎退化，低温影响轮胎升温',
  weather_max_rainfall: '正赛最大降雨量 (mm)。降雨直接影响赛道抓地力与策略',
  weather_humidity: '正赛平均湿度 (%)。高湿度影响引擎进气和轮胎管理',
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
  if (name === 'weather_is_wet') {
    return val >= 1 ? '🌧️ 湿地' : '☀️ 干地'
  }
  if (name === 'weather_air_temp' || name === 'weather_track_temp') {
    return val.toFixed(1) + '°C'
  }
  if (name === 'weather_max_rainfall') {
    return Number(val) > 0 ? val.toFixed(1) + 'mm' : '0mm'
  }
  if (name === 'weather_humidity') {
    return val.toFixed(0) + '%'
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

// ── 特征维度分组（PRD 3.4.2 维度设计：车手状态/车队趋势/赛道特性/环境/上下文）──
const FEATURE_GROUPS = [
  { key: 'qualifying', title: '排位与发车', icon: '🏁', desc: '本场排位赛表现，赛前已知且对结果影响最大', features: ['qualifying_pos', 'grid', 'qualifying_pos_inv', 'grid_inv'] },
  { key: 'driver_season', title: '车手赛季状态', icon: '📊', desc: '本赛季截至上一轮的累计表现（积分/胜场/退赛/平均位次）', features: ['driver_season_points_before', 'driver_season_races_before', 'driver_season_wins_before', 'driver_season_dnfs_before', 'driver_season_avg_pos_before'] },
  { key: 'driver_recent', title: '近 5 场状态', icon: '🔥', desc: '跨赛季最近 5 场比赛表现，反映近期状态', features: ['driver_last5_avg_pos', 'driver_last5_dnfs'] },
  { key: 'driver_circuit', title: '赛道历史', icon: '🏎️', desc: '该车手在此赛道的历史成绩（赛道适配度）', features: ['driver_circuit_avg_pos', 'driver_circuit_races', 'driver_circuit_dnfs'] },
  { key: 'constructor', title: '车队趋势', icon: '🏭', desc: '车队本赛季截至上一轮的整体表现', features: ['constructor_season_points_before', 'constructor_season_avg_pos_before', 'constructor_season_dnfs_before'] },
  { key: 'context', title: '赛季上下文', icon: '📅', desc: '规则时代（2022 地面效应新规）与赛季进度', features: ['regulation_era', 'round_normalized'] },
  { key: 'weather', title: '环境与天气', icon: '🌦️', desc: '正赛实际天气（FastF1 记录）。未来分站/数据缺失时为中性值', features: ['weather_is_wet', 'weather_air_temp', 'weather_track_temp', 'weather_max_rainfall', 'weather_humidity'] },
]

const RULE_FEATURE_GROUPS = [
  { key: 'rule', title: '规则模型特征', icon: '⚖️', desc: 'rule_v1 规则加权模型使用的 5 个特征', features: ['championship_ratio', 'recent_avg_pos', 'win_rate', 'dnf_rate'] },
]

// 当前展开车手的预测条目
const expandedPrediction = computed(
  () => predictions.value.find((p) => p.driver_code === expandedDriver.value) || null
)

// 展开详情中的特征分组（自动过滤旧 19 特征记录中不存在的键）
const activeFeatureGroups = computed(() => {
  if (!expandedPrediction.value) return []
  const feats = expandedPrediction.value.features || {}
  const baseGroups = isXgb.value ? FEATURE_GROUPS : RULE_FEATURE_GROUPS
  return baseGroups
    .map((g) => ({ ...g, visibleFeatures: g.features.filter((f) => f in feats) }))
    .filter((g) => g.visibleFeatures.length)
})

// ── 天气摘要（顶层 weather 字段，来自后端正赛天气记录）──
const weatherRaw = ref(null)
const weatherInfo = computed(() => {
  const w = weatherRaw.value
  if (!w) return null
  // 全部命中中性值 → 视为"天气数据不可用"（未来分站或拉取失败）
  const isNeutral =
    Math.abs(w.weather_is_wet - 0) < 0.01 &&
    Math.abs(w.weather_air_temp - 20) < 0.01 &&
    Math.abs(w.weather_track_temp - 30) < 0.01 &&
    Math.abs(w.weather_max_rainfall - 0) < 0.01 &&
    Math.abs(w.weather_humidity - 60) < 0.01
  return {
    is_wet: Number(w.weather_is_wet) >= 1,
    air_temp: Number(w.weather_air_temp),
    track_temp: Number(w.weather_track_temp),
    rainfall: Number(w.weather_max_rainfall),
    humidity: Number(w.weather_humidity),
    is_neutral: isNeutral,
  }
})

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

// 加载指定分站预测详情（无记录且 forceSave 时现场计算并保存）
const loadPrediction = async (forceSave = false) => {
  if (!selectedRound.value) return
  loading.value = true
  try {
    const data = await getPrediction(season.value, selectedRound.value, {
      params: { save: forceSave },
    })
    if (data.code === 200) {
      predictions.value = data.predictions || []
      modelVersion.value = data.model_version || ''
      featureCount.value = data.feature_count || null
      featureWeights.value = data.feature_weights || null
      featureImportance.value = data.feature_importance || []
      weatherRaw.value = data.weather || null
      predSource.value = data.source || ''
      predTime.value = data.from_db
        ? `预测于 ${String(data.created_at || '').replace('T', ' ').slice(0, 16)}`
        : ''
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

// 加载本赛季预测历史
const loadHistory = async () => {
  loadingHistory.value = true
  try {
    const data = await getPredictionHistory(season.value)
    if (data.code === 200) {
      historyRounds.value = data.rounds || []
    }
  } catch {
    historyRounds.value = []
  }
  loadingHistory.value = false
}

const switchView = (mode) => {
  viewMode.value = mode
  if (mode === 'history') {
    loadHistory()
  }
}

// 历史列表点击 → 切到详情视图查看该站
const viewRound = (round) => {
  selectedRound.value = round
  switchView('detail')
  loadPrediction(false) // 已有记录直接读库，不会重算
}

const onHistoryRowClick = (row) => viewRound(row.round)

const onRoundChange = (round) => {
  if (round) {
    loadPrediction(false)
  }
}

onMounted(async () => {
  await store.fetchRaceList(store.currentSeason)
  loadingRaces.value = false
  // 分站选项：本赛季全部分站（含已结束）
  raceOptions.value = (store.raceList || []).map((r) => ({
    round: Number(r.round),
    raceName: r.raceName || `R${r.round}`,
    date: r.date || '',
    isPast: Boolean(r.date) && new Date(r.date) < new Date(),
  }))
  // 默认选中即将开始的分站；没有则选第一站
  const upcoming = upcomingRace.value
  selectedRound.value = upcoming
    ? Number(upcoming.round)
    : (raceOptions.value[0]?.round || null)
  if (selectedRound.value) {
    await loadPrediction(true)
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

/* 工具条 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 10px; }

.race-title { font-size: 16px; font-weight: 700; margin-right: 8px; }
.race-date { font-size: 13px; color: #909399; }

.block { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
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

/* 天气影响摘要栏 */
.weather-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 8px 14px;
  margin-bottom: 16px;
  background: linear-gradient(90deg, rgba(64,158,255,0.08), rgba(64,158,255,0.02));
  border: 1px solid #d9ecff;
  border-radius: 6px;
  font-size: 12px;
  color: #4a6b8a;
}
.weather-bar.is-neutral {
  background: linear-gradient(90deg, rgba(230,162,60,0.08), rgba(230,162,60,0.02));
  border-color: #f3d19e;
  color: #8a6a3a;
}
.weather-emoji { font-size: 16px; }
.weather-cond { font-weight: 700; }
.weather-sep { color: #c0c4cc; }
.weather-neutral-tag {
  padding: 1px 8px;
  border: 1px dashed #e6a23c;
  border-radius: 10px;
  color: #e6a23c;
  cursor: help;
  font-size: 11px;
}

/* 特征分组折叠 */
.feature-groups { margin-top: 4px; }
.group-desc {
  font-size: 11px;
  color: #909399;
  margin-bottom: 6px;
}

.chart { width: 100%; height: 350px; }

/* 历史表格 */
.history-table { cursor: pointer; }
.round-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  padding: 2px 8px;
  background: #f0f2f5;
  border-radius: 4px;
  font-weight: 700;
  font-size: 12px;
  color: #606266;
}
.top3-mini { display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600; }
.mini-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px; height: 16px;
  border-radius: 50%;
  font-size: 10px;
  color: #fff;
  background: #909399;
}
.mini-rank:nth-child(1) { background: #e10600; }
.mini-prob { font-size: 11px; color: #909399; font-weight: 400; }
.mini-sep { color: #dcdfe6; }
.history-tip {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}
</style>
