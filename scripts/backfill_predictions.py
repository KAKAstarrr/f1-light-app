# -*- coding: utf-8 -*-
"""
backfill_predictions.py — 回填赛季已结束分站的 AI 预测记录

背景：
    predictions 表在建库后长期为空（predict_race 只算不存）。
    本脚本对指定赛季"已结束"的分站逐一调用 predict_race 并落库，
    让前端「预测历史」能回看本赛季每站的预测结果。

用法：
    python scripts/backfill_predictions.py                # 默认回填当前赛季
    python scripts/backfill_predictions.py --season 2025  # 指定赛季
    python scripts/backfill_predictions.py --dry-run      # 只打印将处理的分站，不计算不落库
    python scripts/backfill_predictions.py --force        # 已存在记录的站点也重新计算覆盖

注意：
    - 已存在预测记录的站点默认跳过（保留在线生成的历史）
    - 回算预测 = 用"当前数据"计算"过去分站"的结果，非当时真实预测，
      前端会以 source=backfill 标注
    - 每站需访问 Ergast + 模型推理（SHAP），全程可能数分钟，建议后台运行
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 项目根目录加入 sys.path，保证能 import backend 包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import models, prediction_service  # noqa: E402
from backend.data_source import fetch_ergast_season_by_year  # noqa: E402
from backend.database import SessionLocal, init_db  # noqa: E402


def load_schedule(year: int):
    """获取赛季赛程，返回 [(round, raceName, date)]，按 round 排序。"""
    data = fetch_ergast_season_by_year(year)
    races = data.get("Races") or []
    result = []
    for r in races:
        try:
            result.append({
                "round": int(r["round"]),
                "raceName": r.get("raceName", ""),
                "date": r.get("date", ""),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(result, key=lambda x: x["round"])


def has_round_records(db, season: int, round_num: int) -> bool:
    """该站是否已有预测记录（无论 source）。"""
    return (
        db.query(models.Prediction)
        .filter(models.Prediction.season == season, models.Prediction.round == round_num)
        .first()
        is not None
    )


def save_prediction(db, result: dict, source: str = "backfill") -> int:
    """将 predict_race 结果写入 predictions 表，返回写入条数。"""
    season = result.get("season")
    round_num = result.get("round")
    model_version = result.get("model_version", "rule_v1")
    feature_count = result.get("feature_count")
    count = 0

    for p in result.get("predictions", []):
        row = (
            db.query(models.Prediction)
            .filter(
                models.Prediction.season == season,
                models.Prediction.round == round_num,
                models.Prediction.driver_code == p["driver_code"],
            )
            .first()
        )
        snapshot = dict(p)
        snapshot["feature_count"] = feature_count
        json_str = json.dumps(snapshot, ensure_ascii=False, default=str)

        if not row:
            db.add(models.Prediction(
                season=season,
                round=round_num,
                driver_code=p["driver_code"],
                probability=p["probability"],
                rank_pred=p["rank_pred"],
                model_version=model_version,
                features_json=json_str,
                source=source,
            ))
        else:
            row.probability = p["probability"]
            row.rank_pred = p["rank_pred"]
            row.model_version = model_version
            row.features_json = json_str
            row.source = source
        count += 1

    db.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description="回填赛季 AI 预测记录")
    parser.add_argument("--season", type=int, default=None, help="赛季年份（默认当前年份）")
    parser.add_argument("--dry-run", action="store_true", help="只列出将处理的分站，不计算不落库")
    parser.add_argument("--force", action="store_true", help="已有记录的站点也重新计算覆盖")
    parser.add_argument("--skip-existing", action="store_true", help="跳过已有记录的站点（默认行为，冗余参数）")
    parser.add_argument("--rounds", type=str, default=None,
                        help="只处理指定分站，支持逗号/范围，如 '1,2' 或 '1-12'（默认全部已结束分站）")
    args = parser.parse_args()

    season = args.season or datetime.now().year
    today = datetime.now().date()

    init_db()
    schedule = load_schedule(season)
    if not schedule:
        print(f"[backfill] 未获取到 {season} 赛季赛程，中止")
        sys.exit(1)

    # 过滤已结束分站
    finished = [r for r in schedule if r["date"] and datetime.strptime(r["date"], "%Y-%m-%d").date() < today]

    # --rounds 定点过滤（如 "1,2" / "1-12"）
    if args.rounds:
        wanted = set()
        for part in args.rounds.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo, hi = part.split("-", 1)
                wanted.update(range(int(lo), int(hi) + 1))
            else:
                wanted.add(int(part))
        finished = [r for r in finished if r["round"] in wanted]
        if not finished:
            print(f"[backfill] {season} 赛季 --rounds {args.rounds} 没有匹配到已结束分站")
            return

    if not finished:
        print(f"[backfill] {season} 赛季暂无已结束分站（当前赛季 {len(schedule)} 站）")
        return

    print(f"[backfill] {season} 赛季共 {len(schedule)} 站，已结束 {len(finished)} 站：")
    for r in finished:
        print(f"   R{r['round']:02d}  {r['raceName']}  {r['date']}")

    if args.dry_run:
        print("\n[dry-run] 以上为将处理的分站（未执行预测/落库）")
        return

    db = SessionLocal()
    ok, skipped, failed = 0, 0, 0
    total_start = time.time()

    try:
        for i, r in enumerate(finished, 1):
            if not args.force and has_round_records(db, season, r["round"]):
                print(f"\n[{i}/{len(finished)}] R{r['round']:02d} {r['raceName']} 已有记录，跳过")
                skipped += 1
                continue

            print(f"\n[{i}/{len(finished)}] R{r['round']:02d} {r['raceName']} 预测中...")
            t0 = time.time()
            try:
                result = prediction_service.predict_race(season, r["round"])
            except Exception as e:
                print(f"    ✗ 预测异常: {e}")
                failed += 1
                continue

            if result.get("code") != 200:
                print(f"    ✗ 预测失败: {result.get('msg')}")
                failed += 1
                continue

            count = save_prediction(db, result, source="backfill")
            top3 = ", ".join(result.get("top3", []))
            elapsed = time.time() - t0
            print(f"    ✓ {count} 位车手落库 | 模型 {result.get('model_version')} | "
                  f"Top3: {top3} | 耗时 {elapsed:.1f}s")
            ok += 1

    finally:
        db.close()

    total_elapsed = time.time() - total_start
    print(f"\n[backfill] 完成：成功 {ok} 站 / 跳过 {skipped} 站 / 失败 {failed} 站，总耗时 {total_elapsed / 60:.1f} 分钟")
    if failed:
        print("[backfill] 存在失败站点，可稍后重跑本脚本（成功的站点会自动跳过）")
        sys.exit(2)


if __name__ == "__main__":
    main()
