# -*- coding: utf-8 -*-
"""
按更新后的 match 词表重算 6 个主结果文件的 rule 段（原地覆写）。

为什么需要：
  analyze_results.py 的 combined() 只读取已存储的 rule 值，不会重算规则分。
  本轮对 scenarios.json 的 4 处 match 词做了收窄/删除，必须把这些变更
  重新套到每个主记录存储的 answer 上，才能得到正确的多数票口径。

用法：python rescore_rules.py
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_FILE = os.path.join(BASE_DIR, "..", "scenarios", "scenarios.json")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")

MAIN_FILES = [
    "exp-all-multi-20261018-230557.json",          # multi@glm-4-flash
    "exp-all-multi-20261019-034322.json",          # multi@glm-4-plus
    "exp-all-multi-noaudit-20261019-003210.json",  # multi-noaudit@glm-4-flash
    "exp-all-multi-verify-20261019-013605.json",   # multi-verify@glm-4-flash
    "exp-all-single-20261018-222022.json",         # single@glm-4-flash
    "exp-all-single-20261019-030325.json",         # single@glm-4-plus
]

# 本轮被修改的要点编号（用于校验：这些点在哪些记录上由 1→0 或 0→1）
CHANGED_PIDS = {"F8", "R3", "D6"}
CHANGED_SCENES = {"S012", "S020", "S028", "S001"}
PREFIX = {"事实层": "F", "推理层": "R", "决策层": "D"}


def load_scenarios():
    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["scenarios"]}


def rule_score(scene, answer):
    """与 run_experiment.rule_score 完全一致：命中任意 match 词即得 1。"""
    results = []
    for layer in ["事实层", "推理层", "决策层"]:
        for i, it in enumerate(scene["rubric"][layer], 1):
            hit = any(kw in answer for kw in it["match"])
            results.append({
                "层": layer, "序号": i, "要点": it["要点"],
                "得分": 1 if hit else 0,
                "理由": "关键词命中" if hit else "未命中关键词",
            })
    return results


def summarize(details, layer):
    idx = [d for d in details if d["层"] == layer]
    return sum(d["得分"] for d in idx), len(idx)


def old_score_map(rec):
    out = {}
    for d in rec.get("rule", {}).get("details", []):
        if d.get("层") and d.get("序号"):
            out[PREFIX[d["层"]] + str(d["序号"])] = int(d.get("得分", 0))
    return out


def main():
    scenarios = load_scenarios()
    changes = []
    for fname in MAIN_FILES:
        path = os.path.join(RESULTS_DIR, fname)
        if not os.path.exists(path):
            print("!! 缺失文件：%s" % fname)
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        n_rec = 0
        for rec in data.get("records", []):
            scene = scenarios.get(rec["scene_id"])
            if scene is None:
                continue
            before = old_score_map(rec)
            details = rule_score(scene, rec.get("answer") or "")
            rec["rule"] = {"details": details}
            for layer in ["事实层", "推理层", "决策层"]:
                got, total = summarize(details, layer)
                rec["rule"][layer] = {"得分": got, "总数": total,
                                      "命中率": round(got / total, 3) if total else 0}
            after = {PREFIX[d["层"]] + str(d["序号"]): d["得分"] for d in details}
            if rec["scene_id"] in CHANGED_SCENES:
                for pid in after:
                    if before.get(pid) != after.get(pid):
                        changes.append((fname, rec["scene_id"], pid,
                                        before.get(pid), after.get(pid)))
            n_rec += 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已重算并覆写：%s（%d 条记录）" % (fname, n_rec))

    print("\n== 受影响场景的逐点变化（旧→新）==")
    if not changes:
        print("（无变化）")
    for fname, sid, pid, b, a in changes:
        short = fname.replace("exp-all-", "").replace(".json", "")
        print("  %-42s %s %s：%s -> %s" % (short, sid, pid, b, a))


if __name__ == "__main__":
    main()
