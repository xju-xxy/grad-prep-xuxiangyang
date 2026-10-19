"""eval.py —— 算误差指标，跟基线对比。

指标口径跟论文对齐：
  - RMSE / MAPE：常规误差
  - acc@10：预测值落在真实值 ±10% 之内的比例（论文用的就是这个）
  - acc@15：放宽到 ±15%

对比的方法：
  - pred_formula   ：按论文公式定形状、只学一个全局缩放
  - pred_als       ：W 当变量、交替最小二乘学出来
  - pred_persist   ：朴素基线，直接拿昨天当今天
  - pred_node_mean ：每个实体用训练段的历史均值当常数预测

跑法（在 sstkg-demo 目录下，先跑 gen_data.py 和 sstkg.py）：
  python eval.py
输出：
  results/metrics.json   所有指标
"""

import csv
import json
import os

import numpy as np

TRAIN_DAYS = list(range(1, 20))
TEST_DAYS = list(range(20, 30))
METHODS = ["pred_formula", "pred_als", "pred_persist", "pred_node_mean"]


def load_predictions(path="results/predictions.csv"):
    days, nodes = [], []
    cols = {m: [] for m in METHODS}
    true = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            days.append(int(row["day"]))
            nodes.append(int(row["node"]))
            true.append(float(row["true"]))
            for m in METHODS:
                cols[m].append(float(row[m]))
    return (np.array(days), np.array(nodes), np.array(true),
            {m: np.array(v) for m, v in cols.items()})


def metrics(true, pred):
    err = pred - true
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mape = float(np.mean(np.abs(err) / np.abs(true)) * 100.0)
    acc10 = float(np.mean(np.abs(err) <= 0.10 * np.abs(true)))
    acc15 = float(np.mean(np.abs(err) <= 0.15 * np.abs(true)))
    return dict(rmse=round(rmse, 4), mape=round(mape, 4),
                acc10=round(acc10, 4), acc15=round(acc15, 4))


def main():
    days, nodes, true, preds = load_predictions()
    train_mask = np.isin(days, TRAIN_DAYS)
    test_mask = np.isin(days, TEST_DAYS)

    result = {"train": {}, "test": {}, "test_shock_day_only": {}}
    for scope, mask in (("train", train_mask), ("test", test_mask)):
        for m in METHODS:
            result[scope][m] = metrics(true[mask], preds[m][mask])

    # 单独看冲击日（第 24 天）和之后一天，邻居模型到底顶不顶用
    shock_day = 24
    shock_mask = days == shock_day
    after_mask = days == shock_day + 1
    for name, mask in (("test_shock_day_only", shock_mask),
                       ("test_shock_day_after", after_mask)):
        result[name] = {m: metrics(true[mask], preds[m][mask]) for m in METHODS}

    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("测试段（第 20~29 天，100 个实体，共 %d 个预测点）" % int(test_mask.sum()))
    print(f"{'方法':<16}{'RMSE':>8}{'MAPE%':>9}{'acc@10':>9}{'acc@15':>9}")
    for m in METHODS:
        r = result["test"][m]
        print(f"{m:<16}{r['rmse']:>8.3f}{r['mape']:>9.2f}{r['acc10']:>9.3f}{r['acc15']:>9.3f}")

    print()
    print("训练段（第 1~19 天，共 %d 个预测点）" % int(train_mask.sum()))
    for m in METHODS:
        r = result["train"][m]
        print(f"{m:<16}{r['rmse']:>8.3f}{r['mape']:>9.2f}{r['acc10']:>9.3f}{r['acc15']:>9.3f}")

    print()
    print("冲击当天（第 24 天，100 个实体）")
    for m in METHODS:
        r = result["test_shock_day_only"][m]
        print(f"{m:<16}{r['rmse']:>8.3f}{r['mape']:>9.2f}{r['acc10']:>9.3f}{r['acc15']:>9.3f}")

    print()
    print("冲击次日（第 25 天，100 个实体）")
    for m in METHODS:
        r = result["test_shock_day_after"][m]
        print(f"{m:<16}{r['rmse']:>8.3f}{r['mape']:>9.2f}{r['acc10']:>9.3f}{r['acc15']:>9.3f}")
    print()
    print("已写出 results/metrics.json")


if __name__ == "__main__":
    main()
