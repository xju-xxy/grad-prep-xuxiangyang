# ResNet 复现笔记

> 复现论文：Deep Residual Learning for Image Recognition（CVPR 2016）
> 环境：纯 CPU（torch 2.14.1+cpu），CPU 上跑的，没显卡
> 复现时间：2026年10月

---

## 这个项目做了什么

照着 ResNet 论文里的残差块，用 PyTorch 从零写了一个适配 32x32 输入的小号 ResNet-18，
在 CIFAR-10 上从头训了一遍，把 loss 和准确率曲线、每轮的原始数字都存下来了。

原论文是给 ImageNet 用的，输入 224x224，开头一个 7x7 卷积再 maxpool 把图砍得很小。
CIFAR 的图本来就才 32x32，再这么砍就没剩多少了，所以我照论文和后面大家常用的做法改了**两处**：
开头换成 3x3 卷积、去掉那个 maxpool，剩下的 stage 该怎么下采样还是怎么下采样。
另外论文里还用了 1x1 卷积调维度的 bottleneck 块，那是给更深的网络用的，我这里用的是最基础的
BasicBlock（两层 3x3），只把论文里的 ResNet-18 在 CIFAR 上跑通。

## 怎么运行

```bash
# 第一次：建虚拟环境并装依赖
# 这台机器的系统 python 已经自带 torch 2.13 cpu，但没有 torchvision，
# 所以我建的是带 --system-site-packages 的环境，只单独补了 torchvision
python -m venv .venv --system-site-packages
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 先单独跑一下模型，确认前向 shape 和参数量对得上
.venv\Scripts\python.exe model.py

# 训练（-u 是为了让日志不卡在缓冲区里，能实时看到每一轮结果）
.venv\Scripts\python.exe -u train.py --epochs 8 --train-size 10000

# 只用日志重新画一遍曲线（不重新训练）
.venv\Scripts\python.exe plot_log.py results/train_log.csv results/loss_curve.png
```

`train.py` 默认 `download=True`，会自己下 CIFAR-10。下不动的话下面"踩坑"那节写了备用源。

## 文件说明

```
resnet-demo/
├── model.py            # 残差块 BasicBlock + CIFAR 版 ResNet
├── train.py            # 训练主程序：数据、训练循环、日志、画图都在这
├── plot_log.py         # 读 csv 日志单独画 loss/acc 曲线（改超参后重画方便）
├── requirements.txt    # 依赖清单
├── .gitignore          # 忽略 .venv、__pycache__、data 缓存
├── data/               # CIFAR-10（下载 + 解压出来的，已被 gitignore）
└── results/
    ├── train_log.csv          # 每个 epoch 一行，跑完一轮就刷盘，中途停了也不丢
    ├── summary.json           # 超参 + 每轮明细 + 总耗时，机器可读
    ├── loss_curve.png         # loss + 准确率曲线
    ├── sample_predictions.png # 一批测试图的真实预测
    └── results.md             # 真实运行的完整记录（耗时、数据来源、每个数字）
```

## 核心思路

残差块这个东西说白了就是把"学输出 H(x)"换成"学残差 F(x) = H(x) - x"，
前向的时候再 `out = F(x) + x` 加回去。好处是反传的时候梯度能顺着这条加的支路直接流回浅层，
不用一路穿过一堆卷积和激活函数，深网络才好训。

论文里那个 shortcut 分两种：维度对不上（通道数变了或者特征图被下采样了一半）的时候，
用一层 1x1 卷积 + BN 把 x 的维度调到跟 F(x) 一样；维度对得上就直接原样加过去，这一路不带任何参数。

CIFAR 版的下采样就是靠 stride=2 实现的，每个 stage 第一次进块的时候 stride 给 2：

```python
# 维度不匹配时才挂这层，匹配时 self.shortcut 是空的 Sequential()
if stride != 1 or in_planes != planes * self.expansion:
    self.shortcut = nn.Sequential(
        nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=False),
        nn.BatchNorm2d(planes),
    )
```

## 踩过的最大的坑：CIFAR-10 根本下不动

这个比模型本身还费劲。torchvision 默认那个多伦多大学的源，我用 curl 实测**只有 0.08 MB/s**，
170 MB 的包要跑三十多分钟，第一次我是真等了一会儿，看着进度条一格一格爬，受不了了。

然后我开始到处找镜像，顺手把试过的都记下来：

- huggingface 上的 `uoft-cs/cifar10` 这条想都别想，一是连不上，二是它那个仓库只有 parquet 格式，
  根本没有原始 tar.gz，就算连上了也得再想办法转格式
- 试了一个 huggingface 镜像站，能连，但更慢，0.06 MB/s
- `ossci-datasets.s3.amazonaws.com` 直接 404
- 后来在一个叫什么 brainchip 的镜像站找到了，实测 0.24 MB/s，虽然也不快，但比官方快了三倍

换源之后 11.7 分钟下完。**下完我没敢直接用，先算了 md5，是 `c58f30108f718f92721af3b95e74349a`，
跟 torchvision 源码里 CIFAR10 内置的那个校验值一模一样，确认是原版文件才开始训。**

教训就是：这种内置下载地址的老数据集，源慢了不要傻等，先量一下速度，能换镜像就换，
但换完一定要对 md5，不然拿着一个被人改过的文件训出什么结果都不知道。

另外小坑一个是 **BasicBlock 的 shortcut 我一开始以为永远是个空操作**，
后来发现不是：只要通道数变了或者特征图尺寸变了，维度就对不上，`out + identity` 直接报错。
这个判断写错的话，第一次下采样（layer2 开头）就会炸。

还有个小坑是画样例预测图的时候中文全变成了方框，matplotlib 默认字体没有中文字形，
我懒得去配字体，干脆把图里的标签写成英文了，README 还是中文。

## 测试记录

**真实跑的，不是预期。**

数据：训练集只用了 10000 张（全量的五分之一），测试集用完整的 10000 张。
原因很现实，CPU 上一个 epoch 要 146 秒左右，用满 50000 张一轮就得 12 分钟，
8 轮接近 100 分钟，我耗不起。

命令和参数：

```
.venv\Scripts\python.exe -u train.py --epochs 8 --train-size 10000 --batch-size 128 `
  --lr 0.05 --weight-decay 5e-4 --seed 42 --out-dir ./results
```

8 轮的真实数字：

| epoch | train_loss | train_acc | test_loss | test_acc | 耗时 |
| --- | --- | --- | --- | --- | --- |
| 1 | 2.0911 | 25.14% | 1.9053 | 33.08% | 146.2s |
| 2 | 1.7096 | 35.22% | 2.4072 | 24.37% | 145.3s |
| 3 | 1.6814 | 37.03% | 1.5864 | 40.80% | 146.2s |
| 4 | 1.4906 | 44.40% | 1.4233 | 47.43% | 146.2s |
| 5 | 1.3735 | 49.82% | 1.3792 | 50.15% | 148.8s |
| 6 | 1.2631 | 53.34% | 1.3336 | 51.61% | 149.6s |
| 7 | 1.1678 | 56.97% | 1.2336 | 55.56% | 144.0s |
| 8 | 1.0931 | 60.43% | 1.1546 | **58.43%** | 143.6s |

- **训练总耗时 1170 秒，也就是 19.5 分钟**，8 轮跑满没中断
- **最终测试准确率 58.43%**，训练准确率 60.43%
- 参数量 11.174 M
- 随机猜是 10%，第一轮就有 33%，最后一轮 58%，loss 从 2.09 一路降到 1.09，是明确学到了东西

第 2 轮有个把我吓一跳的现象：测试 loss 从 1.9053 突然窜到 2.4072，
准确率反而掉回 24.37%。第一反应是代码写错了或者 BN 崩了。
后来反应过来是 BatchNorm 在训练早期 running_mean/running_var 还没稳，
测试时用的又是 running stats，加上那会儿 lr 还有 0.048 偏大，两边一凑就抖了一下；
第 3 轮 lr 降下来自己就恢复了。所以代码没改，这个现象我也没再复现第二次去细究，
算是记下来备查。

`results/sample_predictions.png` 里那批测试图 8 张对了 6 张，错的 2 张是
"飞机被认成船"（那张背景是一大片蓝色的海，看着确实像）和"汽车被认成卡车"。
curve 和原图都在 `results/` 里，数字在 `results/results.md` 和 `summary.json` 里，可对。

## 和原论文比还有哪些没做

差得还挺多的，说几个主要的：

- **准确率差一大截**。论文里 CIFAR-10 那组实验（20~110 层那几个）误差在 6.4%~8.8%，
  折下来准确率在 91% 往上，我这里 58.43%。
  不过这个真不能直接比，人家用满 50000 张训练图、训几百个 epoch，我只用了 1 万张、跑了 8 轮。
  我这个更像是"验证残差块能训起来"的最小实验，不是复现论文的准确率。
- **没做最关键的对照实验**。论文最有说服力的是 plain net（无 shortcut）和 ResNet 的对比曲线，
  "plain 网络加深反而变差、加了残差才好"，这个我完全没做。所以严格讲，
  我这轮实验**证明不了"残差块带来了提升"**，只能说"带残差块的网络能训到 58%"，
  这也是我这次最遗憾的一点。
- 论文还对比了网络深度（20/32/56/110 层）和 shortcut 的几种变体（投影 vs 恒等），都没做
- 没在 ImageNet 上跑，没有 7x7 stem 那条原始结构的实验

## 和我的研究方向的关系

我方向是知识增强的多 Agent 灾害态势推理与辅助决策，表面看跟卷积网络八竿子打不着，
但我觉得残差连接这个思路是能借过来的：

- 深层网络的问题是信息一路往前传会衰减、梯度会消失，shortcut 的做法是**别什么都让中间层重算，
  把原始输入直接抄近道送到后面**。多步推理链路（尤其灾害推理那种一长串环节）也有同样的毛病，
  前面的关键事实传到后面就被稀释了，那能不能也给推理链加一条"跳过中间步骤、把原始证据直接
  送到当前决策点"的支路？这是我最近在想的事。
- 多 Agent 之间传消息也可以类比成这样一个跨层的 shortcut：不要求每个 Agent 都从头推一遍，
  把上游某个 Agent 的结论直接挂到后面的汇聚点上。
- 说白了这层类比是我自己联想的，能不能站住脚得后面做实验才知道，先把话记在这。

做这个复现的实际收获，除了练手 PyTorch 和把一个经典结构亲手搭一遍，
更重要的是**磨了一遍"真实记录"的习惯**：下载速度、每个 epoch 的秒数、md5 校验、
那个 BN 的异常尖峰，全都如实写进 results.md，而不是挑好看的数字写。

## 下一步计划

1. 把 `--train-size` 提到 50000、epoch 提到 30 左右，看看准确率能到哪；时间上得攒一个晚上慢慢跑
2. 补上那个最关键的对照：写一个 `--no-shortcut` 开关，把残差加那行去掉，
   跑同样的配置，看准确率到底掉多少 —— 不然这次实验其实没验证到论文的核心结论
3. 画个 epoch 2 那个 BN 尖峰的对比图（开/关 BN 动量调参），确认一下我上面的解释对不对
4. 有余力再试试 1x1 卷积的 shortcut（投影）跟恒等映射哪个好，论文里也讨论了这个
