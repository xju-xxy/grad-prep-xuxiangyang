# U-Net 复现结果

> 对应复现：unet-demo（自己合成的数据，CPU 训练，2026年10月）
> 环境：系统 python 3.14 + torch 2.13.0+cpu（没建 .venv，本机已经装好了 torch）

## 跑的法子

```
python gen_data.py
python train.py --epochs 30
python predict.py
```

数据是我自己造的：训练 800 张、测试 200 张，都是 64x64 灰度图，前景（要分割的形状）像素占比
训练集 0.108、测试集 0.107。网络 base=16，参数量 1.94M。

## 训练日志（这段是 train.py 真实打印出来的，原样抄）

```
训练集 800 张，测试集 200 张，batch=16，epochs=30
epoch  1/30  loss 0.9988  test_dice 0.9794  <- 存权重
epoch  2/30  loss 0.7378  test_dice 0.9906  <- 存权重
epoch  3/30  loss 0.5436  test_dice 0.9992  <- 存权重
epoch  4/30  loss 0.3826  test_dice 0.9995  <- 存权重
epoch  5/30  loss 0.2556  test_dice 0.9995  <- 存权重
epoch  6/30  loss 0.1681  test_dice 0.9996  <- 存权重
epoch  7/30  loss 0.1135  test_dice 0.9998  <- 存权重
epoch  8/30  loss 0.0795  test_dice 0.9998  <- 存权重
epoch  9/30  loss 0.0627  test_dice 0.9998
epoch 10/30  loss 0.0416  test_dice 0.9999  <- 存权重
epoch 11/30  loss 0.0328  test_dice 0.9999  <- 存权重
epoch 12/30  loss 0.0256  test_dice 0.9999  <- 存权重
epoch 13/30  loss 0.0205  test_dice 0.9999  <- 存权重
epoch 14/30  loss 0.0171  test_dice 0.9999
epoch 15/30  loss 0.0145  test_dice 1.0000  <- 存权重
epoch 16/30  loss 0.0131  test_dice 0.9997
epoch 17/30  loss 0.0117  test_dice 0.9999
epoch 18/30  loss 0.0098  test_dice 0.9999
epoch 19/30  loss 0.0085  test_dice 1.0000  <- 存权重
epoch 20/30  loss 0.0076  test_dice 0.9999
epoch 21/30  loss 0.0070  test_dice 0.9999
epoch 22/30  loss 0.0062  test_dice 1.0000
epoch 23/30  loss 0.0058  test_dice 1.0000  <- 存权重
epoch 24/30  loss 0.0051  test_dice 1.0000
epoch 25/30  loss 0.0047  test_dice 1.0000
epoch 26/30  loss 0.0043  test_dice 1.0000
epoch 27/30  loss 0.0039  test_dice 1.0000
epoch 28/30  loss 0.0036  test_dice 1.0000  <- 存权重
epoch 29/30  loss 0.0038  test_dice 1.0000
epoch 30/30  loss 0.0036  test_dice 0.9996
训练结束，共 880.6 秒（14.68 分钟），最好 test_dice=1.0000
```

耗时 880.6 秒，平均一轮大概 29 秒（CPU 上，800 张 64x64）。

## 测试集最终指标（predict.py 输出，用 epoch 28 那个最优权重）

```
测试集 200 张
Dice  平均 0.99998  中位 1.00000  最低 0.99777  最高 1.00000
IoU   平均 0.99996  中位 1.00000  最低 0.99556  最高 1.00000
像素准确率（含背景）1.00000
```

完整数值也存了一份在 `metrics.json`。对比图在 `pred_samples.png`，
三列分别是原图 | 真值掩膜 | 预测，一共 6 行，最后两行是我特意挑的最差的两张。
肉眼上看最差那两张也就是形状尖角处差一两个像素，所以 Dice 只掉到 0.9978。

## 这个结果其实有点"尴尬"

Dice 几乎顶到 1，但我不敢拿它当成绩。原因很简单：我自己造的题太简单了。
形状是纯色块、和背景灰度差得远、边界干净、还没有粘连，U-Net 这种结构基本闭着眼也能分对。
换句话说，这组数字只证明了"网络连通了、损失在正常下降、跳跃连接接对了、推理能出图"，
证明不了模型强。原论文在 ISBI 细胞图上比的是挑战赛排名和它们的评测指标，
历史图像也不一样，我这边没法把两个数字摆一起比，所以干脆不比。

要让它有说服力，得把合成数据做难：让形状互相贴合/重叠、模糊边界、把前景背景灰度拉近、
减少训练张数，那时候 Dice 掉下来才有看头。这条我记在"下一步"里了。

## 值得一提的两次翻车

- 第一次跑 train.py 直接报 `RuntimeError: The size of tensor a (16) must match the size of tensor b (8)`。
  原因是验证集 200 张按 batch=16 切，最后一批只剩 8 张，我在累加 Dice 时把 (batch,) 的张量
  加到 Python 浮点数上，导致第一次攒成一个长度 16 的向量，第二次变成长度 8，维度对不上。
  改成先 `.sum()` 成标量再累加就好了。
- predict.py 第一次出图，图里中文标题全是方框。matplotlib 默认字体没有中文字形，
  要在代码里指定 `Microsoft YaHei`。这个跟 U-Net 没关系，纯环境坑。
