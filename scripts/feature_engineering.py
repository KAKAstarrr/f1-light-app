"""
F1 XGBoost 预测模型 — 特征工程脚本
=====================================
从 races_2018_2025.csv 构建时间安全的特征矩阵。

核心原则：每行特征只能用该轮次【之前】的数据，严禁泄漏赛后信息。

产出：
  - ml/data/features_train.csv  （含特征 + 标签，可直接喂给 XGBoost）
  - ml/data/feature_columns.json（特征列名列表，推理时复用）

运行：python scripts/feature_engineering.py
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "ml" / "data"
RAW_CSV = DATA_DIR / "races_2018_2025.csv"
OUT_CSV = DATA_DIR / "features_train.csv"
OUT_COLS = DATA_DIR / "feature_columns.json"


def load_raw_data() -> pd.DataFrame:
    """加载原始比赛数据"""
    df = pd.read_csv(RAW_CSV)
    # 确保 race_date 是 datetime 类型，便于排序
    df["race_date"] = pd.to_datetime(df["race_date"])
    print(f"[加载] {len(df)} 行, {df['year'].min()}-{df['year'].max()}, {df['driver_code'].nunique()} 位车手")
    return df


# ──────────────────────────────────────────────────────
# 1. 季节内累计特征（groupby driver × year, shift 后 cumsum）
# ──────────────────────────────────────────────────────
def add_season_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    在同一赛季内，截至当前轮次之前的累计统计。
    用 shift(1) 确保当前轮次的数据不参与计算。
    """
    # 先按 车手 × 年份 × 轮次 排序（轮次升序 = 时间升序）
    df = df.sort_values(["driver_code", "year", "round"]).reset_index(drop=True)

    grp = df.groupby(["driver_code", "year"])

    # shift(1) 把当前行的值下移一行 → 前一行的值
    # cumsum() 对 shift 后的值做累加 → 当前轮次之前的累计和
    df["_points_before"] = grp["points"].shift(1)
    df["driver_season_points_before"] = grp["_points_before"].transform(
        lambda x: x.cumsum()
    )

    # 完赛场次（当前轮次之前参加了几场）
    df["_count_before"] = 1
    df["_count_shifted"] = grp["_count_before"].shift(1)
    df["driver_season_races_before"] = grp["_count_shifted"].transform(
        lambda x: x.cumsum()
    )

    # 胜场数
    df["_win_before"] = grp["is_win"].shift(1)
    df["driver_season_wins_before"] = grp["_win_before"].transform(
        lambda x: x.cumsum()
    )

    # DNF 场数
    df["_dnf_before"] = grp["is_dnf"].shift(1)
    df["driver_season_dnfs_before"] = grp["_dnf_before"].transform(
        lambda x: x.cumsum()
    )

    # 平均完赛位次（只算完赛的）
    df["_pos_before"] = grp["finishing_pos"].shift(1)
    df["_pos_sum_before"] = grp["_pos_before"].transform(lambda x: x.cumsum())
    df["driver_season_avg_pos_before"] = np.where(
        df["driver_season_races_before"] > 0,
        df["_pos_sum_before"] / df["driver_season_races_before"],
        np.nan,  # 赛季第一场没有历史数据 → NaN
    )

    # 清理临时列
    drop_cols = [
        "_points_before", "_count_before", "_count_shifted",
        "_win_before", "_dnf_before", "_pos_before", "_pos_sum_before",
    ]
    df = df.drop(columns=drop_cols)

    print(f"[赛季特征] 完成 6 个 driver_season_* 特征")
    return df


# ──────────────────────────────────────────────────────
# 2. 跨赛季近 5 场特征（groupby driver, rolling 5）
# ──────────────────────────────────────────────────────
def add_recent_form_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    跨赛季的近 5 场比赛表现。
    按 race_date 全局排序，对每个 driver 做 rolling(5)。
    """
    # 按 车手 × 日期 排序
    df = df.sort_values(["driver_code", "race_date"]).reset_index(drop=True)

    grp = df.groupby("driver_code")

    # shift(1) 后 rolling(5) → 最近 5 场（不含当前场）
    df["_pos_shift"] = grp["finishing_pos"].shift(1)
    df["driver_last5_avg_pos"] = grp["_pos_shift"].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )

    df["_dnf_shift"] = grp["is_dnf"].shift(1)
    df["driver_last5_dnfs"] = grp["_dnf_shift"].transform(
        lambda x: x.rolling(5, min_periods=1).sum()
    )

    df["_win_shift"] = grp["is_win"].shift(1)
    df["driver_last5_wins"] = grp["_win_shift"].transform(
        lambda x: x.rolling(5, min_periods=1).sum()
    )

    # 近 5 场完赛率
    df["driver_last5_finish_rate"] = 1 - (
        df["driver_last5_dnfs"] / df["driver_last5_wins"].transform(
            lambda x: x.rolling(5, min_periods=1).count()
        ) + df["driver_last5_dnfs"].transform(
            lambda x: x.rolling(5, min_periods=1).count()
        )
    ).clip(lower=1)

    # 简化：直接算 last5 完赛率
    df["driver_last5_finish_rate"] = 1.0 - (
        df["driver_last5_dnfs"] / 5.0
    ).clip(upper=1.0)

    df = df.drop(columns=["_pos_shift", "_dnf_shift", "_win_shift",
                          "driver_last5_wins", "driver_last5_finish_rate"])

    print(f"[近况特征] 完成 3 个 driver_last5_* 特征")
    return df


# ──────────────────────────────────────────────────────
# 3. 赛道特定特征（同赛道历史成绩）
# ──────────────────────────────────────────────────────
def add_circuit_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    车手在该赛道的历史表现（仅看往年数据）。
    按 driver × circuit_id × race_date 排序，shift + cumsum/cumcount。
    """
    df = df.sort_values(["driver_code", "circuit_id", "race_date"]).reset_index(drop=True)

    grp = df.groupby(["driver_code", "circuit_id"])

    df["_circuit_pos_shift"] = grp["finishing_pos"].shift(1)
    df["_circuit_pos_sum"] = grp["_circuit_pos_shift"].transform(lambda x: x.cumsum())
    df["_circuit_count"] = grp["_circuit_pos_shift"].transform(
        lambda x: x.rolling(window=len(df), min_periods=1).count()
    )

    df["driver_circuit_avg_pos"] = np.where(
        df["_circuit_count"] > 0,
        df["_circuit_pos_sum"] / df["_circuit_count"],
        np.nan,
    )
    df["driver_circuit_races"] = df["_circuit_count"]

    # 该赛道 DNF 次数
    df["_circuit_dnf_shift"] = grp["is_dnf"].shift(1)
    df["driver_circuit_dnfs"] = grp["_circuit_dnf_shift"].transform(
        lambda x: x.rolling(window=len(df), min_periods=1).sum()
    )

    df = df.drop(columns=[
        "_circuit_pos_shift", "_circuit_pos_sum", "_circuit_count",
        "_circuit_dnf_shift",
    ])

    print(f"[赛道特征] 完成 3 个 driver_circuit_* 特征")
    return df


# ──────────────────────────────────────────────────────
# 4. 车队特征（同车队两辆车的整体表现）
# ──────────────────────────────────────────────────────
def add_constructor_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    车队在本赛季截至当前的累计表现。
    包含两辆车的数据，所以先聚合再展开。
    """
    # 按 车队 × 年份 × 轮次 排序
    df = df.sort_values(["constructor_name", "year", "round"]).reset_index(drop=True)

    grp = df.groupby(["constructor_name", "year"])

    # 车队赛季累计积分（当前轮次之前）
    df["_const_points_shift"] = grp["points"].shift(1)
    df["constructor_season_points_before"] = grp["_const_points_shift"].transform(
        lambda x: x.cumsum()
    )

    # 车队赛季完赛平均位次
    df["_const_pos_shift"] = grp["finishing_pos"].shift(1)
    df["_const_pos_sum"] = grp["_const_pos_shift"].transform(lambda x: x.cumsum())
    df["_const_count"] = grp["_const_pos_shift"].transform(
        lambda x: x.rolling(window=len(df), min_periods=1).count()
    )
    df["constructor_season_avg_pos_before"] = np.where(
        df["_const_count"] > 0,
        df["_const_pos_sum"] / df["_const_count"],
        np.nan,
    )

    # 车队 DNF 次数
    df["_const_dnf_shift"] = grp["is_dnf"].shift(1)
    df["constructor_season_dnfs_before"] = grp["_const_dnf_shift"].transform(
        lambda x: x.rolling(window=len(df), min_periods=1).sum()
    )

    df = df.drop(columns=[
        "_const_points_shift", "_const_pos_shift", "_const_pos_sum",
        "_const_count", "_const_dnf_shift",
    ])

    print(f"[车队特征] 完成 3 个 constructor_season_* 特征")
    return df


# ──────────────────────────────────────────────────────
# 5. 上下文特征 & 编码
# ──────────────────────────────────────────────────────
def add_context_features(df: pd.DataFrame) -> pd.DataFrame:
    """赛季阶段、规则时代、发车位次等上下文特征"""

    # 规则时代：2022 地面效应新规
    df["regulation_era"] = (df["year"] >= 2022).astype(int)

    # 赛季阶段（归一化到 0-1）
    season_max_round = df.groupby("year")["round"].transform("max")
    df["round_normalized"] = df["round"] / season_max_round

    # 排位赛位次倒数（1=杆位最有利 → 20=最不利）
    # 保留原始 qualifying_pos 作为特征
    df["qualifying_pos_inv"] = 1.0 / df["qualifying_pos"].clip(lower=1)

    # 发车位次倒数
    df["grid_inv"] = 1.0 / df["grid"].clip(lower=1)

    print(f"[上下文特征] 完成 4 个 context 特征")
    return df


# ──────────────────────────────────────────────────────
# 6. NaN 填充 & 最终特征矩阵
# ──────────────────────────────────────────────────────
def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """填充 NaN，选择最终特征列，输出特征矩阵"""

    # ── 定义特征列 ──
    # 分为 5 组，便于后续分析
    feature_groups = {
        "baseline": [
            "qualifying_pos",
            "grid",
            "qualifying_pos_inv",
            "grid_inv",
        ],
        "driver_season": [
            "driver_season_points_before",
            "driver_season_races_before",
            "driver_season_wins_before",
            "driver_season_dnfs_before",
            "driver_season_avg_pos_before",
        ],
        "driver_recent": [
            "driver_last5_avg_pos",
            "driver_last5_dnfs",
        ],
        "driver_circuit": [
            "driver_circuit_avg_pos",
            "driver_circuit_races",
            "driver_circuit_dnfs",
        ],
        "constructor": [
            "constructor_season_points_before",
            "constructor_season_avg_pos_before",
            "constructor_season_dnfs_before",
        ],
        "context": [
            "regulation_era",
            "round_normalized",
        ],
    }

    all_features = []
    for cols in feature_groups.values():
        all_features.extend(cols)

    # ── 保留元信息 + 特征 + 标签 ──
    meta_cols = [
        "year", "round", "race_name", "race_date",
        "driver_code", "driver_name", "constructor_name",
        "circuit_id", "circuit_name",
    ]
    label_col = "is_win"

    result = df[meta_cols + all_features + [label_col]].copy()

    # ── NaN 填充策略 ──
    # 计数类特征（积分/场次/胜场/DNF）→ 填 0（"之前没有" = 零）
    # 平均值类特征（位次均值）→ 填中位数（"无历史数据" → 用典型值兜底）
    zero_fill_cols = {
        "driver_season_points_before",
        "driver_season_races_before",
        "driver_season_wins_before",
        "driver_season_dnfs_before",
        "driver_last5_dnfs",
        "driver_circuit_races",
        "driver_circuit_dnfs",
        "constructor_season_points_before",
        "constructor_season_dnfs_before",
    }
    median_fill_cols = {
        "driver_season_avg_pos_before",
        "driver_last5_avg_pos",
        "driver_circuit_avg_pos",
        "constructor_season_avg_pos_before",
    }

    for col in zero_fill_cols:
        if col in result.columns and result[col].isnull().any():
            n_nan = result[col].isnull().sum()
            result[col] = result[col].fillna(0.0)
            print(f"  [填0] {col}: 填充 {n_nan} 个 NaN")

    for col in median_fill_cols:
        if col in result.columns and result[col].isnull().any():
            n_nan = result[col].isnull().sum()
            median_val = result[col].median()
            result[col] = result[col].fillna(median_val)
            print(f"  [填中位数] {col}: 填充 {n_nan} 个 NaN (median={median_val:.2f})")

    # ── 数据类型转换 ──
    for col in all_features:
        result[col] = result[col].astype(float)

    print(f"[特征矩阵] {len(result)} 行 × {len(all_features)} 个特征")
    print(f"[特征矩阵] NaN 填充完成（计数类填0 / 均值类填中位数）")

    # ── 输出特征列名 JSON（推理时复用）──
    feature_info = {
        "feature_columns": all_features,
        "feature_groups": feature_groups,
        "label_column": label_col,
        "meta_columns": meta_cols,
    }
    with open(OUT_COLS, "w", encoding="utf-8") as f:
        json.dump(feature_info, f, ensure_ascii=False, indent=2)

    print(f"[输出] 特征列名 → {OUT_COLS}")

    return result


# ──────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("F1 XGBoost 特征工程")
    print("=" * 60)

    # 1. 加载
    df = load_raw_data()

    # 2. 按顺序构建特征（每步都可能改变排序，下一步重新排序）
    df = add_season_features(df)
    df = add_recent_form_features(df)
    df = add_circuit_features(df)
    df = add_constructor_features(df)
    df = add_context_features(df)

    # 3. 构建最终特征矩阵
    result = build_feature_matrix(df)

    # 4. 保存
    result.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[输出] 特征矩阵 → {OUT_CSV}")

    # 5. 摘要
    print("\n" + "=" * 60)
    print("特征工程完成 — 摘要")
    print("=" * 60)
    print(f"总行数: {len(result)}")
    print(f"总特征数: {len(result.columns) - 10}  (减去 9 元信息 + 1 标签)")
    print(f"\n标签分布 (is_win):")
    print(result["is_win"].value_counts().to_string())
    print(f"\n特征列:")
    for i, col in enumerate(result.columns[9:-1], 1):
        dtype = result[col].dtype
        sample = result[col].iloc[0]
        print(f"  {i:2d}. {col:40s} dtype={dtype}  sample={sample}")

    # 6. 防泄漏检查
    print("\n" + "=" * 60)
    print("防泄漏检查")
    print("=" * 60)
    # 按 round 排序后取每赛季第一场，检查 driver_season_races_before 应为 0
    check_df = result.sort_values(["driver_code", "year", "round"])
    first_races = check_df.groupby(["driver_code", "year"]).first()
    races_before_col = "driver_season_races_before"
    if races_before_col in first_races.columns:
        vals = first_races[races_before_col]
        print(f"赛季第一场 driver_season_races_before:")
        print(f"  均值: {vals.mean():.2f} (应为 0.0)")
        print(f"  最大值: {vals.max():.2f} (应为 0.0)")
        print(f"  非零行数: {(vals > 0).sum()} / {len(vals)} (应为 0)")
        if vals.max() == 0:
            print("  ✅ 防泄漏检查通过")
        else:
            print("  ⚠️ 发现泄漏！赛季第一场不应有历史数据")

    # 额外检查：qualifying_pos 不应为 NaN（它是赛前已知的）
    if "qualifying_pos" in result.columns:
        n_nan = result["qualifying_pos"].isnull().sum()
        print(f"\nqualifying_pos NaN 数: {n_nan} (应为 0)")

    print("\n✅ 特征工程完成！")


if __name__ == "__main__":
    main()
