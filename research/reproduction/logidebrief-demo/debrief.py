"""
debrief.py —— 主流程

对每通电话跑一遍完整管线：
  detector（LLM 判零件）-> stl（时间窗求值）-> 聚合成质检单
最后把结果写进 results/，并按人工标注算指标。

运行：
  .venv\\Scripts\\python.exe debrief.py            # 全跑
  .venv\\Scripts\\python.exe debrief.py --limit 2  # 只跑前 2 通（调试用）
  .venv\\Scripts\\python.exe debrief.py --no-cache # 忽略缓存重新调 API
"""

import argparse
import io
import json
import os
import sys

from dotenv import load_dotenv
from zhipuai import ZhipuAI

import stl
import detector

# Windows 控制台默认不是 utf-8，中文会乱码，这里强制一下
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
CACHE_PATH = os.path.join(RESULTS_DIR, "llm_raw.json")


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def build_action_status(detected, turns):
    """把 detector 的输出转成 stl 需要的 {action_id: {status,time,turn,quote}}。"""
    status = {}
    for aid, info in detected.items():
        if aid == "_raw":
            continue
        turn = info.get("turn")
        t = None
        if isinstance(turn, int) and 1 <= turn <= len(turns):
            t = turns[turn - 1]["t"]
        status[aid] = {
            "status": info.get("status", "absent"),
            "turn": turn,
            "time": t,
            "quote": info.get("quote", ""),
        }
    return status


def verdict_gt(call_gt, rid):
    """按人工标注的 applicable/violations/refused 推出某需求的标注结论。"""
    if rid in call_gt.get("refused", []):
        return "Refused"
    if rid in call_gt.get("violations", []):
        return "No"
    if rid in call_gt.get("applicable", []):
        return "Yes"
    return "NA"


def evaluate_call(client, call, protocol, cache, use_cache):
    cid = call["id"]
    turns = call["turns"]
    call_end_t = turns[-1]["t"]

    # ---- 1. LLM 判零件（带缓存，重跑不重复烧 token）----
    if use_cache and cid in cache:
        cls = cache[cid]["classify"]
        detected = cache[cid]["actions"]
        print(f"  [{cid}] 使用缓存")
    else:
        print(f"  [{cid}] 调用 GLM 分类 ...")
        cls = detector.classify_call(client, call, protocol)
        print(f"  [{cid}] 调用 GLM 动作检测 ...")
        detected = detector.detect_actions(client, call, protocol)
        cache[cid] = {"classify": cls, "actions": detected}
        save_cache(cache)

    action_status = build_action_status(detected, turns)

    # ---- 2. STL 外壳逐条求值 ----
    rows = []
    for req in protocol["requirements"]:
        verdict, reason, evidence = stl.eval_requirement(req, cls.get("call_type"), call_end_t, action_status)
        rows.append({
            "id": req["id"],
            "title": req["title"],
            "fatal_tag": req.get("fatal_tag"),
            "verdict": verdict,
            "reason": reason,
            "evidence": evidence,
            "gt": verdict_gt(call["gt"], req["id"]),
        })

    return {
        "id": cid,
        "title": call["title"],
        "duration": call_end_t,
        "classify": {k: v for k, v in cls.items() if k != "_raw"},
        "classify_gt": {
            "call_type": call["call_type_gt"],
            "event_type": call["event_type_gt"],
            "fatal_category": call["fatal_category_gt"],
        },
        "rows": rows,
    }


def render_call_md(result):
    c = result["classify"]
    gt = result["classify_gt"]
    lines = []
    lines.append(f"# 质检单 {result['id']}：{result['title']}")
    lines.append("")
    lines.append(f"- 通话时长（相对秒）：{result['duration']}s")
    lines.append(f"- 模型判定类型：{c.get('call_type')}（事件：{c.get('event_type')}，致命情形：{c.get('fatal_category')}，响应：{c.get('response_unit')}）")
    lines.append(f"- 人工标注类型：{gt.get('call_type')}（事件：{gt.get('event_type')}，致命情形：{gt.get('fatal_category')}）")
    lines.append("")
    lines.append("| 需求 | 结论 | 人工标注 | 证据（轮次/时间/原话） | 理由 |")
    lines.append("|---|---|---|---|---|")
    for r in result["rows"]:
        ev = r["evidence"]
        if ev and ev.get("turn"):
            evs = f"第{ev['turn']}轮/{ev['time']}s「{ev['quote']}」"
        else:
            evs = "—"
        flag = "" if r["verdict"] == r["gt"] else " ⚠"
        lines.append(f"| {r['id']} {r['title']} | {r['verdict']}{flag} | {r['gt']} | {evs} | {r['reason']} |")
    lines.append("")
    return "\n".join(lines)


def compute_metrics(results):
    total = agree = 0
    tp = fp = fn = 0            # 违规（No）检出
    refused_hit = refused_tot = 0
    na_agree = na_tot = 0
    cls_ok = 0
    per_call = []

    for res in results:
        if res["classify"].get("call_type") == res["classify_gt"]["call_type"]:
            cls_ok += 1
        for r in res["rows"]:
            total += 1
            if r["verdict"] == r["gt"]:
                agree += 1
            if r["gt"] == "No":
                if r["verdict"] == "No":
                    tp += 1
                else:
                    fn += 1
            else:
                if r["verdict"] == "No":
                    fp += 1
            if r["gt"] == "Refused":
                refused_tot += 1
                if r["verdict"] == "Refused":
                    refused_hit += 1
            if r["gt"] == "NA" or r["verdict"] == "NA":
                na_tot += 1
                if r["gt"] == "NA" and r["verdict"] == "NA":
                    na_agree += 1
        per_call.append(res)

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "n_calls": len(results),
        "n_pairs": total,
        "agreement": agree / total if total else 0.0,
        "violation_tp": tp, "violation_fp": fp, "violation_fn": fn,
        "violation_precision": prec, "violation_recall": rec, "violation_f1": f1,
        "refused_hit": refused_hit, "refused_total": refused_tot,
        "na_agree": na_agree, "na_total": na_tot,
        "type_accuracy": cls_ok / len(results) if results else 0.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

    protocol = stl.load_protocol(os.path.join(HERE, "protocol.json"))
    with open(os.path.join(HERE, "calls.json"), "r", encoding="utf-8") as f:
        calls = json.load(f)["calls"]
    if args.limit:
        calls = calls[:args.limit]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    cache = load_cache()

    results = []
    for call in calls:
        print(f"== {call['id']} {call['title']}")
        res = evaluate_call(client, call, protocol, cache, use_cache=not args.no_cache)
        results.append(res)
        # 每通电话各写一份 json + md
        with open(os.path.join(RESULTS_DIR, f"{call['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        with open(os.path.join(RESULTS_DIR, f"{call['id']}.md"), "w", encoding="utf-8") as f:
            f.write(render_call_md(res))

    metrics = compute_metrics(results)
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    write_summary(results, metrics)
    print("\n完成。结果见 results/")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


def write_summary(results, metrics):
    """生成 results/results.md 的正文（README 会引用这些真实数字）。"""
    lines = []
    lines.append("# LogiDebrief 复现结果")
    lines.append("")
    lines.append(f"> 模型：glm-4-flash　|　通话数：{metrics['n_calls']}　|　需求条数：{len(results[0]['rows'])}"
                 f"　|　(通话×需求) 判定对数：{metrics['n_pairs']}")
    lines.append("")

    lines.append("## 总体指标（与人工标注比对）")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 判定一致率（含 Yes/No/Refused/NA 四类） | {metrics['agreement']*100:.1f}% |")
    lines.append(f"| 通话类型判定准确率 | {metrics['type_accuracy']*100:.1f}% |")
    lines.append(f"| 违规检出（TP/FP/FN） | {metrics['violation_tp']}/{metrics['violation_fp']}/{metrics['violation_fn']} |")
    lines.append(f"| 违规检出精确率 | {metrics['violation_precision']*100:.1f}% |")
    lines.append(f"| 违规检出召回率 | {metrics['violation_recall']*100:.1f}% |")
    lines.append(f"| 违规检出 F1 | {metrics['violation_f1']*100:.1f}% |")
    lines.append(f"| Refused 判定命中 | {metrics['refused_hit']}/{metrics['refused_total']} |")
    lines.append(f"| NA 判定一致 | {metrics['na_agree']}/{metrics['na_total']} |")
    lines.append("")

    lines.append("## 逐通质检单概览")
    lines.append("")
    lines.append("| 通话 | 标题 | 模型类型 | 标注类型 | 违规(标/检) | 一致率 |")
    lines.append("|---|---|---|---|---|---|")
    for res in results:
        n_gt_no = sum(1 for r in res["rows"] if r["gt"] == "No")
        n_sys_no = sum(1 for r in res["rows"] if r["verdict"] == "No")
        agree = sum(1 for r in res["rows"] if r["verdict"] == r["gt"])
        lines.append(f"| {res['id']} | {res['title']} | {res['classify'].get('call_type')} | "
                     f"{res['classify_gt']['call_type']} | {n_gt_no}/{n_sys_no} | {agree}/{len(res['rows'])} |")
    lines.append("")

    lines.append("## 判定不一致的地方（模型 vs 人工）")
    lines.append("")
    lines.append("| 通话 | 需求 | 模型 | 人工 | 模型理由 |")
    lines.append("|---|---|---|---|---|")
    any_bad = False
    for res in results:
        for r in res["rows"]:
            if r["verdict"] != r["gt"]:
                any_bad = True
                lines.append(f"| {res['id']} | {r['id']} {r['title']} | {r['verdict']} | {r['gt']} | {r['reason']} |")
    if not any_bad:
        lines.append("| — | — | — | — | 全部一致 |")
    lines.append("")
    lines.append("逐通完整质检单见 results/ 下的 C01.md ~ C12.md 和同名 json。")
    lines.append("")

    with open(os.path.join(RESULTS_DIR, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
