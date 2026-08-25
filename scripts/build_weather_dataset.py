# -*- coding: utf-8 -*-
"""
build_weather_dataset.py — 构建天气特征数据集
=================================================
从 races_2018_2025.csv 提取全部 (year, round) 场次，
逐场调用 data_source.fetch_fastf1_weather 拉取正赛天气汇总，
输出 ml/data/weather_cache.csv（场次级特征，训练侧合并用）。

设计：
  - 断点续跑：已存在的场次行自动跳过（反复运行安全）
  - 并发拉取：ThreadPoolExecutor 4 workers（FastF1 单场 30-50s，并发可提速 3-4 倍）
  - 缺失兜底：拉取失败/无数据时写入中性值（与 prediction_service.WEATHER_NEUTRAL 一致）
  - 中性值 = 干地典型值：is_wet=0, air=20°C, track=30°C, rain=0, humidity=60%

运行：conda run -n f1_project python scripts/build_weather_dataset.py [--workers 4]
产出：ml/data/weather_cache.csv

注意：
  - FastF1 天气数据仅 2018+ 可用；首次拉取某年数据需要下载缓存，耗时较长
  - 天气 = 正赛实际记录；预测未来分站时该特征不可用（推理端用中性值）
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "backend"))

import pandas as pd
from data_source import fetch_fastf1_weather

RAW_CSV = BASE / "ml" / "data" / "races_2018_2025.csv"
OUT_CSV = BASE / "ml" / "data" / "weather_cache.csv"

# 与 prediction_service.WEATHER_NEUTRAL 保持完全一致
WEATHER_NEUTRAL = {
    "weather_is_wet": 0.0,
    "weather_air_temp": 20.0,
    "weather_track_temp": 30.0,
    "weather_max_rainfall": 0.0,
    "weather_humidity": 60.0,
}


def load_races():
    df = pd.read_csv(RAW_CSV)
    races = df[["year", "round"]].drop_duplicates().sort_values(["year", "round"])
    print(f"[赛程] 共 {len(races)} 场: {races['year'].min()}-{races['year'].max()}")
    return races


def load_existing():
    if OUT_CSV.exists():
        return pd.read_csv(OUT_CSV)
    return pd.DataFrame(columns=["year", "round"] + list(WEATHER_NEUTRAL.keys()))


def fetch_one(year, round_num):
    """返回该场天气 dict，失败返回 None"""
    try:
        res = fetch_fastf1_weather(int(year), int(round_num), "R")
        if res.get("code") != 200:
            return None
        s = res.get("weather_summary") or {}
        if not s or ("avg_air_temp" not in s and "is_wet" not in s):
            return None
        return {
            "weather_is_wet": float(1 if s.get("is_wet") else 0),
            "weather_air_temp": float(s.get("avg_air_temp") if s.get("avg_air_temp") is not None else WEATHER_NEUTRAL["weather_air_temp"]),
            "weather_track_temp": float(s.get("avg_track_temp") if s.get("avg_track_temp") is not None else WEATHER_NEUTRAL["weather_track_temp"]),
            "weather_max_rainfall": float(s.get("max_rainfall") if s.get("max_rainfall") is not None else WEATHER_NEUTRAL["weather_max_rainfall"]),
            "weather_humidity": float(s.get("avg_humidity") if s.get("avg_humidity") is not None else WEATHER_NEUTRAL["weather_humidity"]),
        }
    except Exception as e:
        print(f"    [ERR] {year}R{round_num}: {str(e)[:60]}")
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2, help="并发拉取线程数（建议 ≤2，jolpi.ca 对高频并发限流）")
    parser.add_argument("--start-year", type=int, default=2018, help="起始年份（可跳过早期慢下载）")
    parser.add_argument("--retry-neutral", action="store_true",
                        help="重新拉取上次因限流/失败写入中性值的场次")
    args = parser.parse_args()

    races = load_races()
    if args.start_year > 2018:
        races = races[races["year"] >= args.start_year]
        print(f"[范围] 仅拉取 {args.start_year}+ 赛季（{len(races)} 场）")

    existing = load_existing()

    # 已处理场次集合（year-round 键）
    if len(existing):
        done_keys = set(
            f"{int(r['year'])}-{int(r['round'])}" for _, r in existing.iterrows()
        )
    else:
        done_keys = set()

    rows = existing.to_dict("records")

    # --retry-neutral：把中性值行从已完成集合剔除，重新拉取
    if args.retry_neutral and len(rows):
        neutral_keys = set()
        keep_rows = []
        for r in rows:
            is_neutral = (
                abs(float(r.get("weather_is_wet", 0))) < 0.01
                and abs(float(r.get("weather_air_temp", 20)) - 20) < 0.01
                and abs(float(r.get("weather_track_temp", 30)) - 30) < 0.01
                and abs(float(r.get("weather_max_rainfall", 0))) < 0.01
                and abs(float(r.get("weather_humidity", 60)) - 60) < 0.01
            )
            if is_neutral:
                neutral_keys.add(f"{int(r['year'])}-{int(r['round'])}")
            else:
                keep_rows.append(r)
        if neutral_keys:
            rows = keep_rows
            done_keys -= neutral_keys
            print(f"[重试] 剔除 {len(neutral_keys)} 个中性值场次，重新拉取")

    todo = races[~races.apply(lambda r: f"{int(r['year'])}-{int(r['round'])}" in done_keys, axis=1)]

    print(f"[进度] 已有 {len(done_keys)} 场，待拉取 {len(todo)} 场（并发 {args.workers}）")
    if len(todo) == 0:
        print("✅ 全部场次已处理，无需拉取")
        return

    ok = miss = 0
    t_start = time.time()

    def work(item):
        year, rnd = int(item["year"]), int(item["round"])
        w = fetch_one(year, rnd)
        rec = {"year": year, "round": rnd, **WEATHER_NEUTRAL}
        if w is not None:
            rec.update(w)
        return rec, w is not None

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, r): r for _, r in todo.iterrows()}
        for i, fut in enumerate(as_completed(futures), 1):
            rec, is_ok = fut.result()
            year, rnd = rec["year"], rec["round"]
            if is_ok:
                ok += 1
            else:
                miss += 1
            rows.append(rec)
            done_keys.add(f"{year}-{rnd}")

            elapsed = time.time() - t_start
            avg = elapsed / i
            eta = avg * (len(todo) - i)
            print(f"  [{i}/{len(todo)}] {year}R{rnd:02d} "
                  f"wet={rec['weather_is_wet']:.0f} air={rec['weather_air_temp']:.1f} "
                  f"track={rec['weather_track_temp']:.1f} rain={rec['weather_max_rainfall']:.1f} "
                  f"hum={rec['weather_humidity']:.0f} | 平均 {avg:.1f}s/场 剩余约 {eta/60:.0f}min", flush=True)

            # 每 20 场落盘一次（防中断丢失）
            if i % 20 == 0 or i == len(todo):
                tmp = pd.DataFrame(rows).sort_values(["year", "round"])
                tmp.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
                print(f"    ... 已保存 {len(tmp)} 行 → {OUT_CSV.name}", flush=True)

    # 最终落盘
    final = pd.DataFrame(rows).sort_values(["year", "round"])
    final.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"完成！总场次 {len(final)} | 真实拉取 {ok} | 缺失兜底 {miss}")
    print(f"耗时 {time.time()-t_start:.0f}s | 输出 → {OUT_CSV}")
    wet_count = int(final["weather_is_wet"].sum())
    print(f"湿地场次（is_wet=1）: {wet_count} / {len(final)}")


if __name__ == "__main__":
    main()
