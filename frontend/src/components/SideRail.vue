/**
 * SideRail — 通用侧边快捷栏
 * 收藏分站 + 2026 新规标注 + 快捷信息
 */
<template>
  <aside class="side-rail">
    <!-- 收藏分站 -->
    <div class="rail-section">
      <div class="rail-title">
        <span>⭐ 收藏分站</span>
      </div>
      <div v-if="favorites.length === 0" class="rail-empty">
        点击分站旁的 ⭐ 收藏
      </div>
      <div v-else class="fav-list">
        <div
          v-for="fav in favorites"
          :key="fav.key"
          class="fav-item"
          @click="goToRace(fav)"
        >
          <span class="fav-flag">{{ fav.flag }}</span>
          <span class="fav-name">{{ fav.name }}</span>
          <span class="fav-remove" @click.stop="removeFav(fav.key)">✕</span>
        </div>
      </div>
    </div>

    <!-- 2026 新规标注 -->
    <div class="rail-section">
      <div class="rail-title">
        <span>📋 2026 新规</span>
      </div>
      <div class="notice-list">
        <div class="notice-item">
          <span class="notice-dot warn"></span>
          <span>DRS 数据暂不可用</span>
        </div>
        <div class="notice-item">
          <span class="notice-dot info"></span>
          <span>使用 Ergast 镜像数据源</span>
        </div>
        <div class="notice-item">
          <span class="notice-dot ok"></span>
          <span>遥测数据由 FastF1 提供</span>
        </div>
      </div>
    </div>

    <!-- 快捷信息 -->
    <div class="rail-section">
      <div class="rail-title">
        <span>🏁 赛季进度</span>
      </div>
      <div class="progress-info">
        <div class="progress-text">
          {{ completedCount }} / {{ totalCount }} 站已完成
        </div>
        <el-progress
          :percentage="progressPercent"
          :stroke-width="6"
          :show-text="false"
          color="#e10600"
        />
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useF1Store } from '@/stores/f1'

const router = useRouter()
const store = useF1Store()

const FAV_KEY = 'f1_favorite_races'

const favorites = ref([])

const totalCount = computed(() => store.raceList.length)

const completedCount = computed(() => {
  const now = new Date()
  return store.raceList.filter(r => {
    const d = new Date(r.date + 'T23:59:59')
    return d < now
  }).length
})

const progressPercent = computed(() => {
  if (!totalCount.value) return 0
  return Math.round((completedCount.value / totalCount.value) * 100)
})

onMounted(() => {
  loadFavorites()
})

function loadFavorites() {
  try {
    const raw = localStorage.getItem(FAV_KEY)
    if (raw) favorites.value = JSON.parse(raw)
  } catch (e) {
    favorites.value = []
  }
}

function saveFavorites() {
  localStorage.setItem(FAV_KEY, JSON.stringify(favorites.value))
}

function removeFav(key) {
  favorites.value = favorites.value.filter(f => f.key !== key)
  saveFavorites()
}

function goToRace(fav) {
  router.push(`/race-center?tab=detail&year=${fav.year}&round=${fav.round}`)
}

// 暴露给父组件调用
defineExpose({
  addFavorite(race) {
    const key = `${race.season}_${race.round}`
    if (favorites.value.find(f => f.key === key)) return
    favorites.value.push({
      key,
      year: Number(race.season),
      round: Number(race.round),
      name: race.raceName,
      flag: '🏁',
    })
    saveFavorites()
  },
  isFavorite(season, round) {
    return favorites.value.some(f => f.year === Number(season) && f.round === Number(round))
  },
  toggleFavorite(race) {
    const key = `${race.season}_${race.round}`
    if (this.isFavorite(race.season, race.round)) {
      this.removeFav(key)
    } else {
      this.addFavorite(race)
    }
  }
})
</script>

<style scoped>
.side-rail {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rail-section {
  background: var(--f1-bg-card);
  border: 1px solid var(--f1-border);
  border-radius: 8px;
  padding: 14px;
}

.rail-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--f1-text-secondary);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rail-empty {
  font-size: 12px;
  color: var(--f1-text-muted);
  padding: 8px 0;
}

.fav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.fav-item:hover {
  background: var(--f1-bg-hover);
}

.fav-flag {
  font-size: 14px;
}

.fav-name {
  flex: 1;
  font-size: 12px;
  color: var(--f1-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-remove {
  font-size: 10px;
  color: var(--f1-text-muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}

.fav-item:hover .fav-remove {
  opacity: 1;
}

.fav-remove:hover {
  color: var(--f1-red);
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notice-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--f1-text-secondary);
}

.notice-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.notice-dot.warn { background: var(--f1-warning); }
.notice-dot.info { background: var(--f1-info); }
.notice-dot.ok { background: var(--f1-success); }

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-text {
  font-size: 12px;
  color: var(--f1-text-secondary);
}

@media (max-width: 1200px) {
  .side-rail {
    display: none;
  }
}
</style>
