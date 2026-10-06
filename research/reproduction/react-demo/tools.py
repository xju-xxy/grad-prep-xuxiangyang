"""
tools.py —— ReAct 智能体可以调用的"工具"都放在这里。

一个工具 = 一个普通的 Python 函数。
模型在回答里喊出  Search[关键词]  或  Calculate[算式]，
我们的主程序就调用这里对应的函数，再把结果作为"观察(Observation)"喂回给模型。
"""

import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 和 hello_glm.py 里一样：读 Key、创建客户端。
# 别的文件只要 import tools，就能直接用这里的 client，不用重复写。
load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))


# ----------------------------------------------------------------------
# 工具 1：联网搜索
# ----------------------------------------------------------------------
def search(query: str) -> str:
    """
    输入：搜索关键词（一个字符串）
    输出：整理成纯文本的搜索结果（因为模型只能读懂文字，不能读对象）
    """
    # 调用智谱联网搜索接口
    response = client.web_search.web_search(
        search_query=query,
        search_engine="search-std",
    )

    results = response.search_result   # 一个列表，最多 10 条

    # 把每条结果拼成一段文字。只取前 5 条，太多会浪费 token、也会让模型抓不住重点
    pieces = []
    for i, item in enumerate(results[:5]):
        # 每条结果：序号 + 标题 + 正文（正文只保留前 300 个字，防止太长）
        block = f"[{i+1}] 标题：{item.title}\n    内容：{item.content[:300]}"
        pieces.append(block)

    # 用换行把 5 条结果连成一个大字符串返回
    return "\n".join(pieces)


# ----------------------------------------------------------------------
# 工具 2：计算器
# ----------------------------------------------------------------------
# 先规定：算式里只允许出现这些字符（数字、小数点、空格、括号、加减乘除、百分号）
# 这是一道"安全闸门"——把字母等其他字符全部挡在外面，防止有人写危险代码
_ALLOWED_CHARS = set("0123456789.+-*/%() ")


def calculate(expression: str) -> str:
    """
    输入：一个算式字符串，例如 "(1200 + 350) * 2"
    输出：计算结果，例如 "3100"
    """
    # 第一步：逐个字符检查，只要出现不允许的字符，就直接拒绝
    for ch in expression:
        if ch not in _ALLOWED_CHARS:
            return f"计算失败：算式里出现了不支持的内容「{ch}」，只允许数字和 + - * / % ( )"

    # 第二步：真正计算。
    # eval() 能把字符串当算式算出来，但它本来很危险（能执行任意代码），
    # 所以我们做了两件事让它变安全：
    #   1. 上面的字符白名单已经把字母全挡住了；
    #   2. 这里把 __builtins__ 设成空字典，禁止它调用任何内置功能。
    try:
        value = eval(expression, {"__builtins__": {}}, {})
        return str(value)
    except Exception as e:
        # 万一算式写错了（比如括号不配对），把错误信息返回给模型，让它重试
        return f"计算失败：{e}"


# ----------------------------------------------------------------------
# 工具登记表（重要！）
# ----------------------------------------------------------------------
# 主程序通过这张表，用"名字"找到对应的函数。
# 键 key   = 模型回答里写的工具名（必须和提示词里教它的名字完全一致）
# 值 value = 真正干活的函数
TOOLS = {
    "Search": search,
    "Calculate": calculate,
}
