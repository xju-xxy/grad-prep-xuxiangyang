# -*- coding: utf-8 -*-
"""
CrisisBench 阶段0 实验脚本（试水版）
干什么：挑一个/全部场景，让"研判员"（被测智能体）作答，再用两种方式打分。
用法：
  python run_experiment.py --scene S001                     # 单Agent跑单个场景
  python run_experiment.py --scene all --config multi       # 四Agent串行跑全部场景
  python run_experiment.py --scene S001 --judge rule        # 只做规则打分（免费，快）
可选参数：
  --model  glm-4-flash（默认）| glm-4-plus ...
  --config single（单研判员，默认）| multi（情报官→研判官→决策官→审核官 串行）
  --judge  both（规则+LLM，默认）| rule | llm
环境变量：ZHIPUAI_API_KEY（智谱平台 Key）。不设置也能跑，退化为空回答占位（demo），
方便先验证流水线；正式实验必须设置。
"""
import argparse
import datetime
import json
import os
import sys

import requests

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
    调一次智谱 API。
    失败时抛出异常，由上层决定怎么办（demo 占位 / 报错退出）。
    """
    key = os.environ.get("ZHIPUAI_API_KEY")
    if not key:
        return None  # 没配 Key，返回 None 表示用 demo 占位
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
    if resp.status_code != 200:
        raise RuntimeError("API 调用失败：" + resp.text[:200])
    return resp.json()["choices"][0]["message"]["content"]


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


def run_multi_agent(scene, model):
    """
    multi 配置：四个角色串行发言，除情报官外都能看到前面角色的发言，
    最后以审核官的最终报告作为打分对象。返回（各角色发言列表，最终报告）。
    """
    context = build_scene_context(scene)
    history = []
    final_answer = ""
    for name, duty, output_req in AGENT_ROLES:
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
        lines.append("")
        lines.append(output_req)
        text = call_glm([{"role": "user", "content": "\n".join(lines)}], model=model)
        if text is None:
            text = "（demo 占位：未配置 API Key）"
        history.append((name, text))
        final_answer = text
    return history, final_answer


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
            text = call_glm([{"role": "user", "content": build_judge_prompt(scene, answer)}],
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

    # 1) 推演（被测智能体）
    if config == "multi":
        history, answer = run_multi_agent(scene, model)
        if answer == "（demo 占位：未配置 API Key）":
            print("  [demo] 未配置 ZHIPUAI_API_KEY，使用占位回答")
    else:
        history = []
        answer = call_glm([{"role": "user", "content": build_analyst_prompt(scene)}], model=model)
        if answer is None:
            answer = "（demo 占位：未配置 API Key，回答为空）"
            print("  [demo] 未配置 ZHIPUAI_API_KEY，使用空回答占位")

    record = {
        "scene_id": scene["id"], "model": model, "config": config,
        "judge_mode": judge_mode, "answer": answer, "dialog": history,
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
    parser.add_argument("--config", default="single", choices=["single", "multi"])
    parser.add_argument("--judge-model", default=None, help="裁判模型（默认与被测模型相同）")
    parser.add_argument("--rescore", default=None, help="只重裁判：传入历史结果 JSON 路径，跳过推演")
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

    all_records = []
    for scene in scenarios:
        # 有空回答也无所谓：打分照样跑，验证流水线完整性
        all_records.append(run_one(scene, args.model, args.judge, args.config, args.judge_model))

    # 3) 落盘（文件名带时间戳，避免覆盖历史结果）
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = os.path.join(RESULTS_DIR, "exp-%s-%s-%s.json" % (args.scene, args.config, stamp))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"meta": {"时间": stamp, "model": args.model,
                            "judge": args.judge, "config": args.config,
                            "judge_model": args.judge_model},
                   "records": all_records}, f, ensure_ascii=False, indent=2)
    print("\n结果已保存：%s" % out_file)


if __name__ == "__main__":
    main()