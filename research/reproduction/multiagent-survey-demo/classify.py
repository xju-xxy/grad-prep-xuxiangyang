"""classify.py —— 把一段多智能体系统的文字描述，按综述的四维框架打标签

思路：综述（IJCAI 2024，arXiv:2402.01680）本身没有实验，没法像系统论文
那样照着搭一遍比指标。它最大的贡献是一套四维分析坐标系：
环境接口 / 人设 / 通信 / 能力获取。我做的"可提取组件复现"就是把这套
坐标系编码成 schema.json，再让 GLM 拿着它去读一个系统的文字描述，
吐出四个维度的标签、每个标签的判定依据，外加对四个坑（多模态空白、
幻觉级联、群体优化缺失、缺应急 benchmark）的褒贬核对。

用法：
    .venv\\Scripts\\python.exe classify.py                  # 跑内置示例（MetaGPT 描述）
    .venv\\Scripts\\python.exe classify.py "系统描述文字..."
"""

import json
import os
import re
import sys

import dotenv
from zhipuai import ZhipuAI

dotenv.load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"), timeout=120.0)

MODEL_NAME = "glm-4-flash"
MAX_RETRY = 2

SCHEMA_FILE = "schema.json"


def load_schema(path=SCHEMA_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_schema_text(sch):
    """把 schema.json 摊成一段人话，塞进提示词给模型看"""
    lines = ["【四个分析维度】"]
    for d in sch["dimensions"]:
        lines.append(f"- {d['cn']}（{d['key']}）：{d['desc']}")
        # 平铺维度
        for opt in d.get("options", []):
            lines.append(f"    · 选项 {opt['key']}：{opt['desc']}")
        # 带子面的维度（通信、能力获取）
        for sub in d.get("subfacets", []):
            lines.append(f"    · 子面 {sub['cn']}（{sub['key']}）：")
            for opt in sub["options"]:
                lines.append(f"        - {opt['key']}：{opt['desc']}")
    lines.append("")
    lines.append("【综述点名的四个坑】")
    for p in sch["pitfalls"]:
        lines.append(f"- {p['cn']}（{p['key']}）：{p['desc']}")
    return "\n".join(lines)


SYSTEM_PROMPT_TMPL = """你是一个多智能体系统的分析助手。下面是一篇综述整理出的四维分析框架。
你要严格按这套框架，给用户提供的一段「多智能体系统描述」打标签，并对四个坑做核对。

{schema}

【判定规则】
1. environment_interface：从 Sandbox / Physical / None 里选一个，单选。
2. agent_profiling：从 Pre-defined / Model-Generated / Data-Derived 里选一个，单选。
   如果描述里没明说，就按最可能的情况猜，并在 evidence 里说明是猜的。
3. agent_communication：分两层。
   paradigm（通信范式）从 合作/辩论/竞争 里多选，可多选。
   structure（通信结构）从 分层/去中心化/中心化/共享消息池 里多选，可多选。
4. capability_acquisition：分两层。
   feedback（反馈来源）从 环境/其他Agent/人类/无 里多选。
   mechanism（生长机制）从 记忆机制/自我进化/动态生成新Agent 里多选；都不沾就留空数组。
5. pitfalls：四个坑每个给一个 touched 布尔值（这个系统有没有触及/缓解这个坑）
   和一句说明。只在描述里能看出线索时才标 true，拿不准就 false。
6. 每个维度都要给 evidence，说明你这是根据描述里的哪句话、为什么这么判，
   没明说的要承认是在推测。

【输出格式】
只输出一个 JSON 对象，不要 markdown 代码块、不要多余解释，字段名必须如下：
{{
  "environment_interface": {{"label": "...", "evidence": "..."}},
  "agent_profiling": {{"label": "...", "evidence": "..."}},
  "agent_communication": {{
    "paradigm": ["..."],
    "structure": ["..."],
    "evidence": "..."
  }},
  "capability_acquisition": {{
    "feedback": ["..."],
    "mechanism": ["..."],
    "evidence": "..."
  }},
  "pitfalls": {{
    "multimodal_gap": {{"touched": false, "note": "..."}},
    "hallucination_cascade": {{"touched": false, "note": "..."}},
    "group_optimization": {{"touched": false, "note": "..."}},
    "benchmark_gap": {{"touched": false, "note": "..."}}
  }}
}}"""


def build_system_prompt(sch):
    return SYSTEM_PROMPT_TMPL.format(schema=build_schema_text(sch))


def parse_json(text):
    """模型有时候会包一层 ```json，这里把 JSON 抠出来"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def classify(text, sch, system_prompt):
    """对一个系统描述打四维标签，返回 (结果 dict, 原始输出)"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"多智能体系统描述：{text}"},
    ]
    last_err = None
    for attempt in range(1, MAX_RETRY + 2):
        try:
            r = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1,
            )
            raw = r.choices[0].message.content.strip()
            return parse_json(raw), raw
        except Exception as e:  # 网络超时或模型没按格式输出都可能
            last_err = e
            print(f"  [第 {attempt} 次尝试失败] {e}")
    raise RuntimeError(f"打标失败：{last_err}")


def main():
    sch = load_schema()
    system_prompt = build_system_prompt(sch)

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = ("把软件公司当成一个多智能体组织，给每个 Agent 分配产品经理、架构师、"
                "工程师这类写死的角色，靠一份标准作业流程把一句话需求拆成具体交付物，"
                "Agent 之间通过一个共享的消息池交换结构化文档。")

    print("=" * 70)
    print("输入描述：", text)
    print("=" * 70)
    result, raw = classify(text, sch, system_prompt)
    print("四维标签（JSON）：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
