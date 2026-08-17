# -*- coding: utf-8 -*-
"""
collect_training_data.py -- F1 历史数据采集脚本（XGBoost 训练用）

职责:
    遍历 2018-2025 赛季, 从 Ergast API 采集每场比赛的:
    - 排位赛结果 (grid position)
    - 正赛结果 (finishing position, points, laps, status)
    - 赛季末车手积分榜 (championship position, points, wins)
    - 赛道元数据 (circuit name, locality, country, lat, long)

    输出三份 CSV:
    - ml/data/races_2018_2025.csv   -- 每行 = 一个车手在一场比赛的结果 (主表)
    - ml/data/standings_2018_2025.csv -- 每行 = 一个车手的赛季末积分榜
    - ml/data/circuits.csv           -- 每行 = 一条赛道的元数据

设计原则:
    1. 复用 cache/ergast_cache/ 缓存目录, 历史数据 7 天 TTL (永不变)
    2. 每次请求间隔 0.5s, 避免触发 Ergast 镜像限流
    3. 网络失败自动重试 3 次, 跳过无法获取的分站并记录日志
    4. 输出 CSV 编码 utf-8-sig (Excel 可直接打开)

用法:
    cd C:\\Users\\陈词年\\PycharmProjects\\f1_light_app
    python scripts/collect_training_data.py

    可选参数:
    --start-year 2018   起始年份 (默认 2018)
    --end-year 2025     结束年份 (默认 2025)
    --force             忽略缓存, 强制重新拉取
"""
import os
import sys
import json
import time
import argparse
import datetime as _dt
from pathlib import Path

import requests
import pandas as pd

# ============================================================
# 配置
# ============================================================
ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "ergast_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "ml" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 历史赛季数据永不变, 缓存 7 天
HISTORICAL_TTL = 7 * 24 * 3600

# 请求间隔 (秒), 避免限流
REQUEST_DELAY = 0.5

# 重试次数
MAX_RETRIES = 3


# ============================================================
# Ergast 请求 + 缓存
# ============================================================
def _cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"{cache_key}.json"


def _is_cache_valid(cache_key: str, ttl: int = HISTORICAL_TTL) -> bool:
    fp = _cache_path(cache_key)
    if not fp.exists():
        return False
    age = time.time() - fp.stat().st_mtime
    return age < ttl


def _load_cache(cache_key: str):
    fp = _cache_path(cache_key)
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(cache_key: str, data):
    fp = _cache_path(cache_key)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ergast_get(endpoint: str, cache_key: str, force: bool = False) -> dict:
    """带缓存的 Ergast GET 请求.

    Args:
        endpoint: Ergast API 路径, 如 "2025/1/results.json"
        cache_key: 缓存文件名 (不含 .json)
        force: True 则忽略缓存强制重新拉取

    Returns:
        Ergast MRData 响应的指定 table 数据, 失败返回空 dict/list.
    """
    if not force and _is_cache_valid(cache_key):
        return _load_cache(cache_key)

    url = f"{ERGAST_BASE}/{endpoint}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            raw = resp.json()
            mr_data = raw.get("MRData", {})

            # 根据端点提取 table 数据
            if "RaceTable" in mr_data:
                data = mr_data["RaceTable"]
            elif "StandingsTable" in mr_data:
                data = mr_data["StandingsTable"]
            elif "DriverTable" in mr_data:
                data = mr_data["DriverTable"]
            elif "ConstructorTable" in mr_data:
                data = mr_data["ConstructorTable"]
            elif "CircuitTable" in mr_data:
                data = mr_data["CircuitTable"]
            else:
                data = mr_data

            _save_cache(cache_key, data)
            time.sleep(REQUEST_DELAY)
            return data
        except requests.exceptions.RequestException as e:
            print(f"  [重试 {attempt}/{MAX_RETRIES}] {endpoint}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
            else:
                print(f"  [放弃] {endpoint} 请求失败, 跳过")
                return {}


# ============================================================
# 数据采集函数
# ============================================================
def fetch_season_schedule(year: int, force: bool = False) -> list:
    """获取某赛季的完整赛程.

    Returns:
        [{season, round, raceName, date, circuit: {circuitId, circuitName,
         Location: {locality, country, lat, long}}, ...}]
    """
    data = ergast_get(f"{year}.json", f"season_{year}", force=force)
    races = data.get("Races", [])
    print(f"  {year} 赛季: {len(races)} 场分站")
    return races


def fetch_race_results(year: int, round_num: int, force: bool = False) -> list:
    """获取某场正赛结果.

    Returns:
        [{number, position, positionText, points, driver: {...},
         constructor: {...}, grid, laps, status, Time: {...}}, ...]
    """
    cache_key = f"result_{year}_{round_num}"
    data = ergast_get(f"{year}/{round_num}/results.json", cache_key, force=force)
    races = data.get("Races", [])
    if not races:
        return []
    return races[0].get("Results", [])


def fetch_qualifying(year: int, round_num: int, force: bool = False) -> list:
    """获取某场排位赛结果.

    Returns:
        [{number, position, driver: {...}, constructor: {...},
          Q1, Q2, Q3}, ...]
    """
    cache_key = f"qualifying_{year}_{round_num}"
    data = ergast_get(f"{year}/{round_num}/qualifying.json", cache_key, force=force)
    races = data.get("Races", [])
    if not races:
        return []
    return races[0].get("QualifyingResults", [])


def fetch_driver_standings(year: int, force: bool = False) -> list:
    """获取某赛季末车手积分榜.

    Returns:
        [{position, positionText, points, wins, Driver: {...},
         Constructors: [{...}]}, ...]
    """
    cache_key = f"driverstandings_{year}"
    data = ergast_get(f"{year}/driverstandings.json", cache_key, force=force)
    sl = data.get("StandingsLists", [])
    if not sl:
        return []
    return sl[0].get("DriverStandings", [])


def fetch_constructor_standings(year: int, force: bool = False) -> list:
    """获取某赛季末车队积分榜."""
    cache_key = f"constructorstandings_{year}"
    data = ergast_get(f"{year}/constructorstandings.json", cache_key, force=force)
    sl = data.get("StandingsLists", [])
    if not sl:
        return []
    return sl[0].get("ConstructorStandings", [])


def fetch_all_circuits(force: bool = False) -> list:
    """获取全量赛道元数据."""
    data = ergast_get("circuits.json?limit=1000", "circuits_all", force=force)
    return data.get("Circuits", [])


# ============================================================
# 数据解析与扁平化
# ============================================================
def parse_race_row(year: int, round_num: int, race_name: str,
                   race_date: str, circuit_info: dict,
                   result: dict, qualifying_map: dict) -> dict:
    """将一条 Ergast 正赛结果解析为扁平 dict (CSV 的一行).

    Args:
        qualifying_map: {driver_id: grid_position} 排位赛映射
    """
    driver = result.get("Driver", {})
    constructor = result.get("Constructor", {})
    driver_id = driver.get("driverId", "")
    location = circuit_info.get("Location", {})

    # 完赛位次
    position = result.get("position", "")
    try:
        position = int(position) if position else 0
    except (ValueError, TypeError):
        position = 0

    # grid (发车位)
    grid = result.get("grid", "")
    try:
        grid = int(grid) if grid else 0
    except (ValueError, TypeError):
        grid = 0

    # 圈数
    laps = result.get("laps", "")
    try:
        laps = int(laps) if laps else 0
    except (ValueError, TypeError):
        laps = 0

    # 积分
    points = result.get("points", "")
    try:
        points = float(points) if points else 0.0
    except (ValueError, TypeError):
        points = 0.0

    status = result.get("status", "")

    # 排位赛位次 (优先用排位赛 endpoint 的 position, 回退到正赛 grid)
    qual_pos = qualifying_map.get(driver_id, grid)

    # 派生标签
    is_win = 1 if position == 1 else 0
    is_podium = 1 if 1 <= position <= 3 else 0
    is_points_finish = 1 if points > 0 else 0
    is_dnf = 1 if (position == 0 or "Retired" in status or
                    "Engine" in status or "Gearbox" in status or
                    "Collision" in status or "Accident" in status or
                    "Transmission" in status or "Hydraulic" in status or
                    "Electrical" in status or "Brakes" in status) else 0

    return {
        # 比赛信息
        "year": year,
        "round": round_num,
        "race_name": race_name,
        "race_date": race_date,
        "circuit_id": circuit_info.get("circuitId", ""),
        "circuit_name": circuit_info.get("circuitName", ""),
        "circuit_locality": location.get("locality", ""),
        "circuit_country": location.get("country", ""),
        "circuit_lat": location.get("lat", ""),
        "circuit_long": location.get("long", ""),
        # 车手信息
        "driver_id": driver_id,
        "driver_code": driver.get("code", ""),
        "driver_name": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
        "driver_nationality": driver.get("nationality", ""),
        "driver_number": driver.get("permanentNumber", ""),
        "driver_dob": driver.get("dateOfBirth", ""),
        # 车队信息
        "constructor_id": constructor.get("constructorId", ""),
        "constructor_name": constructor.get("name", ""),
        "constructor_nationality": constructor.get("nationality", ""),
        # 排位 + 正赛
        "qualifying_pos": qual_pos,
        "grid": grid,
        "finishing_pos": position,
        "points": points,
        "laps": laps,
        "status": status,
        # 派生标签
        "is_win": is_win,
        "is_podium": is_podium,
        "is_points_finish": is_points_finish,
        "is_dnf": is_dnf,
    }


def parse_standings_row(year: int, standing: dict) -> dict:
    """将一条赛季末积分榜解析为扁平 dict."""
    driver = standing.get("Driver", {})
    constructors = standing.get("Constructors", [])
    constructor_name = constructors[0].get("name", "") if constructors else ""

    return {
        "year": year,
        "driver_id": driver.get("driverId", ""),
        "driver_code": driver.get("code", ""),
        "driver_name": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
        "driver_nationality": driver.get("nationality", ""),
        "championship_position": int(standing.get("position", 99)),
        "championship_points": float(standing.get("points", 0)),
        "championship_wins": int(standing.get("wins", 0)),
        "constructor_name": constructor_name,
    }


def parse_circuit_row(circuit: dict) -> dict:
    """将一条赛道元数据解析为扁平 dict."""
    location = circuit.get("Location", {})
    return {
        "circuit_id": circuit.get("circuitId", ""),
        "circuit_name": circuit.get("circuitName", ""),
        "circuit_locality": location.get("locality", ""),
        "circuit_country": location.get("country", ""),
        "circuit_lat": location.get("lat", ""),
        "circuit_long": location.get("long", ""),
        "circuit_url": circuit.get("url", ""),
    }


# ============================================================
# 主流程
# ============================================================
def main(start_year: int = 2018, end_year: int = 2025, force: bool = False):
    print("=" * 60)
    print(f"F1 历史数据采集 ({start_year}-{end_year})")
    print(f"缓存目录: {CACHE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"强制刷新: {'是' if force else '否'}")
    print("=" * 60)

    # ---- 1. 采集赛道元数据 ----
    print("\n[1/4] 采集赛道元数据...")
    circuits_raw = fetch_all_circuits(force=force)
    circuits_df = pd.DataFrame([parse_circuit_row(c) for c in circuits_raw])
    circuits_path = OUTPUT_DIR / "circuits.csv"
    circuits_df.to_csv(circuits_path, index=False, encoding="utf-8-sig")
    print(f"  赛道: {len(circuits_df)} 条 -> {circuits_path}")

    # ---- 2. 采集赛季末积分榜 ----
    print("\n[2/4] 采集赛季末车手积分榜...")
    standings_rows = []
    for year in range(start_year, end_year + 1):
        print(f"  {year}...", end=" ")
        standings = fetch_driver_standings(year, force=force)
        if not standings:
            print("无数据, 跳过")
            continue
        for s in standings:
            standings_rows.append(parse_standings_row(year, s))
        print(f"{len(standings)} 位车手")
    standings_df = pd.DataFrame(standings_rows)
    standings_path = OUTPUT_DIR / "standings_2018_2025.csv"
    standings_df.to_csv(standings_path, index=False, encoding="utf-8-sig")
    print(f"  积分榜: {len(standings_df)} 行 -> {standings_path}")

    # ---- 3. 采集每场比赛结果 ----
    print("\n[3/4] 采集每场比赛结果...")
    race_rows = []
    total_races = 0
    skipped = 0

    for year in range(start_year, end_year + 1):
        print(f"\n  === {year} 赛季 ===")
        schedule = fetch_season_schedule(year, force=force)
        if not schedule:
            print(f"  {year} 赛季赛程为空, 跳过")
            continue

        for race in schedule:
            round_num = int(race.get("round", 0))
            race_name = race.get("raceName", "")
            race_date = race.get("date", "")
            circuit_info = race.get("Circuit", {})
            total_races += 1

            # 获取正赛结果
            results = fetch_race_results(year, round_num, force=force)
            if not results:
                print(f"    R{round_num} {race_name}: 无结果数据, 跳过")
                skipped += 1
                continue

            # 获取排位赛结果 (构建 driver_id -> position 映射)
            qualifying = fetch_qualifying(year, round_num, force=force)
            qual_map = {}
            for q in qualifying:
                did = q.get("Driver", {}).get("driverId", "")
                qual_map[did] = int(q.get("position", 0))

            # 解析每条结果
            for res in results:
                row = parse_race_row(
                    year, round_num, race_name, race_date,
                    circuit_info, res, qual_map
                )
                race_rows.append(row)

            print(f"    R{round_num} {race_name}: {len(results)} 位车手")

    race_df = pd.DataFrame(race_rows)
    race_path = OUTPUT_DIR / "races_2018_2025.csv"
    race_df.to_csv(race_path, index=False, encoding="utf-8-sig")
    print(f"\n  比赛结果: {len(race_df)} 行 ({total_races} 场, 跳过 {skipped} 场) -> {race_path}")

    # ---- 4. 数据质量检查 ----
    print("\n[4/4] 数据质量检查...")
    print(f"  races CSV: {len(race_df)} 行, {len(race_df.columns)} 列")
    print(f"  standings CSV: {len(standings_df)} 行, {len(standings_df.columns)} 列")
    print(f"  circuits CSV: {len(circuits_df)} 行, {len(circuits_df.columns)} 列")

    # 年份覆盖
    years_covered = sorted(race_df["year"].unique())
    print(f"  年份覆盖: {years_covered}")

    # 每年比赛数
    races_per_year = race_df.groupby("year")["round"].nunique()
    print(f"  每年分站数:\n{races_per_year.to_string()}")

    # 车手数
    unique_drivers = race_df["driver_id"].nunique()
    print(f"  独立车手数: {unique_drivers}")

    # 胜者分布
    winners = race_df[race_df["is_win"] == 1]["driver_code"].value_counts()
    print(f"  胜者分布 (top 10):\n{winners.head(10).to_string()}")

    # DNF 率
    dnf_rate = race_df["is_dnf"].mean()
    print(f"  总体 DNF 率: {dnf_rate:.1%}")

    # 缺失值检查
    missing = race_df.isnull().sum()
    if missing.any():
        print(f"  缺失值:\n{missing[missing > 0].to_string()}")
    else:
        print("  缺失值: 无")

    print("\n" + "=" * 60)
    print("数据采集完成!")
    print(f"  主表:  {race_path}")
    print(f"  积分榜: {standings_path}")
    print(f"  赛道:  {circuits_path}")
    print("=" * 60)

    return race_df, standings_df, circuits_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F1 历史数据采集 (XGBoost 训练用)")
    parser.add_argument("--start-year", type=int, default=2018, help="起始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")
    parser.add_argument("--force", action="store_true", help="忽略缓存, 强制重新拉取")
    args = parser.parse_args()

    main(start_year=args.start_year, end_year=args.end_year, force=args.force)
