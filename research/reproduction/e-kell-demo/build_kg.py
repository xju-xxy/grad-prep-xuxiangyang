"""build_kg.py —— 把标准条文抽成知识图谱

照着 E-KELL 论文"知识结构化"那步来的：用大模型把条文读成
一条条 (主体, 关系, 客体) 三元组，存进 kg.json。
原论文是 LLM 抽取 + 专家人工校对，我们只有 LLM 抽取这一步。
"""

import json
import re

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=__import__("os").getenv("ZHIPUAI_API_KEY"))

MODEL_NAME = "glm-5.3-flash"
CORPUS_PATH = "corpus.txt"
OUT_PATH = "kg.json"
BATCH_SIZE = 5          # 每批把几条条文一起塞给模型抽

# 抽取提示词：参考论文 Appendix A 里的 KG Construction 模板改的
EXTRACT_PROMPT = """你是知识图谱构建助手。请从下面的应急标准条文中抽取知识三元组。
每个三元组写成一行，格式：主体|关系|客体
要求：
1. 主体和客体尽量简短、规范（比如"二级危险化学品单位""二氧化硫""隔离距离"），
   客体可以是数值、装备、措施。
2. 关系用简短的动词或动词短语，比如：配备、禁止、要求、具有、可引起、
   应穿戴、初始隔离距离为、可能的原因为。
3. 只抽取条文里明确写出的内容，不要推理、不要补充条文里没有的知识。
4. 直接输出三元组，一行一个，不要编号、不要多余解释。

示例：
条文：医疗急救箱应配备 1 个。
输出：
二级危险化学品单位|配备|医疗急救箱
医疗急救箱|数量|1 个

条文：
"""


def load_corpus(path):
    """读语料：按'## 文档X'分份，返回 [(文档名, [条文, ...]), ...]"""
    docs = []
    cur_name, cur_items = None, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("## "):
            if cur_name:
                docs.append((cur_name, cur_items))
            cur_name, cur_items = line[3:].strip(), []
        elif line and not line.startswith("#") and not line.startswith(">"):
            cur_items.append(line)
    if cur_name:
        docs.append((cur_name, cur_items))
    return docs


def extract_triples(items):
    """把一批条文喂给模型，解析返回的三元组"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": "\n".join(items)},
        ],
        temperature=0.2,
    )
    text = response.choices[0].message.content.strip()
    triples = []
    for line in text.splitlines():
        line = re.sub(r"^\s*[0-9]+[.、)]?\s*", "", line.strip())   # 去掉行首编号，模型爱乱加
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and all(parts):
            triples.append({"s": parts[0], "r": parts[1], "o": parts[2]})
        elif line:
            print(f"  [警告] 格式怪，跳过：{line}")
    return triples


def main():
    docs = load_corpus(CORPUS_PATH)
    print(f"语料里有 {len(docs)} 份文档")
    all_triples = []
    for doc_name, items in docs:
        print(f"\n处理《{doc_name}》（{len(items)} 条）")
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            triples = extract_triples(batch)
            for t in triples:
                t["src"] = doc_name
            all_triples.extend(triples)
            print(f"  第 {i+1}-{i+len(batch)} 条 -> 抽到 {len(triples)} 个三元组")

    # 完全重复的丢一个
    seen, unique = set(), []
    for t in all_triples:
        key = (t["s"], t["r"], t["o"])
        if key not in seen:
            seen.add(key)
            unique.append(t)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"triples": unique}, f, ensure_ascii=False, indent=2)
    print(f"\n完成：{len(unique)} 个三元组（去重后）写入 {OUT_PATH}")


if __name__ == "__main__":
    main()