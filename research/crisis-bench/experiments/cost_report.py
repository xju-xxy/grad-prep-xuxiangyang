# -*- coding: utf-8 -*-
"""
A8 成本与延迟统计（CrisisBench v0.4）。
干什么：把各配置的实测 API 调用数 / prompt / completion / total tokens / 累计耗时
        按"运行单元"汇总（主运行、plus 裁判重打分、A7 自一致复核），输出
        results/RESULTS-cost.md 与 results/cost-summary.json。
口径说明：
  - 数据全部来自结果文件 record 的 usage 字段（run_experiment.py 实测记录），不做估算；
  - "主运行"的 usage 含被测智能体的推演调用与 1 次被测同侧裁判调用；
  - 协议总成本 = 主运行 + plus 裁判重打分（正式三裁判多数票口径需要）；
  - A7 自一致复核为额外的裁判稳定性实验，单列不计入协议成本。
用法：python cost_report.py
"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR.parent / "results"
ANALYSIS = RESULTS_DIR / "v0.4-analysis.json"
OUT_MD = RESULTS_DIR / "RESULTS-cost.md"
OUT_JSON = RESULTS_DIR / "cost-summary.json"

CONFIG_CN = {
    "single@glm-4-flash": "single（单研判员）",
    "multi@glm-4-flash": "multi（四角色串行）",
    "multi-noaudit@glm-4-flash": "multi-noaudit（去审核官）",
    "multi-verify@glm-4-flash": "multi-verify（+约束校验）",
    "single@glm-4-plus": "single（单研判员）",
    "multi@glm-4-plus": "multi（四角色串行）",
}


def read_usage(name):
    """读一个结果文件，返回 (场景数, 调用数, prompt, completion, total, 耗时秒)。"""
    if not name:
        return None
    p = RESULTS_DIR / name
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    n = calls = pt = ct = tt = sec = 0
    for r in data.get("records", []):
        u = r.get("usage") or {}
        if not u.get("total_tokens"):
            continue
        n += 1
        calls += u.get("调用数", 0)
        pt += u.get("prompt_tokens", 0)
        ct += u.get("completion_tokens", 0)
        tt += u.get("total_tokens", 0)
        sec += u.get("耗时秒", 0.0)
    if n == 0:
        return None
    return {"场景数": n, "调用数": calls, "prompt": pt, "completion": ct,
            "total": tt, "耗时秒": round(sec, 1)}


PROBE = RESULTS_DIR / "cost-probe" / "single-flash-probe.json"


def main():
    rep = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    configs = rep["configs"]
    rows, totals = [], {}
    for key, c in configs.items():
        model = key.split("@")[1]
        main_u = read_usage(c["file"])
        plus_u = read_usage(c.get("rescore_plus"))
        flash_u = read_usage(c.get("rescore_flash"))
        # single@glm-4-flash 的主运行记录于 usage 统计功能上线之前：
        # 用同提示词的独立复跑（--judge rule，仅生成）补生成成本，
        # 同侧 flash 裁判成本用其自一致复跑文件（同一裁判提示词、1 次调用/场景）代表。
        probe_u = None
        if main_u is None and key == "single@glm-4-flash":
            probe_u = read_usage(str(PROBE.relative_to(RESULTS_DIR)))
        comps = []
        if main_u:
            comps.append(("主运行（推演+同侧裁判）", main_u))
        elif probe_u:
            comps.append(("推演（同提示词独立实测）", probe_u))
            if flash_u:
                comps.append(("同侧 flash 裁判（自一致复跑，等价 1 次裁判）", flash_u))
        if plus_u:
            comps.append(("plus 裁判重打分", plus_u))
        entry = {"配置": key, "被测模型": model, "主运行": main_u, "探针": probe_u,
                 "plus裁判": plus_u, "A7自一致": flash_u, "明细": comps}
        proto = {}
        for _, u in comps:
            for k in ("调用数", "prompt", "completion", "total", "耗时秒"):
                proto[k] = proto.get(k, 0) + u[k]
            proto["场景数"] = u["场景数"]
        entry["协议合计"] = proto or None
        rows.append(entry)
        totals[key] = proto

    # 输出 markdown
    lines = ["# CrisisBench v0.4 成本与延迟（A8）", "",
             "> 口径：三裁判多数票协议下的实测 API 调用；数据源为结果文件记录的 usage 字段，无估算。",
             "> 「主运行」含被测智能体推演调用与 1 次被测同侧裁判调用；「plus 裁判」为正式口径所需的第二次 LLM 裁判；",
             "> 「A7 自一致」为裁判稳定性复核实验（额外开销，不计入协议成本）。", "",
             "## 1 协议总成本（每配置）", "",
             "| 配置 | 被测模型 | 场景数 | API 调用/场景 | 总 token/场景 | 累计耗时(s)/场景 | 全量总 token | 全量模型调用数 |",
             "|---|---|---|---|---|---|---|---|"]
    for key, e in ((k, r) for k, r in zip([r["配置"] for r in rows], rows)):
        p = e["协议合计"]
        if not p:
            lines.append("| %s | %s | — | — | — | — | — | — |" % (CONFIG_CN.get(key, key), e["被测模型"]))
            continue
        n = p["场景数"]
        lines.append("| %s | %s | %d | %.1f | %.0f | %.1f | %d | %d |" % (
            CONFIG_CN.get(key, key), e["被测模型"], n,
            p["调用数"] / n, p["total"] / n, p["耗时秒"] / n, p["total"], p["调用数"]))

    lines += ["", "## 2 分运行单元明细", "",
              "| 配置 | 运行单元 | 场景数 | API 调用 | prompt tokens | completion tokens | total tokens | 累计耗时(s) |",
              "|---|---|---|---|---|---|---|---|"]
    for e in rows:
        units = list(e["明细"])
        if e["主运行"] and e["A7自一致"]:
            units.append(("A7 自一致复核（额外，不计入协议成本）", e["A7自一致"]))
        for unit, u in units:
            lines.append("| %s [%s] | %s | %d | %d | %d | %d | %d | %.1f |" % (
                CONFIG_CN.get(e["配置"], e["配置"]), e["被测模型"], unit, u["场景数"], u["调用数"],
                u["prompt"], u["completion"], u["total"], u["耗时秒"]))

    lines += ["", "## 3 相对成本（以 single 为 1.0）", "",
              "| 配置 | 相对 token | 相对调用数 | 相对耗时 |",
              "|---|---|---|---|"]
    for key in ("single@glm-4-flash", "multi@glm-4-flash", "multi-verify@glm-4-flash",
                "multi-noaudit@glm-4-flash", "single@glm-4-plus", "multi@glm-4-plus"):
        if key not in totals or "single@glm-4-flash" not in totals:
            continue
        if not totals.get(key) or not totals.get("single@glm-4-flash"):
            continue
        b = totals["single@glm-4-flash"]
        t = totals[key]
        lines.append("| %s [%s] | %.2f | %.2f | %.2f |" % (
            CONFIG_CN.get(key, key), key.split("@")[1], t["total"] / b["total"], t["调用数"] / b["调用数"],
            t["耗时秒"] / max(b["耗时秒"], 1e-9)))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_JSON.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()