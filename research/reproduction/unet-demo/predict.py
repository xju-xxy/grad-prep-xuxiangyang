# -*- coding: utf-8 -*-
# 用训好的权重在测试集上算 Dice / IoU，并挑几张画成"原图 | 真值 | 预测"的对比图。
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")           # 只存图不弹窗
import matplotlib.pyplot as plt
# 不设这个的话图里中文标题会变成一堆方框（第一次跑就踩了）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import torch

from model import UNet


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="results/best_unet.pt")
    ap.add_argument("--n_show", type=int, default=6)
    ap.add_argument("--base", type=int, default=16)
    args = ap.parse_args()

    device = torch.device("cpu")
    net = UNet(base=args.base)
    net.load_state_dict(torch.load(args.ckpt, map_location=device, weights_only=True))
    net.eval()

    d = np.load("data/test.npz")
    x = torch.from_numpy(d["imgs"])
    y = torch.from_numpy(d["masks"])

    dice_list, iou_list = [], []
    preds = []
    # 一张一张过，顺便把每张的 Dice/IoU 收起来看分布
    for i in range(x.size(0)):
        xi = x[i:i + 1]
        prob = torch.sigmoid(net(xi))
        pred = (prob > 0.5).float()
        yi = y[i:i + 1]
        inter = float((pred * yi).sum())
        p_sum = float(pred.sum())
        y_sum = float(yi.sum())
        union = p_sum + y_sum - inter
        dice_list.append((2 * inter + 1e-6) / (p_sum + y_sum + 1e-6))
        iou_list.append((inter + 1e-6) / (union + 1e-6))
        preds.append(pred)

    dice = np.array(dice_list)
    iou = np.array(iou_list)

    print("测试集 %d 张" % x.size(0))
    # 数字接近满分了，4 位小数全被抹成 1，用 5 位才看得出差别
    print("Dice  平均 %.5f  中位 %.5f  最低 %.5f  最高 %.5f"
          % (dice.mean(), np.median(dice), dice.min(), dice.max()))
    print("IoU   平均 %.5f  中位 %.5f  最低 %.5f  最高 %.5f"
          % (iou.mean(), np.median(iou), iou.min(), iou.max()))

    # 像素级准确率（把背景也算进去的那种，数字会好看，参考着看）
    all_pred = torch.cat(preds, dim=0)
    acc = float((all_pred == y).float().mean())
    print("像素准确率（含背景）%.5f" % acc)

    os.makedirs("results", exist_ok=True)
    with open("results/metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "n_test": int(x.size(0)),
            "dice_mean": float(dice.mean()),
            "dice_median": float(np.median(dice)),
            "dice_min": float(dice.min()),
            "dice_max": float(dice.max()),
            "iou_mean": float(iou.mean()),
            "iou_median": float(np.median(iou)),
            "iou_min": float(iou.min()),
            "iou_max": float(iou.max()),
            "pixel_acc": acc,
        }, f, ensure_ascii=False, indent=2)

    # 挑图：前几张从"中等偏上"的里选，最后补两张最差的，让对比图别只挑好看的
    order = np.argsort(dice)
    mid = order[len(order) // 2:len(order) // 2 + (args.n_show - 2)]
    worst = order[:2]
    picks = list(mid) + list(worst)

    n_show = len(picks)
    fig, axes = plt.subplots(n_show, 3, figsize=(6, 2.1 * n_show))
    for r, idx in enumerate(picks):
        axes[r, 0].imshow(x[idx, 0].numpy(), cmap="gray", vmin=0, vmax=1)
        axes[r, 0].set_ylabel("dice=%.4f" % dice[idx], fontsize=8)
        axes[r, 1].imshow(y[idx, 0].numpy(), cmap="gray", vmin=0, vmax=1)
        axes[r, 2].imshow(preds[idx][0, 0].numpy(), cmap="gray", vmin=0, vmax=1)
        for c in range(3):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])
    axes[0, 0].set_title("原图", fontsize=10)
    axes[0, 1].set_title("真值掩膜", fontsize=10)
    axes[0, 2].set_title("模型预测", fontsize=10)
    plt.tight_layout()
    plt.savefig("results/pred_samples.png", dpi=130)
    print("对比图已存到 results/pred_samples.png（选了 %d 张，含最差的两张）" % n_show)


if __name__ == "__main__":
    main()
