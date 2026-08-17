# -*- coding: utf-8 -*-
"""
data_source.py — 数据获取层

职责：
    1. Ergast API（赛程 / 成绩 / 车手榜 / 车队榜）  —— 模块 A1/A2/A3
    2. FastF1        （单站圈速 / 轮胎策略）          —— 模块 A4

设计原则：
    - 路由层(main.py)只调用本文件的函数，不关心数据从哪来。
    - 所有第三方请求都带本地缓存，规避限流与网络抖动。
    - 所有返回给路由层的数据都是 JSON 可序列化的原生类型
      (int/float/str/None/list/dict)，避免 FastAPI 序列化 timedleta/np 类型失败。
"""
import requests
import json
import os
import time
from fastapi import HTTPException

import fastf1
import numpy as np
import pandas as pd


# ============================================================
# 通用工具函数
# ============================================================
def _timedelta_to_seconds(td):
    """将 pandas Timedelta / NaT 转为浮点秒数，NaT 返回 None。

    为什么要这个函数：FastF1 的 LapTime / SectorXTime 是 timedelta64[ns]，
    无法直接 json.dump，必须先转成 float。
    """
    if td is None or pd.isna(td):
        return None
    try:
        return float(td.total_seconds())
    except AttributeError:
        # 已经是数字
        return float(td)


def _format_laptime(td):
    """把 Timedelta 格式化为 'M:SS.mmm'，例如 1:22.167。"""
    sec = _timedelta_to_seconds(td)
    if sec is None:
        return None
    minutes = int(sec // 60)
    remainder = sec - minutes * 60
    return f"{minutes}:{remainder:06.3f}"


# ============================================================
# Ergast 配置 + 缓存基础设施
# ============================================================
ERGAST_BASE_URL = "https://api.jolpi.ca/ergast/f1"
CACHE_FOLDER = r"C:\Users\陈词年\PycharmProjects\f1_light_app\cache\ergast_cache"
CACHE_EXPIRE_SECONDS = 3600  # 1小时（赛季进行中新分站数据自动刷新）
# 历史赛季数据永不变，缓存 7 天即可（7 天后重新拉取确认无异常）
CACHE_EXPIRE_HISTORICAL_SECONDS = 7 * 24 * 3600
# 当前年份，用于判断"历史赛季 vs 进行中赛季"
import datetime as _dt
_CURRENT_YEAR = _dt.date.today().year
# 确保缓存文件夹存在
os.makedirs(CACHE_FOLDER, exist_ok=True)


def _get_cache_filepath(cache_key: str):
    """生成缓存文件路径"""
    return os.path.join(CACHE_FOLDER, f"{cache_key}.json")


def _is_cache_valid(file_path: str, ttl: int = None):
    """判断缓存是否没过期

    Args:
        ttl: 自定义有效期（秒），None 则使用默认 CACHE_EXPIRE_SECONDS。
    """
    if not os.path.exists(file_path):
        return False
    expire = ttl if ttl is not None else CACHE_EXPIRE_SECONDS
    modify_time = os.path.getmtime(file_path)
    now = time.time()
    return now - modify_time < expire


def load_from_cache(cache_key: str, ttl: int = None):
    """读取本地缓存

    Args:
        ttl: 自定义有效期（秒），None 则使用默认 CACHE_EXPIRE_SECONDS。
    """
    fp = _get_cache_filepath(cache_key)
    if _is_cache_valid(fp, ttl=ttl):
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_to_cache(cache_key: str, data):
    """写入本地json缓存"""
    fp = _get_cache_filepath(cache_key)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _fetch_ergast_data(endpoint: str, cache_key: str, table_name: str, ttl: int = None):
    """通用Ergast请求+缓存底层函数

    Args:
        ttl: 缓存有效期（秒），None 则使用默认 CACHE_EXPIRE_SECONDS。
             历史赛季数据永不变，可传 7*24*3600 减少无效请求。
    """
    cache_data = load_from_cache(cache_key, ttl=ttl)
    if cache_data is not None:
        return cache_data

    url = f"{ERGAST_BASE_URL}/{endpoint}"
    try:
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Ergast接口访问超时（6s）")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        raise HTTPException(status_code=502, detail=f"Ergast接口返回错误 {status}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ergast接口请求失败: {e}")

    raw = resp.json()
    result = raw["MRData"][table_name]
    save_to_cache(cache_key, result)
    return result


# ---------------- Ergast 业务接口（模块 A1/A2/A3）----------------
def fetch_ergast_current_season():
    return _fetch_ergast_data(endpoint="current.json", cache_key="current_season", table_name="RaceTable")


def fetch_ergast_season_by_year(year: int):
    cache_key = f"season_{year}"
    # 历史赛季数据永不变，用 7 天 TTL；当前赛季用默认 1 小时
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}.json", cache_key=cache_key, table_name="RaceTable", ttl=ttl)


def fetch_ergast_race_result(year: int, round_num: int):
    cache_key = f"result_{year}_{round_num}"
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}/{round_num}/results.json", cache_key=cache_key, table_name="RaceTable", ttl=ttl)


def fetch_ergast_all_circuits():
    cache_key = "circuits_all"
    return _fetch_ergast_data(endpoint="circuits.json", cache_key=cache_key, table_name="CircuitTable")


def fetch_ergast_current_season_drivers():
    cache_key = "current_drivers"
    return _fetch_ergast_data(endpoint="current/drivers.json", cache_key=cache_key, table_name="DriverTable")


def fetch_ergast_season_drivers_by_year(year: int):
    cache_key = f"season_{year}_drivers"
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}/drivers.json", cache_key=cache_key, table_name="DriverTable", ttl=ttl)


def fetch_ergast_current_season_driverstandings():
    cache_key = "current_driverstandings"
    return _fetch_ergast_data(endpoint="current/driverstandings.json", cache_key=cache_key, table_name="StandingsTable")


def fetch_ergast_current_season_qualifying_results(round_num: int):
    cache_key = f"qualifying_standings_{round_num}"
    return _fetch_ergast_data(endpoint=f"current/{round_num}/qualifying.json", cache_key=cache_key, table_name="RaceTable")


def fetch_ergast_season_qualifying_results_by_year(year: int, round_num: int):
    cache_key = f"qualifying_standings_{year}_{round_num}"
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}/{round_num}/qualifying.json", cache_key=cache_key, table_name="RaceTable", ttl=ttl)


def fetch_ergast_current_season_constructorstandings():
    cache_key = "current_constructorstandings"
    return _fetch_ergast_data(endpoint="current/constructorstandings.json", cache_key=cache_key, table_name="StandingsTable")


def fetch_ergast_driverstandings_by_year(year: int):
    """历史赛季车手积分榜（模块 A3 接口缺口补全）"""
    cache_key = f"driverstandings_{year}"
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}/driverstandings.json", cache_key=cache_key, table_name="StandingsTable", ttl=ttl)


def fetch_ergast_constructorstandings_by_year(year: int):
    """历史赛季车队积分榜"""
    cache_key = f"constructorstandings_{year}"
    ttl = CACHE_EXPIRE_HISTORICAL_SECONDS if year < _CURRENT_YEAR else CACHE_EXPIRE_SECONDS
    return _fetch_ergast_data(endpoint=f"{year}/constructorstandings.json", cache_key=cache_key, table_name="StandingsTable", ttl=ttl)


# ============================================================
# FastF1 配置 + 结果缓存（模块 A4）
# ============================================================
# FastF1 自带的 HTTP/解析缓存（.ff1pkl），缓存官方计时接口的原始响应
FASTF1_HTTP_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../cache/fastf1_cache")
os.makedirs(FASTF1_HTTP_CACHE, exist_ok=True)
fastf1.Cache.enable_cache(FASTF1_HTTP_CACHE)
fastf1.set_log_level("Warning")  # 关闭 fastf1 冗余日志，避免控制台刷屏

# 处理后结果的 JSON 缓存（最快圈排行 / 轮胎策略），命中后直接返回，跳过 session.load()
FASTF1_RESULT_CACHE_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../cache/fastf1_result_cache"
)
os.makedirs(FASTF1_RESULT_CACHE_FOLDER, exist_ok=True)
# 赛果一旦产生即不再变化，但保留 7 天刷新窗口，便于官方修正数据后更新
FASTF1_RESULT_CACHE_EXPIRE_SECONDS = 7 * 24 * 3600


def _get_fastf1_result_cache_filepath(cache_key: str):
    return os.path.join(FASTF1_RESULT_CACHE_FOLDER, f"{cache_key}.json")


def _is_fastf1_result_cache_valid(file_path: str):
    if not os.path.exists(file_path):
        return False
    return (time.time() - os.path.getmtime(file_path)) < FASTF1_RESULT_CACHE_EXPIRE_SECONDS


def _load_fastf1_result(cache_key: str):
    fp = _get_fastf1_result_cache_filepath(cache_key)
    if _is_fastf1_result_cache_valid(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_fastf1_result(cache_key: str, data):
    fp = _get_fastf1_result_cache_filepath(cache_key)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        # 缓存写失败不应影响主流程
        pass


def fetch_fastf1_sessions(year: int, round_num: int, session_type: str = "R"):
    """
    加载 F1 单场比赛会话数据（圈速表）。

    :param year: 赛季年份，如 2025
    :param round_num: 分站轮次，1=第一站
    :param session_type: R=正赛，Q=排位，FP1/FP2/FP3=练习赛，S=冲刺赛，SQ=冲刺赛排位
    :return: 成功返回 pandas.DataFrame（session.laps）；失败返回 None。

    注意：
        - FastF1 的 session.load() 参数是 ``messages``（复数），写成 ``message`` 会抛
          ``TypeError: Session.load() got an unexpected keyword argument 'message'``。
        - 官方计时数据通过 fastf1.Cache 缓存，首次加载需联网，后续从本地读取。
    """
    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=False, weather=False, messages=False)
    except Exception as e:
        print(f"[FastF1 加载失败] {year} 第{round_num}站 {session_type}：{e}")
        return None

    laps = getattr(session, "laps", None)
    if laps is None or len(laps) == 0:
        print(f"[FastF1 空数据] {year} 第{round_num}站 {session_type} 无圈速记录")
        return None
    return laps


def fetch_fastf1_fastest_lap(year: int, round_num: int, session_type: str = "R"):
    """
    A4-1：单场车手最快圈排行。

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1, "session": "R",
          "fastest_lap_overall": {"Rank":1,"Driver":"NOR","LapTimeStr":"1:22.167","LapTimeSeconds":82.167},
          "fastest_lap_ranking": [ {...}, ... ]
        }
    数据缺失时返回 {"code":500,"msg":"..."}
    """
    cache_key = f"fastlap_{year}_{round_num}_{session_type}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    laps_df = fetch_fastf1_sessions(year, round_num, session_type)
    if laps_df is None:
        result = {"code": 500, "msg": f"暂无 {year} 第{round_num}站 {session_type} 圈速数据"}
        return result

    # 去掉没有有效圈速（LapTime 为 NaT）的行
    df = laps_df.dropna(subset=["LapTime"]).copy()
    df["LapTimeSeconds"] = df["LapTime"].apply(_timedelta_to_seconds)
    df = df.dropna(subset=["LapTimeSeconds"])
    if df.empty:
        result = {"code": 500, "msg": "本场无有效圈速（LapTime 全为空）"}
        return result

    # 每位车手取最快一圈：groupby Driver 取 LapTimeSeconds 最小所在的行
    idx = df.groupby("Driver")["LapTimeSeconds"].idxmin()
    fastest = df.loc[idx, ["Driver", "LapTime", "LapTimeSeconds"]].copy()
    # 升序：时间越短越快，排在前面
    fastest = fastest.sort_values("LapTimeSeconds", ascending=True).reset_index(drop=True)
    fastest["LapTimeStr"] = fastest["LapTime"].apply(_format_laptime)
    fastest["Rank"] = (fastest.index + 1).astype(int)

    data_list = fastest[["Rank", "Driver", "LapTimeStr", "LapTimeSeconds"]].to_dict("records")
    # 统一转原生类型，避免 numpy.int64/float64 在某些序列化路径下报错
    for item in data_list:
        item["Rank"] = int(item["Rank"])
        item["LapTimeSeconds"] = round(float(item["LapTimeSeconds"]), 3)

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "fastest_lap_overall": data_list[0] if data_list else None,
        "fastest_lap_ranking": data_list,
    }
    _save_fastf1_result(cache_key, result)
    return result


def fetch_fastf1_tyre_strategy(year: int, round_num: int):
    """
    A4-2：单站正赛车手轮胎进站策略。

    利用 laps 表中的 ``Stint``（ stint 编号）+ ``Compound``（轮胎配方）+ ``LapNumber``
    重建每位车手的进站序列，保留先后顺序，便于前端绘制轮胎策略条带图。

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1,
          "tyre_strategy": [
            {"driver":"NOR","stints":[
                {"stint":1,"compound":"INTERMEDIATE","start_lap":1,"end_lap":4,"laps":4}, ...
            ]}, ...
          ]
        }

    踩坑：
        - 轮胎配方列名是 ``Compound``，不是 ``TyreCompound``（旧版/教程里常写错）。
        - 直接 groupby ['Driver','Compound'].count() 会丢失进站先后顺序，故按 Stint 重建。
    """
    cache_key = f"tyre_{year}_{round_num}_R"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    laps_df = fetch_fastf1_sessions(year, round_num, session_type="R")
    if laps_df is None:
        result = {"code": 500, "msg": f"暂无 {year} 第{round_num}站正赛圈速数据"}
        return result

    needed = ["Driver", "Stint", "Compound", "LapNumber"]
    missing = [c for c in needed if c not in laps_df.columns]
    if missing:
        result = {"code": 500, "msg": f"圈速表缺少列：{missing}"}
        return result

    df = laps_df[needed].copy()
    df = df.sort_values(["Driver", "LapNumber"])

    strategy = []
    for driver, grp in df.groupby("Driver", sort=False):
        stints = []
        for stint_no, sg in grp.groupby("Stint", sort=False):
            compound = sg["Compound"].iloc[0]
            # compound 可能为 None/NaN（极少见，进站换胎瞬间）
            if compound is None or (isinstance(compound, float) and np.isnan(compound)):
                compound = "UNKNOWN"
            stints.append({
                "stint": int(stint_no),
                "compound": str(compound),
                "start_lap": int(sg["LapNumber"].min()),
                "end_lap": int(sg["LapNumber"].max()),
                "laps": int(len(sg)),
            })
        if stints:
            strategy.append({"driver": str(driver), "stints": stints})

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "tyre_strategy": strategy,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B2：遥测数据对比（FastF1 car_data）
# ============================================================
def fetch_fastf1_telemetry_compare(
    year: int,
    round_num: int,
    driver_codes: list,
    channels: list,
    session_type: str = "R"
):
    """
    B2：多车手多通道遥测数据对比。

    使用 FastF1 的 session.laps[idx].get_car_data() 获取逐帧遥测数据，
    包含 Speed / Throttle / Brake / RPM / nGear / DRS 六个通道。

    参数：
        driver_codes: ["VER", "NOR"] 最多 3 个
        channels: ["speed", "throttle", "brake", "rpm", "gear", "drs"]
        session_type: "R"=正赛 "Q"=排位 "FP1"/"FP2"/"FP3"=练习赛 "SQ"=冲刺排位 "SS"=冲刺赛

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1,
          "channels": ["speed", "throttle"],
          "circuit_name": "Albert Park Grand Prix Circuit",
          "track_points": [{"x": 12.3, "y": 45.6}, ...],  # 归一化坐标 0-100
          "distances": [0.0, 12.5, 25.0, ...],  # 归一化距离（米）
          "corner_segments": [  # 沿距离等分 N 段，每段标记该段最快车手
            {"segment_index": 0, "start_dist": 0, "end_dist": 187.5,
             "fastest_driver": "VER", "fastest_avg_speed_kmh": 285.3},
            ...
          ],
          "drivers": {
            "VER": {
              "speed": [310, 305, ...],
              "throttle": [100, 95, ...],
              ...
            }, ...
          }
        }

    踩坑：
        - get_car_data() 需要在 session.load(telemetry=True) 之后才能调用
        - 原始数据是逐帧采样（约 20Hz），点数很多，需降采样到 ~200 个点
        - Distance 列用于 X 轴对齐多车手
        - X/Y 坐标在 get_pos_data() 中（不在 get_car_data() 中），用第一位车手最快圈的 pos_data
          提取赛道轮廓，按 distance 列对齐各车手遥测数据
        - corner_segments 按 distances 等分（如 30 段），每段求各车手平均速度，最大者即为该段最快
          车手，颜色用对应车队色绘制赛道分段
    """
    cache_key = f"telemetry_v2_{year}_{round_num}_{session_type}_{'_'.join(driver_codes)}_{'_'.join(channels)}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception as e:
        return {"code": 500, "msg": f"FastF1 加载失败: {e}"}

    laps = getattr(session, "laps", None)
    if laps is None or len(laps) == 0:
        return {"code": 500, "msg": "无圈速数据"}

    # 通道映射
    channel_map = {
        "speed": "Speed",
        "throttle": "Throttle",
        "brake": "Brake",
        "rpm": "RPM",
        "gear": "nGear",
        "drs": "DRS",
    }

    # 取每位车手最快一圈的遥测数据
    drivers_data = {}
    all_distances = None
    track_points = []            # 赛道轮廓 [{x, y}]，从第一位成功车手的最快圈 pos_data 提取
    circuit_name = ""

    for code in driver_codes:
        try:
            drv_laps = laps[laps["Driver"] == code]
            if drv_laps.empty:
                continue
            fastest = drv_laps.pick_fastest()
            car_data = fastest.get_car_data()
            if car_data is None or len(car_data) == 0:
                continue

            # 降采样：取每 N 个点中第一个，目标 ~200 个点
            step = max(1, len(car_data) // 200)
            sampled = car_data.iloc[::step].reset_index(drop=True)

            # FastF1 3.8.x car_data 没有 Distance 列，
            # 用归一化距离（0~1）作为 X 轴，所有车手共享同一索引
            n = len(sampled)
            if all_distances is None:
                all_distances = [round(i / max(n - 1, 1), 4) for i in range(n)]

            # 提取各通道
            drv_channels = {}
            for ch in channels:
                col_name = channel_map.get(ch, ch)
                if col_name in sampled.columns:
                    vals = sampled[col_name].tolist()
                    drv_channels[ch] = [round(float(v), 2) if v is not None and not pd.isna(v) else 0 for v in vals]
                else:
                    drv_channels[ch] = []

            drivers_data[code] = drv_channels

            # 第一位成功提取的车手 = 赛道轮廓基准，用其 pos_data 拿 X/Y
            if not track_points:
                try:
                    pos_data = fastest.get_pos_data()
                    if pos_data is not None and len(pos_data) > 0 \
                            and "X" in pos_data.columns and "Y" in pos_data.columns:
                        # 按与 car_data 相同的 step 降采样
                        pos_step = max(1, len(pos_data) // 200)
                        pos_sampled = pos_data.iloc[::pos_step].reset_index(drop=True)
                        x_vals = pos_sampled["X"].dropna().values
                        y_vals = pos_sampled["Y"].dropna().values
                        if len(x_vals) > 10:
                            x_min, x_max = float(np.min(x_vals)), float(np.max(x_vals))
                            y_min, y_max = float(np.min(y_vals)), float(np.max(y_vals))
                            x_range = max(x_max - x_min, 0.001)
                            y_range = max(y_max - y_min, 0.001)
                            # Y 轴翻转（F1 官方 lat/lon → 屏幕坐标需要翻转）
                            for px, py in zip(x_vals, y_vals):
                                track_points.append({
                                    "x": round((float(px) - x_min) / x_range * 100, 2),
                                    "y": round((1 - (float(py) - y_min) / y_range) * 100, 2),
                                })
                except Exception as e:
                    print(f"[赛道轮廓提取失败] {code}: {e}")

        except Exception as e:
            print(f"[遥测提取失败] {code}: {e}")
            continue

    if not drivers_data:
        return {"code": 500, "msg": "未能提取任何车手的遥测数据"}

    # 赛道名
    try:
        circuit_name = str(session.event["EventName"]) if hasattr(session, "event") else ""
    except Exception:
        circuit_name = ""

    # ============================================================
    # 计算 corner_segments：沿 distances 等分 N 段（默认 30），
    # 每段求各车手平均速度，最大者为该段最快车手
    # ============================================================
    NUM_SEGMENTS = 30
    corner_segments = []
    if all_distances and len(all_distances) >= 2:
        total_dist = float(all_distances[-1])
        if total_dist <= 0:
            total_dist = float(len(all_distances))  # fallback 用索引当距离

        seg_len = total_dist / NUM_SEGMENTS
        for seg_i in range(NUM_SEGMENTS):
            start_d = seg_i * seg_len
            end_d = (seg_i + 1) * seg_len
            # 找出 indices 在该距离区间的所有采样点
            indices = [
                i for i, d in enumerate(all_distances)
                if d is not None and start_d <= float(d) <= end_d
            ]
            if not indices:
                corner_segments.append({
                    "segment_index": seg_i,
                    "start_dist": round(start_d, 4),
                    "end_dist": round(end_d, 4),
                    "fastest_driver": None,
                    "fastest_avg_speed_kmh": None,
                })
                continue

            best_code = None
            best_avg = -1.0
            for code, chans in drivers_data.items():
                speed_arr = chans.get("speed") or []
                if not speed_arr:
                    continue
                seg_speeds = [
                    float(speed_arr[i]) for i in indices
                    if i < len(speed_arr) and speed_arr[i] is not None
                ]
                if not seg_speeds:
                    continue
                avg = sum(seg_speeds) / len(seg_speeds)
                if avg > best_avg:
                    best_avg = avg
                    best_code = code
            corner_segments.append({
                "segment_index": seg_i,
                "start_dist": round(start_d, 4),
                "end_dist": round(end_d, 4),
                "fastest_driver": best_code,
                "fastest_avg_speed_kmh": round(best_avg, 1) if best_avg > 0 else None,
            })

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "channels": channels,
        "circuit_name": circuit_name,
        "track_points": track_points,
        "corner_segments": corner_segments,
        "distances": all_distances or [],
        "drivers": drivers_data,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B1：赛道分段最快（Sector Fastest）
# ============================================================
def fetch_fastf1_sector_fastest(year: int, round_num: int, session_type: str = "R"):
    """
    B1：赛道各分段（Sector 1/2/3）最快车手及时间。

    利用 FastF1 laps 表中的 Sector1Time / Sector2Time / Sector3Time 列，
    找出每个分段的全场最快车手，用于赛道地图着色或分段对比。

    返回结构：
        {
          "code": 200,
          "year": 2024, "round": 5, "session": "R",
          "sectors": [
            {
              "sector": 1,
              "fastest_driver": "VER",
              "fastest_time": 26.123,
              "fastest_time_str": "26.123",
              "ranking": [
                {"driver": "VER", "time": 26.123, "time_str": "26.123"},
                {"driver": "NOR", "time": 26.456, "time_str": "26.456"}
              ]
            },
            ...
          ],
          "overall_fastest_driver": "VER"
        }

    踩坑：
        - Sector 列名是 Sector1Time / Sector2Time / Sector3Time（不是 Sector1）
        - Sector 时间也是 timedelta64[ns]，需要 _timedelta_to_seconds() 转换
        - 某些车手某些圈可能没有 Sector 时间（NaT），需要 dropna
    """
    cache_key = f"sector_{year}_{round_num}_{session_type}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    laps_df = fetch_fastf1_sessions(year, round_num, session_type)
    if laps_df is None:
        return {"code": 500, "msg": f"暂无 {year} 第{round_num}站 {session_type} 圈速数据"}

    sector_cols = ["Sector1Time", "Sector2Time", "Sector3Time"]
    missing = [c for c in sector_cols if c not in laps_df.columns]
    if missing:
        return {"code": 500, "msg": f"圈速表缺少分段列：{missing}"}

    sectors_data = []
    overall_fastest_driver = None
    overall_fastest_sum = float("inf")

    for i, col in enumerate(sector_cols, start=1):
        # 取每人在该分段的最快时间
        df = laps_df[["Driver", col]].dropna(subset=[col]).copy()
        if df.empty:
            sectors_data.append({
                "sector": i,
                "fastest_driver": None,
                "fastest_time": None,
                "fastest_time_str": None,
                "ranking": [],
            })
            continue

        df["seconds"] = df[col].apply(_timedelta_to_seconds)
        df = df.dropna(subset=["seconds"])
        # 每人取最快
        idx = df.groupby("Driver")["seconds"].idxmin()
        per_driver = df.loc[idx, ["Driver", "seconds"]].copy()
        per_driver = per_driver.sort_values("seconds", ascending=True).reset_index(drop=True)

        fastest_row = per_driver.iloc[0]
        fastest_driver = str(fastest_row["Driver"])
        fastest_time = round(float(fastest_row["seconds"]), 3)

        ranking = []
        for _, row in per_driver.iterrows():
            t = round(float(row["seconds"]), 3)
            ranking.append({
                "driver": str(row["Driver"]),
                "time": t,
                "time_str": _format_laptime(row["seconds"]),
            })

        sectors_data.append({
            "sector": i,
            "fastest_driver": fastest_driver,
            "fastest_time": fastest_time,
            "fastest_time_str": _format_laptime(fastest_row["seconds"]),
            "ranking": ranking,
        })

    # 找全场三段总和最快车手（紫色标注用）
    df_all = laps_df[["Driver"] + sector_cols].copy()
    for col in sector_cols:
        df_all[col + "_s"] = df_all[col].apply(_timedelta_to_seconds)
    df_all["total"] = df_all[[c + "_s" for c in sector_cols]].sum(axis=1)
    df_all = df_all.dropna(subset=["total"])
    if not df_all.empty:
        best_row = df_all.loc[df_all["total"].idxmin()]
        overall_fastest_driver = str(best_row["Driver"])

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "sectors": sectors_data,
        "overall_fastest_driver": overall_fastest_driver,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B3：圈速分布（Lap Distribution）
# ============================================================
def fetch_fastf1_lap_distribution(year: int, round_num: int, session_type: str = "R"):
    """
    B3：全部车手的圈速分布数据，用于箱线图（Box Plot）可视化。

    收集每位车手在本场比赛所有有效圈速，
    按车手分组返回原始圈速列表，前端用 ECharts boxplot 绘制。

    返回结构：
        {
          "code": 200,
          "year": 2024, "round": 5, "session": "R",
          "distribution": [
            {
              "driver": "VER",
              "compound": "MEDIUM",
              "lap_times": [80.235, 80.567, 80.123, ...],
              "lap_count": 56,
              "min": 80.123,
              "max": 81.456,
              "mean": 80.567,
              "median": 80.500
            },
            ...
          ]
        }

    踩坑：
        - LapTime 是 timedelta64[ns]，必须 _timedelta_to_seconds() 转换
        - 需要过滤掉 NaT（进站圈/出场圈/退赛圈无有效时间）
        - 每位车手可能使用多种轮胎，取最常用配方展示
    """
    cache_key = f"lapdist_{year}_{round_num}_{session_type}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    laps_df = fetch_fastf1_sessions(year, round_num, session_type)
    if laps_df is None:
        return {"code": 500, "msg": f"暂无 {year} 第{round_num}站 {session_type} 圈速数据"}

    needed = ["Driver", "LapTime", "Compound"]
    missing = [c for c in needed if c not in laps_df.columns]
    if missing:
        return {"code": 500, "msg": f"圈速表缺少列：{missing}"}

    df = laps_df[needed].copy()
    df["LapTimeSeconds"] = df["LapTime"].apply(_timedelta_to_seconds)
    df = df.dropna(subset=["LapTimeSeconds"])

    if df.empty:
        return {"code": 500, "msg": "本场无有效圈速数据"}

    distribution = []
    for driver, grp in df.groupby("Driver", sort=False):
        times = sorted([round(float(t), 3) for t in grp["LapTimeSeconds"]])
        if not times:
            continue

        # 取最常用轮胎配方
        compound_counts = grp["Compound"].value_counts()
        main_compound = str(compound_counts.index[0]) if not compound_counts.empty else "UNKNOWN"

        n = len(times)
        median_val = times[n // 2] if n % 2 == 1 else round((times[n // 2 - 1] + times[n // 2]) / 2, 3)
        mean_val = round(sum(times) / n, 3)

        distribution.append({
            "driver": str(driver),
            "compound": main_compound,
            "lap_times": times,
            "lap_count": n,
            "min": times[0],
            "max": times[-1],
            "mean": mean_val,
            "median": median_val,
        })

    # 按中位数升序排列（快的在前面）
    distribution.sort(key=lambda x: x["median"])

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "distribution": distribution,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B4：速度叠加对比（Speed Overlay）
# ============================================================
def fetch_fastf1_speed_overlay(
    year: int,
    round_num: int,
    driver_codes: list,
    session_type: str = "R"
):
    """
    B4：基于赛道距离归一化的多车手速度曲线叠加。

    与 B2 遥测对比的区别：
        - B2 按距离轴对齐，但各车手距离点不一定相同（不同圈不同路径）
        - B4 将所有车手插值到统一的归一化距离网格（0~track_length），
          使得同一 X 坐标对应同一赛道位置，便于精确对比弯道速度差异

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1,
          "track_length": 5427.0,
          "grid_distances": [0, 50, 100, ..., 5400],
          "drivers": {
            "VER": {"speed": [85, 120, 310, ...], "max_speed": 340.5},
            "NOR": {"speed": [82, 118, 305, ...], "max_speed": 338.0}
          }
        }
    """
    cache_key = f"speedoverlay_{year}_{round_num}_{session_type}_{'_'.join(driver_codes)}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception as e:
        return {"code": 500, "msg": f"FastF1 加载失败: {e}"}

    laps = getattr(session, "laps", None)
    if laps is None or len(laps) == 0:
        return {"code": 500, "msg": "无圈速数据"}

    # 统一距离网格：每 50m 一个点
    GRID_STEP = 50.0

    drivers_data = {}
    max_track_distance = 0.0

    for code in driver_codes:
        try:
            drv_laps = laps[laps["Driver"] == code]
            if drv_laps.empty:
                continue
            fastest = drv_laps.pick_fastest()
            car_data = fastest.get_car_data()
            if car_data is None or len(car_data) == 0:
                continue

            # 提取 Distance + Speed
            if "Distance" not in car_data.columns:
                continue
            distances_raw = car_data["Distance"].fillna(0).values
            speeds_raw = car_data["Speed"].fillna(0).values

            track_len = float(np.nanmax(distances_raw))
            if track_len > max_track_distance:
                max_track_distance = track_len

            # 插值到统一网格
            grid = np.arange(0, track_len + GRID_STEP, GRID_STEP)
            interpolated = np.interp(grid, distances_raw, speeds_raw)

            drivers_data[code] = {
                "speed": [round(float(v), 1) for v in interpolated],
                "max_speed": round(float(np.nanmax(speeds_raw)), 1),
            }
        except Exception as e:
            print(f"[速度叠加提取失败] {code}: {e}")
            continue

    if not drivers_data:
        return {"code": 500, "msg": "未能提取任何车手的速度数据"}

    # 统一所有车手到同一网格长度（取最短）
    min_len = min(len(d["speed"]) for d in drivers_data.values())
    for d in drivers_data.values():
        d["speed"] = d["speed"][:min_len]

    grid_distances = [round(float(i * GRID_STEP), 1) for i in range(min_len)]

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "track_length": round(max_track_distance, 1),
        "grid_distances": grid_distances,
        "drivers": drivers_data,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B5：赛道地图分段着色（Track Map）
# ============================================================
def fetch_fastf1_track_map(year: int, round_num: int, session_type: str = "R"):
    """
    B5：赛道地图坐标 + 各分段最快车手着色数据。

    使用 FastF1 的 session.get_circuit_info() 获取赛道坐标点（经纬度），
    结合 sector-fastest 数据，前端用 SVG 渲染赛道轮廓并按分段着色：
      - Purple（紫色）: 全场最快
      - Green（绿色）: 个人最快但非全场最快
      - Yellow（黄色）: 非个人最快

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1,
          "circuit_name": "Albert Park Grand Prix Circuit",
          "track_points": [{"x": 0.0, "y": 0.0}, ...],  # 归一化坐标
          "track_length": 5427.0,
          "sectors": [
            {
              "sector": 1,
              "fastest_driver": "VER",
              "fastest_time": 26.123,
              "color": "purple"
            }, ...
          ],
          "overall_fastest_driver": "VER"
        }

    踩坑：
        - get_circuit_info() 返回的坐标可能需要旋转/翻转才能正向显示
        - 部分赛道可能没有坐标数据，需 try/except 兜底
        - 坐标需归一化到 0-1 范围，前端 SVG viewBox 即可适配
    """
    cache_key = f"trackmap_{year}_{round_num}_{session_type}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    try:
        session = fastf1.get_session(year, round_num, session_type)
        # 需要加载 telemetry=True 才能从车手遥测数据中提取 X/Y 坐标作为 track_points fallback
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception as e:
        return {"code": 500, "msg": f"FastF1 加载失败: {e}"}

    # 获取赛道坐标
    track_points = []
    circuit_name = ""
    try:
        circuit_info = session.get_circuit_info()
        if circuit_info is not None and hasattr(circuit_info, "columns"):
            # circuit_info 通常包含 X, Y 坐标列
            if "X" in circuit_info.columns and "Y" in circuit_info.columns:
                x_vals = circuit_info["X"].dropna().values
                y_vals = circuit_info["Y"].dropna().values
                if len(x_vals) > 0:
                    # 归一化到 0-100 范围（SVG viewBox 用 0 0 100 100）
                    x_min, x_max = float(np.min(x_vals)), float(np.max(x_vals))
                    y_min, y_max = float(np.min(y_vals)), float(np.max(y_vals))
                    x_range = max(x_max - x_min, 0.001)
                    y_range = max(y_max - y_min, 0.001)
                    for x, y in zip(x_vals, y_vals):
                        track_points.append({
                            "x": round((float(x) - x_min) / x_range * 100, 2),
                            "y": round((float(y) - y_min) / y_range * 100, 2),
                        })
    except Exception as e:
        print(f"[赛道坐标获取失败] {e}")

    # Fallback: 如果 circuit_info 没有坐标，从遥测数据中提取车手 X/Y 轨迹
    if not track_points:
        try:
            laps = getattr(session, "laps", None)
            if laps is not None and len(laps) > 0:
                # 取第一辆车的最快圈位置数据，用 X/Y 坐标画出赛道轮廓
                first_driver = laps["Driver"].iloc[0]
                drv_laps = laps[laps["Driver"] == first_driver]
                if not drv_laps.empty:
                    fastest = drv_laps.pick_fastest()
                    # 使用 get_pos_data() 获取 X/Y 坐标（不是 get_car_data()）
                    pos_data = fastest.get_pos_data()
                    if pos_data is not None and len(pos_data) > 0:
                        if "X" in pos_data.columns and "Y" in pos_data.columns:
                            x_vals = pos_data["X"].dropna().values
                            y_vals = pos_data["Y"].dropna().values
                            if len(x_vals) > 10:  # 确保有足够的数据点
                                # 降采样到 ~200 个点
                                step = max(1, len(x_vals) // 200)
                                x_sampled = x_vals[::step]
                                y_sampled = y_vals[::step]
                                x_min, x_max = float(np.min(x_sampled)), float(np.max(x_sampled))
                                y_min, y_max = float(np.min(y_sampled)), float(np.max(y_sampled))
                                x_range = max(x_max - x_min, 0.001)
                                y_range = max(y_max - y_min, 0.001)
                                for x, y in zip(x_sampled, y_sampled):
                                    track_points.append({
                                        "x": round((float(x) - x_min) / x_range * 100, 2),
                                        "y": round((float(y) - y_min) / y_range * 100, 2),
                                    })
                                print(f"[赛道坐标] 从位置数据提取 {len(track_points)} 个点")
        except Exception as e:
            print(f"[遥测坐标 fallback 失败] {e}")

    # 获取赛道名
    try:
        circuit_name = str(session.event["EventName"]) if hasattr(session, "event") else ""
    except Exception:
        pass

    # 获取分段最快数据（复用 sector-fastest 逻辑）
    sector_data = fetch_fastf1_sector_fastest(year, round_num, session_type)

    sectors = []
    overall_fastest = sector_data.get("overall_fastest_driver") if sector_data.get("code") == 200 else None

    if sector_data.get("code") == 200:
        for s in sector_data.get("sectors", []):
            fastest_driver = s.get("fastest_driver")
            color = "purple" if fastest_driver == overall_fastest else "green"
            sectors.append({
                "sector": s["sector"],
                "fastest_driver": fastest_driver,
                "fastest_time": s.get("fastest_time"),
                "fastest_time_str": s.get("fastest_time_str"),
                "color": color,
            })

    if not track_points and not sectors:
        return {"code": 500, "msg": f"无法获取 {year} 第{round_num}站 赛道地图数据"}

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "circuit_name": circuit_name,
        "track_points": track_points,
        "sectors": sectors,
        "overall_fastest_driver": overall_fastest,
    }
    _save_fastf1_result(cache_key, result)
    return result


# ============================================================
# 模块 B6：天气数据（Weather）
# ============================================================
def fetch_fastf1_weather(year: int, round_num: int, session_type: str = "R"):
    """
    B6：比赛天气数据（Rainfall / AirTemp / TrackTemp / Humidity / Pressure）。

    使用 FastF1 的 session.weather_data 获取逐帧天气信息，
    用于天气叠加分析（轮胎策略 vs 天气变化）。

    返回结构：
        {
          "code": 200,
          "year": 2025, "round": 1,
          "session": "R",
          "weather_summary": {
            "avg_air_temp": 22.5,
            "avg_track_temp": 35.2,
            "max_rainfall": 0.0,
            "avg_humidity": 55.0,
            "is_wet": false
          },
          "weather_timeline": [
            {"time": "14:00:00", "air_temp": 22.0, "track_temp": 35.0, "rainfall": 0.0, "humidity": 55.0},
            ...
          ]
        }

    踩坑：
        - weather_data 需要 session.load(weather=True) 才能获取
        - 天气数据仅 2018+ 可用
        - 某些分站可能没有天气数据（返回空数组）
    """
    cache_key = f"weather_{year}_{round_num}_{session_type}"
    cached = _load_fastf1_result(cache_key)
    if cached is not None:
        return cached

    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=False, telemetry=False, weather=True, messages=False)
    except Exception as e:
        return {"code": 500, "msg": f"FastF1 加载失败: {e}"}

    weather_data = getattr(session, "weather_data", None)
    if weather_data is None or len(weather_data) == 0:
        return {"code": 500, "msg": f"暂无 {year} 第{round_num}站 天气数据（仅 2018+ 可用）"}

    df = weather_data.copy()

    # 时间线数据（降采样到 ~50 个点）
    step = max(1, len(df) // 50)
    sampled = df.iloc[::step].reset_index(drop=True)

    timeline = []
    for _, row in sampled.iterrows():
        entry = {}
        # 时间
        if "Time" in row.index:
            t = row["Time"]
            if hasattr(t, "total_seconds"):
                total_sec = int(t.total_seconds())
                entry["time"] = f"{total_sec // 3600:02d}:{(total_sec % 3600) // 60:02d}:{total_sec % 60:02d}"
            else:
                entry["time"] = str(t)

        for col in ["AirTemp", "TrackTemp", "Rainfall", "Humidity", "Pressure", "WindSpeed", "WindDirection"]:
            if col in row.index:
                val = row[col]
                if val is not None and not pd.isna(val):
                    entry[col.lower()] = round(float(val), 2)
                else:
                    entry[col.lower()] = None
        timeline.append(entry)

    # 汇总统计
    summary = {}
    for col, key in [("AirTemp", "avg_air_temp"), ("TrackTemp", "avg_track_temp"),
                     ("Humidity", "avg_humidity"), ("Pressure", "avg_pressure")]:
        if col in df.columns:
            vals = df[col].dropna()
            summary[key] = round(float(vals.mean()), 1) if len(vals) > 0 else None

    if "Rainfall" in df.columns:
        rainfall = df["Rainfall"].dropna()
        summary["max_rainfall"] = round(float(rainfall.max()), 2) if len(rainfall) > 0 else 0.0
        summary["is_wet"] = bool(rainfall.max() > 0) if len(rainfall) > 0 else False

    result = {
        "code": 200,
        "year": year,
        "round": round_num,
        "session": session_type,
        "weather_summary": summary,
        "weather_timeline": timeline,
    }
    _save_fastf1_result(cache_key, result)
    return result
