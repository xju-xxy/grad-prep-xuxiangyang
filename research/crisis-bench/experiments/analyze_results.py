# -*- coding: utf-8 -*-
"""
CrisisBench v0.4 全量分析脚本（A5/A9/矩阵/裁定表 一站式）

干什么：
  1. 自动扫描 results 目录（stamp >= 2026-10-18 22:00），配对主实验与重裁判文件；
  2. 合成三裁判多数票口径（规则 + flash + plus），输出 36 场景 × 各配置 三层得分矩阵；
  3. 统计检验（A5）：要点级 McNemar、场景级 Wilcoxon 符号秩、自助法 95% CI；
  4. 裁判可靠性（RQ3/A7）：flash vs plus 的 Cohen's kappa、flash 自一致率；
  5. 错误类型学（A9）：9 行错误分布表（论文 8 类 + 推理杂项）；
  6. Verifier 交叉统计：对每份主答案跑 V1~V5，输出违规数与推算交叉清单（RQ4）；
  7. 人工裁定表（A6）：抽 8 个场景导出分歧要点清单供本人打勾。

产物（写入 results/）：
  v0.4-analysis.json           结构化统计（后续图表与论文数据源）
  RESULTS-v0.4.md              人读版结果矩阵与统计表
  adjudication-sampled.md      人工裁定表（A6）

用法：python analyze_results.py
"""
import json
import math
import os
import random
import re
import statistics
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
CUTOFF = datetime.strptime("20261018-220000", "%Y%m%d-%H%M%S")

sys.path.insert(0, BASE_DIR)
from verifier import load_scenarios, load_specs, run_on_answer  # noqa: E402

PREFIX = {"事实层": "F", "推理层": "R", "决策层": "D"}


# ---------------- 工具 ----------------
def read_all_files():
    """扫描 results：返回 {文件名: {stamp, meta, records}}，剔除 cutoff 之前与 partial。"""
    out = {}
    for name in os.listdir(RESULTS_DIR):
        if not name.endswith(".json") or name.endswith(".partial.json"):
            continue
        m = re.search(r"(\d{8}-\d{6})\.json$", name)
        if not m:
            continue
        try:
            stamp = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
        except ValueError:
            continue
        if stamp < CUTOFF:
            continue
        with open(os.path.join(RESULTS_DIR, name), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("meta", {}).get("partial"):
            continue
        out[name] = {"stamp": stamp, "meta": data.get("meta", {}), "records": data.get("records", [])}
    return out


def pair_groups(files):
    """主文件 + 其 rescore 文件分组。返回 [(主文件名, 主data, {"plus": rescore名, "flash": rescore名})...]"""
    mains = {n: d for n, d in files.items() if not d["meta"].get("来源文件")}
    resc = [n for n in files if files[n]["meta"].get("来源文件")]
    groups = []
    for name, d in mains.items():
        plus = flash = None
        for r in resc:
            if files[r]["meta"]["来源文件"] == name:
                if "glm-4-plus" in r:
                    plus = r
                elif "glm-4-flash" in r:
                    flash = r
        groups.append((name, d, {"plus": plus, "flash": flash}))
    return groups


def score_map(record, key="llm"):
    """record[key].details → {编号: 得分}"""
    out = {}
    for d in record.get(key, {}).get("details", []):
        if d.get("层") and d.get("序号"):
            out[PREFIX[d["层"]] + str(d["序号"])] = int(d.get("得分", 0))
    return out


def combined(rec, group):
    """合成三方判分：rule（主文件）、flash（主文件）、plus（rescore 文件）。返回 {pid: {rule,f,p,maj}}"""
    rule_m = score_map(rec, "rule")
    flash_m = score_map(rec, "llm")
    plus_m = score_map(group["recs_by_id"][rec["scene_id"]], "llm") if group["plus_recs"] else {}
    ids = set(rule_m) | set(flash_m) | set(plus_m)
    out = {}
    for pid in ids:
        votes = [rule_m.get(pid, 0), flash_m.get(pid, 0), plus_m.get(pid, 0)]
        out[pid] = {"rule": votes[0], "flash": votes[1], "plus": votes[2],
                    "maj": 1 if sum(votes) >= 2 else 0}
    return out


def layer_rates(judge_map, scene):
    """按层汇总 {层: (got,total,rate)}。judge_map: pid→0/1"""
    out = {}
    for layer in ["事实层", "推理层", "决策层"]:
        n = len(scene["rubric"][layer])
        got = sum(judge_map.get(PREFIX[layer] + str(i + 1), 0) for i in range(n))
        out[layer] = (got, n, round(got / n, 3) if n else 0)
    return out


def cohen_kappa(pairs):
    """两裁判逐要点 0/1 配对 → Cohen's kappa。"""
    n = len(pairs)
    if n == 0:
        return None
    a = sum(1 for x, y in pairs if x == 1 and y == 1)
    b = sum(1 for x, y in pairs if x == 1 and y == 0)
    c = sum(1 for x, y in pairs if x == 0 and y == 1)
    d = sum(1 for x, y in pairs if x == 0 and y == 0)
    po = (a + d) / n
    pe = (a + b) / n * (a + c) / n + (c + d) / n * (b + d) / n
    if pe >= 1:
        return 1.0
    return (po - pe) / (1 - pe)


def mcnemar(b, c):
    """要点级 McNemar：不一致对 b（A=0,B=1）、c（A=1,B=0）。返回 (p, method)。"""
    n = b + c
    if n == 0:
        return None, "无不一致对"
    if n < 25:
        p = 2 * sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) * 0.5 ** n
        return p, "二项精确"
    chi = (abs(b - c) - 1) ** 2 / n
    p = math.erfc(math.sqrt(chi / 2))  # 1 自由度卡方 → erfc(z/√2)
    return p, "卡方(连续校正)"


def wilcoxon(diffs):
    """配对 Wilcoxon 符号秩（Z 近似），diffs 为成对差值列表。返回 (W, z, p, n)。"""
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n < 6:
        return None, None, None, n
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        avg = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    W = sum(r for r, x in zip(ranks, d) if x > 0)
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (W - mu) / sigma if sigma else 0
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return W, z, p, n


def bootstrap_ci(diffs, B=10000, seed=42):
    """成对差值的自助法 95% CI（分位数法）。"""
    rng = random.Random(seed)
    n = len(diffs)
    means = [sum(rng.choices(diffs, k=n)) / n for _ in range(B)]
    means.sort()
    return round(means[int(0.025 * B)], 4), round(means[int(0.975 * B)], 4)


# ---------------- 错误类型学 ----------------
def classify_error(pid, point_text, layer, scene, verifier_viols, judge_reasons, is_contradiction_scene):
    """
    把一条『失分要点』归入错误类（返回类名；不回则不分类）。
    优先级：推算 > 矛盾处理 > 冲突/陷阱 > 资源超配 > 笼统/对象缺失 > 事实丢失 > 推理杂项
    """
    if point_text.startswith("推算"):
        return "数值推算失败"
    if is_contradiction_scene and any(k in point_text for k in ("保守", "统一口径", "矛盾", "核灾", "逐点")):
        return "矛盾处理失当"
    if layer == "决策层":
        # 决策层：先用 Verifier 违规与裁判理由判类
        if any(k in point_text for k in ("绕行", "抢通")) and verifier_viols.get("conflict"):
            return "情报冲突"
        if any(t in point_text for t in ("否决", "识破", "不得", "严禁", "禁止", "须绕", "管控")):
            return "陷阱未识破"
        if verifier_viols.get("resource") and any(k in point_text for k in ("调", "派", "动用", "调用", "增援", "资源", "舟", "直升机", "无人机")):
            return "资源超配"
        reasons = " ".join(judge_reasons.get(pid, []))
        if "笼统" in reasons or "泛" in reasons:
            return "笼统决策"
        if "对象" in reasons or "无具体" in reasons:
            return "对象缺失"
        return "决策未达标(其他)"
    if layer == "推理层":
        if any(k in point_text for k in ("运力", "容量", "缺口", "核算", "帐篷", "安置")):
            return "资源超配"
        return "推理缺失(其他)"
    return "事实丢失"


# ---------------- Verifier 交叉 ----------------
def verifier_pass(scene, specs, rec):
    vr = run_on_answer(scene, specs.get(scene["id"], {}), rec.get("answer") or "")
    return vr


# ---------------- 主流程 ----------------
def main():
    scenarios = {s["id"]: s for s in load_scenarios()}
    specs = load_specs()
    files = read_all_files()
    groups = pair_groups(files)

    def group_meta(name):
        return files[name]["meta"]

    # 主文件按 (config, model) 选最新
    chosen = {}
    for name, d, pair in groups:
        m = group_meta(name)
        key = (m.get("config"), m.get("model"))
        if key not in chosen or d["stamp"] > chosen[key][0]:
            chosen[key] = (d["stamp"], name, d, pair)

    def get(key):
        return chosen.get(key)

    report = {"meta": {"时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, "configs": {}, "tests": {},
              "kappa": {}, "self_consistency": {}, "errors": {}, "verifier": {}, "adjudication": []}

    # ---- 每个配置：合成多数票 + 层得分 + 矩阵 ----
    configs = {}
    for key, (_, name, d, pair) in sorted(chosen.items()):
        cfg, model = key
        plus_recs = {r["scene_id"]: r for r in files[pair["plus"]]["records"]} if pair["plus"] else {}
        flash2_recs = {r["scene_id"]: r for r in files[pair["flash"]]["records"]} if pair["flash"] else {}
        recs = {r["scene_id"]: r for r in d["records"]}
        matrix, maj_layer = {}, {}
        for sid in sorted(recs):
            jm = combined(recs[sid], {"plus_recs": plus_recs, "recs_by_id": plus_recs})
            matrix[sid] = layer_rates(jm, scenarios[sid])
            maj_layer[sid] = {k: v for k, v in matrix[sid].items()}
        configs[cfg + "@" + model] = {
            "file": name, "rescore_plus": pair["plus"], "rescore_flash": pair["flash"],
            "matrix": maj_layer, "recs": recs, "plus_recs": plus_recs, "flash2_recs": flash2_recs,
        }
    report["configs"] = {k: {"file": v["file"], "rescore_plus": v["rescore_plus"],
                             "rescore_flash": v["rescore_flash"], "matrix": v["matrix"]}
                         for k, v in configs.items()}

    # ---- 配对对比 ----
    def compare(a_key, b_key, label):
        if a_key not in configs or b_key not in configs:
            report["tests"][label] = "数据缺失"
            return
        A, B = configs[a_key], configs[b_key]
        b_c, c_c, per_scene_diff, all_pairs = 0, 0, [], []
        for sid in sorted(A["recs"]):
            if sid not in B["recs"]:
                continue
            jm_a = combined(A["recs"][sid], {"plus_recs": A["plus_recs"], "recs_by_id": A["plus_recs"]})
            jm_b = combined(B["recs"][sid], {"plus_recs": B["plus_recs"], "recs_by_id": B["plus_recs"]})
            ta, tb = 0, 0
            for pid in jm_a:
                x, y = jm_a[pid]["maj"], jm_b.get(pid, {}).get("maj", 0)
                all_pairs.append((x, y))
                ta += x
                tb += y
                if x == 0 and y == 1:
                    b_c += 1
                elif x == 1 and y == 0:
                    c_c += 1
            per_scene_diff.append((tb / len(jm_b)) - (ta / len(jm_a)))
        p_mc, method = mcnemar(b_c, c_c)
        W, z, p_w, n_w = wilcoxon(per_scene_diff)
        ci = bootstrap_ci(per_scene_diff)
        mean_diff = statistics.mean(per_scene_diff) if per_scene_diff else None
        report["tests"][label] = {
            "对": "%s vs %s" % (a_key, b_key),
            "mcnemar": {"b(A0B1)": b_c, "c(A1B0)": c_c, "p": p_mc, "method": method},
            "wilcoxon": {"W": W, "z": round(z, 3) if z is not None else None,
                         "p": round(p_w, 4) if p_w is not None else None, "n": n_w},
            "bootstrap_ci_95": list(ci),
            "mean_diff_pp": round(mean_diff * 100, 2) if mean_diff is not None else None,
        }

    compare("multi@glm-4-flash", "single@glm-4-flash", "RQ1: multi vs single")
    compare("multi-noaudit@glm-4-flash", "multi@glm-4-flash", "RQ2: noaudit vs multi")
    compare("multi-verify@glm-4-flash", "multi@glm-4-flash", "RQ4: verify vs multi")
    compare("multi@glm-4-plus", "single@glm-4-plus", "A2: plus模型 multi vs single")
    compare("multi@glm-4-plus", "multi@glm-4-flash", "A2: 被测模型 plus vs flash")

    # ---- kappa 与自一致 ----
    for key, cfgd in configs.items():
        pairs_fp, self_f = [], 0
        n_self = 0
        for sid in cfgd["recs"]:
            jm = combined(cfgd["recs"][sid], {"plus_recs": cfgd["plus_recs"], "recs_by_id": cfgd["plus_recs"]})
            for pid, v in jm.items():
                pairs_fp.append((v["flash"], v["plus"]))
            if cfgd["flash2_recs"]:
                m2 = score_map(cfgd["flash2_recs"][sid], "llm")
                m1 = score_map(cfgd["recs"][sid], "llm")
                for pid in m1:
                    n_self += 1
                    if m1.get(pid, 0) == m2.get(pid, 0):
                        self_f += 1
        report["kappa"]["flash_vs_plus@" + key] = round(cohen_kappa(pairs_fp), 3)
        if n_self:
            report["self_consistency"]["flash@" + key] = round(self_f / n_self, 3)

    # ---- 错误类型学（多数票口径） ----
    ERR_ORDER = ["事实丢失", "数值推算失败", "资源超配", "情报冲突", "陷阱未识破",
                 "笼统决策", "对象缺失", "矛盾处理失当", "推理缺失(其他)", "决策未达标(其他)"]
    for key, cfgd in configs.items():
        counts = {e: 0 for e in ERR_ORDER}
        total_loss = 0
        for sid in cfgd["recs"]:
            scene = scenarios[sid]
            jm = combined(cfgd["recs"][sid], {"plus_recs": cfgd["plus_recs"], "recs_by_id": cfgd["plus_recs"]})
            vr = run_on_answer(scene, specs.get(sid, {}), cfgd["recs"][sid].get("answer") or "")
            viols = {"resource": bool(vr["resource_violations"]), "conflict": bool(vr["trap_violations"]),
                     "trap": bool(vr["trap_violations"]), "capacity": bool(vr["capacity_violations"])}
            reasons = {}
            for jname in ("llm",):
                for dd in cfgd["recs"][sid].get(jname, {}).get("details", []):
                    reasons[PREFIX[dd["层"]] + str(dd["序号"])] = reasons.get(PREFIX[dd["层"]] + str(dd["序号"]), "") + dd.get("理由", "")
            is_contra = scene.get("类别") == "信息矛盾"
            for layer in ["事实层", "推理层", "决策层"]:
                for i, pt in enumerate(scene["rubric"][layer], 1):
                    pid = PREFIX[layer] + str(i + 1)
                    if jm[pid]["maj"] == 0:
                        total_loss += 1
                        cls = classify_error(pid, pt["要点"], layer, scene, viols, reasons, is_contra)
                        counts[cls] += 1
        report["errors"][key] = {"counts": counts, "total_loss": total_loss}

    # ---- Verifier 交叉统计 ----
    for key, cfgd in configs.items():
        agg = {"calc_ok": 0, "calc_total": 0, "resource": 0, "trap": 0, "capacity": 0}
        for sid in cfgd["recs"]:
            vr = run_on_answer(scenarios[sid], specs.get(sid, {}), cfgd["recs"][sid].get("answer") or "")
            agg["calc_ok"] += sum(1 for v in vr["calc"].values() if v["pass"])
            agg["calc_total"] += len(vr["calc"])
            agg["resource"] += len(vr["resource_violations"])
            agg["trap"] += len(vr["trap_violations"])
            agg["capacity"] += len(vr["capacity_violations"])
        report["verifier"][key] = agg

    # ---- 分歧裁定表（A6：对参照组 multi 抽 8 个场景） ----
    ref = configs.get("multi@glm-4-flash")
    if ref:
        sids = sorted(ref["recs"])
        rng = random.Random(42)
        sampled = rng.sample(sids, min(8, len(sids)))
        rows = []
        for sid in sorted(sampled):
            jm = combined(ref["recs"][sid], {"plus_recs": ref["plus_recs"], "recs_by_id": ref["plus_recs"]})
            for layer in ["事实层", "推理层", "决策层"]:
                for i, pt in enumerate(scenarios[sid]["rubric"][layer], 1):
                    pid = PREFIX[layer] + str(i + 1)
                    v = jm[pid]
                    if v["rule"] != v["flash"] or v["flash"] != v["plus"]:
                        rows.append({"场景": sid, "编号": pid, "要点": pt["要点"],
                                     "规则": v["rule"], "flash": v["flash"], "plus": v["plus"],
                                     "多数票": v["maj"], "人工裁定(0/1)": ""})
        report["adjudication"] = rows

    # ---- 落盘 ----
    out_json = os.path.join(RESULTS_DIR, "v0.4-analysis.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    md = build_markdown(report)
    with open(os.path.join(RESULTS_DIR, "RESULTS-v0.4.md"), "w", encoding="utf-8") as f:
        f.write(md)

    adj_md = build_adjudication_md(report)
    with open(os.path.join(RESULTS_DIR, "adjudication-sampled.md"), "w", encoding="utf-8") as f:
        f.write(adj_md)

    print("写入 results/v0.4-analysis.json、RESULTS-v0.4.md、adjudication-sampled.md")
    print("配置组：%s" % list(report["configs"].keys()))
    print("检验：%s" % json.dumps(report["tests"], ensure_ascii=False))


def build_markdown(report):
    lines = ["# CrisisBench v0.4 全量实验结果（36 场景）", "",
             "> 生成时间 %s；口径：三裁判多数票（规则 / glm-4-flash / glm-4-plus，2-of-3）" % report["meta"]["时间"], ""]
    for key in ("single@glm-4-flash", "multi@glm-4-flash", "multi-noaudit@glm-4-flash",
                "multi-verify@glm-4-flash", "single@glm-4-plus", "multi@glm-4-plus"):
        if key not in report["configs"]:
            continue
        c = report["configs"][key]
        lines.append("## %s" % key)
        lines.append("")
        lines.append("| 场景 | 事实层 | 推理层 | 决策层 | 综合 |")
        lines.append("|---|---|---|---|---|")
        for sid, m in sorted(c["matrix"].items()):
            f_, r_, dd_ = m["事实层"], m["推理层"], m["决策层"]
            tot = sum(x[1] for x in (f_, r_, dd_))
            got = sum(x[0] for x in (f_, r_, dd_))
            lines.append("| %s | %s | %s | %s | %.1f%% |" %
                         (sid, "%d/%d" % f_[:2], "%d/%d" % r_[:2], "%d/%d" % dd_[:2], got / tot * 100))
        lines.append("")
    lines.append("## 配对检验（多数票口径）")
    lines.append("")
    lines.append("| 对比 | McNemar(p) | 场景级均值差(pp) | Wilcoxon(p) | 自助法 95% CI(pp) |")
    lines.append("|---|---|---|---|---|")
    for label, t in report["tests"].items():
        if isinstance(t, str):
            lines.append("| %s | %s | - | - | - |" % (label, t))
            continue
        ci = t["bootstrap_ci_95"]
        lines.append("| %s | %s(%s) | %s | %s | [%s, %s] |" %
                     (label, t["mcnemar"]["p"], t["mcnemar"]["method"], t["mean_diff_pp"],
                      t["wilcoxon"]["p"], ci[0], ci[1]))
    lines.append("")
    lines.append("## 裁判可靠性")
    lines.append("")
    lines.append("| 口径 | Cohen's kappa | flash 自一致率 |")
    lines.append("|---|---|---|")
    for k, v in report["kappa"].items():
        lines.append("| %s | %s | %s |" % (k, v, report["self_consistency"].get("flash@" + k.split("@", 1)[1], "-")))
    lines.append("")
    lines.append("## 错误类型学（多数票口径、失分要点计数）")
    lines.append("")
    err_keys = list(report["errors"].keys())
    if err_keys:
        order = ["事实丢失", "数值推算失败", "资源超配", "情报冲突", "陷阱未识破",
                 "笼统决策", "对象缺失", "矛盾处理失当", "推理缺失(其他)", "决策未达标(其他)"]
        lines.append("| 错误类 | " + " | ".join(err_keys) + " |")
        lines.append("|---|" + "---|" * len(err_keys))
        for e in order:
            lines.append("| %s | %s |" % (e, " | ".join(str(report["errors"][k]["counts"].get(e, 0)) for k in err_keys)))
        lines.append("")
    lines.append("## Verifier 确定性检出（逐配置）")
    lines.append("")
    lines.append("| 配置 | 推算合规/总数 | 资源超配 | 陷阱 | 运力缺口 |")
    lines.append("|---|---|---|---|---|")
    for k, v in report["verifier"].items():
        lines.append("| %s | %d/%d | %d | %d | %d |" % (k, v["calc_ok"], v["calc_total"],
                                                       v["resource"], v["trap"], v["capacity"]))
    return "\n".join(lines)


def build_adjudication_md(report):
    lines = ["# 人工裁定表（A6：分歧要点复核）", "",
             "说明：以下为 multi（glm-4-flash）配置抽样 8 个场景中三裁判判定不一致的要点。",
             "请你逐条在最后一列填写你的裁定（0/1），并顺手标注要点是否合理（应急专家口径）。", ""]
    if not report["adjudication"]:
        return "\n".join(lines) + "\n（暂无分歧项）\n"
    lines.append("| 场景 | 编号 | 要点 | 规则 | flash | plus | 多数票 | 人工裁定(0/1) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in report["adjudication"]:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |  |" %
                     (r["场景"], r["编号"], r["要点"].replace("|", "/"),
                      r["规则"], r["flash"], r["plus"], r["多数票"]))
    return "\n".join(lines)


if __name__ == "__main__":
    main()