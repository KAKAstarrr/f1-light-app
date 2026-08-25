# -*- coding: utf-8 -*-
"""第三部分：前端 Vue3 全面知识点（2A.1-2A.9 + 2B.0 全局优化）"""

FRONTEND_INTRO = (
    "本部分对应项目「前端 Vue3」全部知识点：组合式 API、axios 拦截器、Pinia 状态管理、"
    "Vue Router、Element Plus、Composables 复用、全局优化（分站锁定/常量工具）、Vite 代理。"
    "前端技术栈：Vue 3.5 + Vite + Vue Router + Pinia + Element Plus + axios + ECharts。"
)

UNITS = [
{
    "id": "2.1",
    "title": "Vue3 组合式 API 核心",
    "concept": [
        "组合式 API（Composition API）是 Vue3 的组织代码方式：把相关逻辑按功能聚合（而不是按 data/methods 选项切分），通过 ref/reactive/computed/watch 管理响应式状态。",
        ("h3", "四大响应式 API"),
        ("table", ["API", "用途", "示例", "注意"], [
            ["ref", "基础类型响应式", "const year = ref(2025)", "取值/赋值要 .value"],
            ["reactive", "对象/数组响应式", "const state = reactive({list: []})", "直接属性访问"],
            ["computed", "派生状态", "const label = computed(() => `${year.value}赛季`)", "有缓存，依赖变化才重算"],
            ["watch", "副作用监听", "watch(year, (v) => fetchData(v))", "可 deep/immediate"],
        ], [1.6, 3.2, 5.0, 4.5]),
        ("h3", "示例：年份选择联动"),
        ("code", "import { ref, computed, watch } from 'vue'\n\n"
                "const year = ref(2025)\n"
                "const yearOptions = [2026, 2025, 2024, 2023]\n\n"
                "// computed：派生展示文案\n"
                "const yearLabel = computed(() => `${year.value} 赛季`)\n\n"
                "// watch：年份变化自动重新拉数据\n"
                "watch(year, (newVal) => {\n"
                "  loadRaceCalendar(newVal)\n"
                "})",
                "Composition API 使用"),
        ("h3", "生命周期与模板"),
        ("bullet", "onMounted：组件挂载后请求数据（替代 options 的 mounted）。", "生命周期"),
        ("bullet", "模板中 ref 自动解包：{{ year }} 无需 .value；脚本里必须 year.value。", "自动解包"),
        ("bullet", "v-for 必须绑定 :key（唯一值，如车手代号），否则列表复用出错。", "v-for key"),
    ],
    "pits": [
        (".value 遗漏", "脚本里忘记 .value 是 Vue3 初学者第一高频错误：模板正常、逻辑报 undefined。"),
        ("响应式丢失", "用 const { list } = reactive(...) 解构会丢失响应式，必须用 toRefs 或直接用 state.list。"),
    ],
    "qa": [
        ("Vue3 组合式 API 相比选项式 API 的优势？", "① 逻辑聚合：相关代码放一起（选项式按 data/methods 切分，相关逻辑被拆散）；② 复用性：逻辑可抽成 composable 函数跨组件复用；③ 类型推导更好（TS 友好）；④ 代码量减少（setup 内直接写）。"),
        ("ref 和 reactive 怎么选？", "标量/字符串/布尔用 ref；深层对象/数组用 reactive；两者可混用。ref 也能包对象（内部转 reactive），但模板中对象 ref 自动解包规则不同，统一用 ref 更不容易踩坑。"),
        ("computed 和 watch 的区别？", "computed 是派生值（有缓存、同步返回、用于模板渲染）；watch 是副作用（监听变化执行操作，如发请求、写日志）。能 computed 就不用 watch。"),
    ],
},
{
    "id": "2.2",
    "title": "axios 拦截器与请求封装",
    "concept": [
        "统一封装 axios：baseURL 为空字符串走 Vite proxy；请求拦截器附加 JWT；响应拦截器处理两种响应格式（Ergast 数据本体 vs FastF1 的 {code,...}）并统一错误处理。",
        ("h3", "request.js 核心"),
        ("code", "import axios from 'axios'\n\n"
                "const request = axios.create({\n"
                "  baseURL: '',            // 走 Vite proxy /api -> 8010\n"
                "  timeout: 15000,\n"
                "})\n\n"
                "// 请求拦截器：附加 JWT\n"
                "request.interceptors.request.use((config) => {\n"
                "  const token = localStorage.getItem('token')\n"
                "  if (token) config.headers.Authorization = `Bearer ${token}`\n"
                "  return config\n"
                "})\n\n"
                "// 响应拦截器：统一解包 + 统一错误提示\n"
                "request.interceptors.response.use(\n"
                "  (res) => res.data,                 // 直接拿 data，组件里不用 res.data.data\n"
                "  (err) => {\n"
                "    ElMessage.error(err.response?.data?.msg || '请求失败')\n"
                "    return Promise.reject(err)\n"
                "  }\n"
                ")",
                "frontend/src/api/request.js"),
        ("h3", "双格式兼容约定"),
        ("bullet", "Ergast 系接口返回数据本体（无 code 字段）；FastF1 系接口返回 {code, data}。", "格式差异"),
        ("bullet", "组件层约定：FastF1 接口先判 code===200 再取数据；Ergast 接口直接取字段。", "统一约定"),
    ],
    "pits": [
        ("双重 .data", "响应拦截器已解包 res.data，组件里再写 res.data.data 会 undefined——前后端接口都要统一返回结构。"),
        ("超时", "遥测接口（FastF1 处理慢）单独设 60s 超时，其他接口保持 15s，否则 FastF1 首拉数据必超时。"),
    ],
    "qa": [
        ("axios 拦截器解决了什么问题？", "① 请求拦截器统一加鉴权头（JWT），不用每个接口手动带 token；② 响应拦截器统一解包、统一错误提示、统一状态码处理；③ 业务代码只关心数据，关注点分离。"),
        ("为什么 baseURL 设为空字符串？", "开发期由 Vite proxy 把 /api 转发到后端 8010，规避 CORS；生产环境由 Nginx 做同样转发。前端代码不硬编码后端地址，部署灵活。"),
        ("接口超时设置怎么定？", "按接口耗时特征区分：常规接口 15s（Ergast 缓存命中很快）；FastF1 遥测接口首次要下载 50-100MB 数据，60s+。统一超时会导致慢接口误判失败。"),
    ],
},
{
    "id": "2.3",
    "title": "Pinia 状态管理与缓存层",
    "concept": [
        "Pinia 是 Vue3 官方推荐状态管理库。本项目用它做全局共享状态 + 数据缓存层（driverCache/raceListCache + 10 分钟 TTL），避免每个页面重复请求同一数据。",
        ("h3", "Store 定义与 TTL 缓存"),
        ("code", "// stores/useAppStore.js\n"
                "import { defineStore } from 'pinia'\n\n"
                "export const useAppStore = defineStore('app', {\n"
                "  state: () => ({\n"
                "    currentSeason: 2025,\n"
                "    driverCache: {},        // code -> 车手信息\n"
                "    raceListCache: {},      // year -> 赛程列表\n"
                "    lastFetchTime: {},      // key -> 时间戳\n"
                "  }),\n"
                "  actions: {\n"
                "    fetchDrivers(year) {\n"
                "      const key = `drivers_${year}`\n"
                "      // 10 分钟 TTL\n"
                "      if (this.driverCache[key] &&\n"
                "          Date.now() - this.lastFetchTime[key] < 10 * 60 * 1000) {\n"
                "        return this.driverCache[key]\n"
                "      }\n"
                "      const drivers = api.getDrivers(year)\n"
                "      this.driverCache[key] = drivers\n"
                "      this.lastFetchTime[key] = Date.now()\n"
                "      return drivers\n"
                "    },\n"
                "  },\n"
                "})",
                "stores/useAppStore.js"),
        ("h3", "组件中使用"),
        ("bullet", "`const store = useAppStore()` 后组件内可直接 store.currentSeason。", "直接访问"),
        ("bullet", "需要保持响应式解构时用 `storeToRefs(store)`（Pinia 专用，解构不丢响应式）。", "storeToRefs"),
        ("bullet", "2026 年（未开始赛季）车手数据用 mock 返回，fetchDrivers action 内处理。", "mock 兜底"),
    ],
    "pits": [
        ("解构丢响应式", "const { currentSeason } = store 会丢失响应式，必须 storeToRefs。"),
        ("缓存键", "缓存 key 必须与请求参数对应（drivers_2025），漏参数会导致跨年份数据串台。"),
    ],
    "qa": [
        ("为什么需要 Pinia？和 Vuex 比呢？", "Pinia 是 Vuex 的继任者：更轻量（去掉 mutations，actions 直接改 state）、类型友好、支持组合式写法、devtools 支持好。本项目用它做全局年份状态 + 数据缓存，避免各页面重复请求。"),
        ("前端缓存与后端缓存的区别？", "后端缓存（三级缓存）省网络与计算；前端 store 缓存省 HTTP 请求、提升切换页面速度。本项目两层都用：前端 TTL 10 分钟避免重复拉取，后端 TTL 1 小时避免打源。"),
        ("storeToRefs 是什么？为什么要用它？", "Pinia 提供的解构工具，把 store 的 state/getters 解构为 ref 并保持响应式；普通解构会把原始值拷贝出来丢失响应式。actions 直接解构即可（本来就是函数）。"),
    ],
},
{
    "id": "2.4",
    "title": "Vue Router 路由与守卫",
    "concept": [
        "Vue Router 负责单页应用的路由映射。本项目按页面懒加载，守卫控制登录态。",
        ("h3", "路由配置"),
        ("code", "// router/index.js\n"
                "import { createRouter, createWebHistory } from 'vue-router'\n\n"
                "const routes = [\n"
                "  { path: '/', component: () => import('@/pages/Home.vue') },\n"
                "  { path: '/races', component: () => import('@/pages/RaceCalendar.vue') },\n"
                "  { path: '/telemetry', component: () => import('@/pages/TeleCompare.vue') },\n"
                "  { path: '/fantasy', component: () => import('@/pages/Fantasy.vue'),\n"
                "    meta: { requiresAuth: true } },\n"
                "]\n\n"
                "const router = createRouter({\n"
                "  history: createWebHistory(),\n"
                "  routes,\n"
                "})\n\n"
                "// 全局前置守卫：未登录跳登录页\n"
                "router.beforeEach((to) => {\n"
                "  if (to.meta.requiresAuth && !localStorage.getItem('token')) {\n"
                "    return { path: '/login' }\n"
                "  }\n"
                "})",
                "router/index.js"),
        ("bullet", "动态 import 组件 → 路由懒加载，首屏只加载当前页代码，优化性能。", "懒加载"),
        ("bullet", "守卫返回路由对象即重定向；返回 false 取消导航；不 return 放行。", "守卫约定"),
    ],
    "pits": [
        ("废弃 API", "Vue Router 4 中守卫的 next() 已废弃（保留兼容），应直接 return 路由对象，避免控制台 Deprecation 警告。"),
        ("路径拼接", "路由 path 与后端接口路径、页面文件名三处保持一致，曾因 path 拼错导致页面 404。"),
    ],
    "qa": [
        ("路由懒加载是什么？为什么用？", "组件通过 () => import() 动态导入，webpack/Vite 会按路由拆包（code splitting），用户访问该路由时才下载对应 JS，首屏体积变小、加载变快。"),
        ("路由守卫有哪些？各什么时候用？", "全局守卫（beforeEach，登录校验/埋点）、路由级守卫（beforeEnter，页面独有校验）、组件内守卫（onBeforeRouteUpdate，参数变化处理）。本项目用全局 beforeEach 做登录拦截。"),
    ],
},
{
    "id": "2.5",
    "title": "Element Plus 组件库",
    "concept": [
        "Element Plus 是 Vue3 的中文优先 UI 组件库（对标 Element UI for Vue2）。本项目用它构建表格、表单、选择器、消息提示。",
        ("h3", "高频组件用法"),
        ("code", "<template>\n"
                "  <el-select v-model=\"year\" @change=\"onYearChange\">\n"
                "    <el-option v-for=\"y in yearOptions\" :key=\"y\" :value=\"y\" :label=\"`${y} 赛季`\" />\n"
                "  </el-select>\n\n"
                "  <el-table :data=\"results\" stripe>\n"
                "    <el-table-column prop=\"position\" label=\"名次\" width=\"70\" />\n"
                "    <el-table-column prop=\"driver\" label=\"车手\" />\n"
                "    <el-table-column label=\"积分\">\n"
                "      <template #default=\"{ row }\">\n"
                "        <span>{{ row.points }}</span>\n"
                "      </template>\n"
                "    </el-table-column>\n"
                "  </el-table>\n"
                "</template>",
                "表格 + 下拉示例"),
        ("bullet", "表单校验：el-form 的 rules + prop，配合后端 Pydantic 双重校验。", "表单校验"),
        ("bullet", "ElMessage/ElMessageBox 用于全局提示与确认弹窗（注册页校验、删除确认）。", "反馈组件"),
    ],
    "pits": [
        ("废弃 API", "el-checkbox 的 label 属性在 Element Plus 2.6+ 已废弃（改为 value），控制台警告需及时按版本升级。"),
    ],
    "qa": [
        ("Element Plus 和原生 HTML 表单的区别？", "组件化封装（样式/交互/校验开箱即用）、响应式布局、中文文档与生态。缺点是体积较大，可用按需引入（unplugin-vue-components）优化。"),
        ("el-table 自定义列怎么做？", "el-table-column 内嵌 template #default=\"{row}\" 插槽，可放任意自定义渲染（标签、按钮、条件样式）。"),
    ],
},
{
    "id": "2.6",
    "title": "Composables 复用与全局常量",
    "concept": [
        "Composables 是「以 use 开头的组合函数」，把跨组件复用的逻辑抽出来。本项目沉淀了 useYearSelection（年份选择+store 同步）、useNextRace（下一站计算）；utils 层沉淀 f1-constants.js。",
        ("h3", "useNextRace 核心逻辑"),
        ("code", "// composables/useNextRace.js\n"
                "import { computed } from 'vue'\n\n"
                "export function useNextRace(races) {\n"
                "  const now = new Date()\n\n"
                "  // 进行中：比赛日期 <= 今天 且 结束日期 >= 今天\n"
                "  const ongoingRace = computed(() => races.value.find(\n"
                "    (r) => new Date(r.date) <= now && new Date(r.endDate) >= now))\n\n"
                "  // 下一场：日期最早大于今天的比赛\n"
                "  const upcomingRace = computed(() => races.value\n"
                "    .filter((r) => new Date(r.date) > now)\n"
                "    .sort((a, b) => new Date(a.date) - new Date(b.date))[0])\n\n"
                "  // 上一场：最近一场已结束的比赛\n"
                "  const lastCompletedRace = computed(() => races.value\n"
                "    .filter((r) => new Date(r.endDate) < now)\n"
                "    .sort((a, b) => new Date(b.date) - new Date(a.date))[0])\n\n"
                "  return { upcomingRace, ongoingRace, lastCompletedRace }\n"
                "}",
                "composables/useNextRace.js"),
        ("h3", "f1-constants.js 常量工具"),
        ("bullet", "YEAR_OPTIONS（年份下拉）、MOCK_2026_DRIVERS（2026 未开赛 mock 车手）。", "常量"),
        ("bullet", "TEAM_COLORS（车队色板）、COMPOUND_COLORS（轮胎配方色板）、rankTagType（名次标签样式映射）。", "色板"),
        ("bullet", "driverName()（车手代号转全名）、isYear2026()、filterChannelsForYear()（2026 自动隐藏 DRS 通道）。", "工具函数"),
    ],
    "qa": [
        ("什么是 Composables？解决了什么问题？", "以 use 开头的组合函数，把跨组件共享的响应式逻辑（状态 + 方法 + 生命周期）封装复用，替代 mixins 的命名冲突和来源不明问题。useNextRace 被多个页面复用计算下一站/进行中/上一场。"),
        ("useNextRace 是怎么判断「进行中」的？", "用比赛起止日期区间：date <= now <= endDate 判定进行中（周末三天的比赛）；未来日期最小者为 upcoming；已结束最近一场为 lastCompleted。三个 computed 从同一份赛程列表派生。"),
    ],
},
{
    "id": "2.7",
    "title": "全局优化：分站锁定与年份统一",
    "concept": [
        "项目做了三项全局优化，体现工程化思维：",
        ("h3", "① 年份选择统一"),
        ("bullet", "yearOptions = [2026, 2025, 2024, 2023]，初始值从 store.currentSeason 读取。", "统一"),
        ("bullet", "useYearSelection() 封装「选择年份 + 同步到 store」，所有页面复用，避免各自维护。", "封装"),
        ("h3", "② 分站锁定逻辑"),
        ("bullet", "AI 预测 / Fantasy：只能选「即将开始」的一站（未开始的前一站），下拉锁定不可切换。", "锁定规则"),
        ("bullet", "投票：只能选「进行中」的一站，下方展示上一场结果作为参考。", "投票规则"),
        ("bullet", "三个业务（预测/Fantasy/投票）锁定逻辑完全独立，互不影响。", "独立性"),
        ("h3", "③ 2026 适配"),
        ("bullet", "2026 赛季未开始：车手数据返回 mock、DRS 通道自动隐藏、未举办分站显示「分站暂未开始」。", "2026 降级"),
    ],
    "qa": [
        ("「分站锁定」解决了什么用户痛点？", "预测/Fantasy 必须在下注截止前锁定目标分站。若允许切换任意一站，用户可「赛后马后炮」，产品规则失效。锁定到即将开始的一站保证公平与玩法闭环。"),
        ("全局优化从哪些维度做？", "① 复用性（composables/常量工具）；② 一致性（年份统一、颜色统一）；③ 健壮性（mock 兜底、未开始降级）；④ 性能（store 缓存 + 懒加载）。"),
    ],
},
{
    "id": "2.8",
    "title": "Vite 与开发代理",
    "concept": [
        "Vite 是新一代前端构建工具（开发期 ESM 原生、秒级热更新；生产 rollup 打包）。本项目用其 dev server proxy 解决跨域。",
        ("h3", "vite.config.js"),
        ("code", "import { defineConfig } from 'vite'\n"
                "import vue from '@vitejs/plugin-vue'\n\n"
                "export default defineConfig({\n"
                "  plugins: [vue()],\n"
                "  server: {\n"
                "    proxy: {\n"
                "      '/api': {\n"
                "        target: 'http://localhost:8010',\n"
                "        changeOrigin: true,\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "})",
                "vite.config.js"),
        ("bullet", "前端请求 /api/xxx → Vite 转发到 http://localhost:8010/api/xxx。", "转发规则"),
        ("bullet", "5173 被占用时 Vite 自动切 5174，CORS 白名单需同时覆盖。", "端口漂移"),
    ],
    "qa": [
        ("Vite 相比 webpack 的优势？", "开发期基于原生 ESM：无需打包、按需编译，冷启动与 HMR 秒级；配置更简洁（插件体系）；构建用 Rollup 更高效。新一代 Vue 官方脚手架默认 Vite。"),
        ("Vite proxy 和 Nginx 代理的区别？", "Vite proxy 仅开发期生效（node 服务转发）；Nginx 是生产环境反向代理。两者目的相同：统一 /api 入口、规避 CORS、隐藏后端真实地址。"),
    ],
},
{
    "id": "2.9",
    "title": "前端综合面试问答",
    "qa": [
        ("讲一下这个项目前端的技术架构？", "Vue 3.5 + Vite + Vue Router（懒加载+守卫）+ Pinia（全局状态+TTL 缓存）+ Element Plus（UI）+ ECharts（遥测图表）+ axios（拦截器封装）。目录按 pages/api/stores/router/components/composables/utils 分层，数据请求统一走 request.js。"),
        ("列表页数据量很大时怎么优化？", "① 分页/虚拟滚动（el-table 大数据用虚拟滚动）；② 后端裁剪字段；③ 前端 store 缓存；④ ECharts 大数据降采样；⑤ 懒加载路由。本项目遥测图对 300+ 点做了采样渲染。"),
        ("ECharts 多图表联动怎么做？", "echarts.connect(图1, 图2, 图3) 或 connect 组 id，共享 tooltip/缩放/数据视图。TeleCompare 页速度/油门刹车/Delta 三图用 connect 实现同轴联动。"),
        ("前端怎么处理后端返回的 500？", "请求封装统一拦截：错误响应弹 ElMessage + Promise.reject；业务层针对 {code:500} 展示降级文案（如「分站暂未开始」「数据暂不可用」），保证页面不白屏。"),
    ],
},
]
