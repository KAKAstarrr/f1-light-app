/**
 * FilterBar — 通用筛选栏
 * 年份/分站/车手多选 + 可选的"深度分析"跳转按钮
 * GP Tempo 风格：暗色横条
 */
<template>
  <div class="filter-bar">
    <div class="filter-left">
      <!-- 年份 -->
      <el-select
        v-model="localYear"
        placeholder="赛季"
        style="width: 120px"
        @change="onYearChange"
      >
        <el-option v-for="y in yearOptions" :key="y" :label="`${y} 赛季`" :value="y" />
      </el-select>

      <!-- 分站 -->
      <el-select
        v-model="localRound"
        placeholder="选择分站"
        style="width: 200px"
        filterable
        @change="onRoundChange"
      >
        <el-option
          v-for="r in store.raceList"
          :key="r.round"
          :label="`R${r.round} ${r.raceName}`"
          :value="Number(r.round)"
        />
      </el-select>

      <!-- 车手多选 -->
      <el-select
        v-if="showDrivers"
        v-model="localDrivers"
        placeholder="选择车手"
        multiple
        collapse-tags
        collapse-tags-tooltip
        style="min-width: 200px; max-width: 400px"
        @change="onDriversChange"
      >
        <el-option
          v-for="d in driverOptions"
          :key="d.code"
          :label="`${d.code} - ${d.givenName} ${d.familyName}`"
          :value="d.code"
        />
      </el-select>

      <!-- Session Type -->
      <el-select
        v-if="showSessionType"
        v-model="localSessionType"
        style="width: 100px"
        @change="onSessionTypeChange"
      >
        <el-option label="正赛 R" value="R" />
        <el-option label="Q1" value="Q1" />
        <el-option label="Q2" value="Q2" />
        <el-option label="Q3" value="Q3" />
        <el-option label="排位 Q" value="Q" />
      </el-select>

      <!-- 加载/刷新按钮 -->
      <el-button type="primary" :loading="loading" @click="onLoad">
        {{ loadLabel }}
      </el-button>
    </div>

    <div class="filter-right">
      <!-- 深度分析跳转 -->
      <el-button v-if="showJump" type="default" @click="jumpToTelemetry">
        📈 深度分析 →
      </el-button>
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'
import { YEAR_OPTIONS } from '@/utils/f1-constants'

const props = defineProps({
  modelYear: { type: Number, default: 2026 },
  modelRound: { type: [Number, String], default: null },
  modelDrivers: { type: Array, default: () => [] },
  modelSessionType: { type: String, default: 'R' },
  showDrivers: { type: Boolean, default: true },
  showSessionType: { type: Boolean, default: false },
  showJump: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
  loadLabel: { type: String, default: '加载数据' },
})

const emit = defineEmits([
  'update:modelYear',
  'update:modelRound',
  'update:modelDrivers',
  'update:modelSessionType',
  'load',
])

const router = useRouter()
const store = useF1Store()

const yearOptions = YEAR_OPTIONS
const localYear = ref(props.modelYear)
const localRound = ref(props.modelRound)
const localDrivers = ref([...props.modelDrivers])
const localSessionType = ref(props.modelSessionType)
const driverOptions = ref([])

watch(() => props.modelYear, (v) => { localYear.value = v })
watch(() => props.modelRound, (v) => { localRound.value = v })
watch(() => props.modelDrivers, (v) => { localDrivers.value = [...v] })
watch(() => props.modelSessionType, (v) => { localSessionType.value = v })

onMounted(async () => {
  await store.fetchRaceList(localYear.value)
  await loadDrivers()
})

async function onYearChange() {
  emit('update:modelYear', localYear.value)
  await store.fetchRaceList(localYear.value)
  await loadDrivers()
  localRound.value = null
  emit('update:modelRound', null)
}

function onRoundChange() {
  emit('update:modelRound', localRound.value)
}

function onDriversChange() {
  emit('update:modelDrivers', localDrivers.value)
}

function onSessionTypeChange() {
  emit('update:modelSessionType', localSessionType.value)
}

async function loadDrivers() {
  try {
    driverOptions.value = await store.fetchDrivers(localYear.value)
  } catch (e) {
    driverOptions.value = []
  }
}

function onLoad() {
  emit('load')
}

function jumpToTelemetry() {
  const params = new URLSearchParams()
  if (localYear.value) params.set('year', localYear.value)
  if (localRound.value) params.set('round', localRound.value)
  if (localDrivers.value.length) params.set('drivers', localDrivers.value.join(','))
  router.push(`/telemetry?${params.toString()}`)
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
