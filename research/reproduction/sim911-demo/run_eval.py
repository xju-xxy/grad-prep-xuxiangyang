"""run_eval.py —— 主评测：受控生成 + 验证闭环，附带公平性演示和消融

跑三块：
1. 主评测（full）：20 组「事件 × 画像」，走完整的"生成→校验→打回重生成"
2. 公平性演示：同一个事件（心脏骤停、独居老人），换上 8 个不同画像各生成一遍，
   看画像注入到底改不改说话风格
3. 消融：把画像注入关掉（no_profile）、把整套知识库关掉（no_kb），
   和 full 比地址真实率和画像一致率——对应论文"关掉知识构建指标血崩"

所有生成结果都写在 results/raw.json 里，中断重跑会自动续上（缓存命中不重调 API）。

用法：
  .venv\\Scripts\\python.exe run_eval.py          # 三块一起跑（有缓存）
  .venv\\Scripts\\python.exe run_eval.py --fresh  # 丢掉缓存全部重跑
"""

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from generate import BASE_DIR, load_kb
from verify import AddressIndex, generate_with_retry

RESULTS_DIR = os.path.join(BASE_DIR, "results")
RAW = os.path.join(RESULTS_DIR, "raw.json")

# 主评测挑 20 个事件（尽量覆盖不同事件类型），画像按 P1~P8 轮着来
MAIN_EVENTS = ["E01", "E03", "E04", "E05", "E06", "E07", "E09", "E10",
               "E11", "E13", "E15", "E17", "E19", "E20", "E21", "E23",
               "E25", "E27", "E29", "E30"]
PROFILE_CYCLE = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]

# 公平性演示用的事件：心脏骤停、独居老人在家倒地，最能体现不同人来报的差别
FAIRNESS_EVENT = "E01"

_lock = threading.Lock()


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def build_plan(kb):
    """固定好要跑哪些组合，存成 plan.json，谁都能照着重跑"""
    ev = {e["id"]: e for e in kb["events"]}
    pf = {p["id"]: p for p in kb["profiles"]}

    main = [(MAIN_EVENTS[i], PROFILE_CYCLE[i % len(PROFILE_CYCLE)])
            for i in range(len(MAIN_EVENTS))]
    fairness = [(FAIRNESS_EVENT, p["id"]) for p in kb["profiles"]]
    return {"main": main, "fairness": fairness, "ev": ev, "pf": pf}


def run_condition(kb, addr_index, plan, condition, pairs, raw, fresh):
    """跑一个条件下的所有 (event, profile) 组合，结果写进 raw[condition]"""
    use_profile = condition != "no_profile"
    use_kb = condition != "no_kb"
    cache = {} if fresh else raw.get(condition, {})
    raw[condition] = cache
    ev, pf = plan["ev"], plan["pf"]

    todo = []
    for eid, pid in pairs:
        key = f"{eid}|{pid}"
        if fresh or key not in cache:
            todo.append((key, eid, pid))

    print(f"[{condition}] 待跑 {len(todo)} 组 / 共 {len(pairs)} 组", flush=True)
    if not todo:
        return

    done = {"n": 0}

    def work(item):
        key, eid, pid = item
        rec = generate_with_retry(ev[eid], pf[pid], kb, addr_index,
                                  kb["profiles"],
                                  use_profile=use_profile, use_kb=use_kb,
                                  max_rounds=3)
        return key, rec

    with ThreadPoolExecutor(max_workers=3) as pool:
        for key, rec in pool.map(work, todo):
            with _lock:
                cache[key] = rec
                done["n"] += 1
                if done["n"] % 3 == 0:
                    save_json(RAW, raw)
                    print(f"  {condition} 已跑 {done['n']}/{len(todo)}",
                          flush=True)
    save_json(RAW, raw)


# ------------------------- 指标 -------------------------

def rate(records, fn):
    if not records:
        return 0.0
    return sum(1 for r in records if fn(r)) / len(records)


def summarize(records):
    return {
        "n": len(records),
        "地址真实率_最终": rate(records, lambda r: r["final"]["fact_ok"]),
        "地址真实率_首轮": rate(records, lambda r: r["first"]["fact_ok"]),
        "格式通过率_首轮": rate(records, lambda r: r["first"]["format_ok"]),
        "画像一致率_首轮": rate(records, lambda r: r["first"]["profile_ok"]),
        "画像一致率_最终": rate(records, lambda r: r["final"]["profile_ok"]),
        "平均重试轮数": (sum(r["n_rounds"] for r in records) / len(records)
                    if records else 0.0),
        "一次通过率": rate(records, lambda r: r["n_rounds"] == 1),
    }


def pct(x):
    return f"{x * 100:.1f}%"


def main():
    sys.stdout.reconfigure(line_buffering=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fresh = "--fresh" in sys.argv[1:]

    kb = load_kb()
    addr_index = AddressIndex(kb["addresses"])
    plan = build_plan(kb)
    save_json(os.path.join(RESULTS_DIR, "plan.json"),
              {"main": plan["main"], "fairness": plan["fairness"]})
    raw = {} if fresh else load_json(RAW, {})

    conditions = [("full", plan["main"]),
                  ("no_profile", plan["main"]),
                  ("no_kb", plan["main"]),
                  ("fairness", plan["fairness"])]
    for cond, pairs in conditions:
        run_condition(kb, addr_index, plan, cond, pairs, raw, fresh)

    # ---- 主评测 + 消融汇总 ----
    stats = {c: summarize(list(raw[c].values()))
             for c, _ in conditions}

    # ---- 公平性：按画像分组 ----
    fair_by_profile = {}
    for key, r in raw["fairness"].items():
        fair_by_profile.setdefault(r["profile_id"], []).append(r)

    metrics = {"conditions": stats,
               "fairness_by_profile": {
                   pid: summarize(recs)
                   for pid, recs in sorted(fair_by_profile.items())}}
    save_json(os.path.join(RESULTS_DIR, "metrics.json"), metrics)

    # ---- 生成结果表 ----
    write_tables(kb, plan, raw, stats, fair_by_profile)
    print("全部跑完，结果在 results/")
    print(f"  full: 地址真实率 {pct(stats['full']['地址真实率_最终'])}、"
          f"画像一致率(首轮) {pct(stats['full']['画像一致率_首轮'])}、"
          f"平均 {stats['full']['平均重试轮数']:.2f} 轮")


def write_tables(kb, plan, raw, stats, fair_by_profile):
    ev, pf = plan["ev"], plan["pf"]
    L = []

    L.append("## 主评测与消融（真实跑出来的数字）\n")
    L.append("| 条件 | 组合数 | 地址真实率(最终) | 地址真实率(首轮) | "
             "画像一致率(首轮) | 画像一致率(最终) | 格式通过率(首轮) | 平均重试轮数 | 一次通过率 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    name = {"full": "完整（画像+知识库）",
            "no_profile": "消融：关掉画像注入",
            "no_kb": "消融：关掉知识库(地址表+协议)",
            "fairness": "公平性演示"}
    for c in ["full", "no_profile", "no_kb", "fairness"]:
        s = stats[c]
        L.append(f"| {name[c]} | {s['n']} | {pct(s['地址真实率_最终'])} | "
                 f"{pct(s['地址真实率_首轮'])} | {pct(s['画像一致率_首轮'])} | "
                 f"{pct(s['画像一致率_最终'])} | {pct(s['格式通过率_首轮'])} | "
                 f"{s['平均重试轮数']:.2f} | {pct(s['一次通过率'])} |")
    L.append("")

    L.append("## 公平性：同一事件、8 个画像各生成一遍（事件 E01 心脏骤停/独居老人）\n")
    L.append("| 画像 | 类别 | 判定画像 | 一致 | 地址真实 | 轮数 | 呼救者原话（截断） |")
    L.append("|---|---|---|---|---|---|---|")
    for pid, recs in sorted(fair_by_profile.items()):
        r = recs[0]
        fin = r["final"]
        tag = "弱势群体" if pf[pid]["tag"] == "vulnerable" else "普通"
        utt = r["rounds"][-1]["parsed"].get("呼救者原话", "").replace("\n", " ")
        if len(utt) > 46:
            utt = utt[:46] + "…"
        L.append(f"| {pid} {pf[pid]['name']} | {tag} | {fin['profile_guess']} | "
                 f"{'✅' if fin['profile_ok'] else '❌'} | "
                 f"{'✅' if fin['fact_ok'] else '❌'} | {r['n_rounds']} | {utt} |")
    L.append("")

    with open(os.path.join(RESULTS_DIR, "tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
