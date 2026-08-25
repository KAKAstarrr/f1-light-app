# -*- coding: utf-8 -*-
"""
prediction_service.py — AI 预测推理服务

职责：
    基于历史数据和当前状态，输出每位车手的夺冠概率分布。

模型版本：
    - xgb_v2：XGBoost 二分类模型（24 特征，含天气/环境维度），离线训练，在线推理
    - xgb_v1：XGBoost 二分类模型（19 特征），历史版本
    - rule_v1：规则加权模型（5 特征），作为 fallback

推理流程：
    1. 尝试加载 XGBoost 模型 (ml/models/xgb_v2.json)
    2. 从 Ergast API 获取实时数据（积分榜、排位赛、赛季结果）
    3. 从缓存 CSV 获取历史数据（赛道特定特征、跨赛季近 5 场）
    4. 从 FastF1 获取该站正赛天气（干/湿、气温、降雨、湿度）
    5. 构建 24 特征向量 → model.predict_proba() → softmax 归一化
    6. 如果任何步骤失败，降级到 rule_v1

SHAP 解释：
    如果 shap 库已安装，用 TreeExplainer 计算每位车手 top-3 特征贡献。
    未安装时跳过，不影响预测。
"""
import json
import requests
from pathlib import Path
from typing import Optional

ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"

# ── 路径常量 ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "models" / "xgb_v2.json"
MODEL_PATH_V1 = BASE_DIR / "ml" / "models" / "xgb_v1.json"  # 过渡期回退：v2 未重训时用 v1
FEATURE_COLS_PATH = BASE_DIR / "ml" / "data" / "feature_columns.json"
HISTORY_CSV = BASE_DIR / "ml" / "data" / "races_2018_2025.csv"
EVAL_REPORT_PATH = BASE_DIR / "ml" / "models" / "eval_report.json"

# ── 天气特征列（PRD 3.4.2 环境维度，场次级特征）──
WEATHER_FEATURE_COLS = [
    "weather_is_wet",
    "weather_air_temp",
    "weather_track_temp",
    "weather_max_rainfall",
    "weather_humidity",
]

# 天气缺失时的中性填充值（与训练侧 build_weather_dataset 一致）
WEATHER_NEUTRAL = {
    "weather_is_wet": 0.0,
    "weather_air_temp": 20.0,
    "weather_track_temp": 30.0,
    "weather_max_rainfall": 0.0,
    "weather_humidity": 60.0,
}

# ── 懒加载单例 ────────────────────────────────────────
_xgb_model = None
_feature_cols = None
_history_df = None
_shap_explainer = None
_feature_importance = None


# ═══════════════════════════════════════════════════════
# 模型 / 数据加载（懒加载）
# ═══════════════════════════════════════════════════════

def _get_xgb_model():
    """加载 XGBoost 模型。优先 xgb_v2（24 特征），重训前回退 xgb_v1（19 特征）。失败返回 None。"""
    global _xgb_model
    if _xgb_model is None:
        try:
            import xgboost as xgb
            path = (
                MODEL_PATH if MODEL_PATH.exists()
                else (MODEL_PATH_V1 if MODEL_PATH_V1.exists() else None)
            )
            if path is None:
                return None
            _xgb_model = xgb.XGBClassifier()
            _xgb_model.load_model(str(path))
            print(f"[prediction] XGBoost 模型加载成功: {path.name}")
        except Exception as e:
            print(f"[prediction] XGBoost 模型加载失败: {e}")
            return None
    return _xgb_model


def _get_feature_cols():
    """加载特征列名列表。失败返回 None。"""
    global _feature_cols
    if _feature_cols is None:
        try:
            if not FEATURE_COLS_PATH.exists():
                return None
            with open(FEATURE_COLS_PATH, encoding="utf-8") as f:
                _feature_cols = json.load(f)["feature_columns"]
        except Exception as e:
            print(f"[prediction] 特征列名加载失败: {e}")
            return None
    return _feature_cols


def _get_history_df():
    """加载历史数据 CSV。失败返回 None。"""
    global _history_df
    if _history_df is None:
        try:
            if not HISTORY_CSV.exists():
                return None
            import pandas as pd
            _history_df = pd.read_csv(HISTORY_CSV)
            _history_df["race_date"] = pd.to_datetime(_history_df["race_date"])
            print(f"[prediction] 历史 CSV 加载: {len(_history_df)} 行")
        except Exception as e:
            print(f"[prediction] 历史 CSV 加载失败: {e}")
            return None
    return _history_df


def _get_feature_importance():
    """加载特征重要性 top-5。"""
    global _feature_importance
    if _feature_importance is None:
        try:
            if not EVAL_REPORT_PATH.exists():
                return []
            with open(EVAL_REPORT_PATH, encoding="utf-8") as f:
                report = json.load(f)
            _feature_importance = report.get("feature_importance_top10", [])[:5]
        except Exception:
            return []
    return _feature_importance


def _get_shap_explainer():
    """加载 SHAP TreeExplainer。失败返回 None。"""
    global _shap_explainer
    if _shap_explainer is None:
        try:
            import shap
            model = _get_xgb_model()
            if model is None:
                return None
            _shap_explainer = shap.TreeExplainer(model)
            print("[prediction] SHAP Explainer 加载成功")
        except Exception as e:
            print(f"[prediction] SHAP 加载失败（不影响预测）: {e}")
            return None
    return _shap_explainer


# ═══════════════════════════════════════════════════════
# Ergast API 数据获取
# ═══════════════════════════════════════════════════════

def _ergast_get(url: str, timeout: int = 8) -> dict:
    """简单 Ergast GET 封装，带异常兜底。"""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("MRData", {})
    except Exception as e:
        print(f"[Ergast 请求失败] {url}: {e}")
        return {}


def _fetch_driver_standings(year: int) -> list:
    """获取车手积分榜。返回 [{code, name, points, wins, position, constructor}, ...]"""
    data = _ergast_get(f"{ERGAST_BASE}/{year}/driverstandings.json")
    sl = data.get("StandingsTable", {}).get("StandingsLists", [])
    if not sl:
        return []
    drivers = sl[0].get("DriverStandings", [])
    result = []
    for d in drivers:
        code = d.get("Driver", {}).get("code", "")
        if not code:
            continue
        result.append({
            "code": code,
            "name": f"{d.get('Driver', {}).get('givenName', '')} {d.get('Driver', {}).get('familyName', '')}",
            "points": float(d.get("points", 0)),
            "wins": int(d.get("wins", 0)),
            "position": int(d.get("position", 99)),
            "constructor": d.get("Constructors", [{}])[0].get("name", "Unknown"),
        })
    return result


def _fetch_qualifying(year: int, round_num: int) -> dict:
    """获取指定分站排位赛结果。返回 {code: qualifying_position}"""
    data = _ergast_get(f"{ERGAST_BASE}/{year}/{round_num}/qualifying.json")
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return {}
    qual_results = races[0].get("QualifyingResults", [])
    mapping = {}
    for q in qual_results:
        code = q.get("Driver", {}).get("code", "")
        if code:
            mapping[code] = int(q.get("position", 99))
    return mapping


def _fetch_schedule(year: int) -> dict:
    """获取赛季赛程。返回 {total_rounds, circuits: {round: {circuit_id, circuit_name}}}"""
    data = _ergast_get(f"{ERGAST_BASE}/{year}.json", timeout=12)
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return {"total_rounds": 24, "circuits": {}}
    total_rounds = len(races)
    circuits = {}
    for race in races:
        r = int(race.get("round", 0))
        circuits[r] = {
            "circuit_id": race.get("Circuit", {}).get("circuitId", ""),
            "circuit_name": race.get("Circuit", {}).get("circuitName", ""),
        }
    return {"total_rounds": total_rounds, "circuits": circuits}


def _is_dnf(position: int, status: str) -> bool:
    """DNF 判定（与 collect_training_data.py 完全一致）"""
    if position == 0:
        return True
    keywords = ["Retired", "Engine", "Gearbox", "Collision", "Accident",
                "Transmission", "Hydraulic", "Electrical", "Brakes"]
    return any(kw in status for kw in keywords)


def _fetch_all_season_results(year: int) -> list:
    """获取赛季所有已完成比赛结果（一次 API 调用）。

    返回 [{round, code, position, grid, status, points, constructor, is_dnf, is_win}, ...]
    """
    data = _ergast_get(f"{ERGAST_BASE}/{year}/results.json?limit=1000", timeout=15)
    races = data.get("RaceTable", {}).get("Races", [])
    all_results = []
    for race in races:
        rnd = int(race.get("round", 0))
        results = race.get("Results", [])
        for res in results:
            code = res.get("Driver", {}).get("code", "")
            if not code:
                continue
            position = int(res.get("position", 0))
            status = res.get("status", "")
            all_results.append({
                "round": rnd,
                "code": code,
                "position": position,
                "grid": int(res.get("grid", 0)),
                "status": status,
                "points": float(res.get("points", 0)),
                "constructor": res.get("Constructor", {}).get("name", "Unknown"),
                "is_dnf": 1 if _is_dnf(position, status) else 0,
                "is_win": 1 if position == 1 else 0,
            })
    return all_results


def _fetch_recent_results(year: int, round_num: int, count: int = 5) -> list:
    """获取最近 count 场比赛结果（rule_v1 用）。"""
    results = []
    for r in range(max(1, round_num - count), round_num):
        data = _ergast_get(f"{ERGAST_BASE}/{year}/{r}/results.json")
        races = data.get("RaceTable", {}).get("Races", [])
        if races:
            race_results = races[0].get("Results", [])
            parsed = []
            for res in race_results:
                code = res.get("Driver", {}).get("code", "")
                parsed.append({
                    "code": code,
                    "position": int(res.get("position", 0)),
                    "grid": int(res.get("grid", 0)),
                    "status": res.get("status", ""),
                })
            results.append({"round": r, "results": parsed})
    return results


# ═══════════════════════════════════════════════════════
# rule_v1 规则加权模型（fallback）
# ═══════════════════════════════════════════════════════

def _calculate_features(
    standings: list,
    recent: list,
    qualifying: dict,
    total_rounds: int,
) -> list:
    """为每位车手计算 5 特征向量（rule_v1）。"""
    if not standings:
        return []

    max_points = max(d["points"] for d in standings) or 1

    features = []
    for driver in standings:
        code = driver["code"]
        championship_ratio = driver["points"] / max_points if max_points > 0 else 0

        positions = []
        dnf_count = 0
        for race in recent:
            for r in race["results"]:
                if r["code"] == code:
                    pos = r["position"]
                    if pos > 0:
                        positions.append(pos)
                    if _is_dnf(pos, r["status"]):
                        dnf_count += 1
                    break

        recent_avg_pos = sum(positions) / len(positions) if positions else 20
        dnf_rate = dnf_count / len(recent) if recent else 0
        qual_pos = qualifying.get(code, 20)
        win_rate = driver["wins"] / max(total_rounds, 1)

        features.append({
            "code": code,
            "name": driver["name"],
            "constructor": driver["constructor"],
            "features": {
                "championship_ratio": round(championship_ratio, 4),
                "recent_avg_pos": round(recent_avg_pos, 2),
                "qualifying_pos": qual_pos,
                "win_rate": round(win_rate, 4),
                "dnf_rate": round(dnf_rate, 4),
            },
        })
    return features


def _weighted_score(features: dict) -> float:
    """规则加权打分（rule_v1）。"""
    fr = features["features"]
    champ_score = fr["championship_ratio"]
    recent_score = max(0, 1 - (fr["recent_avg_pos"] - 1) / 19)
    qual_score = max(0, 1 - (fr["qualifying_pos"] - 1) / 19)
    win_score = min(1.0, fr["win_rate"] * 5)
    dnf_score = 1 - fr["dnf_rate"]

    return (
        champ_score * 0.35
        + recent_score * 0.25
        + qual_score * 0.15
        + win_score * 0.15
        + dnf_score * 0.10
    )


def _predict_with_rule_v1(
    year: int, round_num: int, standings: list, recent: list, qualifying: dict
) -> dict:
    """规则加权模型完整预测流程。"""
    features_list = _calculate_features(standings, recent, qualifying, round_num - 1)

    scored = []
    for f in features_list:
        raw = _weighted_score(f)
        scored.append({
            "driver_code": f["code"],
            "driver_name": f["name"],
            "constructor": f["constructor"],
            "features": f["features"],
            "raw_score": round(raw, 4),
        })

    total_raw = sum(s["raw_score"] for s in scored)
    if total_raw == 0:
        for s in scored:
            s["probability"] = round(1.0 / len(scored), 4)
    else:
        for s in scored:
            s["probability"] = round(s["raw_score"] / total_raw, 4)

    scored.sort(key=lambda x: x["probability"], reverse=True)
    for i, s in enumerate(scored, 1):
        s["rank_pred"] = i

    top3 = [s["driver_code"] for s in scored[:3]]

    return {
        "code": 200,
        "season": year,
        "round": round_num,
        "model_version": "rule_v1",
        "feature_count": 5,
        "feature_weights": {
            "championship_ratio": 0.35,
            "recent_avg_pos": 0.25,
            "qualifying_pos": 0.15,
            "win_rate": 0.15,
            "dnf_rate": 0.10,
        },
        "predictions": scored,
        "top3": top3,
    }


# ═══════════════════════════════════════════════════════
# XGBoost 在线推理
# ═══════════════════════════════════════════════════════

def _fetch_weather_features(year: int, round_num: int) -> Optional[dict]:
    """拉取该站正赛天气汇总并转成特征 dict。

    复用 data_source.fetch_fastf1_weather（FastF1 weather_data，仅 2018+）。
    失败/数据缺失时返回 None，由 _build_xgb_features 用中性值兜底（不阻塞预测）。

    返回形如：
        {
            "weather_is_wet": 1.0,
            "weather_air_temp": 18.5,
            "weather_track_temp": 31.2,
            "weather_max_rainfall": 2.4,
            "weather_humidity": 78.0,
        }
    """
    try:
        # 兼容两种启动方式：uvicorn（cwd=项目根，backend 为包）与 cd backend 直跑
        try:
            from backend.data_source import fetch_fastf1_weather
        except ImportError:
            from data_source import fetch_fastf1_weather
        res = fetch_fastf1_weather(year, round_num, "R")
        if res.get("code") != 200:
            return None
        s = res.get("weather_summary") or {}
        # 完全无数据（weather_timeline 空或 summary 全空）→ 视为缺失
        if not s or ("avg_air_temp" not in s and "is_wet" not in s):
            return None
        return {
            "weather_is_wet": float(1 if s.get("is_wet") else 0),
            "weather_air_temp": float(s.get("avg_air_temp") if s.get("avg_air_temp") is not None else 20.0),
            "weather_track_temp": float(s.get("avg_track_temp") if s.get("avg_track_temp") is not None else 30.0),
            "weather_max_rainfall": float(s.get("max_rainfall") if s.get("max_rainfall") is not None else 0.0),
            "weather_humidity": float(s.get("avg_humidity") if s.get("avg_humidity") is not None else 60.0),
        }
    except Exception as e:
        print(f"[prediction] 天气特征获取失败（使用中性值兜底）: {e}")
        return None


def _build_xgb_features(
    year: int,
    round_num: int,
    standings: list,
    qualifying: dict,
    season_results: list,
    schedule_info: dict,
    history_df,
    weather_features: Optional[dict] = None,
) -> list:
    """为每位车手构建 24 特征向量（与训练特征完全对齐）。

    核心原则：每行特征只用该轮次【之前】的数据，严禁泄漏。
    weather_features 为场次级特征（同场所有车手相同），缺失时中性值兜底。
    """
    feature_cols = _get_feature_cols()
    if not feature_cols:
        return []

    total_rounds = schedule_info.get("total_rounds", 24)
    circuit_info = schedule_info.get("circuits", {}).get(round_num, {})
    circuit_id = circuit_info.get("circuit_id", "")

    # 本赛季结果按轮次分组
    results_by_round = {}
    for r in season_results:
        rnd = r["round"]
        if rnd >= round_num:
            continue  # 只取当前轮次之前的
        if rnd not in results_by_round:
            results_by_round[rnd] = {}
        results_by_round[rnd][r["code"]] = r

    completed_rounds = sorted(results_by_round.keys())

    all_features = []

    for driver in standings:
        code = driver["code"]

        # 排位赛位次（如果没有排位赛数据，跳过该车手）
        qual_pos = qualifying.get(code)
        if qual_pos is None or qual_pos == 0:
            continue

        grid = qual_pos  # 赛前 grid ≈ qualifying（罚退信息不可得）

        # ── 基线特征 (4 个) ──
        qualifying_pos = qual_pos
        qualifying_pos_inv = 21 - qual_pos
        grid_inv = 21 - grid

        # ── 赛季累计特征 (5 个，截至当前轮次之前) ──
        driver_points = driver["points"]  # 积分榜本身就是截至上一轮的累计
        driver_wins = driver["wins"]

        driver_races = 0
        driver_dnfs = 0
        driver_positions = []
        for rnd in completed_rounds:
            r = results_by_round[rnd].get(code)
            if r:
                driver_races += 1
                if r["is_dnf"]:
                    driver_dnfs += 1
                if r["position"] > 0:
                    driver_positions.append(r["position"])

        driver_avg_pos = (
            sum(driver_positions) / len(driver_positions)
            if driver_positions
            else None
        )

        # ── 近 5 场特征 (2 个，跨赛季) ──
        driver_last5_avg_pos = None
        driver_last5_dnfs = None

        if history_df is not None:
            driver_hist = history_df[
                history_df["driver_code"] == code
            ].sort_values("race_date")
            last5 = driver_hist.tail(5)
            if len(last5) > 0:
                finished = last5[last5["finishing_pos"] > 0]
                driver_last5_avg_pos = (
                    float(finished["finishing_pos"].mean())
                    if len(finished) > 0
                    else None
                )
                driver_last5_dnfs = int(last5["is_dnf"].sum())

        # CSV 没数据时用本赛季数据兜底
        if driver_last5_avg_pos is None and driver_positions:
            recent_5 = driver_positions[-5:]
            driver_last5_avg_pos = sum(recent_5) / len(recent_5)
        if driver_last5_dnfs is None:
            driver_last5_dnfs = driver_dnfs

        # ── 赛道特定特征 (3 个，历史同赛道) ──
        driver_circuit_avg_pos = None
        driver_circuit_races = 0
        driver_circuit_dnfs = 0

        if history_df is not None and circuit_id:
            circuit_hist = history_df[
                (history_df["driver_code"] == code)
                & (history_df["circuit_id"] == circuit_id)
            ].sort_values("race_date")
            if len(circuit_hist) > 0:
                finished = circuit_hist[circuit_hist["finishing_pos"] > 0]
                driver_circuit_avg_pos = (
                    float(finished["finishing_pos"].mean())
                    if len(finished) > 0
                    else None
                )
                driver_circuit_races = len(circuit_hist)
                driver_circuit_dnfs = int(circuit_hist["is_dnf"].sum())

        # ── 车队特征 (3 个) ──
        constructor_name = driver["constructor"]
        constructor_points = 0
        constructor_positions = []
        constructor_dnfs = 0

        for rnd in completed_rounds:
            for _code, r_data in results_by_round[rnd].items():
                if r_data["constructor"] == constructor_name:
                    constructor_points += r_data["points"]
                    if r_data["is_dnf"]:
                        constructor_dnfs += 1
                    if r_data["position"] > 0:
                        constructor_positions.append(r_data["position"])

        constructor_avg_pos = (
            sum(constructor_positions) / len(constructor_positions)
            if constructor_positions
            else None
        )

        # ── 上下文特征 (2 个) ──
        regulation_era = 1 if year >= 2022 else 0
        round_normalized = round(round_num / total_rounds, 4) if total_rounds > 0 else 0

        # ── 环境/天气特征 (5 个，场次级，全部车手相同) ──
        wf = weather_features or {}

        # 组装特征字典
        features = {
            "qualifying_pos": float(qualifying_pos),
            "grid": float(grid),
            "qualifying_pos_inv": float(qualifying_pos_inv),
            "grid_inv": float(grid_inv),
            "driver_season_points_before": float(driver_points),
            "driver_season_races_before": float(driver_races),
            "driver_season_wins_before": float(driver_wins),
            "driver_season_dnfs_before": float(driver_dnfs),
            "driver_season_avg_pos_before": driver_avg_pos,
            "driver_last5_avg_pos": driver_last5_avg_pos,
            "driver_last5_dnfs": float(driver_last5_dnfs),
            "driver_circuit_avg_pos": driver_circuit_avg_pos,
            "driver_circuit_races": float(driver_circuit_races),
            "driver_circuit_dnfs": float(driver_circuit_dnfs),
            "constructor_season_points_before": float(constructor_points),
            "constructor_season_avg_pos_before": constructor_avg_pos,
            "constructor_season_dnfs_before": float(constructor_dnfs),
            "regulation_era": float(regulation_era),
            "round_normalized": float(round_normalized),
            "weather_is_wet": wf.get("weather_is_wet", WEATHER_NEUTRAL["weather_is_wet"]),
            "weather_air_temp": wf.get("weather_air_temp", WEATHER_NEUTRAL["weather_air_temp"]),
            "weather_track_temp": wf.get("weather_track_temp", WEATHER_NEUTRAL["weather_track_temp"]),
            "weather_max_rainfall": wf.get("weather_max_rainfall", WEATHER_NEUTRAL["weather_max_rainfall"]),
            "weather_humidity": wf.get("weather_humidity", WEATHER_NEUTRAL["weather_humidity"]),
        }

        all_features.append({
            "code": code,
            "name": driver["name"],
            "constructor": constructor_name,
            "features": features,
        })

    if not all_features:
        return []

    # ── NaN 填充（与 feature_engineering.py 策略一致）──
    # 计数类特征 → 填 0
    for item in all_features:
        for col in ["driver_season_races_before", "driver_circuit_races"]:
            if item["features"][col] is None:
                item["features"][col] = 0.0

    # DNF 计数类 → 填 0
    for item in all_features:
        for col in ["driver_season_dnfs_before", "driver_last5_dnfs",
                     "driver_circuit_dnfs", "constructor_season_dnfs_before"]:
            if item["features"][col] is None:
                item["features"][col] = 0.0

    # 平均值类 → 填中位数
    for col in ["driver_season_avg_pos_before", "driver_last5_avg_pos",
                "driver_circuit_avg_pos", "constructor_season_avg_pos_before"]:
        values = [
            item["features"][col]
            for item in all_features
            if item["features"][col] is not None
        ]
        median_val = sum(values) / len(values) if values else 15.0
        for item in all_features:
            if item["features"][col] is None:
                item["features"][col] = round(median_val, 2)

    # 确保所有值都是 float
    for item in all_features:
        for col in feature_cols:
            val = item["features"][col]
            if val is None:
                item["features"][col] = 0.0
            item["features"][col] = float(val)

    return all_features


def _predict_with_xgb(features_list: list) -> tuple:
    """XGBoost 模型预测 + SHAP 解释。

    返回 (probabilities_array, shap_values_list_or_none)
    """
    import numpy as np

    model = _get_xgb_model()
    feature_cols = _get_feature_cols()
    if not model or not feature_cols:
        return None, None

    # 构建特征矩阵
    X = np.array([
        [item["features"][col] for col in feature_cols]
        for item in features_list
    ])

    # predict_proba 返回 [P(class=0), P(class=1)]，取 class=1
    proba = model.predict_proba(X)[:, 1]

    # softmax 归一化：每场比赛所有车手概率之和 = 1
    total = proba.sum()
    if total > 0:
        probabilities = proba / total
    else:
        probabilities = np.ones(len(proba)) / len(proba)

    # SHAP 特征解释
    shap_values_list = None
    explainer = _get_shap_explainer()
    if explainer is not None:
        try:
            shap_vals = explainer.shap_values(X)
            # shap_vals shape: (n_samples, n_features)
            shap_values_list = []
            for i in range(len(features_list)):
                contributions = list(zip(feature_cols, shap_vals[i]))
                # 按 |SHAP 值| 降序，取 top-3
                contributions.sort(key=lambda x: abs(x[1]), reverse=True)
                top3 = [
                    {"feature": f, "contribution": round(float(v), 4)}
                    for f, v in contributions[:3]
                ]
                shap_values_list.append(top3)
        except Exception as e:
            print(f"[prediction] SHAP 计算失败: {e}")
            shap_values_list = None

    return probabilities, shap_values_list


# ═══════════════════════════════════════════════════════
# 主入口：predict_race
# ═══════════════════════════════════════════════════════

def predict_race(year: int, round_num: int) -> dict:
    """预测指定分站的夺冠概率分布。

    优先使用 XGBoost (xgb_v2，24 特征含天气)，失败时降级到规则加权 (rule_v1)。

    参数：
        year: 赛季年份
        round_num: 分站序号

    返回：
        {
            "code": 200,
            "season": 2025,
            "round": 5,
            "model_version": "xgb_v2" | "xgb_v1" | "rule_v1" | "rule_v1_fallback",
            "feature_count": 24 | 19 | 5,
            "feature_importance": [...],   # XGBoost only
            "predictions": [
                {
                    "driver_code": "VER",
                    "driver_name": "Max Verstappen",
                    "constructor": "Red Bull",
                    "probability": 0.35,
                    "rank_pred": 1,
                    "features": {...24 个特征，含 weather_*},
                    "model_proba": 0.82,     # XGBoost only
                    "shap_top3": [...]        # XGBoost only
                }, ...
            ],
            "top3": ["VER", "NOR", "LEC"],
        }

    异常返回 {"code": 500, "msg": "..."}
    """
    try:
        # 1. 获取积分榜（两个模型都需要）
        standings = _fetch_driver_standings(year)
        if not standings:
            return {"code": 500, "msg": f"无法获取 {year} 赛季车手积分榜"}

        # 2. 尝试 XGBoost 推理
        model = _get_xgb_model()
        feature_cols = _get_feature_cols()

        if model and feature_cols:
            try:
                qualifying = _fetch_qualifying(year, round_num)
                if not qualifying:
                    raise ValueError("排位赛数据不可用，无法构建 XGBoost 特征")

                schedule_info = _fetch_schedule(year)
                season_results = _fetch_all_season_results(year)
                history_df = _get_history_df()

                # 环境/天气特征（场次级，缺失时内部中性值兜底）
                weather_features = _fetch_weather_features(year, round_num)

                features_list = _build_xgb_features(
                    year, round_num, standings, qualifying,
                    season_results, schedule_info, history_df,
                    weather_features,
                )

                if not features_list:
                    raise ValueError("特征构建失败（可能所有车手都缺排位赛数据）")

                probabilities, shap_values_list = _predict_with_xgb(features_list)

                if probabilities is None:
                    raise ValueError("XGBoost predict_proba 返回 None")

                # 构建结果
                scored = []
                for i, f in enumerate(features_list):
                    entry = {
                        "driver_code": f["code"],
                        "driver_name": f["name"],
                        "constructor": f["constructor"],
                        "features": {
                            k: round(v, 4) if isinstance(v, float) else v
                            for k, v in f["features"].items()
                        },
                        "model_proba": round(float(probabilities[i]), 6),
                        "probability": round(float(probabilities[i]), 4),
                    }
                    if shap_values_list and shap_values_list[i]:
                        entry["shap_top3"] = shap_values_list[i]
                    scored.append(entry)

                scored.sort(key=lambda x: x["probability"], reverse=True)
                for i, s in enumerate(scored, 1):
                    s["rank_pred"] = i

                top3 = [s["driver_code"] for s in scored[:3]]

                result = {
                    "code": 200,
                    "season": year,
                    "round": round_num,
                    "model_version": "xgb_v2" if len(feature_cols) >= 24 else "xgb_v1",
                    "feature_count": len(feature_cols),
                    "feature_importance": _get_feature_importance(),
                    "predictions": scored,
                    "top3": top3,
                    "weather": weather_features,
                }
                print(f"[prediction] XGBoost 推理成功: {len(scored)} 位车手, top3={top3}")
                return result

            except Exception as e:
                print(f"[prediction] XGBoost 推理失败，降级到 rule_v1: {e}")

        # 3. Fallback: rule_v1
        recent = _fetch_recent_results(year, round_num, count=5)
        qualifying = _fetch_qualifying(year, round_num)
        result = _predict_with_rule_v1(year, round_num, standings, recent, qualifying)

        # 标记为 fallback（如果 XGBoost 模型存在但推理失败）
        if model and feature_cols:
            result["model_version"] = "rule_v1_fallback"
            result["fallback_reason"] = "XGBoost 推理失败，使用规则模型兜底"

        print(f"[prediction] rule_v1 预测: {len(result['predictions'])} 位车手")
        return result

    except Exception as e:
        return {"code": 500, "msg": f"预测服务异常: {e}"}
