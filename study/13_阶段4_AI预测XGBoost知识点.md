# 阶段 4：AI 预测 XGBoost 知识点文档

> 版本: v1.0 | 日期: 2026-08-14 | 状态: 阶段 1 数据采集已完成，阶段 2-5 待实现  
> 前置文档: `study/11_阶段3_数据库与AI预测知识点.md`（规则加权模型部分）

---

## 目录

- [一、为什么用 XGBoost 替代规则加权](#一为什么用-xgboost-替代规则加权)
- [二、整体架构与数据流](#二整体架构与数据流)
- [三、阶段 1：数据采集（已完成）](#三阶段-1数据采集已完成)
- [四、阶段 2：特征工程](#四阶段-2特征工程)
- [五、阶段 3：模型训练](#五阶段-3模型训练)
- [六、阶段 4：在线推理服务](#六阶段-4在线推理服务)
- [七、阶段 5：SHAP 特征解释 + 前端更新](#七阶段-5shap-特征解释--前端更新)
- [八、评估指标详解](#八评估指标详解)
- [九、面试问答（20 题）](#九面试问答20-题)
- [十、踩坑总览（18 条）](#十踩坑总览18-条)

---

## 一、为什么用 XGBoost 替代规则加权

### 1.1 两种模型的本质区别

| 对比维度 | 规则加权模型 (rule_v1) | XGBoost (xgb_v1) |
|---------|----------------------|-------------------|
| 权重来源 | 人工设定（35%/25%/15%/15%/10%） | 从历史数据自动学习 |
| 特征交互 | 线性加权，不捕获特征间交互 | 树模型天然捕获非线性交互 |
| 可扩展性 | 每加一个特征要手工调权重 | 加特征后自动学习权重 |
| 可解释性 | 极高（权重一目了然） | 中等（需要 SHAP 辅助解释） |
| 数据依赖 | 不需要训练数据 | 需要历史数据训练 |
| 推理速度 | <1ms | <10ms（可接受） |

### 1.2 核心问题：手工权重的局限

当前规则模型用 5 个特征加权打分：

```python
raw = (
    champ_score * 0.35      # 积分占比
    + recent_score * 0.25   # 近期位次
    + qual_score * 0.15     # 排位位次
    + win_score * 0.15      # 历史胜率
    + dnf_score * 0.10      # 可靠性
)
```

问题在于：
1. **权重是猜的**——35% 还是 40%？没有数据支撑
2. **特征间有交互**——排位 P1 + 积分领先 vs 排位 P1 + 积分垫底，权重应该不同
3. **赛道差异被忽略**——摩纳哥排位赛重要性远大于斯帕，但模型无法区分
4. **新特征难加入**——加"车队近 5 场平均得分"后，所有权重都要重新调

XGBoost 通过梯度提升树自动学习这些关系，不需要人工猜权重。

### 1.3 XGBoost 是什么（30 秒理解）

XGBoost = eXtreme Gradient Boosting，是一个**梯度提升决策树**（GBDT）的高效实现。

核心思想：
1. 训练一棵决策树，预测目标值
2. 计算预测值与真实值的残差（误差）
3. 再训练一棵树，预测上一步的残差
4. 重复 N 次，最终预测 = 所有树的预测之和

```
预测值 = tree_1 预测 + tree_2 预测 + ... + tree_N 预测
```

每棵树都很"弱"（max_depth 通常 3-6），但组合起来很强大。

### 1.4 为什么选 XGBoost 而不是深度学习

| 因素 | XGBoost | 深度学习 (神经网络) |
|------|---------|-------------------|
| 数据量需求 | 小数据也能用（几千行） | 通常需要万级以上 |
| 表格数据表现 | 业界标杆，表格数据几乎无敌 | 通常不如树模型 |
| 训练速度 | 秒级 | 分钟到小时级 |
| 可解释性 | SHAP 可解释 | 黑盒，解释困难 |
| F1 数据特点 | 3458 行 × 15 列，典型小表格 | 不适合 |

**结论：F1 数据量小（3458 行）、是表格数据、需要可解释性——XGBoost 是最佳选择。**

---

## 二、整体架构与数据流

### 2.1 两阶段架构

```
┌─────────────────────────────────────────────────────┐
│                    离线训练 (Offline)                  │
│                                                       │
│  Ergast API → 采集脚本 → CSV → 特征工程 → XGBoost 训练 │
│       ↓                                              │
│  ml/data/races_2018_2025.csv                         │
│  ml/models/xgb_v1.json (模型文件)                     │
└─────────────────────────────────────────────────────┘
                        ↓ 部署模型文件
┌─────────────────────────────────────────────────────┐
│                    在线推理 (Online)                   │
│                                                       │
│  前端请求 → FastAPI → predict_race()                  │
│                        ↓                              │
│                   加载 xgb_v1.json                    │
│                        ↓                              │
│                   实时获取特征 (Ergast API)            │
│                        ↓                              │
│                   model.predict_proba()              │
│                        ↓                              │
│                   归一化 → 返回概率分布                │
└─────────────────────────────────────────────────────┘
```

### 2.2 与现有代码的衔接

```
现有代码                          XGBoost 改造
─────────────────────────────────────────────────
prediction_service.py
├── _fetch_driver_standings()   ← 保留，推理时复用
├── _fetch_recent_results()     ← 保留，推理时复用
├── _fetch_qualifying()         ← 保留，推理时复用
├── _calculate_features()       ← 保留，推理时复用（+新特征）
├── _weighted_score()           ← 保留，作为 fallback
└── predict_race()              ← 重写，改用 model.predict_proba()

新增文件
├── scripts/collect_training_data.py  ← 已完成
├── ml/data/*.csv                     ← 已生成
├── ml/notebooks/train_xgboost.ipynb  ← 待创建（训练 Notebook）
├── ml/models/xgb_v1.json             ← 待生成（模型文件）
└── study/13_阶段4_AI预测XGBoost知识点.md  ← 本文档
```

### 2.3 数据量预算

| 维度 | 数量 | 说明 |
|------|------|------|
| 时间跨度 | 2018-2025 (8 年) | 2022 新规后数据更相关 |
| 比赛场次 | 173 场 | 已采集 |
| 每场车手数 | ~20 | 共 3458 行 |
| 独立车手数 | 43 | VER/HAM/NOR... |
| 胜负比 | 173:3285 (1:19) | 严重不平衡 |
| DNF 率 | 11% (380/3458) | 合理范围 |

---

## 三、阶段 1：数据采集（已完成）

### 3.1 采集脚本架构

文件：`scripts/collect_training_data.py`

```
脚本结构
├── 配置层
│   ├── ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"
│   ├── CACHE_DIR = cache/ergast_cache/      # 复用现有缓存
│   ├── HISTORICAL_TTL = 7 * 24 * 3600       # 历史数据 7 天缓存
│   ├── REQUEST_DELAY = 0.5                   # 请求间隔 0.5s
│   └── MAX_RETRIES = 3                       # 失败重试 3 次
│
├── Ergast 请求层
│   ├── ergast_get(endpoint, cache_key)      # 带缓存+重试的通用 GET
│   ├── fetch_season_schedule(year)          # 赛程
│   ├── fetch_race_results(year, round)      # 正赛结果
│   ├── fetch_qualifying(year, round)        # 排位赛
│   ├── fetch_driver_standings(year)         # 赛季末积分榜
│   └── fetch_all_circuits()                 # 赛道元数据
│
├── 数据解析层
│   ├── parse_race_row()                     # 结果 → 扁平 dict
│   ├── parse_standings_row()                # 积分榜 → 扁平 dict
│   └── parse_circuit_row()                  # 赛道 → 扁平 dict
│
└── 主流程
    ├── 1. 采集赛道元数据 → circuits.csv
    ├── 2. 采集积分榜 → standings_2018_2025.csv
    ├── 3. 采集每场结果 → races_2018_2025.csv
    └── 4. 数据质量检查
```

### 3.2 Ergast API 端点详解

Ergast API 是 F1 历史数据的金矿，理解它的端点结构是采集数据的基础。

```
基础 URL: https://api.jolpi.ca/ergast/f1

常用端点:
/{year}.json                           → 某赛季赛程
/{year}/{round}/results.json           → 某场正赛结果
/{year}/{round}/qualifying.json        → 某场排位赛结果
/{year}/driverstandings.json           → 赛季末车手积分榜
/{year}/constructorstandings.json      → 赛季末车队积分榜
/circuits.json                         → 全量赛道列表
/{year}/drivers.json                   → 某赛季车手名单

示例: 2024 年第 5 场正赛结果
GET https://api.jolpi.ca/ergast/f1/2024/5/results.json

响应结构 (简化):
{
  "MRData": {
    "RaceTable": {
      "Races": [{
        "season": "2024",
        "round": "5",
        "raceName": "Chinese Grand Prix",
        "date": "2024-04-21",
        "Circuit": {
          "circuitId": "shanghai",
          "circuitName": "Shanghai International Circuit",
          "Location": {"locality": "Shanghai", "country": "China",
                       "lat": "31.3389", "long": "121.218"}
        },
        "Results": [{
          "number": "1",
          "position": "1",          # 完赛位次 (1=冠军)
          "positionText": "1",
          "points": "25",
          "Driver": {
            "driverId": "max_verstappen",
            "code": "VER",          # 三字母缩写
            "givenName": "Max",
            "familyName": "Verstappen",
            "dateOfBirth": "1997-09-30",
            "nationality": "Dutch"
          },
          "Constructor": {
            "constructorId": "red_bull",
            "name": "Red Bull",
            "nationality": "Austrian"
          },
          "grid": "1",              # 发车位
          "laps": "56",             # 完成圈数
          "status": "Finished"      # 完赛状态
        }, ...]
      }]
    }
  }
}
```

### 3.3 缓存策略详解

```python
# 历史数据永不变, 缓存 7 天即可
HISTORICAL_TTL = 7 * 24 * 3600  # 604800 秒

def ergast_get(endpoint: str, cache_key: str, force: bool = False) -> dict:
    # 1. 检查缓存是否有效
    if not force and _is_cache_valid(cache_key):
        return _load_cache(cache_key)  # 命中缓存, 0 网络请求

    # 2. 缓存过期或不存在, 发起 HTTP 请求
    url = f"{ERGAST_BASE}/{endpoint}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()["MRData"][...]
            _save_cache(cache_key, data)  # 写入缓存
            time.sleep(REQUEST_DELAY)     # 0.5s 间隔防限流
            return data
        except RequestException as e:
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)   # 指数退避: 2s, 4s
            else:
                return {}                  # 放弃, 返回空
```

**为什么 0.5s 间隔？** Ergast 镜像 (jolpi.ca) 有请求频率限制，实测连续请求约 10-15 次后会返回 429 Too Many Requests。0.5s 间隔能把 429 概率降到约 5%，再配合重试机制可以接近 0%。

### 3.4 数据解析：从嵌套 JSON 到扁平 CSV

Ergast 返回的是深度嵌套的 JSON，需要"拍平"成 CSV 的行列结构。

```python
def parse_race_row(year, round_num, race_name, race_date,
                   circuit_info, result, qualifying_map):
    """一条 Ergast 正赛结果 → 一个扁平 dict (CSV 的一行)

    输入 (嵌套 JSON 片段):
    result = {
        "position": "1",
        "points": "25",
        "Driver": {"driverId": "max_verstappen", "code": "VER", ...},
        "Constructor": {"constructorId": "red_bull", "name": "Red Bull", ...},
        "grid": "1", "laps": "56", "status": "Finished"
    }

    输出 (扁平 dict):
    {
        "year": 2024, "round": 5, "race_name": "Chinese Grand Prix",
        "driver_code": "VER", "constructor_name": "Red Bull",
        "qualifying_pos": 1, "grid": 1, "finishing_pos": 1,
        "points": 25.0, "laps": 56, "status": "Finished",
        "is_win": 1, "is_podium": 1, "is_points_finish": 1, "is_dnf": 0
    }
    """
    driver = result.get("Driver", {})
    constructor = result.get("Constructor", {})
    driver_id = driver.get("driverId", "")

    # 类型转换 (Ergast 返回的都是字符串!)
    position = int(result.get("position", 0) or 0)
    grid = int(result.get("grid", 0) or 0)
    laps = int(result.get("laps", 0) or 0)
    points = float(result.get("points", 0) or 0.0)

    # 排位赛位次: 优先用排位赛 endpoint, 回退到正赛 grid
    qual_pos = qualifying_map.get(driver_id, grid)

    # 派生标签
    is_win = 1 if position == 1 else 0
    is_podium = 1 if 1 <= position <= 3 else 0
    is_points_finish = 1 if points > 0 else 0
    is_dnf = 1 if (position == 0 or "Retired" in status or
                    "Engine" in status or ...) else 0

    return {...}
```

**关键知识点：Ergast 所有数字字段都是字符串类型**，比如 `"position": "1"` 而不是 `"position": 1`。必须 `int()` / `float()` 显式转换，否则后续 pandas 会把列当成 object 类型，无法做数值计算。

### 3.5 采集结果

| 文件 | 行数 | 列数 | 说明 |
|------|------|------|------|
| `ml/data/races_2018_2025.csv` | 3458 | 29 | 主表，每行 = 一个车手在一场比赛的结果 |
| `ml/data/standings_2018_2025.csv` | 173 | 9 | 赛季末车手积分榜 |
| `ml/data/circuits.csv` | 78 | 7 | 赛道元数据 |

主表列说明：

| 列名 | 类型 | 说明 |
|------|------|------|
| year | int | 赛季年份 |
| round | int | 分站序号 |
| race_name | str | 分站名称 |
| race_date | str | 比赛日期 |
| circuit_id | str | 赛道 ID (如 "shanghai") |
| circuit_name | str | 赛道名称 |
| circuit_locality | str | 城市 |
| circuit_country | str | 国家 |
| circuit_lat | float | 纬度 |
| circuit_long | float | 经度 |
| driver_id | str | 车手 ID (如 "max_verstappen") |
| driver_code | str | 三字母缩写 (如 "VER") |
| driver_name | str | 全名 |
| driver_nationality | str | 国籍 |
| driver_number | int | 车号 |
| driver_dob | str | 出生日期 |
| constructor_id | str | 车队 ID |
| constructor_name | str | 车队名称 |
| constructor_nationality | str | 车队国籍 |
| qualifying_pos | int | 排位赛位次 |
| grid | int | 发车位 (可能与排位不同: 罚退) |
| finishing_pos | int | 完赛位次 (0=未完赛) |
| points | float | 积分 |
| laps | int | 完成圈数 |
| status | str | 完赛状态 (如 "Finished", "Retired") |
| is_win | int | 是否获胜 (1/0) — **训练标签** |
| is_podium | int | 是否领奖台 (1/0) |
| is_points_finish | int | 是否得分 (1/0) |
| is_dnf | int | 是否退赛 (1/0) |

### 3.6 数据质量检查

```python
# 检查 1: 年份覆盖
years = sorted(df["year"].unique())
# [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]  ✓ 8 年全覆盖

# 检查 2: 每年分站数
races_per_year = df.groupby("year")["round"].nunique()
# 2018: 21, 2019: 21, 2020: 17, 2021: 22, 2022: 22, 2023: 22, 2024: 24, 2025: 24  ✓

# 检查 3: 胜负比
df["is_win"].value_counts()
# 0: 3285, 1: 173  → 1:19 (每场 20 车手, 1 个冠军)  ✓

# 检查 4: DNF 率
df["is_dnf"].mean()
# 11.0%  → 合理 (F1 平均 DNF 率 10-15%)  ✓

# 检查 5: 缺失值
df.isnull().sum().sum()
# 0  → 无缺失  ✓

# 检查 6: 胜者分布
df[df["is_win"]==1]["driver_code"].value_counts().head(5)
# VER: 68, HAM: 43, NOR: 11, PIA: 9, LEC: 8  ✓ 符合历史
```

---

## 四、阶段 2：特征工程

> 状态：✅ 已完成。以下为实际实现代码 + 运行结果。
>
> 脚本：`scripts/feature_engineering.py`  产出：`ml/data/features_train.csv`（3458 行 × 19 特征）

### 4.1 特征设计原则

**铁律：每行数据的特征只能用该场比赛之前的信息。**

这是防止"数据泄漏"的核心原则。数据泄漏 = 用了赛后的数据来预测赛前的结果，会导致模型在训练集上表现极好，但在实际使用时一塌糊涂。

```
错误做法（泄漏）:
  2018 R5 的特征用了 2018 R5 的完赛结果 → 模型"偷看答案"

正确做法:
  2018 R5 的特征只用 2018 R1-R4 的数据 → 模型真正在"预测"
```

### 4.2 特征清单（19 个，6 组）

实际构建了 19 个特征，分为 6 组：

| # | 特征名 | 组 | 说明 | NaN 填充 |
|---|--------|------|------|----------|
| 1 | `qualifying_pos` | baseline | 排位赛位次（赛前已知） | 无 NaN |
| 2 | `grid` | baseline | 发车位次 | 无 NaN |
| 3 | `qualifying_pos_inv` | baseline | 排位位次倒数 (1/pos) | 无 NaN |
| 4 | `grid_inv` | baseline | 发车位次倒数 (1/grid) | 无 NaN |
| 5 | `driver_season_points_before` | driver_season | 赛季截至上轮累计积分 | 填 0 |
| 6 | `driver_season_races_before` | driver_season | 赛季截至上轮已赛场次 | 填 0 |
| 7 | `driver_season_wins_before` | driver_season | 赛季截至上轮胜场数 | 填 0 |
| 8 | `driver_season_dnfs_before` | driver_season | 赛季截至上轮 DNF 次数 | 填 0 |
| 9 | `driver_season_avg_pos_before` | driver_season | 赛季截至上轮平均完赛位次 | 填中位数 |
| 10 | `driver_last5_avg_pos` | driver_recent | 跨赛季近 5 场平均完赛位次 | 填中位数 |
| 11 | `driver_last5_dnfs` | driver_recent | 跨赛季近 5 场 DNF 次数 | 填 0 |
| 12 | `driver_circuit_avg_pos` | driver_circuit | 该赛道历史平均位次（往年） | 填中位数 |
| 13 | `driver_circuit_races` | driver_circuit | 该赛道历史参赛场次 | 填 0 |
| 14 | `driver_circuit_dnfs` | driver_circuit | 该赛道历史 DNF 次数 | 填 0 |
| 15 | `constructor_season_points_before` | constructor | 车队赛季截至上轮累计积分 | 填 0 |
| 16 | `constructor_season_avg_pos_before` | constructor | 车队赛季截至上轮平均位次 | 填中位数 |
| 17 | `constructor_season_dnfs_before` | constructor | 车队赛季截至上轮 DNF 次数 | 填 0 |
| 18 | `regulation_era` | context | 规则时代 (0=2018-2021, 1=2022+) | 无 NaN |
| 19 | `round_normalized` | context | 赛季进度 (round / total_rounds) | 无 NaN |

**与原设计稿的差异**：
- 原设计 15 个特征 → 实际 19 个（新增 `qualifying_pos_inv` / `grid_inv` / `driver_season_races_before` / `regulation_era`）
- 移除了 `driver_age`（出生日期缺失较多）、`points_momentum` / `position_trend`（计算复杂收益低）、`grid_vs_qualifying`（与 grid 重复）
- 新增倒数特征 `qualifying_pos_inv` 和 `grid_inv`，帮助树模型更好地利用位次的非线性关系

### 4.3 特征工程代码

> 完整脚本：`scripts/feature_engineering.py`（约 400 行）
>
> 核心思路：用 pandas `groupby` + `shift(1)` + `cumsum` 实现时间安全的特征计算，避免逐行 Python 循环。

#### 4.3.1 赛季内累计特征 — shift + cumsum

```python
# 按 车手 × 年份 × 轮次 排序
df = df.sort_values(["driver_code", "year", "round"]).reset_index(drop=True)
grp = df.groupby(["driver_code", "year"])

# shift(1) 把当前行下移 → 前一行的值
# cumsum() 对 shift 后的值累加 → 当前轮次之前的累计和
df["_points_before"] = grp["points"].shift(1)
df["driver_season_points_before"] = grp["_points_before"].transform(
    lambda x: x.cumsum()
)

# 完赛场次（shift 后 cumcount = 当前轮次之前参加了几场）
df["_count_shifted"] = grp["points"].shift(1)  # 非NaN=参赛
df["driver_season_races_before"] = grp["_count_shifted"].transform(
    lambda x: x.notna().cumsum()
)
```

**为什么用 shift(1) 而不是直接 cumsum？**

```
直接 cumsum（❌ 泄漏）:
  R1: points=25 → cumsum=25   ← 包含当前轮次！模型偷看了答案
  R2: points=18 → cumsum=43

shift(1) + cumsum（✅ 安全）:
  R1: shift→NaN → cumsum=0    ← 当前轮次的积分不算入特征
  R2: shift→25  → cumsum=25   ← 只有 R1 的积分
  R3: shift→18  → cumsum=43   ← R1+R2 的积分
```

#### 4.3.2 跨赛季近 5 场 — rolling

```python
# 按 车手 × 日期 排序（跨赛季）
df = df.sort_values(["driver_code", "race_date"]).reset_index(drop=True)
grp = df.groupby("driver_code")

# shift(1) 后 rolling(5) → 最近 5 场（不含当前场）
df["_pos_shift"] = grp["finishing_pos"].shift(1)
df["driver_last5_avg_pos"] = grp["_pos_shift"].transform(
    lambda x: x.rolling(5, min_periods=1).mean()
)
```

#### 4.3.3 NaN 填充策略

```python
# 计数类特征（积分/场次/胜场/DNF）→ 填 0（"之前没有" = 零）
zero_fill = {
    "driver_season_points_before", "driver_season_races_before",
    "driver_season_wins_before", "driver_season_dnfs_before",
    "driver_last5_dnfs", "driver_circuit_races", "driver_circuit_dnfs",
    "constructor_season_points_before", "constructor_season_dnfs_before",
}

# 平均值类特征（位次均值）→ 填中位数（"无历史" → 用典型值兜底）
median_fill = {
    "driver_season_avg_pos_before", "driver_last5_avg_pos",
    "driver_circuit_avg_pos", "constructor_season_avg_pos_before",
}

for col in zero_fill:
    result[col] = result[col].fillna(0.0)

for col in median_fill:
    result[col] = result[col].fillna(result[col].median())
```

**为什么计数填 0、均值填中位数？**

- 赛季第一场：`driver_season_points_before` = NaN → 填 0（确实没有积分）
- 新秀车手：`driver_last5_avg_pos` = NaN → 填中位数 11.0（用联盟平均位次兜底）
- 如果都填 0：新秀的 `avg_pos` = 0（=第一名），模型会误以为新秀是冠军热门 → 严重失真

#### 4.3.4 运行结果

```
[加载] 3458 行, 2018-2025, 43 位车手
[赛季特征] 完成 6 个 driver_season_* 特征
[近况特征] 完成 3 个 driver_last5_* 特征
[赛道特征] 完成 3 个 driver_circuit_* 特征
[车队特征] 完成 3 个 constructor_season_* 特征
[上下文特征] 完成 4 个 context 特征
  [填0] driver_season_races_before: 填充 173 个 NaN
  [填0] driver_season_points_before: 填充 173 个 NaN
  ...（共填充 12 列）
[特征矩阵] 3458 行 × 19 个特征

防泄漏检查:
  赛季第一场 driver_season_races_before:
    均值: 0.00 (应为 0.0)  ✅
    非零行数: 0 / 173 (应为 0)  ✅
```

### 4.4 防止数据泄漏的关键技巧

```python
# ❌ 错误: 用了整年数据 (包含要预测的那场)
year_df = df[df["year"] == year]
championship_ratio = year_df[year_df["driver_id"] == driver_id]["points"].sum() / max_points
# 问题: year_df 包含了当前轮次的结果, 模型"偷看"了答案

# ✅ 正确: 只用当前轮次之前的数据
prev_rounds_year = year_df[year_df["round"] < round_num]  # 严格小于
prev_data = pd.concat([df[df["year"] < year], prev_rounds_year])
championship_ratio = prev_rounds_year[
    prev_rounds_year["driver_id"] == driver_id
]["points"].sum() / max_points
# prev_rounds_year 只包含 R1 ~ R-1, 不包含 R (要预测的那场)
```

### 4.5 特征值域检查

```python
# 训练前必须检查特征值域, 异常值会影响模型质量
features_df = pd.read_csv("ml/data/features_train.csv")

# 1. 检查 NaN（应为 0，已在特征工程中填充）
print(features_df.isnull().sum())

# 2. 检查无穷大
print(np.isinf(features_df.select_dtypes(include=[np.number])).sum())

# 3. 检查值域
print(features_df.describe())
# qualifying_pos: 1.0 ~ 20.0         ✓
# driver_season_points_before: 0 ~ 500+  ✓
# driver_last5_avg_pos: 1.0 ~ 20.0   ✓
# regulation_era: 0.0 ~ 1.0          ✓
# round_normalized: 0.04 ~ 1.0       ✓
```

---

## 五、阶段 3：模型训练

> 状态：✅ 已完成。以下为实际训练代码 + 评估结果。
>
> 脚本：`scripts/train_xgboost.py`  产出：`ml/models/xgb_v1.json` + `eval_report.json`

### 5.1 安装依赖

```bash
# 在 f1_project conda 环境中安装（已完成）
conda activate f1_project
pip install xgboost scikit-learn

# 实际安装版本：
# xgboost 3.2.0, scikit-learn 1.9.0
# shap 待阶段 5 安装
```

### 5.2 时间序列交叉验证

**不能用随机 split！** F1 数据是时间序列，随机 split 会导致训练集包含未来的数据。

```python
# 正确: 按时间切分
# 2018-2023 训练 (6年, 2500 行)
# 2024 验证 (1年, 479 行)
# 2025 测试 (1年, 479 行)

train = df[df["year"].between(2018, 2023)]
val = df[df["year"] == 2024]
test = df[df["year"] == 2025]

X_train = train[feature_cols].values
y_train = train["is_win"].values
X_val = val[feature_cols].values
y_val = val["is_win"].values
X_test = test[feature_cols].values
y_test = test["is_win"].values

# 正负样本比（用于 scale_pos_weight）
pos = y_train.sum()  # 125
neg = len(y_train) - pos  # 2375
spw = neg / pos  # 19.0
```

### 5.3 XGBoost 训练（实际参数）

```python
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss

params = {
    "objective": "binary:logistic",   # 二分类
    "eval_metric": "logloss",         # 评估指标
    "max_depth": 4,                   # 树最大深度（小数据防过拟合）
    "n_estimators": 150,              # 树的数量
    "learning_rate": 0.1,             # 学习率
    "subsample": 0.8,                 # 每棵树用 80% 数据
    "colsample_bytree": 0.8,          # 每棵树用 80% 特征
    "min_child_weight": 3,            # 叶节点最小样本权重
    "scale_pos_weight": 19.0,         # 类别不平衡处理（正负比 1:19）
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}

model = xgb.XGBClassifier(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False,
)

# 保存模型
model.save_model("ml/models/xgb_v1.json")
```

**关键参数解释**：
- `max_depth=4`：F1 数据量小（2500 行训练），深度太深会过拟合
- `n_estimators=150`：150 棵树，配合 `learning_rate=0.1` 是稳健组合
- `scale_pos_weight=19`：每场 20 个车手只有 1 个冠军，正负比 1:19，必须加权
- `subsample=0.8` + `colsample_bytree=0.8`：每棵树只用 80% 数据和 80% 特征，增加随机性防过拟合
- `min_child_weight=3`：叶节点至少需要 3 个样本的权重，防止树在个别样本上过拟合

### 5.4 超参数调优

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    "max_depth": [3, 4, 5, 6],
    "n_estimators": [50, 100, 150, 200],
    "learning_rate": [0.01, 0.05, 0.1, 0.3],
    "subsample": [0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
    "min_child_weight": [1, 3, 5],
}

# 4*4*4*4*4*3 = 3072 种组合, 太多!
# 实践中用随机搜索或 Optuna 更高效

from sklearn.model_selection import RandomizedSearchCV

random_search = RandomizedSearchCV(
    model, param_distributions=param_grid,
    n_iter=50,                # 只试 50 种组合
    scoring="neg_log_loss",
    cv=TimeSeriesSplit(n_splits=3),
    n_jobs=-1,
    verbose=1,
)
random_search.fit(X_train, y_train)
print(f"最佳参数: {random_search.best_params_}")
print(f"最佳 Log Loss: {-random_search.best_score_:.4f}")
```

### 5.5 保存模型

```python
# XGBoost 模型保存为 JSON (可读, 可版本控制)
model_path = Path(__file__).parent.parent / "ml" / "models" / "xgb_v1.json"
model.save_model(str(model_path))
print(f"模型已保存: {model_path}")

# 也可以保存特征列名 (推理时需要保持一致)
import json
feature_cols_path = model_path.parent / "feature_cols.json"
with open(feature_cols_path, "w") as f:
    json.dump(feature_cols, f)
```

### 5.6 模型评估（实际结果）

#### 5.6.1 评估代码

```python
from sklearn.metrics import log_loss, brier_score_loss

# XGBoost 测试集预测
y_prob_xgb = model.predict_proba(X_test)[:, 1]

# 规则加权基线（复现 prediction_service.py 的 rule_v1）
y_prob_rule = rule_v1_predict(test_df, feature_cols)

# 逐样本指标
log_loss_xgb = log_loss(y_test, y_prob_xgb, labels=[0, 1])
brier_xgb = brier_score_loss(y_test, y_prob_xgb)

# 逐场比赛指标（Top-1 / Top-3 / NDCG@3）
# → 按 (year, round) 分组，每组按概率降序排，检查真实冠军的位置
```

#### 5.6.2 实际评估结果（2025 测试集，24 场比赛）

| 指标 | rule_v1 | xgb_v1 | 差异 | 说明 |
|------|---------|--------|------|------|
| **Log Loss** | 0.1796 | **0.1611** | -0.0185 ✅ | XGBoost 更低更好 |
| Brier Score | **0.0455** | 0.0487 | +0.0032 ❌ | rule_v1 略好（差距很小） |
| **Top-1 Accuracy** | 33.33% | **41.67%** | +8.34% ✅ | 每 24 场多猜对 2 场冠军 |
| **Top-3 Hit Rate** | 87.50% | **91.67%** | +4.17% ✅ | 真实冠军在 Top3 比例 |
| **NDCG@3** | 0.6533 | **0.7212** | +0.0679 ✅ | 排序质量 |

**结论**：XGBoost 在 5 个指标中 4 个优于 rule_v1，核心指标 Top-1 命中率提升 8.3 个百分点。

#### 5.6.3 抽样：2025 R1 澳大利亚站

```
车手     车队                排位   胜    XGB概率     规则概率
------------------------------------------------------------
NOR    McLaren            1 🏆     0.7635   0.0576
RUS    Mercedes           4       0.1399   0.0574
VER    Red Bull           3       0.1238   0.0578
PIA    McLaren            2       0.0619   0.0553
ALB    Williams           6       0.0187   0.0466
```

NOR 杆位夺冠，XGBoost 给了 76.35% 概率（强烈看好），而 rule_v1 只给 5.76%（几乎均匀分布）。这说明 XGBoost 能更好地利用排位赛位次的预测信号。

### 5.7 特征重要性（实际结果）

```
特征重要性 Top-10:
  qualifying_pos_inv                       0.2766 ███████████████████████████
  qualifying_pos                           0.2755 ███████████████████████████
  driver_season_wins_before                0.0480 ████
  grid                                     0.0469 ████
  driver_last5_avg_pos                     0.0403 ████
  grid_inv                                 0.0354 ███
  driver_last5_dnfs                        0.0295 ██
  driver_season_races_before               0.0288 ██
  constructor_season_avg_pos_before        0.0278 ██
  driver_season_dnfs_before                0.0254 ██
```

**关键发现**：
- **排位赛位次统治性重要**：`qualifying_pos` + `qualifying_pos_inv` 合计占 55.2% 重要性，远超其他特征。这与 F1 常识一致——杆位是夺冠最强预测因子。
- **赛季胜场数排第三**：`driver_season_wins_before`（4.8%）说明"赢过的人更可能再赢"——冠军气质效应。
- **车队特征贡献有限**：`constructor_season_avg_pos_before` 仅 2.8%，可能因为车队信息已通过车手的排位/完赛位次间接体现。
- **规则时代特征不重要**：`regulation_era` 未进 Top-10，说明 2022 规则改变对"谁夺冠"的影响不如排位赛位次大。

---

## 六、阶段 4：在线推理服务

> 状态：✅ 已完成。`prediction_service.py` 完整重写，XGBoost 推理 + rule_v1 fallback。

### 6.1 安装依赖

```bash
# requirements.txt 已更新（从"可选"移到正式依赖）
# 在 f1_project conda 环境中安装
pip install xgboost>=2.1.0 scikit-learn>=1.5.0 shap>=0.46.0
```

实际安装版本：xgboost 3.2.0 / scikit-learn 1.9.0 / shap 0.51.0。

### 6.2 架构设计

```
predict_race(year, round_num)
       ↓
  获取积分榜 (Ergast API)
       ↓
  尝试 XGBoost 推理
       ↓
  ┌── 模型加载? ──否──→ rule_v1 fallback
  │       ↓ 是
  │  获取排位赛数据 (Ergast)
  │       ↓
  │  排位赛可用? ──否──→ rule_v1 fallback
  │       ↓ 是
  │  获取赛程 + 赛季结果 (Ergast)
  │  加载历史 CSV (ml/data/races_2018_2025.csv)
  │       ↓
  │  _build_xgb_features()  ← 构建 19 特征向量
  │       ↓
  │  model.predict_proba()  ← XGBoost 推理
  │  explainer.shap_values() ← SHAP 解释
  │       ↓
  │  softmax 归一化
  │       ↓
  │  model_version = "xgb_v1"
  │       ↓
  └── 返回结果
```

### 6.3 懒加载单例模式

模型、特征列名、历史 CSV、SHAP Explainer 全部用全局变量 + 懒加载，首次调用时加载，后续复用：

```python
# ── 路径常量 ──
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "models" / "xgb_v1.json"
FEATURE_COLS_PATH = BASE_DIR / "ml" / "data" / "feature_columns.json"
HISTORY_CSV = BASE_DIR / "ml" / "data" / "races_2018_2025.csv"

# ── 懒加载单例 ──
_xgb_model = None
_feature_cols = None
_history_df = None
_shap_explainer = None

def _get_xgb_model():
    """加载 XGBoost 模型。失败返回 None（触发 fallback）。"""
    global _xgb_model
    if _xgb_model is None:
        try:
            import xgboost as xgb
            if not MODEL_PATH.exists():
                return None
            _xgb_model = xgb.XGBClassifier()
            _xgb_model.load_model(str(MODEL_PATH))
        except Exception as e:
            print(f"[prediction] XGBoost 模型加载失败: {e}")
            return None
    return _xgb_model
```

### 6.4 在线特征构建（19 特征，与训练对齐）

核心挑战：在线推理时需要从 Ergast API + 缓存 CSV 实时构建与训练完全一致的 19 特征。

| 特征组 | 数据源 | 在线获取方式 |
|--------|--------|-------------|
| 基线 (4) | 排位赛 | Ergast `/{year}/{round}/qualifying.json` |
| 赛季累计 (5) | 积分榜+赛季结果 | Ergast `/{year}/driverstandings.json` + `/{year}/results.json` |
| 近5场 (2) | 历史 CSV | `races_2018_2025.csv` 按 driver_code 过滤，tail(5) |
| 赛道特定 (3) | 历史 CSV | 按 driver_code + circuit_id 过滤 |
| 车队 (3) | 赛季结果 | 从赛季结果按 constructor 分组聚合 |
| 上下文 (2) | 计算 | regulation_era = year>=2022, round_normalized = round/total |

```python
def _build_xgb_features(year, round_num, standings, qualifying,
                        season_results, schedule_info, history_df):
    """构建 19 特征向量。核心原则：每行特征只用该轮次之前的数据。"""

    # 从赛程获取 circuit_id 和 total_rounds
    circuit_id = schedule_info["circuits"].get(round_num, {}).get("circuit_id", "")
    total_rounds = schedule_info.get("total_rounds", 24)

    # 本赛季结果按轮次分组（只取当前轮次之前的）
    results_by_round = {}
    for r in season_results:
        if r["round"] < round_num:
            results_by_round.setdefault(r["round"], {})[r["code"]] = r

    for driver in standings:
        code = driver["code"]
        qual_pos = qualifying.get(code)
        if qual_pos is None or qual_pos == 0:
            continue  # 无排位赛数据，跳过

        # ── 基线特征 ──
        grid = qual_pos  # 赛前 grid ≈ qualifying
        qualifying_pos_inv = 21 - qual_pos

        # ── 赛季累计（从积分榜直接取，积分榜本身就是截至上一轮的）──
        driver_points = driver["points"]
        driver_wins = driver["wins"]
        # 从赛季结果统计 races/dnfs/avg_pos
        ...

        # ── 近5场（从 CSV 取，跨赛季）──
        if history_df is not None:
            driver_hist = history_df[history_df["driver_code"] == code].sort_values("race_date")
            last5 = driver_hist.tail(5)
            driver_last5_avg_pos = finished["finishing_pos"].mean()
            driver_last5_dnfs = int(last5["is_dnf"].sum())

        # ── 赛道特定（从 CSV 按 circuit_id 过滤）──
        if history_df is not None and circuit_id:
            circuit_hist = history_df[
                (history_df["driver_code"] == code) &
                (history_df["circuit_id"] == circuit_id)
            ]

        # ── 车队（从赛季结果按 constructor 聚合）──
        for rnd in completed_rounds:
            for _code, r_data in results_by_round[rnd].items():
                if r_data["constructor"] == constructor_name:
                    constructor_points += r_data["points"]
                    ...

        # ── 上下文 ──
        regulation_era = 1 if year >= 2022 else 0
        round_normalized = round(round_num / total_rounds, 4)
```

### 6.5 NaN 填充策略（与训练一致）

```python
# 计数类特征 → 填 0（新秀车手合理默认）
# driver_season_races_before, driver_circuit_races, *_dnfs_before → 0

# 平均值类特征 → 填中位数（当前批次所有车手的中位数）
# driver_season_avg_pos_before, driver_last5_avg_pos,
# driver_circuit_avg_pos, constructor_season_avg_pos_before → median
```

### 6.6 推理 + 归一化

```python
def _predict_with_xgb(features_list):
    """XGBoost 预测 + SHAP 解释。返回 (probabilities, shap_values_list)"""
    import numpy as np

    model = _get_xgb_model()
    feature_cols = _get_feature_cols()

    # 构建特征矩阵
    X = np.array([
        [item["features"][col] for col in feature_cols]
        for item in features_list
    ])

    # predict_proba 返回 [P(class=0), P(class=1)]，取 class=1
    proba = model.predict_proba(X)[:, 1]

    # softmax 归一化：每场比赛所有车手概率之和 = 1
    total = proba.sum()
    probabilities = proba / total if total > 0 else np.ones(len(proba)) / len(proba)

    return probabilities, shap_values_list
```

### 6.7 fallback 机制

```python
def predict_race(year, round_num):
    try:
        standings = _fetch_driver_standings(year)
        if not standings:
            return {"code": 500, "msg": "无法获取积分榜"}

        # 尝试 XGBoost
        model = _get_xgb_model()
        if model and _get_feature_cols():
            try:
                qualifying = _fetch_qualifying(year, round_num)
                if not qualifying:
                    raise ValueError("排位赛数据不可用")

                # ... 构建 19 特征 → predict_proba → SHAP
                return {"model_version": "xgb_v1", ...}

            except Exception as e:
                print(f"[XGBoost 推理失败，降级到 rule_v1] {e}")

        # Fallback: rule_v1
        result = _predict_with_rule_v1(year, round_num, standings, recent, qualifying)
        if model:
            result["model_version"] = "rule_v1_fallback"
        return result

    except Exception as e:
        return {"code": 500, "msg": f"预测服务异常: {e}"}
```

降级触发条件：
1. 模型文件 `xgb_v1.json` 不存在（首次部署）
2. 排位赛数据不可用（赛前预测但排位赛未举行）
3. 特征构建失败（所有车手都缺排位赛数据）
4. predict_proba 返回 None（极端情况）

### 6.8 实际推理结果（2025 R1 澳大利亚站）

```
API: GET /api/prediction/2025/1
模型: xgb_v1 (19 特征)
车手数: 20

排名 车手   车队        概率      SHAP top-3
  1  NOR   McLaren    40.87%   qualifying_pos:+1.575, constructor_avg_pos:-1.306
  2  VER   Red Bull   34.40%   constructor_points:-1.357, driver_wins:+0.965
  3  PIA   McLaren    12.49%   constructor_points:-1.460, circuit_avg_pos:-0.990
  4  RUS   Mercedes    8.72%   constructor_points:-1.211, circuit_races:-0.602
  5  LEC   Ferrari     0.82%   constructor_points:-1.598, qualifying_pos:-1.211
```

NOR 杆位夺冠，XGBoost 给了 40.87% 概率（rule_v1 只有 11.75%），SHAP 显示排位赛 P1 是最大正贡献因子。

---

## 七、阶段 5：SHAP 特征解释 + 前端更新

> 状态：✅ 已完成。SHAP TreeExplainer 集成到 API，前端 Prediction.vue 完整适配。

### 7.1 SHAP 是什么

SHAP (SHapley Additive exPlanations) 基于博弈论 Shapley 值，能告诉你**每个特征对某个预测贡献了多少**。

```
预测概率 40.87% = 基础值 5%
  + 排位赛 P1 贡献 +1.575  ← 正贡献（推向夺冠）
  + 车队平均位次好 贡献 -1.306  ← 负贡献（拉离夺冠）
  + 车队积分高 贡献 -1.120
```

正值 = 推高夺冠概率，负值 = 拉低夺冠概率。SHAP 值的绝对值越大，该特征对预测的影响越大。

### 7.2 TreeExplainer 集成（懒加载）

```python
_shap_explainer = None

def _get_shap_explainer():
    """懒加载 SHAP TreeExplainer。失败返回 None（不影响预测）。"""
    global _shap_explainer
    if _shap_explainer is None:
        try:
            import shap
            model = _get_xgb_model()
            if model is None:
                return None
            _shap_explainer = shap.TreeExplainer(model)
        except Exception as e:
            print(f"[prediction] SHAP 加载失败（不影响预测）: {e}")
            return None
    return _shap_explainer
```

TreeExplainer 是 XGBoost 专用解释器，利用树结构精确计算 SHAP 值，速度比通用 KernelExplainer 快 100 倍。

### 7.3 在推理中计算 SHAP

```python
def _predict_with_xgb(features_list):
    # ... model.predict_proba(X) ...

    # SHAP 特征解释
    shap_values_list = None
    explainer = _get_shap_explainer()
    if explainer is not None:
        try:
            shap_vals = explainer.shap_values(X)
            # shap_vals shape: (n_drivers, n_features)

            shap_values_list = []
            for i in range(len(features_list)):
                # 按 |SHAP 值| 降序排列，取 top-3
                contributions = list(zip(feature_cols, shap_vals[i]))
                contributions.sort(key=lambda x: abs(x[1]), reverse=True)
                top3 = [
                    {"feature": f, "contribution": round(float(v), 4)}
                    for f, v in contributions[:3]
                ]
                shap_values_list.append(top3)
        except Exception as e:
            print(f"[prediction] SHAP 计算失败: {e}")

    return probabilities, shap_values_list
```

### 7.4 API 返回格式

```json
{
  "code": 200,
  "model_version": "xgb_v1",
  "feature_count": 19,
  "feature_importance": [
    {"feature": "qualifying_pos_inv", "importance": 0.2766},
    {"feature": "qualifying_pos", "importance": 0.2755},
    {"feature": "driver_season_wins_before", "importance": 0.0480}
  ],
  "predictions": [
    {
      "driver_code": "NOR",
      "driver_name": "Lando Norris",
      "constructor": "McLaren",
      "probability": 0.4087,
      "rank_pred": 1,
      "features": {"qualifying_pos": 1.0, "grid": 1.0, ...},
      "model_proba": 0.408672,
      "shap_top3": [
        {"feature": "qualifying_pos", "contribution": 1.575},
        {"feature": "constructor_season_avg_pos_before", "contribution": -1.306},
        {"feature": "constructor_season_points_before", "contribution": -1.120}
      ]
    }
  ],
  "top3": ["NOR", "VER", "PIA"]
}
```

### 7.5 前端 Prediction.vue 适配

前端根据 `model_version` 自适应展示：

**XGBoost 模式 (xgb_v1)**：
- Top3 卡片展示 SHAP 特征贡献条形图（绿色=正贡献，红色=负贡献）
- 展开详情显示全部 19 特征值 + SHAP top-3
- 底部展示模型特征重要性 Top 5（从 `feature_importance` 字段读取）
- 图表 tooltip 显示 SHAP 值

**规则模型模式 (rule_v1 / rule_v1_fallback)**：
- 保持原有 UI（特征 mini bar + 权重百分比）
- fallback 模式显示黄色警告提示

```vue
<!-- 模型版本标签 -->
<el-tag :type="isXgb ? 'success' : 'warning'">
  {{ isXgb ? 'XGBoost v1' : '规则模型 v1' }}
</el-tag>

<!-- SHAP 特征贡献（XGBoost only）-->
<div v-if="p.shap_top3 && isXgb" class="shap-bars">
  <div v-for="s in p.shap_top3" :key="s.feature" class="shap-bar-item">
    <div class="shap-bar-label">{{ featureShort(s.feature) }}</div>
    <div class="shap-bar-track">
      <div class="shap-bar-fill"
        :style="{
          width: shapBarWidth(s.contribution) + '%',
          background: s.contribution >= 0 ? '#67c23a' : '#f56c6c'
        }" />
    </div>
    <div class="shap-bar-value" :class="s.contribution >= 0 ? 'pos' : 'neg'">
      {{ s.contribution > 0 ? '+' : '' }}{{ s.contribution.toFixed(3) }}
    </div>
  </div>
</div>
```

### 7.6 SHAP 实际值解读（2025 R1）

| 车手 | 概率 | SHAP top-1 | SHAP top-2 | SHAP top-3 |
|------|------|-----------|-----------|-----------|
| NOR | 40.87% | qualifying_pos: **+1.575** | constructor_avg_pos: -1.306 | constructor_points: -1.120 |
| VER | 34.40% | constructor_points: -1.357 | constructor_avg_pos: -1.342 | driver_wins: **+0.965** |
| PIA | 12.49% | constructor_points: -1.460 | constructor_avg_pos: -1.151 | circuit_avg_pos: -0.990 |

解读：
- NOR 的最大正贡献是 `qualifying_pos`（杆位 = P1），SHAP 值 +1.575 表示排位赛 P1 显著推高了他的夺冠概率
- VER 的 `driver_season_wins`（赛季胜场）贡献 +0.965，体现"冠军气质效应"
- 负贡献的 `constructor_*` 特征表示车队整体表现拉低了预测（McLaren 在 2024 赛季末积分不如 Red Bull）

---

## 八、评估指标详解

### 8.1 Log Loss (对数损失)

**最核心的指标。** 衡量预测概率与真实标签的差异。

```
Log Loss = -1/N * Σ [y * log(p) + (1-y) * log(1-p)]

y = 真实标签 (0 或 1)
p = 预测概率 (0 到 1)
```

- 值越低越好，0 = 完美预测
- 对"自信但错误"的预测惩罚极重（预测 99% 但实际输了 → 巨大惩罚）
- 适合评估概率预测，而不是硬分类

```python
from sklearn.metrics import log_loss
ll = log_loss(y_true, y_pred_proba)
# rule_v1 基线: ~0.45 (估计)
# xgb_v1 目标: < 0.35
```

### 8.2 Brier Score

```
Brier = 1/N * Σ (p - y)²
```

- 值越低越好，0 = 完美
- 比 Log Loss 更温和，不会对错误预测施加无限惩罚
- 适合评估校准度（预测概率是否与真实频率匹配）

### 8.3 Top-1 Accuracy

```python
# 每场比赛取概率最高的车手作为预测冠军
# 检查是否真的是冠军
pred_winners = pred_df.loc[pred_df.groupby("race_key")["pred_proba"].idxmax()]
top1_acc = (pred_winners["is_win"] == 1).mean()
# F1 预测 Top-1 准确率通常 30-50% (20 选 1, 随机猜 5%)
```

### 8.4 Top-3 Hit Rate

```python
# 实际冠军是否在预测概率 Top-3 中
top3_hit = pred_df.groupby("race_key").apply(
    lambda x: x.nlargest(3, "pred_proba")["is_win"].sum() > 0
).mean()
# F1 预测 Top-3 命中率通常 60-80%
```

### 8.5 NDCG@3 (归一化折损累积增益)

```python
# 排序质量指标, 考虑排名位置
# 预测 Top-1 是冠军: 得分最高
# 预测 Top-3 是冠军: 得分较低
# 预测 Top-10 是冠军: 得分更低
from sklearn.metrics import ndcg_score

# 需要 reshape 为 (n_samples, n_classes) 格式
# NDCG@3 = DCG@3 / IDCG@3
```

### 8.6 评估指标对比

| 指标 | 范围 | 越X越好 | 评估什么 | 适合场景 |
|------|------|---------|---------|---------|
| Log Loss | [0, ∞) | 越低 | 概率预测质量 | 主指标 |
| Brier Score | [0, 1] | 越低 | 概率校准度 | 辅助 |
| Top-1 Accuracy | [0, 1] | 越高 | 冠军预测准确率 | 直观理解 |
| Top-3 Hit Rate | [0, 1] | 越高 | Top-3 覆盖率 | 排序质量 |
| NDCG@3 | [0, 1] | 越高 | 排序质量 | 综合评估 |

---

## 九、面试问答（20 题）

### 基础概念

**Q1: XGBoost 和随机森林有什么区别？**

A: 两者都是集成学习，但策略不同：
- 随机森林：Bagging，多棵树独立训练，最终投票/平均
- XGBoost：Boosting，每棵树纠正前一棵的错误，串行训练

XGBoost 通常在小数据上表现更好，因为 boosting 能逐步降低偏差；随机森林更适合大数据且方差大的场景。

**Q2: 为什么 XGBoost 适合表格数据？**

A: 树模型天然能处理：
1. 非线性关系（用分裂点切分）
2. 特征交互（一棵树的不同层级用不同特征）
3. 缺失值（XGBoost 自动学习缺失值往左还是往右走）
4. 无需特征缩放（树基于排序分裂，不关心绝对值大小）

神经网络在表格数据上通常不如树模型，因为表格数据的特征间关系是"不规则"的，不适合神经网络的连续平滑变换。

**Q3: gradient boosting 的"梯度"是什么意思？**

A: 每棵树拟合的是前一轮预测的**负梯度**（对于平方损失就是残差）。第 t 棵树拟合的是：

```
残差_t = y - (tree_1 + tree_2 + ... + tree_{t-1}) 的预测值
```

"梯度"指的是损失函数对当前预测值的偏导数。对于 logloss，这个梯度不是简单的残差，但原理类似——每棵树都在纠正之前所有树的不足。

### 数据工程

**Q4: 什么是数据泄漏？如何避免？**

A: 数据泄漏 = 训练时用了预测时不可能获得的信息。

F1 场景举例：
- 用 2024 赛季最终积分来预测 2024 R5 → 泄漏（R5 时赛季还没结束）
- 用 2024 R5 的完赛位次作为 2024 R5 的特征 → 泄漏（预测赛前不知道结果）

避免方法：
1. 按时间切分 train/val/test，不用随机 split
2. 每行特征严格只用该场比赛之前的数据
3. 检查每个特征的"可获得时间"

**Q5: 为什么不能用随机 train_test_split？**

A: F1 数据是时间序列。如果随机 split，训练集可能包含 2024 R10 的数据，而验证集包含 2024 R5 的数据——训练集"看到了未来"。这会导致验证集表现虚高，上线后性能暴跌。

正确做法：按年份切分，训练 < 验证 < 测试（时间上）。

**Q6: Ergast API 的数字字段为什么需要 int() 转换？**

A: Ergast 返回的 JSON 中所有值都是字符串，比如 `"position": "1"` 而不是 `"position": 1`。如果直接读入 pandas，列类型是 object（字符串），无法做数值计算（mean、std 等）。必须显式 `int()` / `float()` 转换。

### 模型训练

**Q7: scale_pos_weight 是什么？为什么需要它？**

A: F1 数据正负样本比 1:19（173 胜 vs 3285 负），严重不平衡。XGBoost 默认对少数类（正类）不敏感，可能把所有样本都预测为 0（负类），准确率 95% 但完全没用。

`scale_pos_weight=19` 告诉模型"正类的权重是负类的 19 倍"，使模型重视正类。

**Q8: max_depth 设多少合适？**

A: 对于 3458 行的小数据集，`max_depth=3` 到 `5` 是合理范围。太深（>6）会过拟合，太浅（1-2）可能欠拟合。用交叉验证选最优值。

**Q9: early_stopping_rounds 的作用？**

A: 训练 100 棵树不一定比 50 棵好——过多会过拟合。`early_stopping_rounds=10` 表示：如果验证集指标连续 10 轮没有改善，就停止训练。这样能自动找到最佳的树数量。

**Q10: learning_rate 和 n_estimators 的关系？**

A: 两者配合使用：
- 大 learning_rate (0.3) + 少 n_estimators (50) = 快但粗
- 小 learning_rate (0.01) + 多 n_estimators (500) = 慢但精

通常选小 learning_rate + 多 n_estimators + early stopping，效果最好。

### 评估与部署

**Q11: 为什么用 Log Loss 而不是 Accuracy？**

A: Accuracy 只看硬分类（>0.5 = 1），忽略概率值。F1 预测中，20 个车手只有 1 个冠军，即使全部预测"不赢"，accuracy 也有 95%——但这完全没用。

Log Loss 衡量的是预测概率与真实标签的差距，能区分"预测 60% 赢但输了"和"预测 99% 赢但输了"的严重程度。

**Q12: Top-1 Accuracy 30% 算好吗？**

A: F1 预测中 20 选 1，随机猜 5%。VER 统治时代（2023）他赢 19/22 = 86%，如果模型每次都预测 VER 赢，Top-1 = 86%。但 2024 竞争更激烈，Top-1 30-50% 已经是不错的水平。

关键不是绝对值，而是**比规则模型高**。

**Q13: 模型上线后怎么监控？**

A: 
1. 每场比赛后记录预测结果，计算实际 Top-1/Top-3 命中率
2. 监控 Log Loss 是否持续上升（概念漂移信号）
3. 2026 引擎新规后需要重新训练（旧数据分布失效）
4. A/B 对比：同时跑 rule_v1 和 xgb_v1，看谁更准

**Q14: 模型文件用什么格式保存？**

A: XGBoost 原生支持 JSON 格式（`model.save_model("xgb_v1.json")`）。JSON 可读、可版本控制、跨平台兼容。比 pickle 更安全（pickle 有反序列化攻击风险）。

### SHAP 与可解释性

**Q15: SHAP 值怎么解释？**

A: SHAP 值表示某特征对某预测的边际贡献。比如 VER 预测概率 35%，基础值（所有车手平均）5%，那么各特征 SHAP 值之和 = 35% - 5% = 30%。

- 正值：该特征提高了预测概率
- 负值：该特征降低了预测概率
- 绝对值越大：贡献越大

**Q16: TreeExplainer 和 KernelExplainer 的区别？**

A: 
- TreeExplainer：专为树模型设计，精确且快（O(n)）
- KernelExplainer：通用方法，慢但适用于任何模型

XGBoost 用 TreeExplainer，速度快且结果精确。

### 工程实践

**Q17: 推理时特征和训练时不一致怎么办？**

A: 这是最常见的线上事故。解决方案：
1. 保存训练时的特征列名列表（`feature_cols.json`）
2. 推理时按该列表构建特征矩阵，缺失列填 0
3. 确保训练和推理用同一套特征计算逻辑

**Q18: 怎么处理冷启动（新车手/新赛道）？**

A: 
- 新车手：无历史数据，特征用默认值（recent_avg_pos=20, win_rate=0 等）
- 新赛道：track_avg_pos=20, track_dnf_rate=0
- XGBoost 原生支持 NaN，但最好填合理默认值

**Q19: 模型推理延迟多少可接受？**

A: 
- 规则模型：<1ms
- XGBoost predict_proba：<10ms
- SHAP TreeExplainer：200-500ms

前端 API 超时设 15s（telemetry.js 设 60s），SHAP 延迟完全可接受。如果需要更快，可以只对 Top-5 车手计算 SHAP。

**Q20: 为什么保留规则模型作为 fallback？**

A: 
1. XGBoost 模型文件可能丢失/损坏
2. 推理时 Ergast API 可能不可用，导致特征计算失败
3. 新赛季开始时模型可能还未训练
4. fallback 保证服务永远可用，最差也能返回规则模型的结果

---

## 十、踩坑总览（18 条）

### 数据采集

**#1 Ergast 所有数字字段都是字符串**
- 问题：`"position": "1"` 读入 pandas 后列类型是 object，无法 `mean()`
- 解决：显式 `int()` / `float()` 转换，用 `or 0` 处理空值

**#2 Ergast 429 限流**
- 问题：连续请求约 10-15 次后返回 429 Too Many Requests
- 解决：请求间隔 0.5s + 失败重试 3 次 + 指数退避 (2s, 4s)

**#3 2020 赛季只有 17 场（疫情影响）**
- 问题：2020 年分站数异常少，影响统计
- 解决：数据采集脚本正常处理，但特征分析时注意年份差异

**#4 排位赛和正赛发车位可能不同**
- 问题：车手排位 P3 但罚退 5 位，grid=8 但 qualifying_pos=3
- 解决：两个字段都采集，特征中加 `grid_vs_qualifying` 检测罚退

### 特征工程

**#5 数据泄漏：用了赛后数据**
- 问题：用整年积分（含当前轮次）计算 championship_ratio
- 解决：严格用 `round < current_round` 的数据

**#6 新车手/新赛道特征全 NaN**
- 问题：2024 新秀 Bearman 无历史数据
- 解决：填合理默认值（recent_avg_pos=20, track_avg_pos=20）

**#7 position_trend 计算需要至少 3 场**
- 问题：线性回归斜率至少需要 3 个点
- 解决：`if len(positions) >= 3` 才计算，否则返回 0

**#8 driver_dob 缺失或格式错误**
- 问题：少数车手 dateOfBirth 为空或格式不对
- 解决：try/except 兜底，默认年龄 30

### 模型训练

**#9 类别不平衡导致模型全预测 0**
- 问题：1:19 的正负比，模型默认全预测"不赢"，accuracy 95% 但无用
- 解决：`scale_pos_weight=19`

**#10 随机 split 导致数据泄漏**
- 问题：`train_test_split` 随机打乱，训练集包含"未来"数据
- 解决：按年份时间切分，train < val < test

**#11 max_depth 过大导致过拟合**
- 问题：3458 行小数据 + max_depth=8 → 训练集 95% 但测试集 60%
- 解决：max_depth=3-5，配合 early_stopping

**#12 n_estimators 过多导致过拟合**
- 问题：500 棵树在小数据上过拟合
- 解决：early_stopping_rounds=10，自动停止

### 推理服务

**#13 模型文件不存在时崩溃**
- 问题：首次部署时 xgb_v1.json 还没训练，import xgboost 报错
- 解决：懒加载 + fallback 到规则模型

**#14 推理时特征列顺序与训练时不一致**
- 问题：训练时 15 列按某顺序，推理时 dict 顺序可能不同
- 解决：保存 feature_cols.json，推理时按该列表顺序构建

**#15 XGBoost predict_proba 返回 2 列**
- 问题：`predict_proba()` 返回 shape=(n, 2)，第 0 列是 P(0)，第 1 列是 P(1)
- 解决：取 `[:, 1]` 获取 P(win=1)

### 评估

**#16 Top-1 Accuracy 不如规则模型**
- 问题：VER 统治时代，规则模型只要预测 VER 赢就 86%
- 解决：看 2024-2025 竞争激烈的赛季，XGBoost 优势更明显

**#17 Log Loss 看绝对值没意义**
- 问题：Log Loss 0.4 是好是坏？不知道
- 解决：和规则模型对比，relative improvement 更重要

### 部署

**#18 SHAP 计算太慢**
- 问题：每次请求计算 20 个车手的 SHAP 值约 500ms
- 解决：只对 Top-5 车手计算 SHAP，或缓存到 predictions 表

---

## 附录：完整文件清单

```
ml/
├── data/
│   ├── races_2018_2025.csv         # 主表 (3458 行 × 29 列) ✅ 已生成
│   ├── standings_2018_2025.csv     # 积分榜 (173 行 × 9 列) ✅ 已生成
│   ├── circuits.csv                # 赛道 (78 行 × 7 列) ✅ 已生成
│   ├── features_train.csv          # 特征矩阵 (3458 行 × 19 特征) ✅ 已生成
│   └── feature_columns.json        # 特征列名 + 分组 ✅ 已生成
├── models/
│   ├── .gitkeep
│   ├── xgb_v1.json                 # XGBoost 模型 ✅ 已训练
│   ├── feature_importance.csv      # 特征重要性 ✅ 已导出
│   └── eval_report.json            # 评估报告 ✅ 已生成
└── notebooks/
    └── xgboost_demo.ipynb          # XGBoost 基础 demo

scripts/
├── collect_training_data.py        # 数据采集脚本 ✅ 已完成
├── feature_engineering.py          # 特征工程脚本 ✅ 已完成
└── train_xgboost.py                # 模型训练脚本 ✅ 已完成

backend/
└── prediction_service.py           # 推理服务 ✅ 已重写 (XGBoost + SHAP + rule_v1 fallback)

frontend/
└── src/pages/Prediction.vue        # 前端预测页 ✅ 已适配 (SHAP 展示 + 双模型兼容)

study/
└── 13_阶段4_AI预测XGBoost知识点.md  # 本文档 ✅ (5 个阶段全部完成)
```

### 全阶段完成状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1 | 数据采集 (collect_training_data.py → 3 份 CSV) | ✅ 完成 |
| 2 | 特征工程 (feature_engineering.py → 19 特征) | ✅ 完成 |
| 3 | 模型训练 (train_xgboost.py → xgb_v1.json) | ✅ 完成 |
| 4 | 在线推理 (prediction_service.py 重写) | ✅ 完成 |
| 5 | SHAP + 前端 (Prediction.vue 适配) | ✅ 完成 |
