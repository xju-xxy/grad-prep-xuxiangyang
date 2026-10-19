# -*- coding: utf-8 -*-
# 经典 U-Net（论文原版结构：收缩路径 double conv+maxpool，扩展路径上采样+跳接concat）。
# 我用 base=16 缩了通道数，因为图和任务都很小，通道开太大纯属浪费 CPU 时间。
import torch
import torch.nn as nn


def double_conv(in_c, out_c):
    """论文里的 '两个 3x3 卷积'，我顺手加了 BN，不然小数据上 loss 抖得厉害。"""
    return nn.Sequential(
        nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_c),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_c, out_c, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_c),
        nn.ReLU(inplace=True),
    )


class UNet(nn.Module):
    def __init__(self, in_ch=1, out_ch=1, base=16):
        super().__init__()
        c1, c2, c3, c4, c5 = base, base * 2, base * 4, base * 8, base * 16

        # 收缩路径（下采样）：每下一次通道翻倍
        self.enc1 = double_conv(in_ch, c1)   # 64 -> 64
        self.enc2 = double_conv(c1, c2)      # 32 -> 32
        self.enc3 = double_conv(c2, c3)      # 16 -> 16
        self.enc4 = double_conv(c3, c4)      # 8  -> 8
        self.pool = nn.MaxPool2d(2)

        self.bottleneck = double_conv(c4, c5)  # 4 -> 4

        # 扩展路径（上采样）：up 之后和左边同尺寸的编码器特征 concat 再 double conv
        self.up4 = nn.ConvTranspose2d(c5, c4, kernel_size=2, stride=2)
        self.dec4 = double_conv(c4 + c4, c4)   # concat 后通道是两倍
        self.up3 = nn.ConvTranspose2d(c4, c3, kernel_size=2, stride=2)
        self.dec3 = double_conv(c3 + c3, c3)
        self.up2 = nn.ConvTranspose2d(c3, c2, kernel_size=2, stride=2)
        self.dec2 = double_conv(c2 + c2, c2)
        self.up1 = nn.ConvTranspose2d(c2, c1, kernel_size=2, stride=2)
        self.dec1 = double_conv(c1 + c1, c1)

        # 最后的 1x1 卷积，输出 1 通道 logits（不接 sigmoid，交给 BCEWithLogits 管）
        self.head = nn.Conv2d(c1, out_ch, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))

        d4 = self.up4(b)
        d4 = self.dec4(torch.cat([e4, d4], dim=1))   # 跳接：编码器的 e4
        d3 = self.up3(d4)
        d3 = self.dec3(torch.cat([e3, d3], dim=1))   # 跳接：e3
        d2 = self.up2(d3)
        d2 = self.dec2(torch.cat([e2, d2], dim=1))   # 跳接：e2
        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([e1, d1], dim=1))   # 跳接：e1
        return self.head(d1)


if __name__ == "__main__":
    net = UNet()
    n_param = sum(p.numel() for p in net.parameters())
    x = torch.randn(2, 1, 64, 64)
    y = net(x)
    print("参数量：%.2f M" % (n_param / 1e6))
    print("输入", tuple(x.shape), "-> 输出", tuple(y.shape))
