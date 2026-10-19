"""eval.py —— 把 systems.json 里的系统逐个喂给打标工具，装成一张对比表

做的事：
1. 读 systems.json，逐个调 classify.py 的打标函数，结果缓存到
   results/predictions.json，跑挂了重跑会跳过已完成的条目。
2. 把模型输出的标签按 schema.json 归一化成规范值，防止它写"沙盒"还是写
   "Sandbox"对不上。
3. 生成两张表：一张四维坐标对比表（comparison.csv / comparison.md），
   一张四个坑的褒贬核对矩阵。
4. 顺手统计每个维度的标签分布，看这些系统在坐标系里各占哪个格子。

用法：.venv\\Scripts\\python.exe eval.py
"""

import csv
import json
import os

from classify import load_schema, build_system_prompt, classify

SCH = load_schema()
SYSTEM_PROMPT = build_system_prompt(SCH)

PRED_FILE = os.path.join("results", "predictions.json")
CSV_FILE = os.path.join("results", "comparison.csv")
MD_FILE = os.path.join("results", "comparison.md")

# ---- 从 schema 建规范值查表 ----
ENV_OPTS = SCH["dimensions"][0]["options"]
PROF_OPTS = SCH["dimensions"][1]["options"]
COMM = SCH["dimensions"][2]
CAP = SCH["dimensions"][3]
PITFALLS = SCH["pitfalls"]

PARADIGM_OPTS = COMM["subfacets"][0]["options"]
STRUCTURE_OPTS = COMM["subfacets"][1]["options"]
FEEDBACK_OPTS = CAP["subfacets"][0]["options"]
MECHANISM_OPTS = CAP["subfacets"][1]["options"]

SPLIT_CHARS = ["；", ";", "、", ",", "，", "/", "|", "+", " "]


def _flatten(value):
    """把模型可能给出的 str / list / 分隔符串统一成 list[str]"""
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(v) for v in value]
    else:
        items = [str(value)]
    out = []
    for it in items:
        for ch in SPLIT_CHARS:
            it = it.replace(ch, "\n")
        for part in it.split("\n"):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _match_one(token, options):
    """把单个 token 对到某个选项，返回规范 key（= 选项的 key 字段）；对不上返回 None"""
    t = token.strip()
    if not t:
        return None
    low = t.lower()
    for opt in options:
        if t == opt["key"] or t == opt.get("cn"):
            return opt["key"]
        if opt["key"].lower() in low or (opt.get("cn") and opt["cn"] in t):
            return opt["key"]
    return None


def norm_single(value, options):
    for tok in _flatten(value):
        hit = _match_one(tok, options)
        if hit:
            return hit
    return str(value).strip() if value else None


def norm_multi(value, options):
    hits = []
    for tok in _flatten(value):
        hit = _match_one(tok, options)
        if hit and hit not in hits:
            hits.append(hit)
    return hits


def _field(dim, key, default=None):
    """容错取值：模型可能把 dimension 写成 {label:..} 也可能写成裸值"""
    if not isinstance(dim, dict):
        return dim if dim is not None else default
    return dim.get(key, default)


def normalize(pred):
    """把模型的一坨输出拍成统一的规范字段"""
    env = norm_single(_field(pred.get("environment_interface"), "label"), ENV_OPTS)
    prof = norm_single(_field(pred.get("agent_profiling"), "label"), PROF_OPTS)
    comm = pred.get("agent_communication") or {}
    cap = pred.get("capability_acquisition") or {}
    pit = pred.get("pitfalls") or {}
    return {
        "env": env,
        "prof": prof,
        "paradigm": norm_multi(comm.get("paradigm"), PARADIGM_OPTS),
        "structure": norm_multi(comm.get("structure"), STRUCTURE_OPTS),
        "feedback": norm_multi(cap.get("feedback"), FEEDBACK_OPTS),
        "mechanism": norm_multi(cap.get("mechanism"), MECHANISM_OPTS),
        "pit": {p["key"]: bool((pit.get(p["key"]) or {}).get("touched")) for p in PITFALLS},
    }


def load_preds():
    if os.path.exists(PRED_FILE):
        with open(PRED_FILE, encoding="utf-8") as f:
            return {r["id"]: r for r in json.load(f)}
    return {}


def save_preds(store):
    os.makedirs("results", exist_ok=True)
    with open(PRED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(store.values()), f, ensure_ascii=False, indent=1)


def run_all(items, store):
    for it in items:
        if it["id"] in store and store[it["id"]].get("pred"):
            print(f"[{it['id']}] 已有缓存，跳过")
            continue
        print(f"[{it['id']}] 调用 GLM ...")
        try:
            pred, raw = classify(it["desc"], SCH, SYSTEM_PROMPT)
        except Exception as e:
            pred, raw = {"__error__": str(e)}, str(e)
        store[it["id"]] = {"id": it["id"], "name": it["name"], "tag": it["tag"],
                           "desc": it["desc"], "pred": pred, "raw": raw}
        save_preds(store)
        if "__error__" in pred:
            print(f"    -> 失败：{pred['__error__']}")
        else:
            n = normalize(pred)
            print(f"    -> 环境={n['env']} 人设={n['prof']} 范式={n['paradigm']} "
                  f"结构={n['structure']} 反馈={n['feedback']} 机制={n['mechanism']}")


def build_tables(items, store):
    os.makedirs("results", exist_ok=True)
    header = ["系统", "来源", "环境接口", "人设", "通信范式", "通信结构",
              "反馈来源", "能力机制"] + [p["cn"] for p in PITFALLS]
    rows = []
    for it in items:
        r = store[it["id"]]
        n = normalize(r["pred"]) if "__error__" not in r["pred"] else None
        if n is None:
            rows.append([r["name"], r["tag"], "ERROR", "ERROR", "", "", "", ""] + ["?"] * len(PITFALLS))
            continue
        row = [r["name"], r["tag"], n["env"], n["prof"],
               "/".join(n["paradigm"]), "/".join(n["structure"]),
               "/".join(n["feedback"]), "/".join(n["mechanism"])]
        row += ["√" if n["pit"][p["key"]] else "×" for p in PITFALLS]
        rows.append(row)

    # CSV
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    # Markdown
    def md_cell(x):
        return str(x).replace("\n", " ").replace("|", "｜")

    lines = ["# 四维坐标对比表" + "\n",
             "> 用综述（arXiv:2402.01680）的四维框架给 12 个多智能体系统打的标签（GLM-4-Flash，温度 0.1）。"
             "标签是模型输出按 schema 归一化后的结果，原始输出和判定依据见 predictions.json。\n"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for row in rows:
        lines.append("| " + " | ".join(md_cell(c) for c in row) + " |")
    lines.append("")
    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return header, rows


def print_summary(items, store):
    dist = {"env": {}, "prof": {}, "paradigm": {}, "structure": {},
            "feedback": {}, "mechanism": {}}
    N = 0
    for it in items:
        r = store[it["id"]]
        if "__error__" in r["pred"]:
            continue
        N += 1
        n = normalize(r["pred"])
        dist["env"][n["env"]] = dist["env"].get(n["env"], 0) + 1
        dist["prof"][n["prof"]] = dist["prof"].get(n["prof"], 0) + 1
        for k in ("paradigm", "structure", "feedback", "mechanism"):
            for v in n[k]:
                dist[k][v] = dist[k].get(v, 0) + 1

    print("\n" + "=" * 70)
    print(f"标签分布（N={N} 个成功打标的系统）")
    print("=" * 70)
    labels = {"env": "环境接口", "prof": "人设", "paradigm": "通信范式",
              "structure": "通信结构", "feedback": "反馈来源", "mechanism": "生长机制"}
    for k, cn in labels.items():
        s = "，".join(f"{kk} {vv}" for kk, vv in sorted(dist[k].items(), key=lambda x: -x[1]))
        print(f"{cn:<8}: {s}")

    print("\n" + "=" * 70)
    print("四个坑的褒贬核对（√=触及/缓解，×=没涉及）")
    print("=" * 70)
    counts = {p["key"]: 0 for p in PITFALLS}
    for it in items:
        r = store[it["id"]]
        if "__error__" in r["pred"]:
            continue
        n = normalize(r["pred"])
        for p in PITFALLS:
            if n["pit"][p["key"]]:
                counts[p["key"]] += 1
    for p in PITFALLS:
        print(f"{p['cn']:<12}: {counts[p['key']]}/{N} 个系统触及")


def main():
    with open("systems.json", encoding="utf-8") as f:
        systems = json.load(f)["systems"]

    store = load_preds()
    run_all(systems, store)
    header, rows = build_tables(systems, store)
    print_summary(systems, store)

    print(f"\n对比表已写入 {CSV_FILE} 和 {MD_FILE}")
    print(f"原始输出（含判定依据）已写入 {PRED_FILE}")


if __name__ == "__main__":
    main()
