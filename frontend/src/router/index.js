import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // ========== 一级入口 ==========

  // 1. 赛事数据中心
  {
    path: '/race-center',
    name: 'race-center',
    component: () => import('@/pages/RaceCenter.vue'),
    meta: { title: '赛事数据中心' },
    children: [
      { path: '', redirect: '/race-center?tab=overview' },
    ],
  },

  // 2. 遥测分析
  {
    path: '/telemetry',
    name: 'telemetry',
    component: () => import('@/pages/TelemetryCockpit.vue'),
    meta: { title: '遥测分析' },
  },

  // 3. AI 预测
  {
    path: '/prediction',
    name: 'prediction',
    component: () => import('@/pages/Prediction.vue'),
    meta: { title: 'AI 预测分析' },
  },

  // 4. Fantasy 管理中心
  {
    path: '/fantasy',
    name: 'fantasy',
    component: () => import('@/pages/FantasyCenter.vue'),
    meta: { title: 'Fantasy 管理中心' },
  },

  // 5. 车手投票
  {
    path: '/vote',
    name: 'vote',
    component: () => import('@/pages/Voting.vue'),
    meta: { title: '车手投票' },
  },

  // ========== 旧 URL 重定向（13 个 → 新入口）==========

  // 首页 → 赛事数据中心
  { path: '/', redirect: '/race-center' },

  // 旧赛事页面 → 赛事中心
  { path: '/results', redirect: '/race-center?tab=detail' },
  { path: '/results/:year?/:round?', redirect: to => `/race-center?tab=detail&year=${to.params.year || ''}&round=${to.params.round || ''}` },
  { path: '/standings', redirect: '/race-center?tab=standings' },

  // 旧数据分析页面 → 遥测分析
  { path: '/lap-rank', redirect: '/telemetry?layer=lap-rank' },
  { path: '/sector-fastest', redirect: '/telemetry?layer=sector-fastest' },
  { path: '/tele-compare', redirect: '/telemetry?layer=telemetry' },
  { path: '/lap-distribution', redirect: '/telemetry?layer=lap-distribution' },
  { path: '/speed-overlay', redirect: '/telemetry?layer=speed-overlay' },
  { path: '/track-map', redirect: '/telemetry?layer=track-map' },

  // 旧 Fantasy 页面 → Fantasy 管理中心
  { path: '/league', redirect: '/fantasy?tab=league' },

  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: '页面未找到' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to, from, next) => {
  const base = 'F1 数据平台'
  document.title = to.meta.title ? `${to.meta.title} - ${base}` : base
  next()
})

export default router
