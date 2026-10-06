"""
第二个程序：单独测试"联网搜索"工具（已根据真实返回结构修正）
会消耗 1 次免费搜索额度。
真实结构：
  response.search_intent  -> 列表，长度1，元素有 .query / .keywords
  response.search_result  -> 列表，长度10，元素有 .title / .link / .media / .content
"""

import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

response = client.web_search.web_search(
    search_query="2024年中国地震最严重的是哪一次",
    search_engine="search-std",
)

print("===== 系统优化后的搜索关键词 =====")
intent = response.search_intent[0]          # 列表里取第一个
print("关键词：", intent.keywords)

print("\n===== 前 3 条搜索结果 =====")
results = response.search_result           # 这是一个列表
for i, item in enumerate(results[:3]):
    print(f"--- 第 {i+1} 条 ---")
    print("标题：", item.title)
    print("来源：", item.media)
    print("链接：", item.link)
    print("正文：", item.content[:150], "...")
    print()
