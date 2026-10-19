"""gen_data.py —— 造一份合成的"时空知识图谱"数据。

拿不到论文里的 SafeGraph / TFNSW 真实数据，所以自己造一个虚拟的
"传感器 / 栅格点"网络来复现 SSTKG 的核心思想：

  - N 个点撒在 2D 平面上，点与点之间有距离；
  - 每个点有一个静态的"底子"(base)，还有一份"记录量"(cnt)，
    用来模仿论文里"记录量比值"这个先验；
  - 每天的值 = 静态底子 + 上一天邻居按距离衰减施加的影响 + 一点季节波动 + 噪声。

生成时刻意用论文那套影响力公式来造"真值"，这样后面建模时
就能拿学到的权重跟已知的"真值权重"对照，看看公式到底准不准。

跑法（在 sstkg-demo 目录下）：
  python gen_data.py
输出：
  data/synthetic_stkg.json   实体表 + 完整时序值
  data/edges.csv             邻居关系（含真实影响力权重）
"""

import csv
import json
import math
import os

import numpy as np

# ---------------- 数据生成用的参数（想改规模改这里就行） ----------------
CONFIG = dict(
    seed=20261019,     # 固定随机种子，保证每次生成一样的图
    n_nodes=100,       # 实体数量
    plane=100.0,       # 平面边长，坐标撒在 [0, plane] x [0, plane]
    theta=16.0,        # 距离阈值：超过它的两实体不算邻居，关系直接过滤
    n_days=30,         # 时间跨度 T（离散 time slot）
    rho=0.8,           # 每个实体收到的邻居影响力占比（保证过程稳定，<1）
    noise_std=8.0,     # 观测噪声标准差（调大一点，acc@10 才有区分度）
    shock_day=24,      # 第 24 天（落在测试段）给某个"震中"实体加一次冲击，看它怎么往外扩散
    shock_size=30.0,
)


def distance_matrix(coords):
    """N x N 的欧氏距离矩阵。"""
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff ** 2).sum(-1))


def influence_shape(dist, cnt_src, cnt_tgt, theta):
    """论文里那条影响力"形状"公式（还没归一化）:

    权重 ∝ (邻居记录量 / 自身记录量) × log(1 + 阈值 / 距离)

    前半截是记录量比值，后半截是带 log 的距离项：离得越近，log 越大，影响越强。
    距离超过阈值的关系在构图时就被过滤掉了，这里只对 d <= theta 的点算。
    """
    cnt_ratio = cnt_src / cnt_tgt          # 邻居记录量 / 自身记录量
    dist_term = np.log(1.0 + theta / np.maximum(dist, 1e-6))
    return cnt_ratio * dist_term


def main():
    rng = np.random.default_rng(CONFIG["seed"])
    n = CONFIG["n_nodes"]
    plane = CONFIG["plane"]
    theta = CONFIG["theta"]
    T = CONFIG["n_days"]

    # 1) 撒点 + 给每个点静态属性和记录量
    coords = rng.uniform(0.0, plane, size=(n, 2))
    base = rng.uniform(10.0, 30.0, size=n)          # 静态底子（论文里的 static 底色）
    cnt = rng.integers(50, 501, size=n).astype(float)  # 记录量，模仿 SafeGraph 的访问记录数
    amp = rng.uniform(2.0, 6.0, size=n)             # 每个点自己的季节波动幅度
    # 相位跟着坐标走，而且变化很慢：位置越近的点，季节波动相位越接近，
    # 这样邻居上一刻的值才真能"还原"当前实体的波动（相位差太大会对不上）
    phase = (coords[:, 0] + coords[:, 1]) / plane * 0.75

    D = distance_matrix(coords)

    # 2) 构图：距离在 (0, theta] 之内才算邻居，之外的关系直接丢掉
    neighbor_mask = (D > 0.0) & (D <= theta)

    # 3) 按公式算"真实"影响力权重，再按每个目标实体归一化到总量 rho
    #    注意方向：真值权重 true_w[j, i] 表示 j 对 i 的施加的影响
    raw = influence_shape(D, cnt[:, None], cnt[None, :], theta)  # raw[j,i] = cnt_j/cnt_i * log(...)
    raw = np.where(neighbor_mask, raw, 0.0)
    col_sum = raw.sum(axis=0, keepdims=True)
    true_w = np.where(col_sum > 0, raw / np.maximum(col_sum, 1e-12) * CONFIG["rho"], 0.0)

    # 4) 沿着时间演化：每天的值 = 底子 + 邻居昨天的影响 + 季节波动 + 噪声
    X = np.zeros((T, n))
    X[0] = base + amp * np.sin(phase) + rng.normal(0.0, CONFIG["noise_std"], n)
    for t in range(1, T):
        seasonal = amp * np.sin(2.0 * math.pi * t / 7.0 + phase)  # 周期 7 天的波动
        neighbor_term = true_w.T @ X[t - 1]                        # 邻居昨天对今天的影响
        X[t] = base + neighbor_term + seasonal + rng.normal(0.0, CONFIG["noise_std"], n)

    # 5) 第 shock_day 天给"震中"点加一次冲击，看它顺着影响力往外扩散
    shock_node = int(np.argmin(np.abs(coords[:, 0] - plane / 2) + np.abs(coords[:, 1] - plane / 2)))
    X[CONFIG["shock_day"], shock_node] += CONFIG["shock_size"]

    # 6) 统计一下图长什么样，打印出来让我心里有数
    deg = neighbor_mask.sum(axis=0)
    edge_rows = []
    for i in range(n):
        for j in range(n):
            if neighbor_mask[j, i]:
                edge_rows.append(dict(
                    source=j, target=i,
                    distance=float(D[j, i]),
                    cnt_source=float(cnt[j]), cnt_target=float(cnt[i]),
                    cnt_ratio=float(cnt[j] / cnt[i]),
                    dist_term=float(math.log(1.0 + theta / D[j, i])),
                    true_weight=float(true_w[j, i]),
                ))

    os.makedirs("data", exist_ok=True)
    payload = dict(
        config=CONFIG,
        theta=theta,
        shock_node=shock_node,
        nodes=[
            dict(id=i, x=float(coords[i, 0]), y=float(coords[i, 1]),
                 base=float(base[i]), cnt=float(cnt[i]),
                 amp=float(amp[i]), phase=float(phase[i]))
            for i in range(n)
        ],
        values=X.tolist(),
    )
    with open(os.path.join("data", "synthetic_stkg.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(os.path.join("data", "edges.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(edge_rows[0].keys()))
        writer.writeheader()
        writer.writerows(edge_rows)

    print(f"实体数 N = {n}，天数 T = {T}，距离阈值 theta = {theta}")
    print(f"邻居关系条数 = {len(edge_rows)}，平均每个实体的邻居数 = {edge_rows and len(edge_rows)/n:.1f}")
    print(f"每个实体邻居数：min={deg.min()} max={deg.max()} mean={deg.mean():.1f}")
    print(f"孤立实体（0 邻居）数量 = {int((deg == 0).sum())}")
    print(f"冲击发生在第 {CONFIG['shock_day']} 天，震中实体 id = {shock_node}")
    print(f"数值范围：min={X.min():.1f} max={X.max():.1f} mean={X.mean():.1f}")
    print("已写出 data/synthetic_stkg.json 和 data/edges.csv")


if __name__ == "__main__":
    main()
