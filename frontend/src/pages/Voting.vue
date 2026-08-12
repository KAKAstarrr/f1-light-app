/**
 * Voting — 投票独立入口
 * 复用 Vote.vue 全部逻辑，暗色主题通过全局样式适配
 */
<template>
  <div class="voting-page">
    <Vote />
  </div>
</template>

<script setup>
import Vote from '@/pages/Vote.vue'
</script>

<style scoped>
.voting-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
