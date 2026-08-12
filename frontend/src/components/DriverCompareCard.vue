/**
 * DriverCompareCard — 车手对比卡片
 * GP Tempo 风格：左上角悬浮，显示车手代码 + 圈速 + delta
 */
<template>
  <div class="driver-compare-card" v-if="drivers.length > 0">
    <div class="card-header">
      <span class="card-title">车手对比</span>
      <span class="card-sub" v-if="lapInfo">Lap {{ lapInfo }}</span>
    </div>
    <div class="driver-list">
      <div
        v-for="(d, i) in drivers"
        :key="d.code"
        class="driver-row"
        :style="{ '--driver-color': d.color || '#e10600' }"
      >
        <div class="driver-code" :style="{ background: d.color || '#e10600' }">
          {{ d.code }}
        </div>
        <div class="driver-info">
          <div class="driver-name">{{ d.name || d.code }}</div>
          <div class="driver-laptime mono">{{ d.lapTime || '--:--.---' }}</div>
        </div>
        <div class="driver-delta mono" :class="deltaClass(d.delta)">
          {{ formatDelta(d.delta) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  drivers: { type: Array, default: () => [] },
  lapInfo: { type: [String, Number], default: '' },
})

function deltaClass(delta) {
  if (!delta) return ''
  const d = typeof delta === 'string' ? parseFloat(delta) : delta
  if (d < 0) return 'faster'
  if (d > 0) return 'slower'
  return ''
}

function formatDelta(delta) {
  if (delta === null || delta === undefined) return ''
  const d = typeof delta === 'string' ? parseFloat(delta) : delta
  if (d === 0) return 'BASE'
  const sign = d > 0 ? '+' : ''
  return `${sign}${d.toFixed(3)}s`
}
</script>

<style scoped>
.driver-compare-card {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  background: rgba(26, 26, 26, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid var(--f1-border);
  border-radius: 10px;
  padding: 12px 14px;
  min-width: 220px;
  max-width: 300px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--f1-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-sub {
  font-size: 11px;
  color: var(--f1-text-muted);
}

.driver-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.driver-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.driver-code {
  width: 36px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 800;
  color: #000;
  flex-shrink: 0;
}

.driver-info {
  flex: 1;
  min-width: 0;
}

.driver-name {
  font-size: 12px;
  color: var(--f1-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.driver-laptime {
  font-size: 14px;
  font-weight: 600;
  color: var(--f1-text-primary);
}

.driver-delta {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.driver-delta.faster {
  color: var(--f1-success);
}

.driver-delta.slower {
  color: var(--f1-red);
}
</style>
