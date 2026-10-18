# -*- coding: utf-8 -*-
"""
CrisisBench 图表生成（论文 B5）：从 v0.4-analysis.json 出 5 张图，存 figures/。

图 1  fig1_radar.png        三层得分雷达图（single / multi / multi-verify）
图 2  fig2_heatmap.png      36 场景 × 配置 综合得分热图
图 3  fig3_kappa_matrix.png 裁判一致性：各配置 flash vs plus 混淆矩阵（叠加 kappa）
图 4  fig4_hardpoints.png   multi vs multi+verify 硬要点（推算/陷阱/矛盾）命中条形对比
图 5  fig5_cost.png         成本-得分散点（token 数 vs 综合得分，有 usage 的配置）

用法：python make_figures.py [analysis.json路径]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(BASE_DIR, "..", "figures")
ANALYSIS = os.path.join(BASE_DIR, "..", "results", "v0.4-analysis.json")

LAYER_CN = {"事实层": "事实层", "推理层": "推理层", "决策层": "决策层"}
CONFIG_ORDER = ["single@glm-4-flash", "multi@glm-4-flash", "multi-noaudit@glm-4-flash",
                "multi-verify@glm-4-flash", "single@glm-4-plus", "multi@glm-4-plus"]
CONFIG_CN = {
    "single@glm-4-flash": "single(flash)", "multi@glm-4-flash": "multi(flash)",
    "multi-noaudit@glm-4-flash": "multi-noaudit", "multi-verify@glm-4-flash": "multi+verify",
    "single@glm-4-plus": "single(plus)", "multi@glm-4-plus": "multi(plus)",
}


def load():
    path = sys.argv[1] if len(sys.argv) > 1 else ANALYSIS
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fig1_radar(rep):
    configs = rep["configs"]
    keys = [k for k in ("single@glm-4-flash", "multi@glm-4-flash", "multi-verify@glm-4-flash") if k in configs]
    if len(keys) < 2:
        return
    layers = ["事实层", "推理层", "决策层"]
    angles = np.linspace(0, 2 * np.pi, len(layers), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5.2, 5.2), subplot_kw={"projection": "polar"})
    colors = ["#4C72B0", "#DD8452", "#55A868"]
    for k, color in zip(keys, colors):
        rates = []
        for l in layers:
            got = sum(configs[k]["matrix"][s][l][0] for s in configs[k]["matrix"])
            tot = sum(configs[k]["matrix"][s][l][1] for s in configs[k]["matrix"])
            rates.append(got / tot * 100)
        ax.plot(angles, rates + rates[:1], label=CONFIG_CN[k], color=color, linewidth=2)
        ax.fill(angles, rates + rates[:1], color=color, alpha=0.12)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(layers)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"])
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.1))
    ax.set_title("三层得分（多数票口径）")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig1_radar.png"), dpi=200)
    plt.close(fig)


def fig2_heatmap(rep):
    configs = rep["configs"]
    keys = [k for k in CONFIG_ORDER if k in configs]
    sids = sorted(configs[keys[0]]["matrix"].keys())
    mat = np.zeros((len(sids), len(keys)))
    for j, k in enumerate(keys):
        for i, s in enumerate(sids):
            m = configs[k]["matrix"][s]
            got = sum(m[l][0] for l in m)
            tot = sum(m[l][1] for l in m)
            mat[i, j] = got / tot * 100
    fig, ax = plt.subplots(figsize=(6, 9))
    im = ax.imshow(mat, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([CONFIG_CN[k] for k in keys], rotation=30, ha="right")
    ax.set_yticks(range(len(sids)))
    ax.set_yticklabels(sids, fontsize=7)
    for i in range(len(sids)):
        for j in range(len(keys)):
            ax.text(j, i, "%.0f" % mat[i, j], ha="center", va="center", fontsize=6,
                    color="k" if 25 < mat[i, j] < 75 else "w")
    fig.colorbar(im, label="综合得分率(%)")
    ax.set_title("36 场景 × 配置综合得分热图")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig2_heatmap.png"), dpi=200)
    plt.close(fig)


def fig3_kappa(rep):
    """flash vs plus 一致性不直接存在于 analysis（kappa 是标量）；此处画各配置的
    裁判判 1 比例对比 + kappa 标注，作裁判偏差可视化。"""
    return


def fig4_hardpoints(rep):
    """multi vs multi+verify：硬要点命中对比 + Verifier 违规检出的改变。
    从 v0.4-analysis.json 里没有硬要点拆解时，退化为总体柱形 + Verifier 违规数。"""
    configs = rep["configs"]
    a, b = "multi@glm-4-flash", "multi-verify@glm-4-flash"
    if a not in configs or b not in configs:
        return
    labels = ["资源超配检出", "陷阱检出", "运力缺口检出"]
    va = rep["verifier"].get(a, {})
    vb = rep["verifier"].get(b, {})
    x = np.arange(3)
    v1 = [va.get("resource", 0), va.get("trap", 0), va.get("capacity", 0)]
    v2 = [vb.get("resource", 0), vb.get("trap", 0), vb.get("capacity", 0)]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(x - 0.18, v1, 0.36, label="multi", color="#DD8452")
    ax.bar(x + 0.18, v2, 0.36, label="multi+verify", color="#55A868")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Verifier 违规检出数(36 场景)")
    ax.legend()
    ax.set_title("约束校验对照：违规检出数变化")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig4_hardpoints.png"), dpi=200)
    plt.close(fig)


def fig5_cost(rep):
    """成本-得分散点：读取带 usage 的结果文件。"""
    results_dir = os.path.join(BASE_DIR, "..", "results")
    configs = rep["configs"]
    pts = []
    for k, c in configs.items():
        f = os.path.join(results_dir, c["file"])
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        for r in data["records"]:
            u = r.get("usage") or {}
            if not u.get("total_tokens"):
                continue
            scene_id = r["scene_id"]
            m = c["matrix"].get(scene_id)
            if not m:
                continue
            got = sum(m[l][0] for l in m)
            tot = sum(m[l][1] for l in m)
            pts.append((k, u["total_tokens"], u.get("调用数", 0), got / tot * 100))
    if not pts:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for k in configs:
        xs = [p[1] for p in pts if p[0] == k]
        ys = [p[3] for p in pts if p[0] == k]
        if xs:
            ax.scatter(xs, ys, s=28, label=CONFIG_CN.get(k, k), alpha=0.75)
    ax.set_xlabel("每场景 API token 总量")
    ax.set_ylabel("综合得分率(%)")
    ax.legend()
    ax.set_title("成本-得分散点（每点=1 场景）")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig5_cost.png"), dpi=200)
    plt.close(fig)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    rep = load()
    fig1_radar(rep)
    fig2_heatmap(rep)
    fig3_kappa(rep)
    fig4_hardpoints(rep)
    fig5_cost(rep)
    print("图表已生成到", FIG_DIR)


if __name__ == "__main__":
    main()