# -*- coding: utf-8 -*-
"""
prediction_service.py — AI 预测推理服务

职责：
    基于历史数据和当前状态，输出每位车手的夺冠概率分布。

实现说明：
    本模块当前使用「规则加权模型」（rule-based），不依赖 XGBoost。
    原因：训练 XGBoost 需要先采集 2018-2025 全部历史数据 + 特征工程 Notebook，
    这属于阶段 3B 的离线训练工作。在线推理先用规则模型跑通端到端流程，
    后续训练完模型后，只需替换 predict_race() 的实现即可无缝切换。

    规则模型的特征维度与 XGBoost 版本保持一致（PRD 3.4.2），只是用手工权重
    代替 GBDT 自动学习权重。

特征权重（手工调优）：
    - 赛季积分占比（championship momentum）：35%
    - 近5场平均完赛位次（recent form）：25%
    - 排位赛平均位次（qualifying strength）：15%
    - 历史胜率（career win rate）：15%
    - 近期 DNF 率（reliability penalty）：10%
"""
import json
import requests
from typing import Optional

ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"


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
    """获取车手积分榜。返回 [{code, points, wins, position, constructor}, ...]"""
    data = _ergast_get(f"{ERGAST_BASE}/{year}/driverstandings.json")
    sl = data.get("StandingsTable", {}).get("StandingsLists", [])
    if not sl:
        return []
    drivers = sl[0].get("DriverStandings", [])
    result = []
    for d in drivers:
        code = d.get("Driver", {}).get("code", "")
        result.append({
            "code": code,
            "name": f"{d.get('Driver', {}).get('givenName', '')} {d.get('Driver', {}).get('familyName', '')}",
            "points": float(d.get("points", 0)),
            "wins": int(d.get("wins", 0)),
            "position": int(d.get("position", 99)),
            "constructor": d.get("Constructors", [{}])[0].get("name", "Unknown"),
        })
    return result


def _fetch_recent_results(year: int, round_num: int, count: int = 5) -> list:
    """获取最近 count 场比赛结果。返回 [{race_round, results: [{code, position, grid, status}]}, ...]"""
    # 从 round-1 往前取 count 场
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


def _fetch_qualifying(year: int, round_num: int) -> dict:
    """获取指定分站排位赛结果。返回 {code: grid_position}"""
    data = _ergast_get(f"{ERGAST_BASE}/{year}/{round_num}/qualifying.json")
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return {}
    qual_results = races[0].get("QualifyingResults", [])
    mapping = {}
    for q in qual_results:
        code = q.get("Driver", {}).get("code", "")
        mapping[code] = int(q.get("position", 99))
    return mapping


def _calculate_features(
    standings: list,
    recent: list,
    qualifying: dict,
    total_rounds: int
) -> list:
    """为每位车手计算特征向量。

    返回 [{code, name, features: {championship_ratio, recent_avg_pos,
            qualifying_pos, win_rate, dnf_rate, constructor}}, ...]
    """
    if not standings:
        return []

    max_points = max(d["points"] for d in standings) or 1

    features = []
    for driver in standings:
        code = driver["code"]

        # 1. 赛季积分占比（0-1）
        championship_ratio = driver["points"] / max_points if max_points > 0 else 0

        # 2. 近5场平均完赛位次
        positions = []
        dnf_count = 0
        for race in recent:
            for r in race["results"]:
                if r["code"] == code:
                    pos = r["position"]
                    if pos > 0:
                        positions.append(pos)
                    if "Retired" in r["status"] or pos == 0:
                        dnf_count += 1
                    break

        recent_avg_pos = sum(positions) / len(positions) if positions else 20
        dnf_rate = dnf_count / len(recent) if recent else 0

        # 3. 排位赛位次
        qual_pos = qualifying.get(code, 20)

        # 4. 历史胜率（本赛季）
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
            }
        })

    return features


def _weighted_score(features: dict) -> float:
    """计算加权得分，输出原始分数（未归一化）。

    权重设计：
        - championship_ratio: 35%（赛季状态最强信号）
        - recent_avg_pos: 25%（近期手感）
        - qualifying_pos: 15%（发车位置影响大）
        - win_rate: 15%（历史统治力）
        - dnf_rate: 10%（可靠性扣分）
    """
    fr = features["features"]

    # 积分占比：0-1 → 直接加权
    champ_score = fr["championship_ratio"]  # 0-1

    # 近期平均位次：1=最好 → 转成 0-1（越低越好）
    recent_score = max(0, 1 - (fr["recent_avg_pos"] - 1) / 19)  # pos=1→1.0, pos=20→0.05

    # 排位位次：同上
    qual_score = max(0, 1 - (fr["qualifying_pos"] - 1) / 19)

    # 胜率：直接 0-1
    win_score = min(1.0, fr["win_rate"] * 5)  # 胜率放大，2场胜利=1.0

    # DNF 率：0=好 → 扣分
    dnf_score = 1 - fr["dnf_rate"]  # 0次DNF=1.0

    raw = (
        champ_score * 0.35
        + recent_score * 0.25
        + qual_score * 0.15
        + win_score * 0.15
        + dnf_score * 0.10
    )
    return raw


def predict_race(year: int, round_num: int) -> dict:
    """预测指定分站的夺冠概率分布。

    参数：
        year: 赛季年份
        round_num: 分站序号

    返回：
        {
            "code": 200,
            "season": 2025,
            "round": 5,
            "model_version": "rule_v1",
            "predictions": [
                {
                    "driver_code": "VER",
                    "driver_name": "Max Verstappen",
                    "constructor": "Red Bull",
                    "probability": 0.35,
                    "rank_pred": 1,
                    "features": {...},
                    "raw_score": 0.82
                }, ...
            ],
            "top3": ["VER", "NOR", "LEC"],
        }

    异常返回 {"code": 500, "msg": "..."}
    """
    try:
        # 1. 获取数据
        standings = _fetch_driver_standings(year)
        if not standings:
            return {"code": 500, "msg": f"无法获取 {year} 赛季车手积分榜"}

        recent = _fetch_recent_results(year, round_num, count=5)
        qualifying = _fetch_qualifying(year, round_num)

        # 2. 计算特征
        features_list = _calculate_features(standings, recent, qualifying, round_num - 1)

        # 3. 加权打分
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

        # 4. 归一化为概率（softmax 变体）
        total_raw = sum(s["raw_score"] for s in scored)
        if total_raw == 0:
            # 所有分数为 0，均分
            for s in scored:
                s["probability"] = round(1.0 / len(scored), 4)
        else:
            for s in scored:
                s["probability"] = round(s["raw_score"] / total_raw, 4)

        # 5. 排序 + 排名
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

    except Exception as e:
        return {"code": 500, "msg": f"预测服务异常: {e}"}
