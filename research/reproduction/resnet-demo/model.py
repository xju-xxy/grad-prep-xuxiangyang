"""CIFAR 版 ResNet-18。

跟论文里给 ImageNet 用的原版差别就两点：
1. 开头不用 7x7 卷积 + maxpool，改成 3x3 卷积直接上去（32x32 的图本来就不大，
   再来个 7x7 下采样就太小了）。
2. 后面每个 stage 的 stride 该下采样还是下采样，这个没动。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BasicBlock(nn.Module):
    """最基础的残差块：两层 3x3 卷积，外面套一条 shortcut。"""

    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        # 只有当 通道数变了 或者 特征图尺寸变了，才需要那层 1x1 卷积把维度调齐。
        # 我一开始以为 shortcut 永远是个空操作，后来发现不是 —— 维度对不上直接加会报错。
        if stride != 1 or in_planes != planes * self.expansion:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, planes * self.expansion, kernel_size=1,
                          stride=stride, bias=False),
                nn.BatchNorm2d(planes * self.expansion),
            )

    def forward(self, x):
        identity = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + identity
        return F.relu(out)


class ResNetCIFAR(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super().__init__()
        self.in_planes = 64

        # CIFAR 版 stem：3x3、不降采样、不加 maxpool
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)

        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)

        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for s in strides:
            layers.append(block(self.in_planes, planes, s))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))       # 3x3 stem
        out = self.layer1(out)                      # 32x32
        out = self.layer2(out)                      # 16x16
        out = self.layer3(out)                      # 8x8
        out = self.layer4(out)                      # 4x4
        out = self.avgpool(out)
        out = torch.flatten(out, 1)
        return self.fc(out)


def resnet18_cifar(num_classes=10):
    return ResNetCIFAR(BasicBlock, [2, 2, 2, 2], num_classes=num_classes)


if __name__ == "__main__":
    # 单独跑一下，确认前向 shape 和参数量对得上
    net = resnet18_cifar()
    n_params = sum(p.numel() for p in net.parameters())
    x = torch.randn(2, 3, 32, 32)
    y = net(x)
    print("输入:", tuple(x.shape), "输出:", tuple(y.shape))
    print("参数量: %.2f M" % (n_params / 1e6))
