# -*- coding: utf-8 -*-
"""第一部分：阶段 0 环境与基础 + 第二部分：阶段 1 后端基础数据"""

PART0_INTRO = (
    "本部分对应项目「阶段 0：环境与基础」知识点，覆盖 FastAPI 路由与参数、CORS 中间件、"
    "Ergast API 数据解包、FastF1 对象模型、Conda 环境、Git 版本控制、Pydantic 数据校验。"
    "所有知识点均遵循「概念 + 本项目代码 + 踩坑 + 面试问答」四段式结构。"
)

UNITS = [
# ============ 阶段 0 ============
{
    "id": "0.1",
    "title": "FastAPI 路由与参数",
    "concept": [
        "FastAPI 是基于 Python 类型提示的异步 Web 框架，核心思想：用函数定义接口（路由），用类型注解声明参数，框架自动完成校验、序列化与文档生成。",
        ("h3", "路径参数 vs 查询参数"),
        ("bullet", "路径参数：写在 URL 路径中，必须提供，用于定位资源。例：`/api/2025/1/results` 中的 `2025`、`1`。", "核心区别"),
        ("bullet", "查询参数：写在 `?` 之后，可带默认值、可省略，用于过滤/分页。例：`/api/races?season=2025&limit=10`。", "核心区别"),
        ("bullet", "FastAPI 根据函数签名自动区分两者：函数参数与路径 `{}` 占位符同名即为路径参数，其余为查询参数。", "自动区分"),
        ("h3", "本项目路由示例"),
        ("code", "# backend/main.py 路由层示例\n"
                "@app.get(\"/api/{year}/races\")\n"
                "def get_races(year: int):          # year 是路径参数，自动校验为 int\n"
                "    return fetch_race_calendar(year)\n\n"
                "@app.get(\"/api/races\")\n"
                "def get_races_query(season: int = 2025, limit: int = 10):\n"
                "    # season/limit 是查询参数，带默认值，可选\n"
                "    return fetch_races_paged(season, limit)",
                "后端 main.py"),
        ("h3", "自动文档"),
        ("bullet", "FastAPI 自动生成 OpenAPI 规范与交互式文档：`/docs`（Swagger UI）、`/redoc`。", "无需额外配置"),
        ("bullet", "接口入参类型错误时自动返回 422 校验错误，无需手写校验逻辑。", "422 校验"),
    ],
    "code": {
        "FastAPI 最小可运行示例": (
            "from fastapi import FastAPI\n"
            "app = FastAPI(title=\"F1 Data API\")\n\n"
            "@app.get(\"/\")\n"
            "def root():\n"
            "    return {\"message\": \"F1 API running\"}\n\n"
            "@app.get(\"/api/{year}/{round}/results\")\n"
            "def race_results(year: int, round: int):\n"
            "    \"\"\"路径参数 year/round + 返回 dict 自动转 JSON\"\"\"\n"
            "    return {\"year\": year, \"round\": round, \"status\": \"ok\"}"
        ),
    },
    "pits": [
        ("顺序", "路径参数与查询参数同名会冲突，FastAPI 要求路径参数优先且不能同时定义同名查询参数。"),
        ("类型", "路径参数声明为 int 后，传入非数字会返回 422 而不是 500——这是特性，调试时别误判为 bug。"),
        ("命名", "路由 URL、后端函数名、前端调用、缓存键四处拼写必须一致，曾因 /telemetry 拼错导致前端 404。"),
    ],
    "qa": [
        ("FastAPI 与 Flask 的核心区别是什么？", "FastAPI 基于类型提示（type hints）自动完成参数校验、序列化和 OpenAPI 文档生成，性能上基于 ASGI 异步框架优于 Flask 的 WSGI 同步模型；Flask 更轻量、生态老，但校验与文档全靠手写。"),
        ("路径参数和查询参数怎么区分？什么时候用哪个？", "定位资源用路径参数（如 /api/2025/1/results），过滤、分页、可选条件用查询参数（?season=2025&limit=10）。路径参数必须有值，查询参数可有默认值。"),
        ("FastAPI 如何做到参数自动校验的？", "依赖 Python 的 type hints 与 pydantic 模型。FastAPI 读取函数签名的注解，将请求数据按注解解析为对应类型，不满足时返回 422 并附带详细错误定位。"),
        ("/docs 有什么用？在面试中怎么讲？", "FastAPI 基于 OpenAPI 规范自动生成交互式 API 文档，可直接在浏览器调试接口、查看请求/响应结构。这是「后端开发提效」的典型卖点，体现工程化意识。"),
    ],
},
{
    "id": "0.2",
    "title": "CORS 与中间件",
    "concept": [
        "CORS（跨域资源共享）是浏览器的安全机制：默认禁止页面脚本跨域（不同协议/域名/端口）读取响应。前端跑在 5173 端口、后端跑在 8010 端口，属典型跨域场景。",
        ("h3", "解决方案：后端加 CORS 中间件"),
        ("code", "from fastapi.middleware.cors import CORSMiddleware\n\n"
                "app.add_middleware(\n"
                "    CORSMiddleware,\n"
                "    allow_origins=[\"http://localhost:5173\", \"http://localhost:5174\"],\n"
                "    allow_credentials=True,\n"
                "    allow_methods=[\"*\"],\n"
                "    allow_headers=[\"*\"],\n"
                ")",
                "backend/main.py 白名单配置"),
        ("bullet", "allow_origins 用白名单而非 *（配合 allow_credentials=True 时浏览器禁止 *）。", "白名单"),
        ("bullet", "预检请求（Preflight）：带自定义 Header 或非简单方法时，浏览器先发 OPTIONS 请求探测服务端是否允许。", "OPTIONS 预检"),
        ("bullet", "本项目的替代方案：Vite dev server 配置 proxy，前端 baseURL 为空字符串，/api 请求由 Vite 转发到 8010，从根本上避免跨域。", "代理方案"),
    ],
    "pits": [
        ("CORS 误报", "FastAPI 返回 500 时不附加 CORS 头，浏览器会报 CORS 错误——真相是后端 500。遇到 CORS 报错先查后端日志，而非改 CORS 配置。这是本项目最大的排查陷阱。"),
        ("端口变化", "5173 被占用时 Vite 自动切 5174，白名单必须同时加两个端口，否则偶发跨域。"),
    ],
    "qa": [
        ("什么是 CORS？为什么前后端分离会碰到？", "CORS 是浏览器同源策略的延伸机制：浏览器阻止跨域脚本读取响应，通过服务端返回 Access-Control-Allow-* 头放行。前后端分离部署在不同端口/域名时必然触发。"),
        ("简单请求和预检请求的区别？", "简单请求：GET/HEAD/POST + 标准 Content-Type（application/x-www-form-urlencoded、multipart/form-data、text/plain），直接发请求。非简单请求（自定义 Header、application/json、PUT/DELETE 等）先发 OPTIONS 预检，确认服务端允许后再发正式请求。"),
        ("allow_origins=['*'] 与 allow_credentials=True 为什么不能共存？", "浏览器规范要求：携带凭证（Cookie/Authorization）的跨域请求，响应必须明确指定来源，不能是通配符 *，否则响应会被浏览器拒绝。"),
        ("除了后端 CORS，还有什么规避跨域的办法？", "反向代理（Nginx 将 /api 转发到后端）、Vite dev proxy（开发期）、JSONP（仅 GET，已过时）、WebSocket（不受同源策略限制）。本项目用 Vite proxy。"),
    ],
},
{
    "id": "0.3",
    "title": "Ergast API 与 MRData 数据解包",
    "concept": [
        "Ergast 是 F1 官方历史数据 API（现镜像为 https://api.jolpi.ca/ergast/f1，原 ergast.com 已停用）。返回 JSON 包裹结构：所有数据都在 `MRData` 根节点下，且按资源类型再包一层。",
        ("h3", "典型响应结构与解包路径"),
        ("code", "# 赛历接口 GET /api/f1/{year}.json\n"
                "{\"MRData\": {\"RaceTable\": {\"Races\": [ {...}, ... ]}}}\n\n"
                "# 积分榜接口 GET /api/f1/{year}/driverstandings.json\n"
                "{\"MRData\": {\"StandingsTable\": {\"StandingsLists\": [\n"
                "    {\"DriverStandings\": [...]}]}}}\n\n"
                "# 分站结果接口 GET /api/f1/{year}/{round}/results.json\n"
                "{\"MRData\": {\"RaceTable\": {\"Races\": [{\"Results\": [...]}]}}",
                "Ergast JSON 结构"),
        ("h3", "本项目解包约定（写死在 data_source.py）"),
        ("bullet", "赛程 → `data.Races`", "Races"),
        ("bullet", "积分榜 → `data.StandingsLists[0].DriverStandings`（取第 0 个赛季列表）", "StandingsLists"),
        ("bullet", "分站结果 → `data.Races[0].Results`（取第 0 场比赛）", "Results"),
        ("bullet", "车手名单 → `data.Drivers`", "Drivers"),
    ],
    "code": {
        "通用请求 + 解包工具函数": (
            "import requests, json\n\n"
            "ERGAST_BASE = \"https://api.jolpi.ca/ergast/f1\"\n\n"
            "def _ergast_get(path: str) -> dict:\n"
            "    url = f\"{ERGAST_BASE}{path}\"\n"
            "    resp = requests.get(url, timeout=10)\n"
            "    resp.raise_for_status()\n"
            "    return resp.json()[\"MRData\"]  # 统一解包一层\n\n"
            "def fetch_race_calendar(year: int):\n"
            "    data = _ergast_get(f\"/{year}.json\")\n"
            "    return [{\"round\": r[\"round\"], \"name\": r[\"raceName\"],\n"
            "             \"date\": r[\"date\"], \"circuit\": r[\"Circuit\"][\"circuitName\"]}\n"
            "            for r in data[\"RaceTable\"][\"Races\"]]"
        ),
    },
    "pits": [
        ("镜像域名", "原 ergast.com 已停用，必须用 api.jolpi.ca/ergast/f1，否则请求超时/404。"),
        ("层级", "解包路径少一层会拿到 dict 而不是 list，前端遍历报 undefined。统一在数据源层解包，路由层与前端只面对干净的 list。"),
        ("限流", "Ergast 有 429 限流（约每秒 4 次），批量采集需加 0.5s 间隔 + 3 次重试。"),
    ],
    "qa": [
        ("Ergast 返回结构有什么特点？项目中怎么处理的？", "所有数据包在 MRData 根节点下，按资源类型（RaceTable/StandingsTable/DriverTable）再包一层。项目在数据源层写统一解包函数，只暴露干净的 list 给路由层，避免每处重复解包。"),
        ("第三方 API 集成时要注意什么？", "① 限流（429）与重试策略；② 数据结构变化（解包层集中处理）；③ 缓存降低请求量；④ 超时与异常兜底；⑤ 镜像/停用风险（本项目就遇到 ergast.com 停用）。"),
    ],
},
{
    "id": "0.4",
    "title": "FastF1 对象模型",
    "concept": [
        "FastF1 是 F1 官方数据（计时、遥测、天气）的 Python 封装库，核心入口是 Session 对象。数据量大（每场 50-100MB），因此必须用缓存。",
        ("h3", "核心调用链"),
        ("code", "import fastf1\n\n"
                "session = fastf1.get_session(2025, 1, 'R')   # (年份, 分站序号, 场次类型)\n"
                "session.load(laps=True, telemetry=True,\n"
                "             weather=True, messages=True)     # 注意是 messages 复数！\n\n"
                "laps = session.laps                  # 所有圈速 DataFrame\n"
                "results = session.results            # 完赛成绩\n"
                "circuit = session.get_circuit_info() # 赛道信息（对象，非 DataFrame）",
                "FastF1 核心调用"),
        ("bullet", "场次类型：'R' 正赛 / 'Q' 排位赛 / 'FP1' 'FP2' 'FP3' 练习赛 / 'S' 冲刺赛。", "session 类型"),
        ("bullet", "laps 表关键列：Driver、LapTime（timedelta64[ns]）、Compound（轮胎配方，注意不是 TyreCompound）、Stint（进站段）、Sector1Time 等。", "laps 列"),
        ("bullet", "get_circuit_info() 返回 CircuitInfo 对象（非 DataFrame），hasattr(ci,'columns') 为 False，不能当 DataFrame 用。", "CircuitInfo"),
        ("bullet", "遥测数据在 get_car_data()（速度/转速/油门/刹车）与 get_pos_data()（X/Y 位置坐标，赛道轮廓从这里取）。", "遥测来源"),
    ],
    "pits": [
        ("参数名", "session.load() 的参数是 messages（复数），写成 message 会直接报 TypeError。"),
        ("列名", "laps 表轮胎列是 Compound，不是 TyreCompound，写错列名 KeyError。"),
        ("CircuitInfo", "get_circuit_info() 不是 DataFrame，不能调用 .columns；其属性有 .corners、.marshal_lights 等。"),
        ("缓存", "FastF1 自带 .ff1pkl 缓存目录，首次下载慢、后续快；本项目把缓存目录指向 cache/fastf1_cache/。"),
    ],
    "qa": [
        ("FastF1 的数据从哪里来？有什么特点？", "FastF1 从 F1 官方/定时数据源获取计时、遥测、天气数据。特点是数据量巨大（每场 50-100MB），需本地缓存；API 封装为 Session 对象模型，laps 是 DataFrame，可直接用 Pandas 分析。"),
        ("session.load 有哪些参数？", "laps（圈速）、telemetry（遥测，含位置）、weather（天气）、messages（比赛消息）。注意必须全部用复数形式参数名。"),
        ("遥测数据有哪些列？赛道轮廓怎么画？", "车手遥测（get_car_data）含 Speed/RPM/Throttle/Brake/DRS/nGear；位置数据（get_pos_data）含 X/Y 坐标。赛道轮廓需从 position data 提取 X/Y，不在 car data 里。"),
    ],
},
{
    "id": "0.5",
    "title": "Conda / Git / Pydantic",
    "concept": [
        ("h3", "Conda 环境管理"),
        ("bullet", "隔离依赖：本项目用 conda 环境 f1_project（Python 3.11，fastf1 3.8.3 / fastapi / pandas / numpy / uvicorn）。", "作用"),
        ("bullet", "`conda create -n f1_project python=3.11` 创建；`conda activate f1_project` 激活；`conda env list` 查看。", "常用命令"),
        ("bullet", "依赖清单用 requirements.txt 固定版本，便于复现环境。", "复现"),
        ("h3", "Git 版本控制"),
        ("bullet", "工作流：git status 查看状态 → git add 暂存 → git commit 提交 → git push 推送。", "基本流"),
        ("bullet", ".gitignore 排除 cache/（含 .ff1pkl 大文件与 JSON 缓存）和 *.sqlite 数据库，避免仓库膨胀与密钥泄漏。", ".gitignore"),
        ("bullet", "提交信息遵循「类型 + 简述」：feat 新功能 / fix 修 Bug / docs 文档 / refactor 重构。", "提交规范"),
        ("h3", "Pydantic 数据校验"),
        ("bullet", "FastAPI 依赖 Pydantic：用类声明数据模型，字段类型注解即校验规则。", "与 FastAPI 关系"),
        ("code", "from pydantic import BaseModel, Field\n\n"
                "class UserCreate(BaseModel):\n"
                "    username: str = Field(..., min_length=3, max_length=20)\n"
                "    email: str\n"
                "    age: int = Field(ge=0, le=120)   # 范围校验\n",
                "Pydantic 模型示例"),
    ],
    "qa": [
        ("为什么用 conda 而不是直接 pip install？", "conda 能管理 Python 解释器版本 + 包依赖 + 虚拟环境隔离，适合数据科学栈（pandas/numpy/fastf1 有编译依赖）；pip 只装包。团队协作时 conda env 文件可完整复现环境。"),
        ("requirements.txt 与 conda environment.yml 的区别？", "requirements.txt 是 pip 格式的包清单；environment.yml 是 conda 格式，还能锁定 Python 版本与渠道。本项目用 requirements.txt + 文档记录 conda 环境名。"),
        ("git 遇到冲突怎么处理？", "git status 查看冲突文件 → 手动编辑保留正确内容（去掉 <<<<<<< 标记）→ git add 标记已解决 → commit。避免 git pull 时直接覆盖他人代码。"),
        ("Pydantic 在校验什么场景最有用？", "请求体校验（注册/登录表单）、响应模型约束（避免返回多余字段）、配置管理（环境变量解析）。校验失败自动返回 422，比手写 if-else 高效且规范。"),
    ],
},
{
    "id": "0.6",
    "title": "阶段 0 综合面试问答",
    "qa": [
        ("如果让你从零搭建一个前后端分离项目，你会怎么做？", "① 技术选型：FastAPI（后端）+ Vue3/Vite（前端）+ SQLite（开发期数据库）；② 目录分层：backend 路由层/数据源层分离，frontend 按 pages/api/stores/components 组织；③ 环境：conda 虚拟环境 + requirements.txt；④ 开发联调：Vite proxy 转发 /api 规避 CORS；⑤ 文档：PRD/架构/接口文档先行。"),
        ("接口返回 500 但浏览器报 CORS 错误，怎么排查？", "先看后端日志确认是否真实 500——FastAPI 返回 500 时不附加 CORS 头，浏览器误报跨域。这是前后端联调最常见的迷惑性错误，排查顺序：后端日志 → 接口状态码 → 前端请求头 → CORS 配置。"),
        ("讲一下本项目的数据流？", "前端 Vue 组件 → axios → Vite proxy → FastAPI 路由层（main.py）→ 数据源层（data_source.py）→ 三级缓存 → Ergast API / FastF1 → 处理成 JSON 可序列化原生类型 → 返回前端渲染。"),
        ("openpyxl/python-docx/requests 这类库你用过哪些？", "回答时结合真实使用：requests 调 Ergast API（带超时/重试）、python-docx 生成知识点手册、openpyxl 做数据导出。体现「会用 + 知道坑」。"),
    ],
},

# ============ 阶段 1 ============
{
    "id": "1.1",
    "title": "分层架构：路由层与数据源层",
    "concept": [
        "后端按职责分两层：main.py 只负责「接请求、转发、返回」，data_source.py 负责「拿数据、处理、兜底」。路由层不出现任何数据处理逻辑，数据源层不出现任何 HTTP 细节。",
        ("h3", "分层收益"),
        ("bullet", "接口变更只改路由层；数据逻辑变更只改数据源层，互不影响。", "职责单一"),
        ("bullet", "数据源层可复用：同一个 fetch 函数服务多个路由（如赛程列表页 + 首页都调 fetch_race_calendar）。", "复用"),
        ("bullet", "缓存、异常兜底集中在数据源层，不会散落在各路由。", "集中"),
        ("code", "# main.py 路由层：薄，只做转发\n"
                "@app.get(\"/api/{year}/races\")\n"
                "def races(year: int):\n"
                "    return fetch_race_calendar(year)\n\n"
                "# data_source.py 数据源层：厚，处理一切\n"
                "def fetch_race_calendar(year: int):\n"
                "    key = f\"races_{year}\"\n"
                "    if cached := _read_cache(key):      # 三级缓存\n"
                "        return cached\n"
                "    data = _ergast_get(f\"/{year}.json\")\n"
                "    races = [_unpack_race(r) for r in data[\"RaceTable\"][\"Races\"]]\n"
                "    _write_cache(key, races)\n"
                "    return races",
                "分层示例"),
        ("h3", "JSON 可序列化约定"),
        ("bullet", "data_source 对外只返回 JSON 可序列化的原生类型（int/float/str/None/list/dict）。", "硬性约定"),
        ("bullet", "timedelta、numpy 数值、numpy.datetime64 必须显式转换，否则 json.dumps 报 TypeError。", "转换"),
    ],
    "qa": [
        ("为什么要把后端分成路由层和数据源层？", "① 职责单一、可维护：改数据逻辑不动接口定义；② 可复用：缓存与兜底集中管理；③ 可测试：数据源层可单独单测；④ 团队协作：前端只看路由契约。这是后端工程化的基础分层思想。"),
        ("「数据源层只返回 JSON 可序列化类型」这条约定解决了什么问题？", "FastAPI 的 JSONResponse 用 json.dumps 序列化，timedelta/numpy 类型会直接抛 TypeError 导致 500。约定在源头转换，避免每个接口踩雷。"),
    ],
},
{
    "id": "1.2",
    "title": "三级缓存架构",
    "concept": [
        "Ergast 是公网限流 API、FastF1 数据下载慢，因此设计三级缓存分层，命中率与实时性兼顾：",
        ("table", ["层级", "目录", "内容", "过期策略"], [
            ["L1", "cache/ergast_cache/", "Ergast 各接口 JSON 结果", "1 小时（赛季进行中自动刷新）"],
            ["L2", "cache/fastf1_cache/", "FastF1 官方 .ff1pkl 原始计时缓存", "FastF1 内置，长期"],
            ["L3", "cache/fastf1_result_cache/", "FastF1 处理后结果 JSON", "7 天 TTL"],
        ], [2.5, 4.5, 5.5, 4.0]),
        ("h3", "缓存读写的通用实现"),
        ("code", "CACHE_EXPIRE_SECONDS = 3600   # 1 小时\n\n"
                "def _read_cache(key: str):\n"
                "    path = _cache_path(key)\n"
                "    if not path.exists():\n"
                "        return None\n"
                "    age = time.time() - path.stat().st_mtime   # 基于 mtime 判过期\n"
                "    if age > CACHE_EXPIRE_SECONDS:\n"
                "        return None\n"
                "    return json.loads(path.read_text(encoding=\"utf-8\"))\n\n"
                "def _write_cache(key: str, data) -> None:\n"
                "    path = _cache_path(key)\n"
                "    path.write_text(json.dumps(data, ensure_ascii=False), encoding=\"utf-8\")\n\n"
                "def _cache_path(key: str):\n"
                "    return CACHE_DIR / f\"{key}.json\"",
                "data_source.py 缓存工具"),
        ("h3", "三大缓存问题与对策"),
        ("bullet", "缓存穿透：查询不存在的数据（如非法年份）每次都打源。对策：空结果也缓存短时间。", "穿透"),
        ("bullet", "缓存雪崩：大量 key 同时过期。对策：TTL 加随机抖动。", "雪崩"),
        ("bullet", "缓存击穿：热点 key 过期瞬间大量请求打源。对策：单飞/互斥锁，或接口层限流。", "击穿"),
    ],
    "pits": [
        ("坏缓存", "trackmap_2024_1_R.json 曾缓存了 0 点的坏结果，7 天 TTL 导致接口持续返回空赛道轮廓。修复：删坏缓存 + 缓存写入前校验数据非空。这是「缓存有毒」的典型案例。"),
        ("mtime", "用文件 mtime 判断过期简单可靠；不要用缓存内部写时间戳字段，避免解析成本与格式问题。"),
    ],
    "qa": [
        ("讲一下你们项目的三级缓存设计。", "L1 存 Ergast JSON（1 小时 TTL，赛季进行中自动刷新赛程/结果）；L2 是 FastF1 官方的 .ff1pkl 原始数据缓存（避免重复下载 50-100MB/场）；L3 存 FastF1 处理后的结果 JSON（7 天）。每层解决一类成本：网络请求、下载带宽、计算耗时。"),
        ("缓存穿透/雪崩/击穿分别是什么？怎么防？", "穿透：查不存在的数据绕过缓存打库/打源，用空值缓存 + 参数校验；雪崩：大量 key 同时失效，用随机 TTL 抖动；击穿：热点 key 失效瞬间高并发打源，用互斥锁重建缓存（singleflight）。"),
        ("缓存和数据库/数据源的一致性怎么保证？", "本项目是只读数据（F1 历史数据不可变），TTL 过期即刷新，无一致性问题。若涉及用户写入数据（如 Fantasy 持仓），必须用「写库 + 删缓存」或双写策略。"),
    ],
},
{
    "id": "1.3",
    "title": "数据序列化：timedelta 与 numpy 类型",
    "concept": [
        "FastF1/Pandas 返回大量非 JSON 原生类型：LapTime 是 timedelta64[ns]、分数可能是 numpy.float64、时长可能是 datetime.timedelta。json.dumps 无法处理这些类型，直接序列化会 500。",
        ("h3", "转换工具函数"),
        ("code", "def _timedelta_to_seconds(td) -> float:\n"
                "    \"\"\"timedelta64 / datetime.timedelta -> 秒 (float)\"\"\"\n"
                "    if td is None or (isinstance(td, float) and math.isnan(td)):\n"
                "        return None\n"
                "    return float(td.total_seconds())\n\n"
                "def _format_laptime(seconds: float) -> str:\n"
                "    \"\"\"秒 -> '1:12.345' 展示格式\"\"\"\n"
                "    if seconds is None:\n"
                "        return None\n"
                "    m, s = divmod(seconds, 60)\n"
                "    return f\"{int(m)}:{s:06.3f}\"\n\n"
                "def _to_native(v):\n"
                "    \"\"\"递归清洗：numpy 标量 -> Python 原生类型\"\"\"\n"
                "    if isinstance(v, np.generic):\n"
                "        return v.item()\n"
                "    if isinstance(v, (pd.Timedelta, datetime.timedelta)):\n"
                "        return v.total_seconds()\n"
                "    return v",
                "data_source.py 序列化工具"),
        ("h3", "应用场景"),
        ("bullet", "最快圈：LapTime.total_seconds() 得到秒数，再 format 成 m:ss.fff。", "最快圈"),
        ("bullet", "轮胎策略：Stint 时长、进站窗口用 timedelta 转秒后比较。", "轮胎"),
        ("bullet", "API 返回统一为 float/int/str/None，前端直接渲染。", "对外约定"),
    ],
    "pits": [
        ("NaN", "缺失圈速是 NaN（float），不是 None，直接返回会让 JSON 序列化失败或前端显示 NaN。必须显式判断 math.isnan 并转 None。"),
        ("numpy 标量", "numpy.float64/numpy.int64 不是 JSON 原生类型，用 .item() 或 float()/int() 转换。"),
    ],
    "qa": [
        ("json.dumps 序列化不了哪些类型？遇到过什么报错？", "datetime.timedelta、numpy 标量、numpy.datetime64、set、bytes 都会抛 TypeError。项目里 LapTime 是 timedelta64[ns]，直接返回接口就 500。"),
        ("NaN 和 None 在 JSON 里的区别？", "JSON 没有 NaN 概念（严格标准），Python json 库默认把 float('nan') 序列化成 NaN（非标准但能解析）；前端展示会出问题。最佳实践：数据源层统一把 NaN/缺失转 None。"),
    ],
},
{
    "id": "1.4",
    "title": "最快圈提取：groupby + idxmin",
    "concept": [
        "每场比赛有约 20 名车手 × 60 圈 = 1200+ 行圈速数据，需要提取每位车手的最快圈，再求全场最快。",
        ("h3", "核心实现"),
        ("code", "# 每位车手最快圈\n"
                "fastest_per_driver = laps.loc[\n"
                "    laps.groupby(\"Driver\")[\"LapTime\"].idxmin()\n"
                "] \n\n"
                "# 全场最快（含罚时后官方最快圈）\n"
                "fastest_lap = laps.loc[laps[\"LapTime\"].idxmin()]",
                "idxmin 提取最快圈"),
        ("bullet", "idxmin() 返回最小值的索引标签，再 .loc 取整行——比 sort_values().drop_duplicates() 更高效（O(n) vs O(n log n)）。", "为什么用 idxmin"),
        ("bullet", "groupby('Driver') 按车手分组，每组内取 LapTime 最小的行。", "分组思路"),
        ("bullet", "注意过滤无效圈（如 InLap/OutLap 进出站圈，LapTime 可能为 NaN 或异常大）。", "数据清洗"),
    ],
    "qa": [
        ("groupby + idxmin 提取最快圈的原理？为什么不用排序？", "idxmin 直接返回每组的极值索引，一次遍历 O(n)；排序是 O(n log n) 且要处理重复值。数据量大时（1200+ 行）性能差异明显，写法也更语义化。"),
        ("提取最快圈前要做什么清洗？", "过滤 NaN（缺失/事故圈）、过滤进站圈（InLap/OutLap）、必要时过滤蓝旗/黄旗干扰圈；正赛还应注意赛道限制被取消的圈速。"),
    ],
},
{
    "id": "1.5",
    "title": "轮胎策略重建：按 Stint 分组",
    "concept": [
        "轮胎策略 = 车手每段（Stint）使用的轮胎配方 + 圈数。Stint 号从 1 递增，每进一次站 +1。直接 groupby compound 计数会丢失进站顺序（例如 C3→C2→C3 会被合并成两个 C3）。",
        ("h3", "正确实现"),
        ("code", "stints = laps.dropna(subset=[\"Stint\"]).groupby(\n"
                "    [\"Driver\", \"Stint\"]\n"
                ")[\"Compound\"].first().reset_index()\n\n"
                "# 对每位车手按 Stint 排序，保留进站顺序\n"
                "stints = stints.sort_values([\"Driver\", \"Stint\"])\n\n"
                "# 统计每段圈数\n"
                "stint_laps = laps.groupby([\"Driver\", \"Stint\"]).size()",
                "轮胎策略重建"),
        ("bullet", "按 (Driver, Stint) 双分组取 Compound 首值，再按 Stint 排序，即得「第 1 段 C3、第 2 段 C2、第 3 段 C3」的顺序。", "顺序"),
        ("bullet", "Stint 可能有 NaN（未进站数据），先 dropna。", "清洗"),
        ("bullet", "前端用颜色区分配方：C1-C5 有标准色板（COMPOUND_COLORS）。", "可视化"),
    ],
    "pits": [
        ("顺序丢失", "只 groupby compound 计数会把 C3→C2→C3 合并成 2 段 C3，策略图完全错误。必须按 Stint 分组保留进站顺序。"),
    ],
    "qa": [
        ("轮胎策略为什么要按 Stint 分组而不是按 Compound 分组？", "进站后可能换回同一配方（C3→C2→C3），按 Compound 分组会丢失进站顺序和段数，策略图错误。Stint 号自带顺序语义，按 (Driver, Stint) 分组才能还原真实策略。"),
        ("怎么从圈速数据判断进站次数？", "Stint 列的最大值 - 1 即进站次数（或统计 Stint 变化次数）；更精确的是对比 PitInTime/PitOutTime 或每圈 Pit 状态标记。"),
    ],
},
{
    "id": "1.6",
    "title": "异常兜底：None 模式",
    "concept": [
        "F1 数据常有异常分站（大雨取消、数据缺失、FastF1 版本不兼容字段变化）。原则：数据源层捕获所有异常，返回「带 code 的兜底结构」而非让异常穿透到前端。",
        ("h3", "两种兜底模式"),
        ("code", "# 模式一：字段级兜底（缺失字段返回 None）\n"
                "def _safe_get(d: dict, key: str):\n"
                "    try:\n"
                "        return d[key]\n"
                "    except (KeyError, TypeError):\n"
                "        return None\n\n"
                "# 模式二：接口级兜底（整体失败返回 {code:500}）\n"
                "def fetch_race_weather(year: int, rnd: int):\n"
                "    try:\n"
                "        session = fastf1.get_session(year, rnd, 'R')\n"
                "        session.load(weather=True)\n"
                "        return {\"code\": 200, \"weather\": _pack_weather(session)}\n"
                "    except Exception as e:\n"
                "        logger.error(f\"weather failed: {e}\")\n"
                "        return {\"code\": 500, \"msg\": f\"天气数据暂不可用\"}",
                "data_source.py 兜底模式"),
        ("bullet", "前端约定：检查 res.code === 200 才渲染数据，500 时展示降级文案（如「分站暂未开始」）。", "前端配合"),
        ("bullet", "异常必须记日志（logger.error），否则线上问题无法排查。", "日志"),
    ],
    "qa": [
        ("数据源层异常兜底的设计原则？", "① 不让异常穿透到 HTTP 层（避免 500 连带 CORS 误报）；② 返回结构化错误 {code, msg}，前端可判断降级；③ 记录日志便于排查；④ 区分字段级（None）与接口级（code 500）两种粒度。"),
        ("前端怎么配合后端的兜底结构？", "统一在请求封装或组件中判断 code：200 渲染数据、500 显示兜底文案。TelemetryCockpit 的 loadAll() 就要求检查每个 API 的 code，只要至少一个数据源成功就 hasData=true。"),
    ],
},
{
    "id": "1.7",
    "title": "阶段 1 综合面试问答",
    "qa": [
        ("讲一下项目从请求到响应的完整链路？", "前端 axios 请求 → Vite proxy 转发（规避 CORS）→ FastAPI 路由层校验参数 → 数据源层查三级缓存（未命中再请求 Ergast/FastF1）→ 清洗、解包、序列化为原生类型 → JSON 响应 → 前端按 code 判断渲染。"),
        ("如果 Ergast API 挂了，你的接口会怎样？", "依赖「异常兜底 + 缓存」：L1 缓存未过期时直接命中不依赖网络；缓存过期时 try/except 返回 {code:500}，前端展示降级文案。有缓存时系统仍可用（最多数据滞后 1 小时）。"),
        ("为什么要缓存？缓存放哪里？", "① Ergast 公网限流；② FastF1 数据下载慢（每场 50-100MB）；③ 同一数据被多个页面复用。放本地文件（JSON/.ff1pkl），重启不丢，比内存缓存更持久，适合单机项目。"),
        ("如何设计一个通用缓存工具？", "核心是 key-value + TTL：key 由业务唯一标识拼成（fastlap_2025_1_R），value 序列化存储，过期用 mtime 判断；提供 read/write/delete 三件套；可选加：空值缓存（防穿透）、TTL 抖动（防雪崩）、重建锁（防击穿）。"),
    ],
},
]
