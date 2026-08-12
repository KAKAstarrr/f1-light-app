# F1 Light App — F1 赛事数据互动平台

> 基于 FastAPI + Ergast + FastF1 + Vue 3 的 F1 全栈分析应用。
> 已完成 **模块 A（基础数据）+ 模块 B（遥测分析：分段最快/遥测对比/圈速分布）+ 模块 3A（用户鉴权）+ 模块 3B（AI 预测）+ 模块 3C（Fantasy + 投票）**，后端 28 个 API 全部跑通。

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
│   ├── main.py                 # 路由层：28 个 API + CORS + 自动建表
│   ├── data_source.py          # 数据源层：Ergast + FastF1 封装与三级缓存
│   ├── config.py               # 配置管理（DB/JWT/Fantasy 规则）
│   ├── database.py             # SQLAlchemy 引擎 + 会话 + 建表
│   ├── models.py               # 8 张 ORM 表（User/Driver/Constructor/FantasyTeam/...）
│   ├── schemas.py              # Pydantic 请求/响应模型
│   ├── auth.py                 # JWT 鉴权（bcrypt 哈希 + Token 签发/校验）
│   ├── game_service.py         # Fantasy 积分规则 + 动态定价
│   ├── prediction_service.py   # AI 预测（规则加权模型）
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
│   │   │   │   └── LapBoxPlot.vue  # 圈速分布箱线图
│   │   │   ├── Prediction.vue  #   AI 夺冠概率预测
│   │   │   ├── FantasyTeam.vue #   Fantasy 阵容管理
│   │   │   ├── Vote.vue        #   最佳车手投票
│   │   │   └── NotFound.vue    #   404 页
│   │   ├── components/         # 可复用组件
│   │   ├── composables/        # 组合式函数
│   │   ├── stores/
│   │   │   └── f1.js           #   Pinia 全局状态
│   │   ├── router/
│   │   │   └── index.js        #   路由配置 + 导航守卫
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
│   ├── 05_部署文档.md
│   ├── 06_复盘文档.md
│   ├── 07_学习规划路线.md
│   ├── 08_Vue3前端知识点.md
│   ├── 09_阶段0_环境与基础知识点.md
│   ├── 10_阶段1_后端基础数据知识点.md
│   ├── 11_阶段3_数据库与AI预测知识点.md
│   ├── 12_阶段2_遥测分析知识点.md
│   ├── data_knowledge.md       # NumPy/Pandas/Matplotlib 知识点
│   ├── streamlit知识点.md      # Streamlit 知识点
│   └── F1项目规划.md           # 初始规划
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

## 三、API 接口清单（28 个 API）

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

### A4 / B 圈速 / 轮胎 / 遥测（5 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/fastf1/{year}/{round}/fast-lap` | 单场车手最快圈排行 |
| GET | `/api/fastf1/{year}/{round}/tyre-strategy` | 单站正赛轮胎进站策略 |
| GET | `/api/fastf1/{year}/{round}/telemetry` | 多车手遥测对比（speed/throttle/brake 等） |
| GET | `/api/fastf1/{year}/{round}/sector-fastest` | 赛道分段最快（Sector 1/2/3 排行） |
| GET | `/api/fastf1/{year}/{round}/lap-distribution` | 圈速分布（箱线图数据） |

### 3A 用户鉴权（3 个）
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册（返回 JWT） | 无 |
| POST | `/api/auth/login` | 用户登录（返回 JWT） | 无 |
| GET | `/api/auth/me` | 获取当前用户信息 | Bearer Token |

### 3B AI 预测（1 个）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/prediction/{year}/{round}` | AI 夺冠概率预测（规则加权模型） |

### 3C Fantasy（4 个）
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/fantasy/team` | 创建/更新 Fantasy 阵容 | Bearer Token |
| GET | `/api/fantasy/team/{season}/{round}` | 查看我的阵容 | Bearer Token |
| POST | `/api/fantasy/score/{season}/{round}` | 结算 Fantasy 积分 | Bearer Token |
| GET | `/api/fantasy/leaderboard/{season}` | 赛季排行榜 | 无 |

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
| AI 预测 | `/prediction` | 夺冠概率 Top3 卡片 + ECharts 柱状图 |
| Fantasy | `/fantasy` | 车手/车队选择 + 预算追踪 + 队长/芯片 + 排行榜 |
| 投票 | `/vote` | 最佳车手投票 + 投票结果条形图 |
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
# 项目根目录
uvicorn backend.main:app --reload          # http://127.0.0.1:8000
```

### 3. 启动前端
```bash
cd frontend
npm install
npm run dev                                 # http://127.0.0.1:5173
```

### 4. 访问
- 后端接口文档：http://127.0.0.1:8000/docs
- 前端页面：http://127.0.0.1:5173
- 跨域已通过后端 `CORSMiddleware` 打通。
- 首次启动后端时自动建表（SQLite），无需手动执行 SQL。

> 首次请求 FastF1 接口需联网下载官方计时数据（较慢），之后命中本地缓存秒级返回。

---

## 九、后续迭代方向

- [ ] XGBoost 替代规则加权模型（离线训练 → joblib → 在线推理）
- [ ] Fantasy 联盟功能（创建/加入/联盟内排行榜）
- [ ] Docker 化部署 + CI/CD
- [ ] 单元测试覆盖（pytest）
- [ ] WebSocket 实时通知（Fantasy 结算后推送）
- [ ] Redis 替代文件缓存
