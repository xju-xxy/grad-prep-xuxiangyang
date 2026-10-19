"""把 train.py 写出来的 csv 日志画成 loss / acc 曲线。"""

import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_log(path):
    cols = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for name in reader.fieldnames:
            cols[name] = []
        for row in reader:
            for name in reader.fieldnames:
                cols[name].append(float(row[name]))
    return cols


def main(log_path="results/train_log.csv", out_path="results/loss_curve.png"):
    c = read_log(log_path)
    epochs = c["epoch"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax1.plot(epochs, c["train_loss"], "o-", label="train loss", color="tab:blue")
    ax1.plot(epochs, c["test_loss"], "s-", label="test loss", color="tab:orange")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.set_title("loss curve")
    ax1.grid(alpha=0.3)
    ax1.legend()

    ax2.plot(epochs, c["train_acc"], "o-", label="train acc", color="tab:blue")
    ax2.plot(epochs, c["test_acc"], "s-", label="test acc", color="tab:green")
    ax2.set_xlabel("epoch")
    ax2.set_ylabel("accuracy (%)")
    ax2.set_ylim(0, 100)
    ax2.set_title("accuracy curve")
    ax2.grid(alpha=0.3)
    ax2.legend()

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    print("已保存曲线图:", out_path)


if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else "results/train_log.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "results/loss_curve.png"
    main(log_path, out_path)
