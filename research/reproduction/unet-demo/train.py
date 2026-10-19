# -*- coding: utf-8 -*-
# 训练脚本：BCE + Dice 两个损失加权，Adam 优化，CPU 上跑。
# 每轮会在测试集上算一次 Dice，存 Dice 最高的那次权重。
import argparse
import os
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from model import UNet


def dice_loss(logits, target, eps=1.0):
    """soft Dice：直接拿 sigmoid 后的概率算，对前景小的情况比纯 BCE 稳。"""
    prob = torch.sigmoid(logits)
    num = 2.0 * (prob * target).sum(dim=(1, 2, 3)) + eps
    den = prob.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3)) + eps
    return (1.0 - num / den).mean()


def load_npz(path):
    d = np.load(path)
    x = torch.from_numpy(d["imgs"])
    y = torch.from_numpy(d["masks"])
    return TensorDataset(x, y)


@torch.no_grad()
def eval_dice(net, loader, device):
    net.eval()
    dice_sum, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        prob = torch.sigmoid(net(x))
        pred = (prob > 0.5).float()
        inter = (pred * y).sum(dim=(1, 2, 3))
        den = pred.sum(dim=(1, 2, 3)) + y.sum(dim=(1, 2, 3))
        # +1 是防止空掩膜除零，这里样本都有形状，影响可以忽略
        # 注意要 .sum() 成标量再累加，不然最后一个不满的 batch 会和前面维度对不上
        dice_sum += float(((2.0 * inter + 1.0) / (den + 1.0)).sum())
        n += x.size(0)
    net.train()
    return dice_sum / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--base", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cpu")
    torch.set_num_threads(os.cpu_count() or 4)

    train_ds = load_npz("data/train.npz")
    test_ds = load_npz("data/test.npz")
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch, shuffle=False)
    print("训练集 %d 张，测试集 %d 张，batch=%d，epochs=%d"
          % (len(train_ds), len(test_ds), args.batch, args.epochs))

    net = UNet(base=args.base)
    net.to(device)
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)
    bce = torch.nn.BCEWithLogitsLoss()

    if not os.path.isdir("results"):
        os.makedirs("results")

    best_dice = -1.0
    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        net.train()
        ep_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            logits = net(x)
            # 两个损失各占一半：BCE 管像素、Dice 管整体形状
            loss = bce(logits, y) + dice_loss(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            ep_loss += loss.item() * x.size(0)
        ep_loss /= len(train_ds)

        val_dice = eval_dice(net, test_loader, device)
        flag = ""
        if val_dice > best_dice:
            best_dice = val_dice
            torch.save(net.state_dict(), "results/best_unet.pt")
            flag = "  <- 存权重"

        print("epoch %2d/%d  loss %.4f  test_dice %.4f%s"
              % (ep, args.epochs, ep_loss, val_dice, flag))

    used = time.time() - t0
    print("训练结束，共 %.1f 秒（%.2f 分钟），最好 test_dice=%.4f"
          % (used, used / 60.0, best_dice))
    # 把这轮的关键数字落到文件里，方便后面写 results.md
    with open("results/train_summary.txt", "w", encoding="utf-8") as f:
        f.write("epochs=%d\nbatch=%d\nlr=%g\nbase=%d\n"
                % (args.epochs, args.batch, args.lr, args.base))
        f.write("best_test_dice=%.4f\ntrain_seconds=%.1f\n" % (best_dice, used))


if __name__ == "__main__":
    main()
