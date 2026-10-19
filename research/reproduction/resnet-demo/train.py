"""在 CIFAR-10 上训练 CIFAR 版 ResNet-18（CPU）。

用法示例：
    .venv\\Scripts\\python.exe train.py --epochs 8 --train-size 10000

每跑完一个 epoch 就往 results/train_log.csv 追加一行，所以中途 Ctrl+C 掉
日志也不会丢，能看出跑到哪了。
"""

import argparse
import csv
import json
import os
import time

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as T
from torch.utils.data import DataLoader, Subset

from model import resnet18_cifar
from plot_log import main as plot_main

CIFAR_MEAN = (0.4914, 0.4822, 0.4465)
CIFAR_STD = (0.2470, 0.2435, 0.2616)
CLASSES = ["airplane", "automobile", "bird", "cat", "deer",
           "dog", "frog", "horse", "ship", "truck"]


def get_loaders(args):
    train_tf = T.Compose([
        T.RandomCrop(32, padding=4),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
        T.Normalize(CIFAR_MEAN, CIFAR_STD),
    ])
    test_tf = T.Compose([
        T.ToTensor(),
        T.Normalize(CIFAR_MEAN, CIFAR_STD),
    ])

    train_set = torchvision.datasets.CIFAR10(
        root=args.data_dir, train=True, download=True, transform=train_tf)
    test_set = torchvision.datasets.CIFAR10(
        root=args.data_dir, train=False, download=True, transform=test_tf)

    total = len(train_set)
    if args.train_size and args.train_size < total:
        # 固定种子的随机子集，保证每次实验用的都是同一批 10000 张
        g = torch.Generator().manual_seed(args.seed)
        idx = torch.randperm(total, generator=g)[:args.train_size].tolist()
        train_set = Subset(train_set, idx)

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True,
                              num_workers=args.num_workers, drop_last=False)
    test_loader = DataLoader(test_set, batch_size=256, shuffle=False,
                             num_workers=args.num_workers)
    return train_loader, test_loader, len(train_set), len(test_set)


def run_epoch(net, loader, criterion, optimizer, device, train=True):
    net.train(train)
    tot_loss, correct, n = 0.0, 0, 0
    torch.set_grad_enabled(train)
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        if train:
            optimizer.zero_grad()
        out = net(x)
        loss = criterion(out, y)
        if train:
            loss.backward()
            optimizer.step()
        tot_loss += loss.item() * y.size(0)
        correct += (out.argmax(1) == y).sum().item()
        n += y.size(0)
    return tot_loss / n, 100.0 * correct / n


def save_samples(net, loader, device, path):
    """挑一批测试图，把预测结果贴出来看看到底认没认对。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    net.eval()
    x, y = next(iter(loader))
    x, y = x.to(device), y.to(device)
    with torch.no_grad():
        pred = net(x).argmax(1)

    fig, axes = plt.subplots(2, 4, figsize=(10, 5.4))
    for i, ax in enumerate(axes.flatten()):
        img = x[i].cpu() * torch.tensor(CIFAR_STD).view(3, 1, 1) \
            + torch.tensor(CIFAR_MEAN).view(3, 1, 1)
        img = img.clamp(0, 1).permute(1, 2, 0).numpy()
        ax.imshow(img)
        ok = pred[i].item() == y[i].item()
        # 图里的标签用英文，因为 matplotlib 默认字体没有中文字形，写中文会变成方框
        ax.set_title("pred: %s (true: %s)" % (CLASSES[pred[i]], CLASSES[y[i]]),
                     fontsize=9, color="green" if ok else "red")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print("已保存样例预测图:", path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--train-size", type=int, default=10000,
                   help="用多少张训练图，0 或 >=50000 表示全用")
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=0.05)
    p.add_argument("--momentum", type=float, default=0.9)
    p.add_argument("--weight-decay", type=float, default=5e-4)
    p.add_argument("--data-dir", default="./data")
    p.add_argument("--out-dir", default="./results")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-workers", type=int, default=2)
    p.add_argument("--threads", type=int, default=0, help="0 表示用 torch 默认")
    args = p.parse_args()

    if args.threads > 0:
        torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    os.makedirs(args.out_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("设备:", device, "| torch", torch.__version__,
          "| 线程数", torch.get_num_threads())

    t_data = time.time()
    train_loader, test_loader, n_train, n_test = get_loaders(args)
    print("数据就绪: 训练 %d 张 / 测试 %d 张，耗时 %.1fs"
          % (n_train, n_test, time.time() - t_data))

    net = resnet18_cifar().to(device)
    n_params = sum(p.numel() for p in net.parameters())
    print("参数量: %.2f M" % (n_params / 1e6))

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=args.lr,
                          momentum=args.momentum, weight_decay=args.weight_decay)
    # 余弦退火，最后几个 epoch 把 lr 压下去，收得稳一点
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    log_path = os.path.join(args.out_dir, "train_log.csv")
    new_file = not os.path.exists(log_path)
    log_f = open(log_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(log_f)
    if new_file:
        writer.writerow(["epoch", "lr", "train_loss", "train_acc",
                         "test_loss", "test_acc", "seconds"])
        log_f.flush()

    t_start = time.time()
    best_acc = 0.0
    rows = []
    try:
        for epoch in range(1, args.epochs + 1):
            t0 = time.time()
            lr_now = optimizer.param_groups[0]["lr"]
            tr_loss, tr_acc = run_epoch(net, train_loader, criterion,
                                        optimizer, device, train=True)
            te_loss, te_acc = run_epoch(net, test_loader, criterion,
                                        optimizer, device, train=False)
            scheduler.step()
            dt = time.time() - t0
            best_acc = max(best_acc, te_acc)
            writer.writerow(["%d" % epoch, "%.6f" % lr_now, "%.4f" % tr_loss,
                             "%.2f" % tr_acc, "%.4f" % te_loss,
                             "%.2f" % te_acc, "%.1f" % dt])
            log_f.flush()
            rows.append((epoch, lr_now, tr_loss, tr_acc, te_loss, te_acc, dt))
            print("epoch %2d/%d | lr %.4f | train loss %.4f acc %.2f%% | "
                  "test loss %.4f acc %.2f%% | %.1fs"
                  % (epoch, args.epochs, lr_now, tr_loss, tr_acc,
                     te_loss, te_acc, dt))
    except KeyboardInterrupt:
        print("\n[中断] 手动停了，已经跑完的 epoch 都写进日志了。")
    finally:
        log_f.close()

    total_time = time.time() - t_start
    print("训练总耗时: %.1f s (%.1f min)" % (total_time, total_time / 60))
    print("最好测试准确率: %.2f%%" % best_acc)

    summary = {
        "args": vars(args),
        "device": str(device),
        "train_images": n_train,
        "test_images": n_test,
        "params_M": round(n_params / 1e6, 3),
        "epochs_done": len(rows),
        "best_test_acc": round(best_acc, 2),
        "last_test_acc": round(rows[-1][5], 2) if rows else None,
        "total_train_seconds": round(total_time, 1),
        "torch": torch.__version__,
        "epochs_detail": [
            {"epoch": e, "lr": round(lr, 6), "train_loss": round(a, 4),
             "train_acc": round(b, 2), "test_loss": round(c, 4),
             "test_acc": round(d, 2), "seconds": round(s, 1)}
            for (e, lr, a, b, c, d, s) in rows
        ],
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("已保存 summary:", os.path.join(args.out_dir, "summary.json"))

    if rows:
        plot_main(log_path, os.path.join(args.out_dir, "loss_curve.png"))
        save_samples(net, test_loader, device,
                     os.path.join(args.out_dir, "sample_predictions.png"))


if __name__ == "__main__":
    main()
