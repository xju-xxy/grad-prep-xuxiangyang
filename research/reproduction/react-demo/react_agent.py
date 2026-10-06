"""
react_agent.py —— ReAct 智能体主程序（把前面所有零件组装起来）。

运行方式：
    .venv\\Scripts\\python.exe react_agent.py
    .venv\\Scripts\\python.exe react_agent.py "你自己的问题"

整体就是一个循环：
    模型出 Thought+Action  ->  程序解析并执行工具  ->  把 Observation 喂回去  ->  再来一轮
    直到模型输出 Finish[答案]，或者达到最大轮数（防止它无限循环）。
"""

import os
import re
import sys

from dotenv import load_dotenv
from zhipuai import ZhipuAI

# prompt.py 里存的系统提示词，tools.py 里存的工具表和客户端
from prompt import SYSTEM_PROMPT
import tools

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

# 指定用哪个模型。glm-5.3-flash 走你的免费额度，速度也快。
MODEL_NAME = "glm-5.3-flash"

# 最多允许循环多少轮，防止模型一直不结束、白白烧 token
MAX_STEPS = 6

# 正则表达式：用来从模型的回答里把 "Action 1: Search[关键词]" 这种行抠出来。
# 拆开理解这个模式：
#   Action        必须以 Action 开头
#   \s*\d*\s*     \s*=任意个空格，\d*=任意个数字（用来匹配 "Action 1"，数字可有可无）
#   [:：]         冒号，英文 : 或中文 ：都接受
#   \s*           冒号后面的空格
#   ([A-Za-z]+)   第1个括号：工具名，由字母组成，比如 Search
#   \s*\[         空格 + 左方括号
#   ([^\]]*)      第2个括号：参数，[^\]] 表示"除右括号以外的任意字符"，即一直取到 ] 之前
#   \]            右方括号
ACTION_PATTERN = re.compile(r"Action\s*\d*\s*[:：]\s*([A-Za-z]+)\s*\[([^\]]*)\]")


def run_react(question: str) -> str:
    """
    给定一个问题，跑完整的 ReAct 循环，返回最终答案字符串。
    """
    # messages 是对话记录，模型每一轮都能看到之前发生的所有事情（这就是它的"记忆"）
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"问题：{question}"},
    ]

    print("=" * 70)
    print("用户问题：", question)
    print("=" * 70)

    # 开始 ReAct 循环，step 是当前第几轮
    for step in range(1, MAX_STEPS + 1):
        # 1) 把目前的完整对话发给模型，让它生成下一步
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,          # 温度低一些，输出更稳定、更守格式
        )
        text = response.choices[0].message.content.strip()

        # 把模型这一轮说的话先记进对话历史，再打印给我们看
        messages.append({"role": "assistant", "content": text})
        print(f"\n【第 {step} 轮 · 模型输出】\n{text}")

        # 2) 解析动作。注意：我们只认"第一个"Action。
        first_match = ACTION_PATTERN.search(text)

        # 情况一：一个 Action 都没识别出来 -> 提醒模型按格式重来
        if first_match is None:
            obs = "我没有从你上一步的输出里识别出 Action。请严格按格式输出：Action 编号: 工具名[参数]"
            messages.append({"role": "user", "content": obs})
            print(f"\n【系统提示】{obs}")
            continue

        # 保险：如果模型在第一个 Action 之后还写了别的东西
        # （比如它自己编造的 Observation、或提前写好的第 2 轮内容），一律砍掉。
        # 这样可以强制它"写完一个动作就停"，老老实实用真实的工具结果，而不是靠幻觉编完整条轨迹。
        cut_pos = first_match.end()          # 第一个 Action 右括号 ] 在文本里的结束位置
        if cut_pos < len(text):
            text = text[:cut_pos].rstrip()   # 只保留到第一个 Action 为止
            messages[-1]["content"] = text   # 用裁剪后的内容替换刚才存进历史的那条
            print("\n  [系统拦截] 检测到模型在第一个动作后自行补写了内容，已忽略，强制等待真实工具结果。")

        # 从第一个 Action 里取出工具名和参数
        tool_name = first_match.group(1)
        tool_arg = first_match.group(2).strip()
        # 统一成首字母大写，避免模型写成 search / SEARCH 导致查不到工具
        tool_name = tool_name[0].upper() + tool_name[1:].lower()

        # 情况二：模型选择结束
        if tool_name == "Finish":
            print("\n" + "=" * 70)
            print("最终答案：", tool_arg)
            print("=" * 70)
            return tool_arg

        # 情况三：模型调用了一个真实工具
        if tool_name in tools.TOOLS:
            print(f"\n  >>> 程序执行工具：{tool_name}[{tool_arg}]")
            result = tools.TOOLS[tool_name](tool_arg)     # 真正调用 search / calculate
            print(f"  >>> 工具返回：{result[:200]}")       # 屏幕上只预览前200字
        else:
            # 工具名不在表里 -> 告诉模型它写错了
            result = f"没有叫 {tool_name} 的工具。可用工具只有 Search、Calculate、Finish。"

        # 3) 把工具结果包装成 Observation，以 user 身份追加进对话，下一轮模型就能看到
        observation = f"Observation {step}: {result}"
        messages.append({"role": "user", "content": observation})

    # 如果循环到上限还没 Finish，返回一个兜底提示
    print("\n达到最大轮数仍未得出结论。")
    return "（未能在限定轮数内得出答案）"


# 这一段的意思：直接运行本文件时才执行；被别的文件 import 时不执行。
if __name__ == "__main__":
    # 如果命令行里带了问题参数就用它，否则用一个默认的演示问题。
    # 这个默认问题故意需要"先搜索年份、再做减法"，能同时逼出 Search 和 Calculate 两个工具。
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "雅安地震是哪一年发生的？到2026年是多少周年？"

    run_react(q)
