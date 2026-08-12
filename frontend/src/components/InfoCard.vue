/**
 * InfoCard — 通用信息卡片
 * GP Tempo 风格：暗色卡片 + 标题 + 内容插槽
 */
<template>
  <div class="info-card" :class="{ 'no-padding': noPadding }">
    <div v-if="title || $slots.header" class="card-header">
      <slot name="header">
        <span class="card-title">{{ title }}</span>
        <span v-if="subtitle" class="card-subtitle">{{ subtitle }}</span>
      </slot>
      <div v-if="$slots.action" class="card-action">
        <slot name="action" />
      </div>
    </div>
    <div class="card-body">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  noPadding: { type: Boolean, default: false },
})
</script>

<style scoped>
.info-card {
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--f1-border);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--f1-text-primary);
}

.card-subtitle {
  font-size: 12px;
  color: var(--f1-text-muted);
  margin-left: 8px;
}

.card-action {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-body {
  padding: 16px;
}

.info-card.no-padding .card-body {
  padding: 0;
}
</style>
