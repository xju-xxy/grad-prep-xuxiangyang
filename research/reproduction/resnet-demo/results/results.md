# 训练结果记录（真实跑出来的，没有编）

## 跑的环境

- Python 3.14.4
- torch 2.14.1+cpu（注意：机器上系统 python 原本带的是 torch 2.13.0+cpu，我建虚拟环境时用了
  `--system-site-packages`，然后单独装 torchvision，结果 pip 顺带把 torch 升到了 2.14.1，装在了 venv 里）
- torchvision 0.29.1+cpu
- matplotlib 3.11.2
- `torch.cuda.is_available()` = False，全程 CPU
- 线程数 16（torch.get_num_threads() 默认）

## 数据是怎么弄到手的（这段有点折腾，如实记录）

torchvision 默认从 `https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz` 下，
我用 curl 测了一下这个源的实际速度：**只有 0.08 MB/s**，170 MB 的话得跑半小时以上，实在等不了。

试过的其它源：

| 源 | 结果 |
| --- | --- |
| www.cs.toronto.edu（官方） | 206，0.08 MB/s |
| huggingface.co/datasets/uoft-cs/cifar10 | 连不上（http 000）；而且这个仓库只有 parquet 格式，没有原始 tar.gz |
| ossci-datasets.s3.amazonaws.com | 404 |
| hf-mirror.com（HF 镜像） | 能连，但只有 0.06 MB/s |
| **data.brainchip.com/dataset-mirror** | **206，实测约 0.24 MB/s，最快，最后用的就是这个** |

最终下载命令：

```
curl.exe -L -C - --retry 8 --retry-delay 3 --retry-all-errors `
  -o "data\cifar-10-python.tar.gz" `
  "https://data.brainchip.com/dataset-mirror/cifar10/cifar-10-python.tar.gz"
```

实际结果：

- 下载 **170,498,071 字节**，耗时 **700.6 秒（约 11.7 分钟）**，平均 243.6 kB/s
- md5 = `c58f30108f718f92721af3b95e74349a`
- 这个 md5 和 torchvision 里 CIFAR10 类内置的校验值一模一样，说明镜像的这个文件是原版，
  才敢用它（不对的话 torchvision 会直接报 md5 不匹配然后重新下载）
- 之后 train.py 用 `download=True` + 这个已存在的 tar.gz，torchvision 校验通过并解压出
  `data/cifar-10-batches-py/`，没有再去联网

## 训练命令

```
.venv\Scripts\python.exe -u train.py --epochs 8 --train-size 10000 --batch-size 128 `
  --lr 0.05 --weight-decay 5e-4 --seed 42 --out-dir ./results
```

说明：**训练集只用了 10000 张（全量的 1/5）**，因为 CPU 上一个 epoch 就要 146 秒左右，
用满 50000 张的话一轮得 12 分钟，8 轮就快 100 分钟了，太耗。测试集是完整的 10000 张。

超参：SGD，lr 0.05，momentum 0.9，weight decay 5e-4，余弦退火（T_max=8）。
数据增强：RandomCrop(32, padding=4) + RandomHorizontalFlip；归一化用 CIFAR 的均值方差。

## 每个 epoch 的真实输出

| epoch | lr | train_loss | train_acc | test_loss | test_acc | 耗时(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.050000 | 2.0911 | 25.14% | 1.9053 | 33.08% | 146.2 |
| 2 | 0.048097 | 1.7096 | 35.22% | 2.4072 | 24.37% | 145.3 |
| 3 | 0.042678 | 1.6814 | 37.03% | 1.5864 | 40.80% | 146.2 |
| 4 | 0.034567 | 1.4906 | 44.40% | 1.4233 | 47.43% | 146.2 |
| 5 | 0.025000 | 1.3735 | 49.82% | 1.3792 | 50.15% | 148.8 |
| 6 | 0.015433 | 1.2631 | 53.34% | 1.3336 | 51.61% | 149.6 |
| 7 | 0.007322 | 1.1678 | 56.97% | 1.2336 | 55.56% | 144.0 |
| 8 | 0.001903 | 1.0931 | 60.43% | 1.1546 | 58.43% | 143.6 |

## 汇总数字

- **训练总耗时：1170.0 秒 = 19.5 分钟**（8 个 epoch，含每个 epoch 跑一遍 10000 张测试集）
- 平均一个 epoch：146.25 秒
- **最终（第 8 轮）测试准确率：58.43%**
- **最好测试准确率：58.43%**（就是最后这一轮）
- 训练准确率：60.43%
- 参数量：11.174 M
- 训练/测试图片数：10000 / 10000
- 随机猜的基线是 10%，所以从 33% 一路升到 58%，明显学到了东西

## 一个我觉得值得记的现象

epoch 2 的测试 loss 从 1.9053 突然窜到 **2.4072**，测试准确率反而从 33.08% 掉回 **24.37%**，
曲线图上那根橙线会看到一个很突兀的尖峰。当时我第一反应是代码写错了或者 BN 出问题。

后来想明白了：ResNet 这种带 BatchNorm 的网络，训练早期 BN 的 running_mean / running_var
还在动，而测试的时候是用 running stats 的，两边的统计量对不上就会出现这种"训练明明在降、
测试却崩一下"的情况；再加上第 2 轮 lr 还有 0.048，比较大，也放大了这个抖动。
到第 3 轮 lr 降下来、BN 统计稳了，就自己恢复了（40.80%），所以没去改代码。

## 产物

| 文件 | 内容 |
| --- | --- |
| `results/train_log.csv` | 每个 epoch 的原始日志（train.py 每轮追加，中途 Ctrl+C 也不丢） |
| `results/summary.json` | 超参 + 每轮明细 + 总耗时 + 最终准确率，机器可读 |
| `results/loss_curve.png` | 左边 loss 曲线、右边准确率曲线 |
| `results/sample_predictions.png` | 一批测试图的实际预测（8 张里对了 6 张；错的 2 张：飞机被认成船、汽车被认成卡车） |

样例预测图里 2 张错的：飞机那张背景是大片蓝色的海／水，被认成 ship；一辆白色小车被认成 truck。
都是肉眼也觉得"挺像那么回事"的错，属于这个准确率下的正常水平。
