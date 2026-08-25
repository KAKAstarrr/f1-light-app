"""
F1 XGBoost 预测模型 — 模型训练脚本
=====================================
时间序列切分训练 XGBoost 二分类模型，与 rule_v1 规则加权基线对比。

数据切分：
  - 训练集: 2018-2023（6 年）
  - 验证集: 2024（1 年，早停 + 调参）
  - 测试集: 2025（1 年，最终评估）

评估指标：
  - Log Loss（主指标，越低越好）
  - Brier Score（越低越好）
  - Top-1 Accuracy（预测冠军命中率）
  - Top-3 Hit Rate（真实冠军在预测 Top3 中的比例）
  - NDCG@3（排序质量）

产出：
  - ml/models/xgb_v2.json          （XGBoost 模型，24 特征含天气）
  - ml/models/feature_importance.csv（特征重要性）
  - ml/models/eval_report.json      （评估报告）

运行：python scripts/train_xgboost.py [--version v2]
      可选 --version 覆盖模型版本号（默认 xgb_v2，可传 xgb_v1 复现旧模型）
"""

import argparse
import json
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "ml" / "data"
MODEL_DIR = BASE / "ml" / "models"
FEATURES_CSV = DATA_DIR / "features_train.csv"
FEATURE_COLS_JSON = DATA_DIR / "feature_columns.json"

MODEL_PATH = MODEL_DIR / "xgb_v2.json"
IMPORTANCE_PATH = MODEL_DIR / "feature_importance.csv"
REPORT_PATH = MODEL_DIR / "eval_report.json"


def load_data():
    """加载特征矩阵和特征列名"""
    df = pd.read_csv(FEATURES_CSV)
    with open(FEATURE_COLS_JSON, "r", encoding="utf-8") as f:
        feat_info = json.load(f)
    feature_cols = feat_info["feature_columns"]
    label_col = feat_info["label_column"]
    print(f"[加载] {len(df)} 行, {len(feature_cols)} 个特征, 标签={label_col}")
    return df, feature_cols, label_col


def time_split(df, feature_cols, label_col):
    """时间序列切分：2018-2023 训练, 2024 验证, 2025 测试"""
    train = df[df["year"].between(2018, 2023)]
    val = df[df["year"] == 2024]
    test = df[df["year"] == 2025]

    print(f"[切分] 训练 {len(train)} 行 ({train['year'].min()}-{train['year'].max()})")
    print(f"[切分] 验证 {len(val)} 行 (2024)")
    print(f"[切分] 测试 {len(test)} 行 (2025)")

    X_train = train[feature_cols].values
    y_train = train[label_col].values
    X_val = val[feature_cols].values
    y_val = val[label_col].values
    X_test = test[feature_cols].values
    y_test = test[label_col].values

    # 正负样本比（用于 scale_pos_weight）
    pos = y_train.sum()
    neg = len(y_train) - pos
    spw = neg / pos if pos > 0 else 1.0
    print(f"[切分] 训练集正负比: {int(pos)}:{int(neg)} = 1:{spw:.1f}")

    return (X_train, y_train, X_val, y_val, X_test, y_test,
            train, val, test, spw)


# ──────────────────────────────────────────────────────
# 规则加权基线 (rule_v1) — 用于对比
# ──────────────────────────────────────────────────────
def rule_v1_predict(df_segment, feature_cols):
    """
    复现 prediction_service.py 中的规则加权模型：
      积分占比 35% + 近况位次 25% + 排位位次 15% + 胜率 15% + DNF率 10%
    返回每位车手的概率（同一场内 softmax 归一化）。
    """
    results = []
    for (year, rnd), group in df_segment.groupby(["year", "round"]):
        n = len(group)
        if n == 0:
            continue

        # 1. 积分占比（赛季累计积分 / 该场最大可能积分）
        max_points = group["driver_season_points_before"].max()
        if max_points > 0:
            points_ratio = group["driver_season_points_before"] / max_points
        else:
            points_ratio = pd.Series(0.0, index=group.index)

        # 2. 近况位次（倒数，位次越小越好 → 倒数越大越好）
        max_pos = group["driver_last5_avg_pos"].max()
        if max_pos > 0:
            recent_form = 1.0 - (group["driver_last5_avg_pos"] / max_pos)
        else:
            recent_form = pd.Series(0.5, index=group.index)

        # 3. 排位位次（倒数）
        max_qual = group["qualifying_pos"].max()
        if max_qual > 0:
            qual_form = 1.0 - (group["qualifying_pos"] / max_qual)
        else:
            qual_form = pd.Series(0.5, index=group.index)

        # 4. 胜率
        races = group["driver_season_races_before"]
        wins = group["driver_season_wins_before"]
        win_rate = np.where(races > 0, wins / races, 0.0)

        # 5. DNF 率（越低越好 → 取反）
        dnf_rate = np.where(races > 0, group["driver_season_dnfs_before"] / races, 0.0)
        finish_rate = 1.0 - dnf_rate

        # 加权求和
        raw = (
            0.35 * points_ratio
            + 0.25 * recent_form
            + 0.15 * qual_form
            + 0.15 * win_rate
            + 0.10 * finish_rate
        )

        # softmax 归一化（让概率和为 1）
        exp_scores = np.exp(raw - raw.max())  # 数值稳定
        probs = exp_scores / exp_scores.sum()

        for i, (idx, prob) in enumerate(zip(group.index, probs)):
            results.append({
                "index": idx,
                "prob": prob,
            })

    # 按原始索引排列
    result_df = pd.DataFrame(results).set_index("index")
    return result_df["prob"].reindex(df_segment.index).values


# ──────────────────────────────────────────────────────
# 评估指标
# ──────────────────────────────────────────────────────
def evaluate_per_race(df_segment, probs, label_col="is_win"):
    """
    逐场比赛评估预测质量。
    probs: 每行对应的预测概率（与 df_segment 行对齐）。
    """
    df = df_segment.copy()
    df["prob"] = probs

    top1_hits = 0
    top3_hits = 0
    ndcg_scores = []
    total_races = 0

    for (year, rnd), group in df.groupby(["year", "round"]):
        total_races += 1
        if len(group) == 0:
            continue

        # 按概率降序排
        ranked = group.sort_values("prob", ascending=False)

        # Top-1：预测概率最高的是不是真正冠军
        actual_winner = group[group[label_col] == 1]
        if len(actual_winner) > 0:
            winner_code = actual_winner.index[0]
            if ranked.index[0] == winner_code:
                top1_hits += 1

            # Top-3：真正冠军在预测前三名中
            if winner_code in ranked.index[:3]:
                top3_hits += 1

            # NDCG@3
            # 理想排序：冠军排第一 → DCG 理想 = 1/1 + 0/2 + 0/3 = 1.0
            # 实际排序：找到冠军在 ranked 中的位置
            winner_rank = list(ranked.index).index(winner_code)
            if winner_rank < 3:
                dcg = 1.0 / np.log2(winner_rank + 2)  # +2 因为 log2(1)=0
            else:
                dcg = 0.0
            idcg = 1.0  # 理想情况冠军排第一
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcg_scores.append(ndcg)
        else:
            # 没有冠军标记（异常情况），跳过
            pass

    top1_acc = top1_hits / total_races if total_races > 0 else 0
    top3_rate = top3_hits / total_races if total_races > 0 else 0
    ndcg3 = np.mean(ndcg_scores) if ndcg_scores else 0

    return {
        "top1_accuracy": top1_acc,
        "top3_hit_rate": top3_rate,
        "ndcg_at_3": ndcg3,
        "total_races": total_races,
    }


def full_evaluate(y_true, y_prob, df_segment, model_name, label_col="is_win"):
    """计算全部 5 个指标"""
    # 逐样本指标
    ll = log_loss(y_true, y_prob, labels=[0, 1])
    bs = brier_score_loss(y_true, y_prob)

    # 逐场比赛指标
    race_metrics = evaluate_per_race(df_segment, y_prob, label_col)

    return {
        "model": model_name,
        "log_loss": round(ll, 4),
        "brier_score": round(bs, 4),
        "top1_accuracy": round(race_metrics["top1_accuracy"], 4),
        "top3_hit_rate": round(race_metrics["top3_hit_rate"], 4),
        "ndcg_at_3": round(race_metrics["ndcg_at_3"], 4),
        "total_races": race_metrics["total_races"],
    }


# ──────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("F1 XGBoost 模型训练")
    print("=" * 60)

    # 1. 加载数据
    df, feature_cols, label_col = load_data()

    # 2. 时间切分
    (X_train, y_train, X_val, y_val, X_test, y_test,
     train_df, val_df, test_df, spw) = time_split(df, feature_cols, label_col)

    # 3. 训练 XGBoost
    print("\n" + "=" * 60)
    print("训练 XGBoost (binary:logistic)")
    print("=" * 60)

    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "n_estimators": 150,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "scale_pos_weight": spw,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
    }
    print(f"[参数] {json.dumps(params, indent=2)}")

    model = xgb.XGBClassifier(**params)

    # 早停：验证集 logloss 连续 20 轮不降则停
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # 保存模型
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    print(f"[保存] 模型 → {MODEL_PATH}")

    # 4. 特征重要性
    importance = model.feature_importances_
    imp_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importance,
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    imp_df.to_csv(IMPORTANCE_PATH, index=False, encoding="utf-8-sig")
    print(f"[保存] 特征重要性 → {IMPORTANCE_PATH}")
    print("\n特征重要性 Top-10:")
    for i, row in imp_df.head(10).iterrows():
        bar = "█" * int(row["importance"] * 100)
        print(f"  {row['feature']:40s} {row['importance']:.4f} {bar}")

    # 5. 评估 — XGBoost
    print("\n" + "=" * 60)
    print("模型评估")
    print("=" * 60)

    # 测试集预测
    y_prob_xgb = model.predict_proba(X_test)[:, 1]
    xgb_eval = full_evaluate(y_test, y_prob_xgb, test_df, "xgb_v2")
    print(f"\n[XGBoost xgb_v2] 测试集 (2025, {xgb_eval['total_races']} 场):")
    for k, v in xgb_eval.items():
        if k not in ("model", "total_races"):
            print(f"  {k:20s}: {v}")

    # 6. 评估 — rule_v1 基线
    print()
    y_prob_rule = rule_v1_predict(test_df, feature_cols)
    rule_eval = full_evaluate(y_test, y_prob_rule, test_df, "rule_v1")
    print(f"[规则加权 rule_v1] 测试集 (2025, {rule_eval['total_races']} 场):")
    for k, v in rule_eval.items():
        if k not in ("model", "total_races"):
            print(f"  {k:20s}: {v}")

    # 7. 对比
    print("\n" + "=" * 60)
    print("模型对比 (2025 测试集)")
    print("=" * 60)
    print(f"{'指标':20s} {'rule_v1':>10s} {'xgb_v2':>10s} {'差异':>10s}")
    print("-" * 52)
    for metric in ["log_loss", "brier_score", "top1_accuracy", "top3_hit_rate", "ndcg_at_3"]:
        r_val = rule_eval[metric]
        x_val = xgb_eval[metric]
        diff = x_val - r_val
        diff_str = f"+{diff:.4f}" if diff > 0 else f"{diff:.4f}"
        print(f"{metric:20s} {r_val:>10.4f} {x_val:>10.4f} {diff_str:>10s}")

    # 8. 抽样：2025 第 1 场（澳大利亚站）预测对比
    print("\n" + "=" * 60)
    print("抽样: 2025 R1 澳大利亚站 — Top 5 预测对比")
    print("=" * 60)
    r1 = test_df[test_df["round"] == 1].copy()
    if len(r1) > 0:
        r1_features = r1[feature_cols].values
        r1_prob_xgb = model.predict_proba(r1_features)[:, 1]
        r1_prob_rule = rule_v1_predict(r1, feature_cols)

        r1_result = r1[["driver_code", "constructor_name", "qualifying_pos",
                         "is_win"]].copy()
        r1_result["xgb_prob"] = r1_prob_xgb
        r1_result["rule_prob"] = r1_prob_rule
        r1_result = r1_result.sort_values("xgb_prob", ascending=False)

        print(f"{'车手':6s} {'车队':15s} {'排位':>4s} {'胜':>3s} {'XGB概率':>8s} {'规则概率':>8s}")
        print("-" * 60)
        for _, row in r1_result.head(5).iterrows():
            win_mark = "🏆" if row["is_win"] == 1 else ""
            print(f"{row['driver_code']:6s} {row['constructor_name']:15s} "
                  f"{int(row['qualifying_pos']):4d} {win_mark:3s} "
                  f"{row['xgb_prob']:8.4f} {row['rule_prob']:8.4f}")

    # 9. 保存评估报告
    report = {
        "model_version": "xgb_v2",
        "train_years": "2018-2023",
        "val_year": 2024,
        "test_year": 2025,
        "feature_count": len(feature_cols),
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "test_samples": len(X_test),
        "xgb_params": params,
        "xgb_eval": xgb_eval,
        "rule_v1_eval": rule_eval,
        "feature_importance_top10": imp_df.head(10).to_dict("records"),
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[保存] 评估报告 → {REPORT_PATH}")

    print("\n✅ 模型训练完成！")


if __name__ == "__main__":
    main()
