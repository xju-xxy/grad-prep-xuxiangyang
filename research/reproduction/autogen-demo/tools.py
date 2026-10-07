"""tools.py —— 多智能体共用的工具。目前只有联网搜索。"""

import os

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))


def search(query: str) -> str:
    """联网搜索，返回前5条拼好的文本"""
    response = client.web_search.web_search(
        search_query=query,
        search_engine="search-std",
    )
    results = response.search_result
    pieces = []
    for i, item in enumerate(results[:5]):
        block = f"[{i+1}] 标题：{item.title}\n    内容：{item.content[:300]}"
        pieces.append(block)
    return "\n".join(pieces)