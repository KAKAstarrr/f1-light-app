# -*- coding: utf-8 -*-
"""
game_service.py — Fantasy 积分结算服务

职责：
    Fantasy 阵容积分计算、芯片效果、动态定价。
    纯 Python 计算逻辑，不涉及 IO，是积分规则的唯一真相源。

积分规则（来自 PRD 3.3.1）：
    车手完赛 Top 10：+10/8/6/5/4/3/2/1/0/0
    车手排位 Top 3：  +3/+2/+1
    车手 DNF：        -5
    车队完赛 Top 5：  +5/4/3/2/1
    最快圈：          +5
    位置提升：        +1 × 提升位次
    队长 x2：         车手积分 ×2

动态定价算法（来自 PRD 3.3.3）：
    driver_price = base_price × (0.5 + 0.5 × season_points_ratio)
      + trend_bonus - penalty
    base_price: Top3=30M, Top5=25M, Top10=20M, 其余=15M, 新秀=10M
"""

# ============================================================
# 完赛积分
# ============================================================
FINISH_POINTS = {1: 10, 2: 8, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1, 9: 0, 10: 0}

# 排位赛积分
QUALIFYING_POINTS = {1: 3, 2: 2, 3: 1}

# 车队完赛积分（取车队最好的名次）
CONSTRUCTOR_FINISH_POINTS = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}

# 最快圈加分
FASTEST_LAP_BONUS = 5

# DNF 扣分
DNF_PENALTY = -5

# 预算上限
BUDGET_LIMIT = 100.0
MAX_DRIVERS = 5
MAX_CONSTRUCTORS = 2


def calculate_driver_points(
    driver_code: str,
    finish_position: int,
    qualifying_position: int,
    is_fastest_lap: bool,
    status: str,
    is_captain: bool = False,
    chip: str = "none"
) -> dict:
    """计算单个车手的 Fantasy 积分。

    参数：
        driver_code: 车手三字母代码 "VER"
        finish_position: 完赛名次（1=冠军），DNF 传 0 或 >20
        qualifying_position: 排位名次
        is_fastest_lap: 是否全场最快圈
        status: 完赛状态 "Finished" / "+1 Lap" / "Retired" 等
        is_captain: 是否队长（x2 Boost）
        chip: 使用的芯片

    返回：
        {
            "code": "VER",
            "finish_points": 10,
            "qualifying_points": 3,
            "fastest_lap_bonus": 5,
            "position_gain": 2,
            "dnf_penalty": 0,
            "subtotal": 20,
            "captain_bonus": 20,
            "total": 40,
            "breakdown": "..."
        }
    """
    is_dnf = "Retired" in status or "Not Classified" in status or finish_position == 0

    # 1. 完赛积分
    finish_pts = FINISH_POINTS.get(finish_position, 0) if not is_dnf else 0

    # 2. 排位积分
    qual_pts = QUALIFYING_POINTS.get(qualifying_position, 0)

    # 3. 最快圈
    fastest_bonus = FASTEST_LAP_BONUS if is_fastest_lap else 0

    # 4. 位置提升（排位 → 正赛，每提升1位 +1）
    position_gain = 0
    if not is_dnf and qualifying_position and finish_position:
        gain = qualifying_position - finish_position
        if gain > 0:
            position_gain = gain  # 正数才加分

    # 5. DNF 扣分
    dnf_penalty = 0
    if is_dnf:
        if chip == "no_negative":
            dnf_penalty = 0  # 芯片抵消
        else:
            dnf_penalty = DNF_PENALTY

    # 汇总
    subtotal = finish_pts + qual_pts + fastest_bonus + position_gain + dnf_penalty

    # 队长加倍
    captain_bonus = subtotal if is_captain else 0
    total = subtotal + captain_bonus

    breakdown_parts = [
        f"完赛 {finish_pts}",
        f"排位 {qual_pts}" if qual_pts else None,
        f"最快圈 +{fastest_bonus}" if fastest_bonus else None,
        f"位置提升 +{position_gain}" if position_gain else None,
        f"DNF {dnf_penalty}" if dnf_penalty else None,
        f"队长加倍 +{captain_bonus}" if captain_bonus else None,
    ]
    breakdown = " | ".join(p for p in breakdown_parts if p)

    return {
        "code": driver_code,
        "finish_points": finish_pts,
        "qualifying_points": qual_pts,
        "fastest_lap_bonus": fastest_bonus,
        "position_gain": position_gain,
        "dnf_penalty": dnf_penalty,
        "subtotal": subtotal,
        "captain_bonus": captain_bonus,
        "total": total,
        "breakdown": breakdown,
    }


def calculate_constructor_points(
    constructor_ref: str,
    best_finish_position: int,
    is_fastest_lap_by_team: bool = False
) -> dict:
    """计算车队的 Fantasy 积分（取车队最好的完赛名次）。"""
    finish_pts = CONSTRUCTOR_FINISH_POINTS.get(best_finish_position, 0)
    return {
        "ref": constructor_ref,
        "finish_points": finish_pts,
        "total": finish_pts,
    }


def calculate_team_points(
    team_drivers: list[dict],
    team_constructors: list[dict],
    race_results: list[dict],
    fastest_lap_driver: str,
    chip: str = "none"
) -> dict:
    """计算 Fantasy 阵容总分。

    参数：
        team_drivers: [{code, is_captain, price}, ...]
        team_constructors: [{ref, price}, ...]
        race_results: Ergast 结果列表 [{Driver:{code}, Constructor:{constructorId}, position, grid, status, ...}]
        fastest_lap_driver: 全场最快圈车手代码
        chip: 使用的芯片

    返回：
        {
            "total_points": 42,
            "driver_details": [...],
            "constructor_details": [...],
            "bonuses": {...},
            "penalties": {...},
        }
    """
    # 构建车手名次映射
    driver_map = {}
    for r in race_results:
        code = r.get("Driver", {}).get("code", "")
        if code:
            driver_map[code] = r

    # 构建车队名次映射（取车队最好的名次）
    constructor_map = {}
    for r in race_results:
        cref = r.get("Constructor", {}).get("constructorId", "")
        pos = int(r.get("position", 999))
        if cref and (cref not in constructor_map or pos < constructor_map[cref]):
            constructor_map[cref] = pos

    # 计算每个车手
    driver_details = []
    for pick in team_drivers:
        code = pick["driver_code"]
        race_data = driver_map.get(code, {})
        finish_pos = int(race_data.get("position", 0))
        grid_pos = int(race_data.get("grid", 0))
        status = race_data.get("status", "Retired")
        is_fastest = code == fastest_lap_driver

        detail = calculate_driver_points(
            driver_code=code,
            finish_position=finish_pos,
            qualifying_position=grid_pos,
            is_fastest_lap=is_fastest,
            status=status,
            is_captain=pick.get("is_captain", False),
            chip=chip
        )
        driver_details.append(detail)

    # 计算每个车队
    constructor_details = []
    for pick in team_constructors:
        ref = pick["constructor_ref"]
        best_pos = constructor_map.get(ref, 0)
        detail = calculate_constructor_points(ref, best_pos)
        constructor_details.append(detail)

    total = sum(d["total"] for d in driver_details) + sum(c["total"] for c in constructor_details)

    return {
        "total_points": total,
        "driver_details": driver_details,
        "constructor_details": constructor_details,
    }


def validate_team_budget(
    drivers: list[dict],
    constructors: list[dict],
    chip: str = "none"
) -> tuple[bool, float, str]:
    """校验阵容预算是否超标。

    返回：(是否合法, 总花费, 错误信息)
    """
    if len(drivers) > MAX_DRIVERS:
        return False, 0, f"车手数量超出限制（最多{MAX_DRIVERS}个）"
    if len(constructors) > MAX_CONSTRUCTORS:
        return False, 0, f"车队数量超出限制（最多{MAX_CONSTRUCTORS}个）"

    total = sum(d["price"] for d in drivers) + sum(c["price"] for c in constructors)

    if chip == "limitless":
        return True, total, "Limitless 芯片：无预算限制"

    if total > BUDGET_LIMIT:
        return False, total, f"预算超标：¥{total:.1f}M > ¥{BUDGET_LIMIT}M"

    return True, total, ""


def calculate_driver_price(
    season_points: float = 0,
    max_season_points: float = 600,
    recent_avg_position: float = 10,
    dnf_count: int = 0,
    last_season_rank: int = 0,
) -> float:
    """动态定价算法。

    base_price: 上赛季排名决定基础价
    season_points_ratio: 当前赛季积分占比
    trend_bonus: 近期表现趋势
    penalty: DNF 惩罚

    返回价格（M，百万）。
    """
    # 基础价
    if last_season_rank <= 3:
        base = 30
    elif last_season_rank <= 5:
        base = 25
    elif last_season_rank <= 10:
        base = 20
    elif last_season_rank > 0:
        base = 15
    else:
        base = 10  # 新秀

    # 赛季积分占比
    ratio = min(1.0, season_points / max(max_season_points, 1))

    # 趋势加成：近期平均名次越低（越好）价格越高
    trend = max(0, (15 - recent_avg_position)) * 0.5  # 每提升1位 +0.5M

    # DNF 惩罚：每次 -2M，最多 -10M
    penalty = min(dnf_count * 2, 10)

    price = base * (0.5 + 0.5 * ratio) + trend - penalty
    return round(max(5.0, price), 1)  # 最低 5M
