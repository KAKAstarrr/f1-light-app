# F1 Light App — F1 赛事数据互动平台

> 基于 FastAPI + Ergast + FastF1 + Vue 3 的 F1 全栈分析应用。
> 已完成 **模块 A（基础数据）+ 模块 B（遥测分析：分段最快/遥测对比/圈速分布/速度叠加/赛道地图/天气）+ 模块 3A（用户鉴权）+ 模块 3B（AI 预测）+ 模块 3C（Fantasy + 投票 + 定价 + 芯片 + 联盟）**，后端 39 个 API 全部跑通。

---

## 一、技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 后端框架 | FastAPI | 自动 `/docs` 交互文档，异步支持 |
| 数据源-赛程成绩 | Ergast API（jolpi 镜像） | 免费、无需 key |
| 数据源-圈速轮胎 | FastF1 3.8.x | 官方计时数据，开源 |
| 数据库 | SQLAlchemy 2.0 + SQLite | ORM 自动建表，生产切 PostgreSQL |
| 鉴权 | python-jose (JWT) + bcrypt | 无状态鉴权，密码哈希存储 |
| 数据处理 | pandas / numpy | 圈速清洗、分组聚合 |
| 缓存 | 三级文件缓存 | Ergast JSON + FastF1 .ff1pkl + 结果 JSON |
| 前端框架 | Vue 3.5 + Vite 8 | Composition API + SFC |
| UI 组件库 | Element Plus 2.14 | 中文优先，表格/表单/布局 |
| 状态管理 | Pinia 4 | 官方推荐 |
| 路由 | Vue Router 5 | 懒加载 + 动态路由 |
| HTTP | axios | 拦截器统一处理 |
| 运行环境 | Conda `f1_project`（Python 3.11） | 独立虚拟环境 |

---

## 二、项目目录结构

```
f1_light_app/
├── backend/
│   ├── __init__.py             # Python 包标识
│   ├── main.py                 # 路由层：39 个 API + CORS + 自动建表 + 自动迁移
│   ├── data_source.py          # 数据源层：Ergast + FastF1 封装与三级缓存
│   ├── config.py               # 配置管理（DB/JWT/Fantasy 规则）
│   ├── database.py             # SQLAlchemy 引擎 + 会话 + 建表
│   ├── models.py               # 10 张 ORM 表（User/Driver/Constructor/FantasyTeam/League/...）
│   ├── schemas.py              # Pydantic 请求/响应模型
│   ├── auth.py                 # JWT 鉴权（bcrypt 哈希 + Token 签发/校验）
│   ├── game_service.py         # Fantasy 积分规则 + 动态定价
│   ├── prediction_service.py   # AI 预测（XGBoost v2 24 特征含天气，降级规则模型）
│   └── streamlit_app.py        # Streamlit 快速原型看板
│
├── frontend/
│   ├── src/
│   │   ├── api/                # axios 封装 + 接口模块
│   │   │   ├── request.js      #   拦截器（双格式响应兼容）
│   │   │   ├── race.js         #   赛程/结果接口
│   │   │   ├── driver.js      #   车手/车队接口
│   │   │   ├── telemetry.js    #   FastF1 圈速/轮胎/遥测接口
│   │   │   ├── auth.js         #   注册/登录/用户信息
│   │   │   ├── prediction.js   #   AI 预测接口
│   │   │   ├── fantasy.js      #   Fantasy 阵容/排行榜
│   │   │   └── vote.js         #   投票接口
│   │   ├── pages/              # 页面视图
│   │   │   ├── RaceList.vue    #   赛程列表页
│   │   │   ├── RaceResults.vue #   分站结果 + 最快圈 + 轮胎策略
│   │   │   ├── Standings.vue   #   车手/车队排行榜
│   │   │   ├── F1Analysis/     #   数据分析子页面
│   │   │   │   ├── LapRank.vue #   最快圈排行
│   │   │   │   ├── SectorFastest.vue # 赛道分段最快
│   │   │   │   ├── TeleCompare.vue # 遥测对比
│   │   │   │   ├── LapBoxPlot.vue  # 圈速分布箱线图
│   │   │   │   ├── SpeedOverlay.vue # 速度叠加对比
│   │   │   │   └── TrackMap.vue    # 赛道地图 SVG
│   │   │   ├── TelemetryCockpit.vue # 遥测大屏（6 图层联动）
│   │   │   ├── Prediction.vue  #   AI 预测（分站选择 + 历史回看）
│   │   │   ├── Login.vue       #   登录/注册页
│   │   │   ├── FantasyTeam.vue #   Fantasy 阵容管理（含芯片/历史）
│   │   │   ├── League.vue      #   Fantasy 联盟管理
│   │   │   ├── Vote.vue        #   最佳车手投票
│   │   │   └── NotFound.vue    #   404 页
│   │   ├── components/         # 可复用组件
│   │   ├── composables/        # 组合式函数
│   │   ├── stores/
│   │   │   ├── f1.js           #   Pinia 全局状态（赛事数据）
│   │   │   ├── user.js         #   用户状态（token/登录/退出）
│   │   │   ├── player.js       #   遥测回放播放状态
│   │   │   └── layer.js        #   遥测图层开关
│   │   ├── router/
│   │   │   └── index.js        #   路由配置（懒加载 + /login）
│   │   ├── utils/              # 工具函数
│   │   ├── assets/             # 静态资源
│   │   ├── App.vue             # 根组件（布局外壳）
│   │   └── main.js             # 应用入口
│   ├── vite.config.js
│   └── package.json
│
├── ml/                         # 机器学习模块
│   ├── notebooks/              # Jupyter 探索/训练 Notebook
│   └── models/                 # 训练好的模型文件
│
├── cache/                      # 数据缓存（.gitignore）
│   ├── ergast_cache/           # Ergast JSON 缓存（永久）
│   ├── fastf1_cache/            # FastF1 .ff1pkl 原始缓存
│   ├── fastf1_result_cache/    # FastF1 处理结果 JSON（7 天）
│   └── f1_app.db               # SQLite 数据库文件
│
├── scripts/                    # 运维脚本
│   ├── refresh_cache.sh        # 缓存刷新脚本
│   └── debug_fastf1.py         # FastF1 独立调试脚本
│
├── study/                      # 学习文档与知识点
│   ├── 01_PRD_需求文档.md
│   ├── 02_架构文档.md
│   ├── 03_接口文档.md
│   ├── 04_数据库设计.md
│   ├── 06_复盘文档.md
│   ├── 07_学习规划路线.md
│   ├── 08_Vue3前端知识点.md
│   ├── 09_阶段0_环境与基础知识点.md
│   ├── 10_阶段1_后端基础数据知识点.md
│   ├── 11_阶段3_数据库与AI预测知识点.md
│   ├── 12_阶段2_遥测分析知识点.md
│   ├── 13_阶段2_3扩展_速度叠加_赛道地图_天气_Fantasy扩展知识点.md
│   ├── data_knowledge.md       # NumPy/Pandas/Matplotlib 知识点
│   ├── streamlit知识点.md      # Streamlit 知识点
│   └── F1项目规划.md           # 初始规划（早期版本留念）
│
├── .gitignore
├── requirements.txt
└── README.md
```

### 分层职责
- `main.py`：路由注册、参数校验、CORS 配置、JWT 依赖注入。
- `data_source.py`：封装第三方请求、缓存读写、数据解析，**对外只返回 JSON 可序列化的原生类型**。
- `models.py` / `database.py` / `auth.py`：数据库 ORM、连接管理、用户鉴权。
- `game_service.py` / `prediction_service.py`：Fantasy 积分规则和 AI 预测的纯计算逻辑。

---

## 三、API 接口清单（39 个 API）

### A1 当年赛程（2 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/current-season` | 当前赛季分站日历 |
| GET | `/api/season/{year}` | 历史赛季赛历 |

### A2 分站基础结果（4 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/race-result/{year}/{round_num}` | 分站比赛结果 |
| GET | `/api/circuits` | 全部赛道信息 |
| GET | `/api/current/{round_num}/qualifying` | 当前赛季分站排位赛 |
| GET | `/api/{year}/{round_num}/qualifying` | 历史赛季分站排位赛 |

### A3 车手 / 车队信息（6 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/current/drivers` | 当前赛季车手名单 |
| GET | `/api/{year}/drivers` | 历史赛季车手名单 |
| GET | `/api/current/driverstandings` | 当前赛季车手积分榜 |
| GET | `/api/{year}/driverstandings` | 历史赛季车手积分榜 |
| GET | `/api/current/constructorstandings` | 当前赛季车队积分榜 |
| GET | `/api/{year}/constructorstandings` | 历史赛季车队积分榜 |

### A4 / B 圈速 / 轮胎 / 遥测（8 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/fastf1/{year}/{round}/fast-lap` | 单场车手最快圈排行 |
| GET | `/api/fastf1/{year}/{round}/tyre-strategy` | 单站正赛轮胎进站策略 |
| GET | `/api/fastf1/{year}/{round}/telemetry` | 多车手遥测对比（speed/throttle/brake 等）+ 赛道轮廓 + 30 段最快车手染色 |
| GET | `/api/fastf1/{year}/{round}/sector-fastest` | 赛道分段最快（Sector 1/2/3 排行） |
| GET | `/api/fastf1/{year}/{round}/lap-distribution` | 圈速分布（箱线图数据） |
| GET | `/api/fastf1/{year}/{round}/speed-overlay` | 多车手速度叠加（numpy.interp 统一网格） |
| GET | `/api/fastf1/{year}/{round}/track-map` | 赛道 SVG 坐标 + 分段着色 |
| GET | `/api/fastf1/{year}/{round}/weather` | 天气数据（温度/湿度/风速/降雨） |

### 3A 用户鉴权（3 个）
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册（返回 JWT） | 无 |
| POST | `/api/auth/login` | 用户登录（返回 JWT） | 无 |
| GET | `/api/auth/me` | 获取当前用户信息 | Bearer Token |

### 3B AI 预测（2 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/prediction/{year}/{round}` | AI 夺冠概率预测（XGBoost v2，24 特征含天气；重训前自动回退 v1，失败降级规则模型；无历史记录时 `?save=true` 计算并落库） |
| GET | `/api/prediction/history?season=` | 赛季预测历史（各站 Top3 摘要 + 模型版本 + 回算标记） |

### 3C Fantasy（11 个）
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/fantasy/team` | 创建/更新 Fantasy 阵容 | Bearer Token |
| GET | `/api/fantasy/team/{season}/{round}` | 查看我的阵容 | Bearer Token |
| POST | `/api/fantasy/score/{season}/{round}` | 结算 Fantasy 积分 | Bearer Token |
| GET | `/api/fantasy/leaderboard/{season}` | 赛季排行榜 | 无 |
| GET | `/api/fantasy/prices?season=` | 动态定价（双赛季积分加权） | 无 |
| GET | `/api/fantasy/history?season=` | 历史阵容及积分记录 | Bearer Token |
| POST | `/api/fantasy/chip` | 使用芯片（Limitless/Wildcard/NoNegative） | Bearer Token |
| GET | `/api/fantasy/chip-status?season=` | 查询芯片剩余次数 | Bearer Token |
| POST | `/api/fantasy/leagues` | 创建联盟（生成邀请码） | Bearer Token |
| POST | `/api/fantasy/leagues/{id}/join` | 加入联盟（验证邀请码） | Bearer Token |
| GET | `/api/fantasy/leagues/{id}/leaderboard` | 联盟内排行榜 | Bearer Token |
| GET | `/api/fantasy/my-leagues` | 我的联盟列表 | Bearer Token |

### E 投票（2 个）
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/vote` | 最佳车手投票 | Bearer Token |
| GET | `/api/vote/results/{season}/{round}` | 投票结果统计 | 无 |

### 其他（1 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |

---

## 四、前端页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 赛程列表 | `/` | 年份选择 + 赛程表格 + 跳转结果页 |
| 分站结果 | `/results/:year?/:round?` | Top10 结果表 + 最快圈排行 + 轮胎策略条带图 |
| 排行榜 | `/standings` | 车手/车队双 Tab + 排序筛选 + 关键词过滤 |
| 最快圈排行 | `/lap-rank` | 单场车手最快圈排行表格 |
| 赛道分段最快 | `/sector-fastest` | Sector 1/2/3 分段排行 + 全场分段总和最快 |
| 遥测对比 | `/tele-compare` | 多车手多通道遥测叠加图 |
| 圈速分布 | `/lap-distribution` | 箱线图 + 异常值散点 + 统计明细 |
| 速度叠加 | `/speed-overlay` | 多车手速度叠加对比（numpy.interp 统一网格） |
| 赛道地图 | `/track-map` | SVG 赛道轮廓 + 分段着色（Purple/Green/Yellow） |
| 遥测大屏 | `/telemetry` | 6 图层联动（速度/油门刹车/Delta/赛道染色/分段/分布） |
| AI 预测 | `/prediction` | 夺冠概率 Top3 卡片 + ECharts 柱状图 + SHAP/特征解释 + **分站选择器（可回看任意一站）+ 本赛季预测历史** |
| Fantasy | `/fantasy` | 车手/车队选择 + 预算追踪 + 队长/芯片 + 历史记录 + 排行榜 |
| Fantasy 联盟 | `/league` | 创建/加入联盟 + 邀请码 + 联盟排行榜 |
| 投票 | `/vote` | 最佳车手投票 + 投票结果条形图 |
| 登录 / 注册 | `/login` | 独立登录页（导航栏入口，可选登录，登录后导航栏显示用户菜单） |
| 404 | `/*` | 兜底页 |

---

## 五、Fantasy 积分规则

| 积分项 | 规则 | 说明 |
|--------|------|------|
| 完赛 Top 10 | 10/8/6/5/4/3/2/1/0/0 | 冠军 10 分，递减 |
| 排位 Top 3 | 3/2/1 | 杆位 3 分 |
| 最快圈 | +5 | 全场最快圈车手 |
| 位置提升 | +1 × 提升位次 | 排位→正赛每提升 1 位 +1 |
| DNF | -5 | 退赛扣分（no_negative 芯片豁免） |
| 队长加倍 | ×2 | 队长车手积分翻倍 |
| 车队完赛 Top 5 | 5/4/3/2/1 | 取车队最好的完赛名次 |

**预算限制**: ¥100M，最多 5 车手 + 2 车队，limitless 芯片豁免预算。

---

## 六、缓存策略

| 缓存 | 位置 | 有效期 | 作用 |
|------|------|--------|------|
| Ergast 结果 | `cache/ergast_cache/*.json` | 永久 | 历史赛果不变，避免重复请求 |
| FastF1 原始计时 | `cache/fastf1_cache/*.ff1pkl` | 由 FastF1 管理 | 缓存官方接口响应 |
| FastF1 处理结果 | `cache/fastf1_result_cache/*.json` | 7 天 | 命中后跳过 session.load() |
| SQLite 数据库 | `cache/f1_app.db` | 持久 | 用户/Fantasy/投票数据 |

---

## 七、踩坑清单

### 模块 A（FastF1 数据层）
1. **`session.load()` 参数名是 `messages`（复数）**，写成 `message` 会抛 `TypeError`。
2. **轮胎配方列名是 `Compound`**，不是 `TyreCompound`。
3. **`LapTime` 是 `timedelta64[ns]`**，需 `_timedelta_to_seconds()` 转换。
4. **`to_dict("records")` 返回 `numpy.int64/float64`**，需 `int()`/`float()` 显式转换。
5. **轮胎策略按 `Stint` 分组**保留进站顺序。
6. **异常分站需 `try/except` 兜底**返回 `{code:500,msg}`。

### 模块 B（遥测分析）
7. **Sector 列名是 `Sector1Time`**（不是 `Sector1`），某些圈可能 NaT（进站圈），需 `dropna()`。
8. **`nGear` 列名不是 `Gear`**，遥测通道映射时注意 `n` 前缀。
9. **ECharts boxplot data 格式**必须是 `[min, Q1, median, Q3, max]` 五数概括；Q1/Q3 需排序后手动取位置。
10. **ECharts 实例必须 `dispose()`**，否则组件卸载后内存泄漏。
11. **遥测数据降采样**：原始 ~20Hz/~20MB，用 `step = max(1, len(car_data) // 200)` 降到 ~200 点。
12. **TeleCompare.vue 硬编码问题**：原代码写死 `year: 2023, round: 1`，已修复为动态选择器 + Pinia store 加载赛程。

### 模块 3（数据库 + 鉴权 + Fantasy + AI）
13. **passlib + bcrypt 5.0 不兼容**：`AttributeError: module 'bcrypt' has no attribute '__about__'` → 弃用 passlib，直接用 `bcrypt.hashpw()` / `bcrypt.checkpw()`。
14. **Python 路径参数 `round` 遮蔽内置 `round()` 函数**：`get_vote_results(season, round)` 中调用 `round()` 报 `TypeError: 'int' object is not callable` → 改参数名为 `round_num`。
15. **Ergast 比赛结果 endpoint 错误**：`{year}/{round}.json` 返回赛历（无 Results），应使用 `{year}/{round}/results.json`。
16. **SQLAlchemy Column default 取值**：`models.Vote.__table__.c.voted_at.default.arg` 返回函数对象而非时间值，应直接用 `datetime.utcnow()`。
17. **Vue 3 变量名拼写不一致**：`captianCode`（错）vs `captainCode`（对），template 和 script 不关联。

### 2026-08-12 全项目体检修复
18. **SQLite `create_all` 不给已存在表加新列**：给 `User` 表新增芯片字段后登录报 `no such column: users.chip_limitless_used` → 500。修复：`database.py` 新增 `_auto_migrate()`，启动时用 `PRAGMA table_info` 对比 ORM 模型与库表，自动 `ALTER TABLE` 补缺失列（保留数据）。以后加字段无需手动迁移。
19. **Vue Router 空路径子路由 redirect 无限循环**：`children: [{ path: '', redirect: '/race-center?tab=overview' }]` 导致 `/race-center` 反复重定向 → `Maximum call stack size exceeded`。修复：删除 children，组件内部用 `route.query.tab || 'default'` 处理默认 Tab。
20. **Vue Router 4 的 `next()` 已废弃**：`beforeEach((to, from, next) => next())` 触发 `VUE_ROUTER_R0025` 警告。修复：守卫函数改为直接返回值（`return false` / `return '/login'` / 不返回 = 放行）。
21. **Element Plus `el-checkbox` 的 `:label` 作 value 已废弃**：触发 `ElementPlusError` 警告，升级后无法选中。修复：`:label="y"` → `:value="y"`。
22. **FastF1 遥测首次加载超时**：首次需从 F1 官网下载 50-100MB 原始数据，60s 不够。修复：遥测接口 timeout 提升到 120s，拦截器对遥测超时给出专属提示（第二次请求走缓存秒回）。

### 2026-08-14 工程稳定性
23. **Windows 端口残留 500（uvicorn `--reload` 反复触发）**：`uvicorn --reload` 在 Windows 上 worker fork/terminate 后**进程死了但 TCP socket 没释放**（Windows 网络栈 bug）。多次 reload 后 `netstat -ano | grep :PORT` 会看到 ≥2 个 LISTEN，内核通过 SO_REUSEADDR 随机分发请求，落到 stale worker 后 500。修复：`scripts/restart_backend.py`（基于 psutil）一键清端口 + 等 15s 释放 + 用 `DETACHED_PROCESS` 标志位后台启动。**任何 HTTP 500 + 端口多 LISTEN，立刻跑这个脚本**。**进一步**：开发期可放弃 `--reload` 改用 `nodemon`/`watchdog` 外部触发，避免 reload 残留。
24. **PowerShell 5.1 `Start-Process -FilePath python.exe` 在路径含 `f1_project` 时触发 `Path 重复` bug**：PowerShell 把 `-FilePath` 当成 `-Path` + 环境变量 `$PATH` 冲突抛 `ArgumentException`。回避：用 Python `subprocess.Popen` + `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` 标志位，比 Start-Process 稳。
26. **FastF1 3.8.x `car_data` 无 `Distance` 列**：`car_data.columns` 已变为 `['Date','RPM','Speed','nGear','Throttle','Brake','DRS','Source','Time','SessionTime']`，无 `Distance`。原代码 fallback 到 `range(len(sampled))` 导致 distances 为索引而非距离。修复：改用归一化 `i/(N-1)`，所有车手共享同一索引基准。赛道轮廓改从 `fastest.get_pos_data()` 提取 X/Y（position data），而非 `get_circuit_info()`。
27. **`round()` 精度丢失**：`round(0.0333, 1)` = 0.0，corner_segments 的 start/end_dist 显示 0.0。修复：round 到 4 位小数。

---

## 八、环境与启动

### 1. 创建 Conda 环境
```bash
conda create -n f1_project python=3.11 -y
conda activate f1_project
pip install -r requirements.txt
```

### 2. 启动后端
```bash
# 项目根目录（默认 8010 端口，避开 8000 端口残留进程）
uvicorn backend.main:app --reload --port 8010    # http://127.0.0.1:8010
```

> ⚠️ **推荐用脚本**避免 Windows 端口残留：`scripts/start_backend.bat`（快速启动，遇到僵尸时换下方）：
> ```bash
> # 遇到端口残留/500 时一键自愈（python 写,杀掉 8010 全部占用 + 等 15s + 后台启动）
> python scripts/restart_backend.py
> # 或只清端口不启动：python scripts/restart_backend.py --no-start
> ```

### 3. 启动前端
```bash
cd frontend
npm install
npm run dev                                        # http://127.0.0.1:5173
```

### 4. 访问
- 后端接口文档：http://127.0.0.1:8010/docs
- 前端页面：http://127.0.0.1:5173
- 前端通过 Vite proxy 代理 `/api` → 8010，无需 CORS 配置。
- 首次启动后端时自动建表（SQLite）+ 自动迁移（`_auto_migrate()` 补缺失列）。

> 首次请求 FastF1 接口需联网下载官方计时数据（较慢），之后命中本地缓存秒级返回。

---

## 九、后续迭代方向

- [x] XGBoost 替代规则加权模型（完成于 2026-08-14，Top-1 41.67% vs 33.33%）
- [x] 天气维度入模型：xgb_v2（24 特征 = 原 19 + 干湿/气温/赛道温度/降雨/湿度），前端按 7 组特征维度折叠展示 + 天气摘要栏（完成于 2026-08-25，指标对比见 ml/models/eval_report.json）
- [x] Windows 端口残留 500 修复 + 自愈脚本（完成于 2026-08-14）
- [ ] 单元测试覆盖（pytest）
- [ ] WebSocket 实时通知（Fantasy 结算后推送）
- [ ] Redis 替代文件缓存
- [ ] DNF 检测白名单判定（当前 `"Retired" in status` 不覆盖 Engine/Disqualified）
- [ ] 缓存路径改用配置项（当前硬编码本机绝对路径）
- [ ] 弃用 uvicorn `--reload`，改用 `watchdog`/`nodemon` 外部触发，彻底解决 Windows 僵尸 socket

---

## 十、已知技术债

| 项目 | 说明 | 影响 |
|------|------|------|
| Tailwind CSS v4 | `@tailwindcss/vite` 插件已加载，但无 CSS 文件 `@import "tailwindcss"`，样式未生成。实际 CSS 用传统手写 | 零功能影响，package.json 有冗余依赖 |
| Leaflet / vue3-leaflet | 安装但代码中零导入，赛道地图实际用 SVG polyline 实现 | 零功能影响，package.json 有冗余依赖 |
| JWT 密钥默认值 | 开发环境使用硬编码默认值，生产环境需配 `JWT_SECRET` 环境变量 | 安全风险 |
| 无速率限制 | 登录/注册接口可被暴力破解 | 安全风险 |
