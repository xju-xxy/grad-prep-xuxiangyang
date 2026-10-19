# -*- coding: utf-8 -*-
# 自己造一个小分割数据集，省得去下 ISBI 那套细胞图（还要注册、还挺大）。
# 思路很土：64x64 的灰底图上随机画 1~3 个形状（圆/矩形/多边形），
# 画过的像素在掩膜里记成 1，其他是 0，最后给图加点高斯噪声。
# 这样"前景"就是几个亮块，U-Net 要学的就是把亮块圈出来。
import os
import numpy as np
from PIL import Image, ImageDraw

SIZE = 64          # 图像边长
N_TRAIN = 800      # 训练集张数
N_TEST = 200       # 测试集张数
OUT_DIR = "data"


def one_sample(rng):
    """画一张图和对应的二值掩膜（都是 SIZE x SIZE）。"""
    bg = int(rng.integers(15, 70))                     # 背景灰度
    img = Image.new("L", (SIZE, SIZE), bg)
    mask = Image.new("L", (SIZE, SIZE), 0)
    di = ImageDraw.Draw(img)
    dm = ImageDraw.Draw(mask)

    n_shape = int(rng.integers(1, 4))                  # 1~3 个形状
    for _ in range(n_shape):
        kind = rng.choice(["circle", "rect", "poly"])
        cx = int(rng.integers(14, SIZE - 14))          # 尽量别贴着边
        cy = int(rng.integers(14, SIZE - 14))
        fg = int(rng.integers(120, 255))               # 前景比背景亮

        if kind == "circle":
            r = int(rng.integers(5, 15))
            box = [cx - r, cy - r, cx + r, cy + r]
            di.ellipse(box, fill=fg)
            dm.ellipse(box, fill=1)

        elif kind == "rect":
            w = int(rng.integers(8, 24))
            h = int(rng.integers(8, 24))
            box = [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]
            di.rectangle(box, fill=fg)
            dm.rectangle(box, fill=1)

        else:
            k = int(rng.integers(3, 6))                # 3~5 个顶点
            ang = np.sort(rng.uniform(0, 2 * np.pi, k))
            rad = rng.uniform(6, 15, k)
            pts = [(cx + rad[i] * np.cos(ang[i]),
                    cy + rad[i] * np.sin(ang[i])) for i in range(k)]
            di.polygon(pts, fill=fg)
            dm.polygon(pts, fill=1)

    arr = np.asarray(img, dtype=np.float32)
    arr = arr + rng.normal(0, 8.0, arr.shape)          # 一点噪声，别太干净
    arr = np.clip(arr, 0, 255) / 255.0                 # 归一化到 [0,1]

    m = (np.asarray(mask) > 0).astype(np.float32)
    return arr, m


def build(n, seed):
    rng = np.random.default_rng(seed)
    imgs = np.zeros((n, 1, SIZE, SIZE), dtype=np.float32)
    masks = np.zeros((n, 1, SIZE, SIZE), dtype=np.float32)
    for i in range(n):
        a, m = one_sample(rng)
        imgs[i, 0] = a
        masks[i, 0] = m
    return imgs, masks


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    tr_x, tr_y = build(N_TRAIN, seed=42)
    te_x, te_y = build(N_TEST, seed=2026)   # 训练和测试用不同种子

    np.savez_compressed(os.path.join(OUT_DIR, "train.npz"), imgs=tr_x, masks=tr_y)
    np.savez_compressed(os.path.join(OUT_DIR, "test.npz"), imgs=te_x, masks=te_y)

    print("train imgs", tr_x.shape, "前景占比 %.3f" % tr_y.mean())
    print("test  imgs", te_x.shape, "前景占比 %.3f" % te_y.mean())
    print("已保存到", OUT_DIR)


if __name__ == "__main__":
    main()
