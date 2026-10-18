# -*- coding: utf-8 -*-
"""
CrisisBench 实验脚本（v0.4 全量版）
干什么：挑一个/全部场景，让"研判员"（被测智能体）作答，再用两种方式打分。
用法：
  python run_experiment.py --scene S001                     # 单Agent跑单个场景
  python run_experiment.py --scene all --config multi       # 四Agent串行跑全部场景
  python run_experiment.py --scene S001 --judge rule        # 只做规则打分（免费，快）
可选参数：
  --model  glm-4-flash（默认）| glm-4-plus ...
  --config single（单研判员，默认）
           multi（情报官→研判官→决策官→审核官 串行）
           multi-noaudit（A3 消融：去掉审核官，以决策官发言为打分对象）
           multi-verify（A4 对照：审核官出最终报告前注入 Verifier 违规清单）
  --judge  both（规则+LLM，默认）| rule | llm
环境变量：ZHIPUAI_API_KEY（智谱平台 Key）。不设置也能跑，退化为空回答占位（demo），
方便先验证流水线；正式实验必须设置。
A8 成本统计：每次 API 调用记录 usage（prompt/completion/total tokens）与耗时，
汇总写进每条 record 的 usage 字段。
"""
import argparse
import datetime
import json
import os
import sys
import time

import requests

from verifier import load_specs, run_on_answer

# 全进程 API 用量日志（A8）：[(model, prompt, completion, total, 耗时秒), ...]
USAGE_LOG = []

# ---------------- 路径准备 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_FILE = os.path.join(BASE_DIR, "..", "scenarios", "scenarios.json")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


# ---------------- 工具函数 ----------------
def load_scenarios():
    """读入场景文件，返回场景列表。"""
    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        return json.load(f)["scenarios"]


def call_glm(messages, model="glm-4-flash", temperature=0.1):
    """
    调一次智谱 API，返回 (内容, usage) 并把 usage 记入全局 USAGE_LOG。
    网络错误/超时重试 2 次；仍失败抛异常，由上层决定（demo 占位 / 报错退出）。
    """
    key = os.environ.get("ZHIPUAI_API_KEY")
    if not key:
        return None, None  # 没配 Key，返回 None 表示用 demo 占位
    last_err = None
    for attempt in range(3):
        t0 = time.time()
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": "Bearer " + key},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                js = resp.json()
                u = js.get("usage", {}) or {}
                usage = {
                    "model": model,
                    "prompt_tokens": u.get("prompt_tokens", 0),
                    "completion_tokens": u.get("completion_tokens", 0),
                    "total_tokens": u.get("total_tokens", 0),
                    "耗时秒": round(time.time() - t0, 1),
                }
                USAGE_LOG.append(usage)
                return js["choices"][0]["message"]["content"], usage
            last_err = RuntimeError("API 调用失败：" + resp.text[:200])
        except Exception as e:
            last_err = e
        if attempt < 2:
            time.sleep(6)
    raise last_err


def _sum_usage(logs):
    """把一段 usage 日志汇总成一个字典（A8）。"""
    if not logs:
        return {"调用数": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "total_tokens": 0, "耗时秒": 0.0}
    return {
        "调用数": len(logs),
        "prompt_tokens": sum(x["prompt_tokens"] for x in logs),
        "completion_tokens": sum(x["completion_tokens"] for x in logs),
        "total_tokens": sum(x["total_tokens"] for x in logs),
        "耗时秒": round(sum(x["耗时秒"] for x in logs), 1),
        "模型分布": {m: sum(1 for x in logs if x["model"] == m)
                    for m in sorted({x["model"] for x in logs})},
    }


def build_scene_context(scene):
    """把场景的情报和资源拼成一段共享上下文（两种配置的输入都一样）。"""
    lines = ["【灾害类型】" + scene["灾种"], "【时间点】" + scene["时间点"], ""]
    lines.append("【情报】")
    for i, b in enumerate(scene["情报"], 1):
        lines.append("%d. %s" % (i, b))
    lines.append("")
    lines.append("【本区域可用资源】" + "；".join(scene["资源"]))
    return "\n".join(lines)


def build_analyst_prompt(scene):
    """
    single 配置的题目：单研判员一次作答三层内容。
    注意：题目里只给情报，绝不给任何正确要点（那是打分用的答案，不能泄题）。
    """
    lines = []
    lines.append("你是一名灾害应急指挥中心的研判员。下面是当前收到的灾情情报：")
    lines.append("")
    lines.append(build_scene_context(scene))
    lines.append("")
    lines.append("请按以下三部分作答：")
    lines.append("一、关键事实要素：列出你认为最重要的情报点。")
    lines.append("二、态势研判：给出因果链条（基于什么事实、为什么、推出什么风险或结论）。")
    lines.append("三、行动建议：给出具体可执行的处置建议（写明对象和措施）。")
    return "\n".join(lines)


# multi 配置的四个角色：每个角色 = 名字 + 职责说明 + 输出要求。
# 情报官只看情报；后面三个角色额外看到前面角色的发言（公开对话，可追溯）。
AGENT_ROLES = [
    ("情报官", "你的职责是灾情要素提取：从情报中筛选出关键事实要素，逐条列出，不遗漏重要信息，也不采信未经证实的传言。", 
     "请输出【情报官发言】关键事实要素清单："),
    ("研判官", "你的职责是态势研判：基于情报和情报官的要素清单，给出因果链条（基于什么事实、为什么、推出什么风险或结论），包括次生灾害风险与信息甄别结论。",
     "请输出【研判官发言】态势研判："),
    ("决策官", "你的职责是行动建议：基于前述情报与研判，给出具体可执行的处置建议，每条写明对象与措施；注意只能使用本区域可用资源，不得虚构调用清单外的大型装备。",
     "请输出【决策官发言】行动建议："),
    ("审核官", "你的职责是汇总审核：检查前面三位的发言有无遗漏关键事实、推理链条是否完整、建议是否可执行或存在超配；然后输出最终报告，按“一、关键事实要素 二、态势研判 三、行动建议”组织，吸收前面发言的合理内容。",
     "请输出【最终报告】：" + "\n".join(["一、关键事实要素", "二、态势研判", "三、行动建议"])),
]


def run_multi_agent(scene, model, config="multi"):
    """
    multi 系配置：角色串行发言，除情报官外都能看到前面角色的发言。
      multi        ：四角色，以审核官的最终报告作为打分对象。
      multi-noaudit ：三角色（A3 消融），以决策官发言作为打分对象。
      multi-verify  ：审核官出报告前注入 Verifier 违规清单（A4 对照）。
    返回（各角色发言列表，最终报告，注入的校验文本 or None）。
    """
    context = build_scene_context(scene)
    history = []
    final_answer = ""
    verify_notes = None
    roles = AGENT_ROLES if config != "multi-noaudit" else AGENT_ROLES[:3]
    for name, duty, output_req in roles:
        lines = []
        lines.append("你是灾害应急多智能体协作系统中的" + name + "。" + duty)
        lines.append("")
        lines.append("【灾情情报与资源】")
        lines.append(context)
        if history:  # 非首个角色：把前面角色的发言接进来
            lines.append("")
            lines.append("【前面角色的发言】")
            for h_name, h_text in history:
                lines.append("—— " + h_name + " 说：")
                lines.append(h_text)
        if name == "审核官" and config == "multi-verify":
            verify_notes = build_verifier_notes(scene, history)
            if verify_notes:
                lines.append("")
                lines.append("【系统约束校验提醒（确定性规则检查，逐条核查后修正）】")
                lines.append(verify_notes)
                lines.append("请逐条核查上述提醒：确认属实的必须在最终报告中修正；若判定为误报，也请在报告中说明理由。")
        lines.append("")
        lines.append(output_req)
        text, _ = call_glm([{"role": "user", "content": "\n".join(lines)}], model=model)
        if text is None:
            text = "（demo 占位：未配置 API Key）"
        history.append((name, text))
        final_answer = text
    return history, final_answer, verify_notes


def build_verifier_notes(scene, history):
    """
    A4：对前序发言（情报官+研判官+决策官）跑 Verifier，把违规项转成给审核官的中文提醒。
    只报「哪里违反了什么约束」，不报期望数值（不泄答案，V2 推算仅做事后交叉统计）。
    """
    specs = load_specs().get(scene["id"], {})
    draft = "\n\n".join("%s 发言：\n%s" % (n, t) for n, t in history)
    vr = run_on_answer(scene, specs, draft)
    lines = []
    if vr["resource_violations"]:
        for r in vr["resource_violations"]:
            lines.append("- 【资源超配】疑似动用了本区域资源清单之外的「%s」；清单里没有这项资源，若确需调用必须写明外部调援来源。" % r)
    if vr["trap_violations"]:
        for t in vr["trap_violations"]:
            lines.append("- 【处置风险】「%s」这一错误做法在建议中出现；必须明确否决并给出正确做法，而不是照做。" % t)
    if vr["capacity_violations"]:
        for c in vr["capacity_violations"]:
            lines.append("- 【运力缺口】「%s」存在缺口，建议必须写明如何弥补（如提请外部增援），不能默认够用。" % c)
    return "\n".join(lines) if lines else None


def build_judge_prompt(scene, answer):
    """
    拼给"裁判模型"的题目：把该场景的评分要点清单 + 研判员回答交给它，
    要求按唯一编号逐条输出 0/1 和一句理由。
    编号约定：事实层 F1..Fn、推理层 R1..Rn、决策层 D1..Dn（解析时不依赖裁判写的层名）。
    裁判可以看到情报原文，用于核对数值型要点是否推算正确。
    """
    lines = []
    lines.append("你是灾害应急决策评测的独立裁判。下面是场景的评分要点（每条有唯一编号）和一个研判员的回答。")
    lines.append("请逐条判断要点是否在回答中被满足，只输出 JSON 数组，格式：")
    lines.append('[{"编号":"F1","得分":0或1,"理由":"一句话"}]')
    lines.append("")
    lines.append("判定规则：")
    lines.append("- 事实层（F编号）：回答中准确陈述该要素（关键数值与情报一致或推算正确）得1；未提及或被错误陈述得0；要点注明“推算”的，回答必须给出推算出的数值或数值区间，只复述原始情报里的数字不算满足；")
    lines.append("- 推理层（R编号）：回答中明确表达出该条目的结论（表述可以不同，意思到位即可）且与情报一致得1；结论未出现或与情报矛盾得0；起点/机制/终点仅作参考，不要求逐字对应；")
    lines.append("- 决策层（D编号）：回答中明确给出该条措施、写明具体对象与动作得1；仅笼统表述（如“加强力量”“做好工作”）得0；若目标对象完全缺失、动用了资源清单之外的资源、或与情报事实冲突，得0；")
    lines.append("- 每条要点都必须给出判定，不得漏条；只判断要点是否被满足，不评判回答的其他内容；")
    lines.append("- 你对所有回答按统一标准打分，不因措辞风格而放宽或收紧。")
    lines.append("")
    lines.append("【场景情报原文（核对数值与事实用）】")
    lines.append(build_scene_context(scene))
    lines.append("")
    lines.append("【评分要点清单】")
    prefix = {"事实层": "F", "推理层": "R", "决策层": "D"}
    for layer in ["事实层", "推理层", "决策层"]:
        items = scene["rubric"][layer]
        for i, it in enumerate(items, 1):
            tip = it["要点"]
            if layer == "推理层" and all(k in it for k in ("起点", "机制", "终点")):
                tip += "（起点：%s | 机制：%s | 终点：%s）" % (it["起点"], it["机制"], it["终点"])
            lines.append("- %s%d：%s" % (prefix[layer], i, tip))
    lines.append("")
    lines.append("【研判员回答】")
    lines.append(answer)
    return "\n".join(lines)


# 编号 → (层, 序号) 的映射，供解析用
def build_id_map(scene):
    prefix = {"事实层": "F", "推理层": "R", "决策层": "D"}
    id_map = {}
    for layer in ["事实层", "推理层", "决策层"]:
        for i in range(len(scene["rubric"][layer])):
            id_map[prefix[layer] + str(i + 1)] = (layer, i)
    return id_map


# ---------------- 两种打分 ----------------
def rule_score(scene, answer):
    """
    规则打分：每个要点若干关键词（match 词），回答里命中任意一个就算得分。
    定位是开发自检；正式数字用 LLM 打分。返回和 llm_score 相同结构的列表。
    """
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


def llm_score(scene, answer, model):
    """
    LLM 打分：把要点清单+回答发给裁判模型，解析它返回的 JSON（按唯一编号映射回层与序号）。
    裁判漏判的条目按 0 分计并在理由里标注"裁判未返回判定"；解析失败重试一次。
    """
    for attempt in range(2):
        try:
            text, _ = call_glm([{"role": "user", "content": build_judge_prompt(scene, answer)}],
                               model=model, temperature=0)
            if text is None:
                return None
            # 裁判可能输出 ```json ... ``` 包裹，剥掉代码块围栏再解析
            start = text.find("[")
            end = text.rfind("]")
            raw_items = json.loads(text[start:end + 1])

            id_map = build_id_map(scene)
            judged = {}
            for it in raw_items:
                pid = str(it.get("编号", "")).strip()
                if pid in id_map:
                    judged[pid] = {"编号": pid, "得分": int(it.get("得分", 0)), "理由": str(it.get("理由", ""))}
            # 补齐裁判漏掉的条目：按 0 分计
            details = []
            for pid, (layer, idx) in sorted(id_map.items(), key=lambda kv: (kv[1][0], kv[1][1])):
                if pid in judged:
                    d = judged[pid]
                else:
                    d = {"编号": pid, "得分": 0, "理由": "裁判未返回判定"}
                details.append({
                    "层": layer, "序号": idx + 1,
                    "要点": scene["rubric"][layer][idx]["要点"],
                    "得分": d["得分"], "理由": d["理由"],
                })
            return details
        except Exception as e:  # 解析失败就再试一次
            if attempt == 1:
                print("  [警告] 裁判输出解析失败：%s" % str(e)[:80])
    return None


def summarize(details, scene, layer):
    """把逐条 0/1 汇总成某一层的得分率。"""
    idx = [d for d in details if d["层"] == layer]
    total = len(idx)
    got = sum(d["得分"] for d in idx)
    return got, total


def fill_llm_judge_record(record, scene, details, key="llm"):
    """把 llm_score 返回的明细写进 record 的指定键下（含各层得分率汇总）。"""
    for d in details:
        d["要点"] = scene["rubric"][d["层"]][d["序号"] - 1]["要点"]
    record[key]["details"] = details
    for layer in ["事实层", "推理层", "决策层"]:
        got, total = summarize(details, scene, layer)
        record[key][layer] = {"得分": got, "总数": total,
                              "命中率": round(got / total, 3) if total else 0}
        print("  [LLM] %s：%d/%d" % (layer, got, total))


# ---------------- 主流程 ----------------
def run_one(scene, model, judge_mode, config, judge_model=None):
    """对单个场景跑一遍：推演 + 打分，返回结果字典。judge_model 为 None 时与被测模型相同。"""
    print("== 场景 %s（%s/%s，配置 %s）==" % (scene["id"], scene["类别"], scene["灾种"], config))
    usage_start = len(USAGE_LOG)

    # 1) 推演（被测智能体）
    verify_notes = None
    if config in ("multi", "multi-noaudit", "multi-verify"):
        history, answer, verify_notes = run_multi_agent(scene, model, config)
        if answer == "（demo 占位：未配置 API Key）":
            print("  [demo] 未配置 ZHIPUAI_API_KEY，使用占位回答")
    else:
        history = []
        answer, _ = call_glm([{"role": "user", "content": build_analyst_prompt(scene)}], model=model)
        if answer is None:
            answer = "（demo 占位：未配置 API Key，回答为空）"
            print("  [demo] 未配置 ZHIPUAI_API_KEY，使用空回答占位")

    record = {
        "scene_id": scene["id"], "model": model, "config": config,
        "judge_mode": judge_mode, "answer": answer, "dialog": history,
        "verify_notes": verify_notes,
        "rule": {}, "llm": {},
    }

    # 2) 打分
    if judge_mode in ("rule", "both"):
        details = rule_score(scene, answer)
        record["rule"]["details"] = details
        for layer in ["事实层", "推理层", "决策层"]:
            got, total = summarize(details, scene, layer)
            record["rule"][layer] = {"得分": got, "总数": total,
                                     "命中率": round(got / total, 3) if total else 0}
            print("  [规则] %s：%d/%d" % (layer, got, total))
    if judge_mode in ("llm", "both"):
        jm = judge_model or model
        details = llm_score(scene, answer, jm)
        if details is None:
            record["llm"]["error"] = "解析失败"
            print("  [LLM裁判] 失败（无 Key 或解析错误）")
        else:
            fill_llm_judge_record(record, scene, details)
    record["usage"] = _sum_usage(USAGE_LOG[usage_start:])
    return record


def rescore_file(path, judge_model):
    """
    只重打分不重推演：读入一份历史结果文件，用（更严格的）裁判对已有回答重新打 LLM 分。
    用于裁判一致性/裁判模型消融——同样的回答，换裁判或换裁判模型后得分变化多少。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    scenarios = {s["id"]: s for s in load_scenarios()}
    out_records = []
    for rec in data["records"]:
        scene = scenarios.get(rec["scene_id"])
        if scene is None:
            print("跳过 %s：场景不存在" % rec["scene_id"])
            continue
        print("== 重裁判 %s（config=%s，裁判模型=%s）==" % (rec["scene_id"], rec.get("config"), judge_model))
        usage_start = len(USAGE_LOG)
        new_rec = {
            "scene_id": rec["scene_id"], "model": rec.get("model"), "config": rec.get("config"),
            "judge_mode": "llm", "answer": rec["answer"], "dialog": rec.get("dialog", []),
            "orig_rule": rec.get("rule", {}), "rescore_judge": judge_model,
            "rule": {}, "llm": {},
        }
        details = llm_score(scene, rec["answer"], judge_model)
        if details is None:
            new_rec["llm"]["error"] = "解析失败"
            print("  [LLM裁判] 失败（无 Key 或解析错误）")
        else:
            fill_llm_judge_record(new_rec, scene, details)
        new_rec["usage"] = _sum_usage(USAGE_LOG[usage_start:])
        out_records.append(new_rec)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = os.path.splitext(os.path.basename(path))[0]
    out_file = os.path.join(RESULTS_DIR, "%s-rescore-%s-%s.json" % (tag, judge_model, stamp))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"meta": {"时间": stamp, "来源文件": os.path.basename(path),
                            "judge": "llm", "judge_model": judge_model,
                            "note": "只重打分未重推演（严格裁判提示词）"},
                   "records": out_records}, f, ensure_ascii=False, indent=2)
    print("\n重裁判结果已保存：%s" % out_file)


def main():
    parser = argparse.ArgumentParser(description="CrisisBench 阶段0 实验")
    parser.add_argument("--scene", default="S001", help="场景编号或 all")
    parser.add_argument("--model", default="glm-4-flash")
    parser.add_argument("--judge", default="both", choices=["rule", "llm", "both"])
    parser.add_argument("--config", default="single",
                        choices=["single", "multi", "multi-noaudit", "multi-verify"])
    parser.add_argument("--judge-model", default=None, help="裁判模型（默认与被测模型相同）")
    parser.add_argument("--rescore", default=None, help="只重裁判：传入历史结果 JSON 路径，跳过推演")
    parser.add_argument("--resume", default=None, help="从 partial 文件恢复继续跑（断点续跑）")
    args = parser.parse_args()

    if args.rescore:
        rescore_file(args.rescore, args.judge_model or args.model)
        sys.exit(0)

    scenarios = load_scenarios()
    if args.scene != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scene]
        if not scenarios:
            print("找不到场景 " + args.scene)
            sys.exit(1)

    # 断点续跑：读 partial 文件里已完成的场景，跳过；没 --resume 就新建 partial
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    all_records = []
    done_ids = set()
    if args.resume:
        partial_path = args.resume
        with open(partial_path, encoding="utf-8") as f:
            all_records = json.load(f)["records"]
        done_ids = {r["scene_id"] for r in all_records}
        print("恢复运行：已跳过 %d 个已完成场景" % len(done_ids))
    else:
        partial_path = os.path.join(RESULTS_DIR, "exp-%s-%s-%s.partial.json" % (args.scene, args.config, stamp))

    for scene in scenarios:
        if scene["id"] in done_ids:
            print("== 跳过已完成场景 %s ==" % scene["id"])
            continue
        # 有空回答也无所谓：打分照样跑，验证流水线完整性
        all_records.append(run_one(scene, args.model, args.judge, args.config, args.judge_model))
        # 每跑完一个场景就落盘 partial，防止长跑中断丢进度
        with open(partial_path, "w", encoding="utf-8") as f:
            json.dump({"meta": {"时间": stamp, "model": args.model,
                                "judge": args.judge, "config": args.config,
                                "judge_model": args.judge_model, "partial": True},
                       "records": all_records}, f, ensure_ascii=False, indent=2)
        print("  [进度] 已完成 %d/%d" % (len(all_records), len(scenarios)))

    # 3) 落盘（文件名带时间戳，避免覆盖历史结果）
    out_file = os.path.join(RESULTS_DIR, "exp-%s-%s-%s.json" % (args.scene, args.config, stamp))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"meta": {"时间": stamp, "model": args.model,
                            "judge": args.judge, "config": args.config,
                            "judge_model": args.judge_model},
                   "records": all_records}, f, ensure_ascii=False, indent=2)
    if os.path.exists(partial_path):
        os.remove(partial_path)
    print("\n结果已保存：%s" % out_file)


if __name__ == "__main__":
    main()