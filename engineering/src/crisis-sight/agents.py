# -*- coding: utf-8 -*-
"""4 个 Agent 的编排逻辑，每个 Agent 依次发言两轮，含 demo 与 llm 两条路径。"""

import config
import kb

# Agent 的固定顺序
AGENT_ORDER = ["情报官", "研判官", "决策官", "审核官"]


def _render_kb_prompt(kb_key, entry):
    """把知识库条目渲染成提示词片段。"""
    return (
        f"【知识库】灾害类型：{kb_key}\n"
        f"特征：{entry['特征']}\n"
        f"主要危害：{entry['主要危害']}\n"
        f"应对要点：{entry['应对要点']}\n"
        f"次生灾害：{entry['次生灾害']}\n"
        f"监测指标：{entry['监测指标']}"
    )


def _call_llm(system_prompt, user_prompt):
    """调用 DeepSeek 对话接口，返回文本；失败时返回空字符串。"""
    try:
        import requests  # 仅 LLM 模式需要，延迟导入避免 demo 模式强依赖
    except ImportError:
        return ""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
    }
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "stream": False,
    }
    try:
        resp = requests.post(config.DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# 每个 Agent 的系统提示词与任务描述
AGENT_PROMPT = {
    "情报官": (
        "你是一名灾害情报官，负责从灾情描述中提取关键要素，并结合知识库输出结构化灾情信息。"
    ),
    "研判官": (
        "你是一名灾害态势研判专家，负责结合知识库判断主要威胁、可能的次生灾害并给出风险等级。"
    ),
    "决策官": (
        "你是一名应急决策官，负责给出分级行动建议，覆盖立即行动、短期安排与部门协同。"
    ),
    "审核官": (
        "你是一名决策审核专家，负责指出研判中的不确定性、信息盲点与需要进一步核实的事项。"
    ),
}

AGENT_TASK = {
    "情报官": "请提取灾情描述中的关键要素，并结合知识库输出结构化灾情要素（时间地点、灾种、影响范围、承灾体、资源需求等）。",
    "研判官": "请结合知识库对灾情进行态势研判，输出：主要威胁、可能的次生灾害、风险等级（高/中/低），并说明理由。",
    "决策官": "请给出分级行动建议，分为「立即行动」「短期安排」「部门协同」三部分，条目化输出。",
    "审核官": "请给出本次研判的不确定性提示与信息盲点，说明哪些信息缺失、哪些判断需要进一步核实。",
}


def _llm_speech(agent, scene, disaster_type, kb_key, entry):
    """LLM 模式：提示词注入知识库命中内容，调用大模型生成发言。"""
    kb_prompt = _render_kb_prompt(kb_key, entry)
    user_prompt = (
        f"灾情描述：{scene}\n灾害类型：{disaster_type}\n\n{kb_prompt}\n\n"
        f"任务：{AGENT_TASK[agent]}"
    )
    result = _call_llm(AGENT_PROMPT[agent], user_prompt)
    if result:
        return result
    # 调用失败时回退到模板规则，保证系统可用
    return None


def _demo_speech(agent, scene, disaster_type, kb_key, entry, round_no):
    """demo 模式：基于知识库与模板规则确定性生成发言，无需 API Key。"""
    if round_no == 1:
        if agent == "情报官":
            return (
                f"一、《灾情要素提取》\n"
                f"1. 灾种：{disaster_type}（知识库命中：{kb_key}）。\n"
                f"2. 灾情概况：{scene}\n"
                f"3. 关键特征：{entry['特征']}\n"
                f"4. 主要危害：{entry['主要危害']}\n"
                f"5. 监测指标：{entry['监测指标']}。"
            )
        if agent == "研判官":
            return (
                f"二、《态势研判》\n"
                f"1. 主要威胁：{entry['主要危害']}\n"
                f"2. 可能的次生灾害：{entry['次生灾害']}。\n"
                f"3. 风险等级：高（灾情规模较大、承灾体密集，需优先处置）。"
            )
        if agent == "决策官":
            return (
                f"三、《分级行动建议》\n"
                f"【立即行动】启动应急响应，疏散危险区群众，组织专业救援力量赶赴现场。\n"
                f"【短期安排】落实以下应对要点：{entry['应对要点']}\n"
                f"【部门协同】应急、气象、水利、交通、卫健、电力等部门联动作业，信息共享。"
            )
        if agent == "审核官":
            return (
                f"四、《不确定性提示与盲点》\n"
                f"1. 当前描述缺少精确伤亡与损失数据，风险等级为初步判断。\n"
                f"2. 次生灾害（{entry['次生灾害']}）发展需结合现场监测持续更新。\n"
                f"3. 建议补充受灾人口、基础设施受损、当地救援力量的实时信息。"
            )
    else:
        # 第二轮：结合前一轮结论做补充，聚焦交叉验证与协同
        if agent == "情报官":
            return (
                f"【第二轮补充】建议进一步核实：{entry['监测指标']}；"
                f"重点收集现场人口分布、生命线工程中断与救援资源到位情况。"
            )
        if agent == "研判官":
            return (
                f"【第二轮补充】结合补充信息，维持风险等级为「高」，并提示关注"
                f"{entry['次生灾害']}的连锁演化，滚动更新研判结论。"
            )
        if agent == "决策官":
            return (
                f"【第二轮补充】在前期措施基础上，增加对口支援与医疗救治，"
                f"对次生灾害风险点安排专人盯守，做好舆情引导与信息发布。"
            )
        if agent == "审核官":
            return (
                f"【第二轮补充】仍存在盲点：受灾范围边界、交通阻断情况、物资缺口等数据未闭合，"
                f"建议每 6 小时更新一次现场信息并复核决策。"
            )


def analyze(scene, disaster_type):
    """编排 4 个 Agent 两轮发言，返回 report、messages、kb_hits。"""
    kb_key, entry = kb.lookup(disaster_type)
    use_llm = config.llm_enabled()
    mode = "llm" if use_llm else "demo"

    messages = []
    # 两轮：第一轮给结论，第二轮给补充
    for round_no in (1, 2):
        for agent in AGENT_ORDER:
            if use_llm:
                text = _llm_speech(agent, scene, disaster_type, kb_key, entry)
                if text is None:
                    # 大模型调用失败，回退到模板规则
                    text = _demo_speech(agent, scene, disaster_type, kb_key, entry, round_no)
            else:
                text = _demo_speech(agent, scene, disaster_type, kb_key, entry, round_no)
            messages.append({
                "agent": agent,
                "round": round_no,
                "content": text,
            })

    # 组装四段式报告：取各 Agent 第一轮发言作为报告主体
    report_sections = {}
    for m in messages:
        if m["round"] == 1:
            report_sections[m["agent"]] = m["content"]

    report = {
        "title": f"{disaster_type}灾害态势推演与决策建议报告",
        "summary": f"灾种：{disaster_type}；知识库命中：{kb_key}；风险等级：高。",
        "情报官": report_sections.get("情报官", ""),
        "研判官": report_sections.get("研判官", ""),
        "决策官": report_sections.get("决策官", ""),
        "审核官": report_sections.get("审核官", ""),
    }

    kb_hits = {
        "type": kb_key,
        "entry": entry,
    }

    return {
        "mode": mode,
        "report": report,
        "messages": messages,
        "kb_hits": kb_hits,
    }