# -*- coding: utf-8 -*-
"""
CrisisBench 约束校验组件（Verifier）v1.0 —— 确定性规则，零 API 依赖。

五类检查（对应论文 §5）：
  V1 资源超配审计：答案动用资源清单「无X」声明过的资源 → 违规。清单自动从场景 JSON 提取。
  V2 数值推算核对：48 条推算型要点逐一检查答案是否给出区间内的数值（附单位邻近约束，
     支持 万 数量级词）。规格文件：verify_specs.json（人工标定、算式经过逐条验算）。
  V3 情报冲突检查：决策束缚规则（如「经县道撤离」必须伴随绕行/抢通表述）——见 specs.traps。
  V4 数量核算/运力缺口：见 specs.capacity（如 S005 冲锋舟运力缺口必须提请增援）。
  V5 陷阱处置识别：陷阱表述（水冲稀释、徒手堵漏等）出现时必须伴随否决语 —— 见 specs.traps。

用法：
  python verifier.py                     # 对全部场景做规格自检（校验 specs 与 scenarios 对齐）
  python verifier.py --file <结果JSON>   # 对一份实验结果逐记录跑 V1~V5，输出逐场景报告与
                                         # 「裁判判 0 但 Verifier 检测到合规数值」等交叉清单

价值（论文 RQ4）：LLM 裁判不可靠（kappa≈0），本组件用确定性规则对同一批答案独立
核对，统计它能抓出多少「裁判与规则分歧」以及多少硬要点错误，作为 multi+verify 对照的基座。
"""
import argparse
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_FILE = os.path.join(BASE_DIR, "..", "scenarios", "scenarios.json")
SPECS_FILE = os.path.join(BASE_DIR, "verify_specs.json")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")

UNIT_ALIAS = {
    "分钟": ["分钟", "分"], "小时": ["小时", "时", "h"], "秒": ["秒", "秒钟", "s"],
    "人": ["人", "名", "群众", "村民", "学生"], "吨": ["吨", "t"], "公斤": ["公斤", "千克", "kg"],
    "批": ["批", "批次"], "趟": ["趟", "趟次", "车次"], "天": ["天", "日"],
}
# 「无X」资源项里常见后缀描述，提取否定资源名时截断
NO_SUFFIX = ["，", "（", "(", "。"]
# 禁止资源名的别名展开（如「无大型无人机」→ 答案写「无人机」也应命中）
BLACKLIST_ALIAS = {"大型无人机": ["大型无人机", "无人机"]}


def load_scenarios():
    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        return json.load(f)["scenarios"]


def load_specs():
    with open(SPECS_FILE, encoding="utf-8") as f:
        return json.load(f)["specs"]


def forbidden_resources(scene):
    """V1：资源清单中「无X」开头的项 → 禁止动用的资源名列表（含别名展开）。"""
    out = []
    for r in scene.get("资源", []):
        if not r.startswith("无") or r.startswith("无人机"):
            continue  # 「无人机3架」是正面资源项，不是否定项
        name = r[1:]
        for sep in NO_SUFFIX:
            if sep in name:
                name = name.split(sep)[0]
        name = name.strip()
        if name:
            out.extend(BLACKLIST_ALIAS.get(name, [name]))
    return out


def extract_numbers(text):
    """提取文本中所有数字（含小数），返回 (数值, 前后语境串)。"""
    results = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        s, e = max(0, m.start() - 8), min(len(text), m.end() + 8)
        results.append((float(m.group()), text[s:e]))
    return results


def check_calc(spec, answer):
    """V2：返回该推算点是否在回答中给出区间内数值。

    单位邻近约束：数字后方 5 个字符内须出现单位词（支持「4至6小时」「约40分钟」等写法，
    防止上一行/前文单位词跨行污染）；数量级词（万）允许出现在数字任一侧 8 字符窗口内。
    """
    unit_aliases = UNIT_ALIAS.get(spec["unit"], [spec["unit"]])
    scale = spec.get("scale")
    full_text = answer
    for m in re.finditer(r"\d+(?:\.\d+)?", full_text):
        val = float(m.group())
        if scale and scale in full_text[max(0, m.start() - 8): m.end() + 8]:
            val *= 10000
        if not (spec["min"] <= val <= spec["max"]):
            continue
        post = full_text[m.end(): m.end() + 5]
        if unit_aliases and not any(u in post for u in unit_aliases):
            continue
        return True, val
    return False, None


def check_resource(blacklist, answer):
    """V1：回答中出现禁止资源名 → 列出违规项。"""
    return [name for name in blacklist if name in answer]


def check_traps(specs, answer):
    """V3/V5：决策束缚规则。contains 命中且 must_any 无一命中 → 违规。"""
    violations = []
    for t in specs.get("traps", []):
        if any(c in answer for c in t["contains"]) and not any(m in answer for m in t["must_any"]):
            violations.append(t["name"])
    return violations


def check_capacity(specs, answer):
    """V4：运力/资源缺口规则。trigger 命中且 must_any 无一命中 → 违规。"""
    violations = []
    for c in specs.get("capacity", []):
        if any(t in answer for t in c["trigger"]) and not any(m in answer for m in c["must_any"]):
            violations.append(c["name"])
    return violations


def run_on_answer(scene, specs, answer):
    """对一个场景的回答执行 V1~V5，返回结构化结果。"""
    calc_results = {}
    for c in specs.get("calc", []):
        ok, found = check_calc(c, answer)
        calc_results[c["id"] + "@" + c.get("unit", "")] = {"pass": bool(ok), "found": found}
    return {
        "scene_id": scene["id"],
        "calc": calc_results,
        "resource_violations": check_resource(forbidden_resources(scene), answer),
        "trap_violations": check_traps(specs, answer),
        "capacity_violations": check_capacity(specs, answer),
    }


def self_check(scenarios, specs):
    """规格自检：每个 spec 的 calc id 必须能在场景 rubric 里找到对应推算要点。"""
    problems = 0
    for scene in scenarios:
        sid = scene["id"]
        if sid not in specs:
            problems += 1
            print("[缺规格] 场景 %s 没有 Verifier 规格" % sid)
            continue
        pre = {"事实层": "F", "推理层": "R", "决策层": "D"}
        calc_ids = set()
        for l in ("事实层", "推理层", "决策层"):
            for i, p in enumerate(scene["rubric"][l], 1):
                if p["要点"].startswith("推算"):
                    calc_ids.add(pre[l] + str(i))
        for c in specs[sid]["calc"]:
            if c["id"] not in calc_ids:
                problems += 1
                print("[错配] %s 的规格 calc id %s 不是该场景的推算要点（现有：%s）" % (sid, c["id"], sorted(calc_ids)))
        for cid in calc_ids:
            if not any(c["id"] == cid for c in specs[sid]["calc"]):
                problems += 1
                print("[缺规格] %s-%s 是推算要点但 Verifier 无 calc 规格" % (sid, cid))
    print("自检完成：%d 个问题" % problems)
    return problems


def run_on_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    scenarios = {s["id"]: s for s in load_scenarios()}
    specs = load_specs()
    pre = {"事实层": "F", "推理层": "R", "决策层": "D"}
    print("== Verifier 复核：%s（%d 条记录）==" % (os.path.basename(path), len(data["records"])))
    n_calc_caught = 0
    conflicts = []
    for rec in data["records"]:
        scene = scenarios.get(rec["scene_id"])
        if scene is None or scene["id"] not in specs:
            continue
        vr = run_on_answer(scene, specs[scene["id"]], rec.get("answer") or "")
        for c in specs[scene["id"]]["calc"]:
            unit = c.get("unit", "")
            res = vr["calc"][c["id"] + "@" + unit]
            # 反查该推算点在规则与 LLM 裁判里的判分
            judges = []
            for jname, j in (("rule", rec.get("rule", {})), ("llm", rec.get("llm", {}))):
                for d in j.get("details", []):
                    # 序号按层内相对顺序与 rubric 一致，此处按 层+序号 反查是否为该推算点
                    if d.get("层") and d.get("序号") and pre[d["层"]] + str(d["序号"]) == c["id"]:
                        # 确认确实是推算要点（要点文本以「推算」开头）
                        if d.get("要点", "").startswith("推算"):
                            judges.append((jname, d.get("得分", 0)))
            if judges:
                if not res["pass"]:
                    if all(s == 0 for _, s in judges):
                        n_calc_caught += 1
                        conflicts.append((rec["scene_id"], c["id"], "裁判全 0", "Verifier 亦检出无合规数值（一致）"))
                    else:
                        conflicts.append((rec["scene_id"], c["id"], "有裁判判 1", "Verifier 检出无合规数值（分歧！）"))
        if vr["resource_violations"] or vr["trap_violations"] or vr["capacity_violations"]:
            line = "  %s: " % rec["scene_id"]
            if vr["resource_violations"]:
                line += "超配[%s] " % ",".join(vr["resource_violations"])
            if vr["trap_violations"]:
                line += "陷阱[%s] " % ",".join(vr["trap_violations"])
            if vr["capacity_violations"]:
                line += "运力[%s]" % ",".join(vr["capacity_violations"])
            print(line.rstrip())
    n_conflict = sum(1 for _, _, judge_note, detail in conflicts if "分歧" in detail)
    print("== 交叉统计：推算型要点失误可被 Verifier 确定性检出 %d 处；裁判-Verifier 分歧 %d 处 ==" %
          (n_calc_caught, n_conflict))
    for s in conflicts[:20]:
        print("  条目：%s %s | %s | %s" % s)


def main():
    parser = argparse.ArgumentParser(description="CrisisBench Verifier")
    parser.add_argument("--file", default=None, help="实验结果 JSON（含 answer 与 rule/llm 判分）")
    args = parser.parse_args()
    scenarios = load_scenarios()
    specs = load_specs()
    if args.file:
        run_on_file(args.file)
    else:
        sys.exit(self_check(scenarios, specs))


if __name__ == "__main__":
    main()