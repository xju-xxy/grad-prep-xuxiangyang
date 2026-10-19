"""extract.py —— 把一段中文灾情文本按综述的分类框架抽成结构化 JSON

思路：综述本身没提出新模型，没法像系统论文那样"复现"。
我做的"可提取组件复现"，是把它的核心贡献——Figure 1 那张
「灾害四阶段 x 任务 x 模型类型」分类框架——编码成 taxonomy.json，
再让 GLM 拿着这套框架去读一段灾情文本，吐出：
{阶段, 子任务, 建议模型类型, 依据}。

用法：
    .venv\\Scripts\\python.exe extract.py                  # 跑内置示例
    .venv\\Scripts\\python.exe extract.py "灾情文本..."
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

TAXONOMY_FILE = "taxonomy.json"


def load_taxonomy(path=TAXONOMY_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_taxonomy_text(tax):
    """把 taxonomy.json 摊成一段人话，塞进提示词给模型看"""
    lines = ["【灾害阶段与任务】"]
    for st in tax["stages"]:
        lines.append(f"- {st['cn']}（{st['key']}，论文占比 {st['share'] * 100:.1f}%）：{st['desc']}")
        for tk in st["tasks"]:
            extra = ""
            if "subtasks" in tk:
                subs = "、".join(f"{s['cn']}" for s in tk["subtasks"])
                extra = f"（其下细分为：{subs}）"
            lines.append(f"    · 任务：{tk['cn']}{extra} —— {tk['desc']}")
    lines.append("")
    lines.append("【模型类型】")
    for m in tax["model_types"]:
        lines.append(f"- {m['key']}（{m['cn']}，{m['en']}）：{m['desc']}")
    return "\n".join(lines)


SYSTEM_PROMPT_TMPL = """你是一个灾害信息分析助手。下面是一篇灾害管理综述整理出的分类框架，
你要严格按这个框架，把用户给的一段灾情文本/情报归到某一阶段、某个子任务，并给出建议的模型类型。

{taxonomy}

【判定规则】
1. 阶段只能从四阶段里选一个，填中文名（如"灾害响应"）。
2. 子任务要从该阶段下的任务里选一个，填中文名。若归到"灾害响应"，五个子任务里只能选一个；
   如果是"灾害态势评估"，尽量再点出它属于哪个细分（态势分类/严重程度估计/灾情描述生成），
   写成"灾害态势评估（态势分类）"这种形式。判断不了细分就只写"灾害态势评估"。
3. 建议模型类型从 ELM / DLM / MLLM 里选一个：偏分类/理解的任务选 ELM，
   偏生成文本的任务选 DLM，需要同时处理图片的任务选 MLLM。
4. 依据要说明为什么这么归，以及为什么是这个子任务而不是相邻的那个（比如
   "信息协调"和"态势评估"容易混）。

【输出格式】
只输出一个 JSON 对象，不要 markdown 代码块、不要多余解释，字段名必须如下：
{{"阶段": "...", "子任务": "...", "建议模型类型": "...", "依据": "..."}}"""


def build_system_prompt(tax):
    return SYSTEM_PROMPT_TMPL.format(taxonomy=build_taxonomy_text(tax))


def parse_json(text):
    """模型有时候会包一层 ```json，这里把 JSON 抠出来"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 兜底：从第一个 { 到最后一个 }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def extract(text, tax, system_prompt):
    """对一段文本做结构化抽取，返回 (结果 dict, 原始输出)"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"灾情文本：{text}"},
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
    raise RuntimeError(f"抽取失败：{last_err}")


def main():
    tax = load_taxonomy()
    system_prompt = build_system_prompt(tax)

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "城东出现山洪，道路被冲毁，多处房屋进水，请判断这是什么类型的灾害。"

    print("=" * 70)
    print("输入文本：", text)
    print("=" * 70)
    result, raw = extract(text, tax, system_prompt)
    print("抽取结果（JSON）：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
