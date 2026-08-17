# 阶段 2/3 扩展知识点：速度叠加 / 赛道地图 / 天气 / Fantasy 扩展

> 对应模块 B4（速度叠加）、B5（赛道地图）、B6（天气）、C 扩展（定价 API / 历史记录 / 芯片 / 转会 / 联盟）。
> 每个知识点配「概念 + 代码 + 踩坑 + 面试问答」四段式。

---

## 目录

- [一、B4 速度叠加对比（Speed Overlay）](#一b4-速度叠加对比speed-overlay)
- [二、B5 赛道地图分段着色（Track Map）](#二b5-赛道地图分段着色track-map)
- [三、B6 天气数据叠加（Weather）](#三b6-天气数据叠加weather)
- [四、Fantasy 动态定价 API](#四fantasy-动态定价-api)
- [五、Fantasy 历史阵容记录](#五fantasy-历史阵容记录)
- [六、Fantasy 芯片系统](#六fantasy-芯片系统)
- [七、Fantasy 转会市场](#七fantasy-转会市场)
- [八、Fantasy 联盟系统](#八fantasy-联盟系统)
- [九、面试问答](#九面试问答)
- [十、踩坑总览表](#十踩坑总览表)

---

## 一、B4 速度叠加对比（Speed Overlay）

### 1.1 概念

速度叠加对比（Speed Overlay）与 B2 遥测对比的区别：

| 特性 | B2 遥测对比 | B4 速度叠加 |
|------|-----------|-----------|
| X 轴 | 各车手自己的 Distance | 统一的归一化距离网格 |
| 对齐方式 | 各车手独立 X 轴 | 所有车手插值到同一网格 |
| 对比精度 | 弯道位置可能错位 | 同一 X = 同一赛道位置 |
| 通道 | 6 通道可选 | 专注速度单通道 |
| 用途 | 看油门/刹车/RPM | 精确对比弯道速度差 |

### 1.2 核心算法：距离插值

不同车手的遥测数据采样点不同（圈速不同 → 距离点不同），需要用 `numpy.interp()` 将所有车手插值到统一的距离网格：

```python
import numpy as np

# 原始数据：车手 A 的距离和速度
distances_raw = car_data["Distance"].fillna(0).values  # [0, 12.5, 25.0, ...]
speeds_raw = car_data["Speed"].fillna(0).values         # [85, 120, 310, ...]

# 统一网格：每 50m 一个点
GRID_STEP = 50.0
track_len = float(np.nanmax(distances_raw))
grid = np.arange(0, track_len + GRID_STEP, GRID_STEP)

# 一维线性插值：把原始速度映射到统一网格
interpolated = np.interp(grid, distances_raw, speeds_raw)
# 结果：[85.0, 110.2, 145.5, ..., 305.3]
```

**为什么要插值？**
- 车手 A 在距离 100m 处的速度是 200 km/h
- 车手 B 在距离 103m 处才有采样点（速度 195 km/h）
- 不插值 → 两个车手的数据点不对齐 → 画出来的曲线在弯道处错位
- 插值后 → 两个车手在 100m 处都有值 → 可以精确对比

### 1.3 统一网格长度

不同车手的赛道距离可能略有差异（切弯 vs 走外线），所有车手的插值结果长度可能不同。处理方式：取最短长度截断：

```python
# 所有车手插值后，取最短长度对齐
min_len = min(len(d["speed"]) for d in drivers_data.values())
for d in drivers_data.values():
    d["speed"] = d["speed"][:min_len]
```

### 1.4 前端 ECharts 渲染

速度叠加图用 ECharts line + dataZoom，支持拖拽缩放：

```javascript
const series = Object.entries(data.drivers).map(([code, d], idx) => ({
  name: code,
  type: 'line',
  data: d.speed,
  smooth: true,
  symbol: 'none',
  lineStyle: { width: 2, color: driverColors[idx] },
}))

chart.setOption({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: distances, name: '赛道距离 (m)' },
  yAxis: { type: 'value', name: '速度 (km/h)' },
  dataZoom: [
    { type: 'inside', start: 0, end: 100 },  // 鼠标滚轮缩放
    { type: 'slider', start: 0, end: 100 },   // 底部滑块
  ],
  series,
})
```

### 1.5 踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| 插值后曲线有尖刺 | 原始数据有异常值 | `smooth: true` 平滑 + `fillna(0)` 处理 NaN |
| 不同车手曲线长度不同 | 赛道距离不一致 | 取 `min_len` 截断 |
| 首次加载慢（30s+） | FastF1 需要下载遥测数据 | 前端 timeout 设 60s + 结果缓存 |

---

## 二、B5 赛道地图分段着色（Track Map）

### 2.1 概念

赛道地图分段着色是 GP Tempo 的标志性功能：
- 用 SVG 渲染赛道轮廓
- 按 Sector 1/2/3 三段分别着色
- Purple（紫色）= 全场最快，Green（绿色）= 个人最快，Yellow（黄色）= 非个人最快

### 2.2 获取赛道坐标

FastF1 通过 `session.get_circuit_info()` 获取赛道坐标点：

```python
session = fastf1.get_session(2025, 1, "R")
session.load(laps=True, telemetry=False, weather=False, messages=False)

circuit_info = session.get_circuit_info()
# circuit_info 包含 X, Y 坐标列（归一化坐标）
```

**注意**：`get_circuit_info()` 返回的是 DataFrame，包含 `X` 和 `Y` 列。坐标可能需要旋转/翻转才能正向显示，但在本项目中我们做了归一化处理。

### 2.3 坐标归一化

将原始坐标归一化到 0-100 范围，前端 SVG 用 `viewBox="0 0 100 100"` 即可适配：

```python
x_vals = circuit_info["X"].dropna().values
y_vals = circuit_info["Y"].dropna().values

x_min, x_max = float(np.min(x_vals)), float(np.max(x_vals))
y_min, y_max = float(np.min(y_vals)), float(np.max(y_vals))
x_range = max(x_max - x_min, 0.001)  # 防除零
y_range = max(y_max - y_min, 0.001)

track_points = [{
    "x": round((float(x) - x_min) / x_range * 100, 2),
    "y": round((float(y) - y_min) / y_range * 100, 2),
} for x, y in zip(x_vals, y_vals)]
```

### 2.4 前端 SVG 渲染

用 SVG `<polyline>` 绘制赛道轮廓，分段用不同颜色覆盖：

```html
<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
  <!-- 底层：灰色赛道轮廓 -->
  <polyline :points="trackPointsStr" fill="none" stroke="#c0c0c0" stroke-width="3" />
  <!-- 上层：分段着色 -->
  <polyline v-for="(seg, i) in trackSegments" :key="i"
    :points="seg.points" fill="none" :stroke="seg.color" stroke-width="4" />
  <!-- 起点标记 -->
  <circle :cx="start.x" :cy="start.y" r="1.5" fill="#333" />
</svg>
```

**分段着色逻辑**（前端）：
```javascript
const total = trackPoints.length
const perSeg = Math.ceil(total / 3)  // 每段约 1/3

for (let i = 0; i < 3; i++) {
  const start = i * perSeg
  const end = i === 2 ? total : (i + 1) * perSeg + 1  // +1 连接点
  const segPts = trackPoints.slice(start, end)
  const sectorInfo = sectors.find(s => s.sector === i + 1)
  const color = colorMap[sectorInfo.color]  // purple=#a020f0, green=#00aa00
  segments.push({ points: segPts, color })
}
```

### 2.5 踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| 部分赛道无坐标数据 | `get_circuit_info()` 返回空 | try/except 兜底，显示"暂无地图数据" |
| 坐标方向反了 | 原始坐标系可能翻转 | 可用 `100 - y` 翻转 Y 轴 |
| SVG 不显示 | viewBox 与坐标范围不匹配 | 归一化到 0-100 + `preserveAspectRatio` |

### 2.6 赛道 30 段分段最快车手染色（GP Tempo 风格）

> **2026-08-14 新增**：在 B2 telemetry 接口中扩展，直接返回 `track_points` + `corner_segments`，前端 TrackLayer 用 ECharts 分段渲染。

#### 2.6.1 与 B5 三段着色的区别

| 特性 | B5 三段着色（Sector） | 2.6 三十段染色（Corner Segment） |
|------|----------------------|-------------------------------|
| 分段数 | 3（Sector 1/2/3） | 30（等分整圈） |
| 最快判定 | Sector 计时快慢 | 各段平均速度 |
| 数据来源 | `session.get_circuit_info()` | `fastest.get_pos_data()` + `get_car_data()` |
| 颜色规则 | Purple/Green/Yellow | 该段最快车手的车队色 |
| 渲染方式 | SVG `<polyline>` | ECharts 多 series `type:'line'` |
| 接口 | `/track-map` 独立接口 | `/telemetry` 接口扩展字段 |
| 对标 | F1 官方 sector 时间 | GP Tempo 弯角速度对比 |

#### 2.6.2 后端算法：corner_segments

把归一化 0~1 距离等分 30 段，每段求各车手 speed 数组对应索引的平均值：

```python
NUM_SEGMENTS = 30
corner_segments = []
total_dist = float(all_distances[-1])  # 1.0
seg_len = total_dist / NUM_SEGMENTS    # 0.0333

for seg_i in range(NUM_SEGMENTS):
    start_d = seg_i * seg_len
    end_d = (seg_i + 1) * seg_len
    # 找出该距离范围内的采样点索引
    indices = [i for i, d in enumerate(all_distances)
               if d is not None and start_d <= float(d) <= end_d]
    # 对每位车手，求该段 speed 平均值，取最大者为 fastest_driver
    best_code, best_avg = None, -1.0
    for code, chans in drivers_data.items():
        seg_speeds = [float(chans["speed"][i]) for i in indices
                      if i < len(chans["speed"]) and chans["speed"][i] is not None]
        if seg_speeds:
            avg = sum(seg_speeds) / len(seg_speeds)
            if avg > best_avg:
                best_avg, best_code = avg, code
    corner_segments.append({
        "segment_index": seg_i,
        "start_dist": round(start_d, 4),
        "end_dist": round(end_d, 4),
        "fastest_driver": best_code,
        "fastest_avg_speed_kmh": round(best_avg, 1) if best_avg > 0 else None,
    })
```

#### 2.6.3 track_points 提取

从车手最快圈的 **position data**（不是 circuit_info）提取赛道轮廓：

```python
fastest = laps.pick_fastest()
pos_data = fastest.get_pos_data()  # 需要 session.load(telemetry=True)

# 降采样
step = max(1, len(pos_data) // 200)
sampled = pos_data.iloc[::step]

# 归一化 X/Y 到 0-100，Y 轴翻转
x_vals = sampled["X"].fillna(0).values
y_vals = sampled["Y"].fillna(0).values
x_min, x_max = float(np.min(x_vals)), float(np.max(x_vals))
y_min, y_max = float(np.min(y_vals)), float(np.max(y_vals))

track_points = [{
    "x": round((float(x) - x_min) / max(x_max - x_min, 0.001) * 100, 2),
    "y": round(100 - (float(y) - y_min) / max(y_max - y_min, 0.001) * 100, 2),
} for x, y in zip(x_vals, y_vals)]
```

#### 2.6.4 前端 ECharts 分段渲染

TrackLayer.vue 接收 `cornerSegments` + `driverColorMap` 两个 props，按段生成独立 series：

```javascript
// 每段一个 series，颜色 = 该段最快车手的车队色
for (let i = 0; i < segCount; i++) {
  const seg = cornerSegments[i]
  const startIdx = Math.floor((i / segCount) * N)
  const endIdx = Math.max(startIdx + 1, Math.floor(((i + 1) / segCount) * N))
  const slice = trackLine.slice(startIdx, endIdx)
  const code = seg.fastest_driver
  const color = driverColorMap[code] || '#444'
  segSeriesList.push({
    name: code, type: 'line', data: slice,
    showSymbol: false, smooth: true,
    lineStyle: { width: 5, color },
    emphasis: { lineStyle: { width: 7 } },
  })
}
```

#### 2.6.5 关键踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| distances 返回 `[0,1,2,...,310]` | FastF1 3.8.x `car_data` 无 `Distance` 列，fallback 到 `range()` | 改用归一化 `i/(N-1)`，所有车手共享索引基准 |
| corner_segments `end_dist=0.0` | `round(0.0333, 1)` = 0.0 精度丢失 | round 改为 4 位小数 |
| track_points 为空 | `get_pos_data()` 需要 `telemetry=True` | `session.load(telemetry=True)` |
| 改后接口仍返回旧数据 | `telemetry_v2_` 缓存命中旧结果 | 删除 `cache/fastf1_result_cache/telemetry_v2_*.json` |
| 改错文件没效果 | 误改 `TeleCompare.vue`（legacy 页面），实际组件是 `views/telemetry/TrackLayer.vue` | 确认路由 `/telemetry` → `TelemetryCockpit.vue` → `TrackLayer.vue` |

---

## 三、B6 天气数据叠加（Weather）

### 3.1 概念

FastF1 提供 `session.weather_data` 属性，包含比赛期间的逐帧天气信息：
- `AirTemp`：气温（°C）
- `TrackTemp`：赛道温度（°C）
- `Rainfall`：降雨量（mm）
- `Humidity`：湿度（%）
- `Pressure`：气压（mbar）
- `WindSpeed`：风速（m/s）
- `WindDirection`：风向（°）

### 3.2 加载天气数据

天气数据需要显式指定 `weather=True`：

```python
session = fastf1.get_session(2025, 1, "R")
session.load(laps=False, telemetry=False, weather=True, messages=False)

weather_data = session.weather_data  # pandas DataFrame
```

**注意**：天气数据仅 2018+ 可用（FastF1 的数据源限制）。

### 3.3 数据处理

天气数据是逐帧的（约每分钟一条），需要降采样到 ~50 个点：

```python
df = weather_data.copy()
step = max(1, len(df) // 50)
sampled = df.iloc[::step].reset_index(drop=True)

# 汇总统计
summary = {
    "avg_air_temp": round(float(df["AirTemp"].mean()), 1),
    "avg_track_temp": round(float(df["TrackTemp"].mean()), 1),
    "max_rainfall": round(float(df["Rainfall"].max()), 2),
    "is_wet": bool(df["Rainfall"].max() > 0),
}
```

### 3.4 timedelta 处理

天气数据中的 `Time` 列是 `timedelta64[ns]`，需要转成可读字符串：

```python
t = row["Time"]  # timedelta
if hasattr(t, "total_seconds"):
    total_sec = int(t.total_seconds())
    time_str = f"{total_sec // 3600:02d}:{(total_sec % 3600) // 60:02d}:{total_sec % 60:02d}"
```

### 3.5 踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `weather_data` 为 None | 没加 `weather=True` | `session.load(weather=True)` |
| 部分分站无天气数据 | 2018 之前无数据 | try/except 返回提示信息 |
| `Time` 列序列化失败 | timedelta 无法 JSON 序列化 | 手动转字符串 |

---

## 四、Fantasy 动态定价 API

### 4.1 概念

PRD 3.3.3 定义了动态定价算法：

```
driver_price = base_price × (0.5 + 0.5 × season_points_ratio)
  + trend_bonus（近期表现趋势）
  - penalty（DNF 惩罚，每次 -2M，最多 -10M）

base_price: Top3=30M, Top5=25M, Top10=20M, 其余=15M, 新秀=10M
```

### 4.2 API 实现

定价 API 需要聚合两个赛季的数据：
1. **上赛季积分榜** → 决定 base_price（上赛季排名）
2. **当前赛季积分榜** → 决定 season_points_ratio

```python
@app.get("/api/fantasy/prices")
def get_fantasy_prices(season: int, db: Session = Depends(get_db)):
    # 获取上赛季排名（决定 base_price）
    last_standings = fetch_ergast_driverstandings_by_year(season - 1)
    last_rank_map = {code: position for ...}

    # 获取当前赛季积分（决定 ratio）
    current_standings = fetch_ergast_driverstandings_by_year(season)
    max_points = max(d["points"] for d in current_standings)

    for driver in current_standings:
        price = game_service.calculate_driver_price(
            season_points=driver["points"],
            max_season_points=max_points,
            recent_avg_position=driver["position"],
            dnf_count=0,
            last_season_rank=last_rank_map.get(code, 0),
        )
```

### 4.3 边界处理

```python
# 新车手无上赛季数据 → last_season_rank=0 → base_price=10M（新秀价）
# 价格下限保底 → max(5.0, price)，避免出现 0 元车手
```

### 4.4 面试问答

> **Q: 为什么动态定价需要两个赛季的数据？**
> A: 上赛季排名决定车手的基础价值（base_price），反映车手的长期实力；当前赛季积分决定即时状态（season_points_ratio），反映本赛季的发挥。两者结合可以避免"上赛季冠军今年摆烂但价格还很高"的问题。

---

## 五、Fantasy 历史阵容记录

### 5.1 概念

用户需要查看自己整个赛季的 Fantasy 阵容历史和每站得分明细。

### 5.2 实现要点

```python
@app.get("/api/fantasy/history")
def get_fantasy_history(season: int, user=Depends(get_current_user), db=Depends(get_db)):
    teams = db.query(FantasyTeam).filter(
        FantasyTeam.user_id == user.id,
        FantasyTeam.season == season,
    ).order_by(FantasyTeam.round.asc()).all()

    return {
        "season": season,
        "total_rounds": len(teams),
        "total_points": sum(t.total_points for t in teams if t.is_scored),
        "history": [{...} for t in teams],
    }
```

**SQLAlchemy 查询技巧**：
- `order_by(FantasyTeam.round.asc())` — 按分站序号升序
- `sum(t.total_points for t in teams if t.is_scored)` — 只统计已结算的分站

---

## 六、Fantasy 芯片系统

### 6.1 芯片规则

| 芯片 | 效果 | 赛季使用上限 |
|------|------|-------------|
| Limitless | 本站无视预算限制 | 2 次 |
| Wildcard | 本站无限制转会 | 2 次 |
| No Negative | 本站 DNF 不扣分 | 1 次 |

### 6.2 数据模型设计

芯片使用计数存在 User 表上（赛季维度）：

```python
class User(Base):
    # ...
    chip_limitless_used = Column(Integer, default=0)
    chip_wildcard_used = Column(Integer, default=0)
    chip_no_negative_used = Column(Integer, default=0)
```

**为什么存在 User 表而不是单独建表？**
- 芯片计数是简单的整数累加，不需要单独建表
- 每个用户每赛季最多 5 次使用（2+2+1），不存在复杂查询
- 如果需要赛季维度重置，可以在赛季初始化时清零

### 6.3 使用逻辑

```python
@app.post("/api/fantasy/chip")
def use_chip(req: ChipUseRequest, user=Depends(get_current_user), db=Depends(get_db)):
    chip_limits = {"limitless": 2, "wildcard": 2, "no_negative": 1}
    chip_fields = {"limitless": "chip_limitless_used", "wildcard": "chip_wildcard_used", "no_negative": "chip_no_negative_used"}

    field = chip_fields[req.chip]
    used = getattr(user, field, 0)

    if used >= chip_limits[req.chip]:
        raise HTTPException(400, f"{req.chip} 芯片已用完")

    setattr(user, field, used + 1)
    db.commit()
```

### 6.4 踩坑

| 问题 | 解决 |
|------|------|
| 芯片使用后用户更新阵容，芯片状态如何处理？ | 芯片绑定到站不可撤销，阵容更新不退回芯片 |
| 赛季重置时芯片计数如何清零？ | 可在赛季初始化脚本中 `user.chip_*_used = 0` |
| 前端如何防止选了已用完的芯片？ | `el-option :disabled="chipStatus.limitless.remaining <= 0"` |

---

## 七、Fantasy 转会市场

### 7.1 转会规则

- 每人每站 2 次免费转会
- 超出免费次数 → 按规则扣分
- Wildcard 芯片 → 本站无限制转会，不消耗免费次数

### 7.2 数据模型

在 FantasyTeam 表添加 `transfers_used` 字段：

```python
class FantasyTeam(Base):
    # ...
    transfers_used = Column(Integer, default=0)  # 本站已用转会次数
```

### 7.3 转会次数重置

转会次数是**每站重置**的（与芯片的赛季维度不同）：
- 每站创建新阵容时 `transfers_used = 0`
- 同一站更新阵容时 `transfers_used += 1`
- Wildcard 芯片下不增加 `transfers_used`

---

## 八、Fantasy 联盟系统

### 8.1 数据模型

联盟系统需要两张表：

```python
class League(Base):
    """联盟表"""
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(20), unique=True, nullable=False)  # 邀请码
    creator_id = Column(Integer, ForeignKey("users.id"))
    season = Column(Integer, nullable=False)
    max_members = Column(Integer, default=50)

class LeagueMembership(Base):
    """联盟成员关联表（多对多）"""
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    # 唯一约束：同一用户不能重复加入同一联盟
    __table_args__ = (UniqueConstraint("league_id", "user_id"),)
```

### 8.2 邀请码生成

使用 Python 标准库 `secrets.token_urlsafe()` 生成安全的随机邀请码：

```python
import secrets

invite_code = secrets.token_urlsafe(8)[:10].upper()
# 示例: "A3B7C9X2M1"
```

**为什么用 `secrets` 而不是 `random`？**
- `random` 是伪随机，可预测
- `secrets` 使用操作系统级 CSPRNG（密码学安全随机数生成器）
- 邀请码相当于"准密码"，需要不可猜测

### 8.3 联盟排行榜查询

联盟排行榜需要跨用户聚合 Fantasy 积分：

```python
from sqlalchemy import func

rows = db.query(
    User.id, User.username,
    func.sum(FantasyTeam.total_points).label("season_points"),
    func.count(FantasyTeam.id).label("rounds_scored"),
).join(
    LeagueMembership, LeagueMembership.user_id == User.id
).outerjoin(
    FantasyTeam, FantasyTeam.user_id == User.id
).filter(
    LeagueMembership.league_id == league_id,
    FantasyTeam.season == league.season,
    FantasyTeam.is_scored == True,
).group_by(
    User.id, User.username
).order_by(
    func.sum(FantasyTeam.total_points).desc()
).all()
```

**SQLAlchemy JOIN 要点**：
- `join()` — INNER JOIN，只返回匹配的行
- `outerjoin()` — LEFT JOIN，左表全部保留，右表不匹配的为 NULL
- 这里用 `outerjoin(FantasyTeam)` 因为新加入的联盟成员可能还没有 Fantasy 阵容

### 8.4 面试问答

> **Q: 联盟排行榜的 SQL 查询为什么用 outerjoin 而不是 join？**
> A: 因为联盟成员可能刚加入还没创建 Fantasy 阵容。用 `join` 会把这些成员排除在排行榜外，用 `outerjoin` 可以保留所有成员，没阵容的成员积分为 0。

> **Q: 为什么邀请码存在数据库里而不是每次动态生成？**
> A: 邀请码是联盟的唯一入口，必须持久化存储。如果动态生成，每次查询结果不同，用户无法分享。存在 `League.invite_code` 字段，创建时生成一次，永久有效。

---

## 九、面试问答

### B4 速度叠加

> **Q: 速度叠加和遥测对比有什么区别？**
> A: 遥测对比用各车手自己的 Distance 做 X 轴，不同车手的采样点不对齐，弯道处可能错位。速度叠加用 `numpy.interp()` 将所有车手插值到统一的距离网格（每 50m 一个点），同一 X 坐标对应同一赛道位置，可以精确对比弯道速度差异。

> **Q: numpy.interp 的工作原理？**
> A: 一维线性插值。给定原始 x/y 数组和目标 x 网格，对每个目标 x 找到它在原始 x 中的位置，然后线性插值计算对应的 y 值。例如原始 (100, 200) 和 (110, 220)，目标 x=105 → y=210。

### B5 赛道地图

> **Q: 为什么赛道坐标要归一化？**
> A: FastF1 返回的原始坐标范围不确定（可能是经纬度或归一化值），直接用于 SVG 会超出 viewBox。归一化到 0-100 范围后，SVG `viewBox="0 0 100 100"` 可以完美适配，不需要额外的坐标变换。

### C 联盟系统

> **Q: 联盟系统的数据库设计要点？**
> A: 两张表：League（联盟主表）+ LeagueMembership（多对多关联表）。关键设计：1) 邀请码用 `secrets.token_urlsafe()` 生成，存在 League 表；2) LeagueMembership 用 `UniqueConstraint("league_id", "user_id")` 防止重复加入；3) 外键设 `ondelete="CASCADE"`，删联盟自动删成员。

> **Q: 如何处理"用户加入了联盟但还没有 Fantasy 阵容"的情况？**
> A: 查询联盟排行榜时用 `outerjoin(FantasyTeam)` 而不是 `join()`。LEFT JOIN 保留所有联盟成员，没有阵容的成员 `SUM(total_points)` 为 NULL，前端显示为 0 分。

---

## 十、踩坑总览表

| 模块 | 问题 | 原因 | 解决 |
|------|------|------|------|
| B4 | 插值后曲线长度不一致 | 不同车手赛道距离不同 | 取 `min_len` 截断 |
| B4 | NaN 导致 interp 报错 | 原始数据有空值 | `fillna(0)` 预处理 |
| B5 | `get_circuit_info()` 返回空 | 部分赛道无坐标数据 | try/except 兜底 |
| B5 | SVG 不显示 | viewBox 与坐标不匹配 | 归一化到 0-100 |
| B6 | `weather_data` 为 None | 没加 `weather=True` | `session.load(weather=True)` |
| B6 | Time 列序列化失败 | timedelta 不可 JSON 序列化 | 手动转字符串 |
| C 定价 | 新车手价格异常 | 无上赛季数据 | `max(5.0, price)` 保底 |
| C 芯片 | 芯片计数不重置 | 没有赛季初始化逻辑 | 赛季初始化脚本清零 |
| C 联盟 | 重复加入联盟 | 缺少唯一约束 | `UniqueConstraint("league_id", "user_id")` |
| C 联盟 | 邀请码可预测 | 用了 `random` | 改用 `secrets.token_urlsafe()` |
| C 联盟 | 成员无阵容时排行榜报错 | 用了 `join` 而非 `outerjoin` | 改用 `outerjoin` |
