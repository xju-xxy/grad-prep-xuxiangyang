"""
react_agent.py —— ReAct 主程序

运行：.venv\\Scripts\\python.exe react_agent.py ["问题"]
"""

import os
import re
import sys

from dotenv import load_dotenv
from zhipuai import ZhipuAI

from prompt import SYSTEM_PROMPT
import tools

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

MODEL_NAME = "glm-5.3-flash"

# 最多跑6轮，防止模型一直不喊停烧token
MAX_STEPS = 6

# 从模型输出里抠 "Action 1: Search[关键词]" 这种行
ACTION_PATTERN = re.compile(r"Action\s*\d*\s*[:：]\s*([A-Za-z]+)\s*\[([^\]]*)\]")


def run_react(question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"问题：{question}"},
    ]

    print("=" * 70)
    print("用户问题：", question)
    print("=" * 70)

    for step in range(1, MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,  # 低一点稳一点，不容易跑偏格式
        )
        text = response.choices[0].message.content.strip()

        messages.append({"role": "assistant", "content": text})
        print(f"\n【第 {step} 轮 · 模型输出】\n{text}")

        # 只认第一个 Action
        first_match = ACTION_PATTERN.search(text)

        if first_match is None:
            obs = "我没有从你上一步的输出里识别出 Action。请严格按格式输出：Action 编号: 工具名[参数]"
            messages.append({"role": "user", "content": obs})
            print(f"\n【系统提示】{obs}")
            continue

        # 之前踩的坑：模型会在第一个 Action 后面自己编 Observation，
        # 假装已经查完了。所以这里把 ] 之后的内容全部砍掉，逼它停下来等真实结果。
        cut_pos = first_match.end()
        if cut_pos < len(text):
            text = text[:cut_pos].rstrip()
            messages[-1]["content"] = text
            print("\n  [系统拦截] 检测到模型在动作后自行补写内容，已忽略。")

        tool_name = first_match.group(1)
        tool_arg = first_match.group(2).strip()
        # 防止模型写成 search / SEARCH 对不上表
        tool_name = tool_name[0].upper() + tool_name[1:].lower()

        if tool_name == "Finish":
            print("\n" + "=" * 70)
            print("最终答案：", tool_arg)
            print("=" * 70)
            return tool_arg

        if tool_name in tools.TOOLS:
            print(f"\n  >>> 程序执行工具：{tool_name}[{tool_arg}]")
            result = tools.TOOLS[tool_name](tool_arg)
            print(f"  >>> 工具返回：{result[:200]}")
        else:
            result = f"没有叫 {tool_name} 的工具。可用工具只有 Search、Calculate、Finish。"

        observation = f"Observation {step}: {result}"
        messages.append({"role": "user", "content": observation})

    print("\n达到最大轮数仍未得出结论。")
    return "（未能在限定轮数内得出答案）"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        # 默认问题会逼模型先用搜索再用计算器
        q = "雅安地震是哪一年发生的？到2026年是多少周年？"

    run_react(q)