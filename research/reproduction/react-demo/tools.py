"""
tools.py —— 给 ReAct 用的工具集合。
模型输出 Search[关键词] / Calculate[算式] 时，主程序来这里找对应函数。
"""

import os

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))


def search(query: str) -> str:
    """联网搜索，返回拼好的纯文本（模型只能读文字）"""
    response = client.web_search.web_search(
        search_query=query,
        search_engine="search-std",
    )

    results = response.search_result

    pieces = []
    for i, item in enumerate(results[:5]):  # 只留前5条，多了费token也没用
        block = f"[{i+1}] 标题：{item.title}\n    内容：{item.content[:300]}"
        pieces.append(block)

    return "\n".join(pieces)


_ALLOWED_CHARS = set("0123456789.+-*/%() ")


def calculate(expression: str) -> str:
    """计算器。eval 之前先过一遍白名单，只放数字和运算符进去"""
    for ch in expression:
        if ch not in _ALLOWED_CHARS:
            return f"计算失败：算式里出现了不支持的内容「{ch}」，只允许数字和 + - * / % ( )"

    try:
        value = eval(expression, {"__builtins__": {}}, {})
        return str(value)
    except Exception as e:
        return f"计算失败：{e}"


# 工具登记表，主程序靠这个表找工具
TOOLS = {
    "Search": search,
    "Calculate": calculate,
}