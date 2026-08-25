# -*- coding: utf-8 -*-
"""第四部分：阶段 2 遥测分析 + 扩展（B1-B6）"""

PART2_INTRO = (
    "本部分对应项目「阶段 2：遥测分析」全部知识点：FastF1 核心进阶、B1 分段最快、"
    "B2 遥测对比（速度/油门刹车/Delta）、B3 圈速分布、ECharts 可视化，以及扩展模块 "
    "B4 速度叠加、B5 赛道地图、B6 天气数据。遥测数据量大，是本项目技术含量最高的模块。"
)

UNITS = [
{
    "id": "3.1",
    "title": "FastF1 核心进阶：遥测与位置数据",
    "concept": [
        "遥测数据（Telemetry）是每秒采样的车辆传感器数据（速度/转速/油门/刹车/挡位/DRS），一场正赛约 20 车手 × 60 圈 × 每秒 2-4 次采样，数据量达数十万行，是全项目最大的数据源。",
        ("h3", "数据获取与列结构"),
        ("code", "session = fastf1.get_session(2025, 1, 'R')\n"
                "session.load(laps=True, telemetry=True)   # 必须 telemetry=True\n\n"
                "car = session.car_data  # 或 lap.get_car_data()\n"
                "# 列：Date, RPM, Speed, nGear, Throttle, Brake, DRS, Source,\n"
                "#     Time, SessionTime  （FastF1 3.8.x 无 Distance 列！）\n\n"
                "pos = session.pos_data  # 或 lap.get_pos_data()\n"
                "# 列：X, Y（赛道坐标）, Distance, SessionTime",
                "遥测数据获取"),
        ("h3", "关键踩坑：3.8.x 无 Distance 列"),
        ("bullet", "旧版本 car_data 有 Distance 列（累计行驶距离），3.8.x 版本移除。", "版本差异"),
        ("bullet", "旧代码 fallback 到 range(len(sampled)) 会把「距离」变成行号索引，导致速度曲线横轴错乱。", "错误 fallback"),
        ("bullet", "正确做法：用归一化索引 i/(N-1) 作为 x 轴，所有车手共享同一基准，前端仍可对齐比较。", "正确做法"),
        ("h3", "轨道轮廓来源"),
        ("bullet", "赛道轮廓 X/Y 坐标在 position data（get_pos_data），不在 car data。", "轮廓来源"),
        ("bullet", "2024 起含 X/Y 坐标的 pos 数据接口更稳定；2023 及更早部分比赛缺失时需兜底。", "兼容"),
    ],
    "code": {
        "采样 + 归一化处理": (
            "import numpy as np\n\n"
            "def _sample_telemetry(lap, n=300):\n"
            "    car = lap.get_car_data().add_distance()   # 3.7 及以下可用\n"
            "    # 3.8.x 无 Distance：改用归一化索引\n"
            "    sampled = car.iloc[::max(1, len(car) // n)]\n"
            "    speeds = sampled['Speed'].astype(float).tolist()\n"
            "    x_norm = [i / (len(sampled) - 1) for i in range(len(sampled))]\n"
            "    return {'speed': speeds, 'x_norm': x_norm}"
        ),
    },
    "pits": [
        ("Distance 列", "FastF1 3.8.x 的 car_data 已无 Distance 列，fallback 到 range(len) 会把索引当距离。修复：归一化 i/(N-1) 共享基准。"),
        ("telemetry 参数", "session.load 必须传 telemetry=True，否则 get_car_data() 报错或返回空。"),
        ("数据量", "一场比赛全部遥测约 50-100MB，接口必须采样（约 300 点/车手）+ 三级缓存，否则前端卡死。"),
    ],
    "qa": [
        ("遥测数据有哪些字段？分析中怎么用？", "Speed（速度对比）、Throttle/Brake（出弯开油/刹车点分析）、RPM/nGear（转速换挡策略）、DRS（直道尾流效果）。横轴用归一化距离或实际 Distance，纵轴各通道。"),
        ("为什么遥测接口要采样？", "一场比赛遥测数十万行/车手，全量返回 JSON 达几十 MB，前端 ECharts 也渲染不动。采样到 300 点左右保留曲线形态，误差可接受。"),
        ("赛道轮廓怎么画？", "取某位车手飞驰圈（fastest lap）的 get_pos_data() 的 X/Y 坐标序列，前端用 SVG path 或 ECharts line 绘制闭环。注意 X/Y 在 position data，不在 car data。"),
    ],
},
{
    "id": "3.2",
    "title": "B1 分段最快（SectorFastest）",
    "concept": [
        "赛道分 3 个计时段（Sector），分段最快 = 每个计时段的最快时间 + 创造者。用于分析「谁在哪个段最快、优势在哪」——比全场最快圈更细粒度。",
        ("h3", "实现思路"),
        ("code", "# 每位车手每个计时段的最快时间\n"
                "sector_cols = ['Sector1Time', 'Sector2Time', 'Sector3Time']\n"
                "fastest_by_sector = {}\n"
                "for col in sector_cols:\n"
                "    best = laps.loc[laps[col].notna()].loc[laps[col].idxmin()]\n"
                "    fastest_by_sector[col] = {\n"
                "        'time': _format_laptime(best[col].total_seconds()),\n"
                "        'driver': best['Driver'],\n"
                "    }\n\n"
                "# 后端返回字段（前端契约）\n"
                "# {'code': 200, 'fastest_time': '28.301', 'fastest_driver': 'VER',\n"
                "#  'sectors': [{'sector': 1, 'time': '28.301', 'driver': 'VER'}, ...]}",
                "SectorFastest 后端"),
        ("bullet", "前端契约字段名：fastest_time / fastest_driver（不是 time/driver）。", "字段约定"),
        ("bullet", "SectorXTime 是 timedelta64，需先过滤 NaN 再 idxmin。", "清洗"),
        ("bullet", "页面展示：每段一个卡片，显示最快时间 + 车手 + 车队色。", "展示"),
    ],
    "qa": [
        ("分段最快和全场最快圈有什么区别？为什么都要？", "全场最快圈是「同一圈完成 3 段」的综合最优；分段最快允许 3 个不同车手各赢一段，体现「各自赛段优势」。对分析排位赛单圈能力更有参考性。"),
        ("怎么找每个计时段的最快？", "对 Sector1Time/Sector2Time/Sector3Time 三列分别过滤 NaN 后 idxmin 取最小行，记录时间和车手。"),
    ],
},
{
    "id": "3.3",
    "title": "B2 遥测对比：速度 / 油门刹车 / Delta",
    "concept": [
        "核心页面：选 2-6 位车手，对比他们的速度曲线、油门/刹车操作、以及与基准的 Delta（时间差）曲线，定位弯道得失。",
        ("h3", "后端数据结构"),
        ("code", "{\n"
                "  'code': 200,\n"
                "  'drivers': {\n"
                "    'VER': {'speed': [310, 308, ...], 'throttle': [100, 100, ...],\n"
                "            'brake': [0, 0, 1, ...], 'distance': [0, 12, 24, ...]},\n"
                "    'NOR': { ... }\n"
                "  },\n"
                "  'distances': [0, 1, 2, ...]   # 归一化横轴\n"
                "}",
                "fetch_fastf1_telemetry_compare 返回结构"),
        ("bullet", "前端 6 个图层组件：SpeedLayer / ThrottleBrakeLayer / DeltaLayer / TrackLayer / SectorFastestLayer / LapDistributionLayer，读 drivers[code].channel_array 格式。", "图层组件"),
        ("bullet", "所有图层组件加了双格式 fallback：优先新格式（flat array），降级旧格式（object array .Speed/.Throttle）。", "双格式兼容"),
        ("h3", "Delta 前端梯形积分法"),
        ("bullet", "后端只给速度 + 距离，不给时间 → 前端用梯形积分反推时间：dt = dx / speed_mps。", "原理"),
        ("bullet", "逐点累加得累计时间，两车手累计时间差即 delta 曲线；某点 delta>0 表示落后基准。", "计算"),
        ("code", "function buildDelta(speedKmh, distance) {\n"
                "  const time = [0]\n"
                "  for (let i = 1; i < speedKmh.length; i++) {\n"
                "    const v = (speedKmh[i] + speedKmh[i-1]) / 2 / 3.6  // km/h -> m/s\n"
                "    const dx = distance[i] - distance[i-1]\n"
                "    time.push(time[i-1] + (dx > 0 ? dx / v : 0))       // 梯形积分\n"
                "  }\n"
                "  return time\n"
                "}",
                "前端 DeltaLayer 积分"),
        ("h3", "页面布局（GP Tempo 三栏）"),
        ("bullet", "顶部筛选栏（100%）+ 左栏车手卡片（15%）+ 中栏图表（70%）+ 右栏信息（15%）。", "布局"),
        ("bullet", "3 个 ECharts 图表（速度 line / 油门刹车 areaStyle 半透明 / Delta）用 echarts.connect() 三图联动。", "联动"),
        ("bullet", "右侧车手卡片点击切换可见性 → 重新渲染所有图表（隐藏该车手全部 series）。", "交互"),
    ],
    "pits": [
        ("字段名", "前端必须读 drivers[code].channel_array 格式，不能假设 telemetry[code].telemetry 对象数组——两种格式都写 fallback。"),
        ("积分除零", "速度=0（静止/起步）时 dx/v 除零，需 dx>0 条件保护。"),
        ("session_type", "Q1/Q2/Q3 下拉映射到 FastF1 'Q' 场次（Q1/Q2/Q3 为计时段，非独立 session）。"),
    ],
    "qa": [
        ("Delta 曲线是怎么算出来的？", "后端提供速度+距离，前端梯形积分：把速度曲线按距离离散成小段，每段用时 dt=dx/v，逐段累加得到累计时间曲线，两车手时间曲线逐点相减即 delta。这避免了传输大体积时间序列。"),
        ("油门刹车图怎么表达操作差异？", "油门/刹车为 0-100/0-1 通道，ECharts 用 areaStyle 半透明面积图叠加多位车手，直观看出谁更早开油、谁刹车点更晚。"),
        ("三图联动怎么实现？", "echarts.connect(threeCharts)：任一图的 tooltip、坐标轴缩放、数据视图变化同步到其他图。"),
    ],
},
{
    "id": "3.4",
    "title": "B3 圈速分布（LapDistribution）",
    "concept": [
        "统计每位车手全部有效圈速的分布（直方图/箱线），判断稳定性与轮胎衰减。",
        ("h3", "实现"),
        ("bullet", "后端：按车手分组，收集有效圈速秒数 → 前端直方图。", "后端"),
        ("bullet", "返回字段：distribution（数组），不是 lap_distribution/drivers。", "字段约定"),
        ("bullet", "用于分析：排位赛单圈能力 vs 正赛长距离节奏；轮胎衰减（圈速随圈数漂移）。", "用途"),
    ],
    "qa": [
        ("圈速分布图能看出什么？", "① 稳定性：分布越窄越稳定；② 轮胎衰减：后段圈速均值抬升；③ 车手风格：激进型分布偏宽。"),
        ("为什么分布图比平均圈速更有信息量？", "平均圈速掩盖方差：两位车手平均相同，一个稳定 1:30±0.2，另一个 1:29 与 1:31 交替，比赛结果完全不同。分布图保留形状信息。"),
    ],
},
{
    "id": "3.5",
    "title": "ECharts 可视化要点",
    "concept": [
        "ECharts 是百度开源的图表库（本项目图表主力），要点：option 驱动、series 类型、dataZoom、tooltip、联动、主题色。",
        ("h3", "多车手对比的 option 结构"),
        ("code", "option = {\n"
                "  xAxis: { type: 'category', data: distances },\n"
                "  yAxis: { type: 'value', name: 'km/h' },\n"
                "  series: drivers.map(d => ({\n"
                "    name: d.code,\n"
                "    type: 'line',\n"
                "    showSymbol: false,\n"
                "    lineStyle: { width: 2, color: teamColor(d.code) },\n"
                "    data: d.speed,\n"
                "  })),\n"
                "  tooltip: { trigger: 'axis' },\n"
                "  legend: { top: 0 },\n"
                "}\n"
                "chart.setOption(option)",
                "速度对比图 option"),
        ("bullet", "showSymbol:false + 密集数据点 → 只画线不画点，性能更好。", "性能"),
        ("bullet", "车手隐藏：series 数组过滤 + setOption(notMerge) 重设。", "隐藏逻辑"),
        ("bullet", "ECharts 主题需与页面风格统一（本项目深色驾驶舱风格）。", "主题"),
    ],
    "qa": [
        ("ECharts 大图性能怎么优化？", "① 采样（300 点内）；② showSymbol:false；③ large:true 大数据优化模式；④ 关闭动画；⑤ tooltip trigger:'axis' 而非 item。"),
        ("如何实现车手显隐切换？", "维护可见车手数组，重算 series 后 setOption({series}, true)（notMerge 替换而非合并），图表立即重绘。"),
    ],
},
{
    "id": "3.6",
    "title": "B4 速度叠加：numpy.interp 网格对齐",
    "concept": [
        "不同车手的速度数据采样点不同（圈数不同、点数不同），直接画在同一个横轴会错位。B4 用 numpy.interp 把所有人的速度重采样到统一的 50m 距离网格。",
        ("h3", "实现"),
        ("code", "import numpy as np\n\n"
                "def resample_to_grid(distances, speeds, step=50):\n"
                "    \"\"\"把速度重采样到 50m 等距网格\"\"\"\n"
                "    grid = np.arange(0, max(distances), step)\n"
                "    interp = np.interp(grid, distances, speeds)\n"
                "    return grid.tolist(), interp.tolist()\n\n"
                "# 使用：先 add_distance() 补距离（或归一化），再插值\n"
                "grid, speed_interp = resample_to_grid(\n"
                "    lap.telemetry['Distance'], lap.telemetry['Speed'])",
                "numpy.interp 插值"),
        ("bullet", "np.interp 线性插值：给定新 x 网格与旧 (x, y)，计算网格点处的 y 值。", "原理"),
        ("bullet", "对齐后所有车手同一横轴，叠加比较才公平（同位置比速度）。", "意义"),
        ("bullet", "B4 是「B2 速度对比」的底层增强，保证对比科学性。", "定位"),
    ],
    "qa": [
        ("为什么速度对比前要做重采样？", "不同车手采样点数不同（行驶圈速差异、采样频率），直接画会错位或依赖各自索引。重采样到统一距离网格（50m 步长）后，同一横轴位置代表同一条赛道位置，对比才公平。"),
        ("numpy.interp 和 scipy.interpolate 的区别？", "np.interp 只做一维线性插值、API 极简、性能好；scipy.interpolate 支持高阶样条（平滑、外推）。本项目速度对比线性插值足够。"),
    ],
},
{
    "id": "3.7",
    "title": "B5 赛道地图：SVG 与分段着色",
    "concept": [
        "把赛道轮廓渲染成地图，并按 30 段（corner_segments）着色展示速度/攻弯表现——比纯折线更直观。",
        ("h3", "两种渲染方案"),
        ("bullet", "SVG 方案：position X/Y 归一化后映射到 viewBox，生成 polyline path；段着色用分段 path 或 stroke-dasharray。", "SVG"),
        ("bullet", "ECharts 方案：scatter/line series 带 data 分段颜色，30 段各自渐变色。", "ECharts"),
        ("bullet", "corner_segments 算法：按曲率/速度变化切分弯道段，标记弯道序号。", "分段算法"),
        ("h3", "常见错误：坏缓存"),
        ("bullet", "trackmap 曾因坏缓存（缓存了 0 点的结果，7 天 TTL）返回空轮廓——删缓存后恢复 338 点。", "教训"),
    ],
    "qa": [
        ("赛道地图怎么画出来的？", "取 position data 的 X/Y 坐标序列 → 归一化到画布坐标 → SVG polyline 或 ECharts line 绘制闭环。弯道分段用速度变化/曲率阈值切分，30 段各着色。"),
        ("SVG 和 ECharts 画赛道选哪个？", "SVG：轮廓精细、矢量放大不糊、交互需手写；ECharts：事件/tooltip 现成、适合与数据绑定（每段颜色映射）。本项目按场景：纯地图用 SVG，带数据用 ECharts。"),
    ],
},
{
    "id": "3.8",
    "title": "B6 天气数据",
    "concept": [
        "比赛天气（气温/赛道温度/湿度/降雨概率）影响轮胎选择与策略判断。FastF1 提供 session.weather 时序数据。",
        ("h3", "实现"),
        ("code", "session.load(weather=True)\n"
                "weather = session.weather  # DataFrame：AirTemp, TrackTemp, Humidity,\n"
                "                           # Pressure, Rainfall, WindSpeed, Time\n\n"
                "def _pack_weather(session):\n"
                "    w = session.weather\n"
                "    return {\n"
                "        'air_temp': float(w['AirTemp'].mean()),\n"
                "        'track_temp': float(w['TrackTemp'].mean()),\n"
                "        'humidity': float(w['Humidity'].mean()),\n"
                "        'rainfall': bool(w['Rainfall'].any()),\n"
                "    }",
                "天气数据"),
        ("bullet", "降雨标记：Rainfall 列布尔值，any() 判断赛段内是否下雨。", "降雨"),
        ("bullet", "天气是时序数据：可绘制全程温度曲线，观察策略窗口。", "时序"),
    ],
    "qa": [
        ("天气数据对 F1 分析的价值？", "影响轮胎配方选择（雨胎/半雨胎/干胎）、进站策略窗口（降雨前换胎）、引擎与刹车散热。产品上可做「天气+轮胎策略」联动分析。"),
    ],
},
{
    "id": "3.9",
    "title": "阶段 2 综合面试问答",
    "qa": [
        ("遥测分析模块的完整技术链路？", "FastF1 拉取原始遥测（telemetry=True）→ 三级缓存（.ff1pkl 原始 + JSON 结果 7 天）→ 采样约 300 点/车手 → 归一化横轴 → JSON 返回 → 前端 ECharts 渲染速度/油门/刹车/Delta，echarts.connect 三图联动。"),
        ("处理大数据量遥测遇到过什么问题？", "① JSON 体积过大（全量数十 MB）→ 采样解决；② FastF1 3.8.x 无 Distance 列 → 归一化索引；③ 接口超时 → 单独 60s 超时；④ 前端渲染卡顿 → 300 点采样 + showSymbol:false。"),
        ("怎么验证 Delta 梯形积分的正确性？", "① 与官方最快圈时间对比误差（积分总时间 vs LapTime）；② 起点 delta=0、终点 delta 应等于两车圈速差；③ 单调性检查（同车手积分时间应递增）。"),
        ("如果让你给产品加一个「车手对决」功能，怎么设计？", "选两位车手 → 同圈对比：速度叠加（网格对齐）+ 每段 Delta + 刹车点/出弯速度标注 → 输出「弯道得失摘要」（谁在哪段快多少秒）。复用 B2 数据管道 + B4 插值 + 分段最快。"),
    ],
},
]
