"""reason.py —— 问答主管线：问题 -> 图谱检索 -> 带证据的回答

对应 E-KELL 论文 3.2 节的 prompt 链，裁掉了向量库那步：
1. 让模型从问题里挑检索关键词
2. 代码拿关键词去图谱检索 + 邻域扩展
3. 把检到的三元组喂给模型，按论文要求"只用图谱里的知识"回答

这样每一句答案都有三元组兜底，模型想编造也没有空间。
"""

import os
import re

from dotenv import load_dotenv
from zhipuai import ZhipuAI

from kg import KnowledgeGraph

load_dotenv()
# 加个超时，不然碰到网络抖动会无限挂起（踩过坑）
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"), timeout=180.0, max_retries=2)

MODEL_NAME = "glm-5.3-flash"
kg = KnowledgeGraph()

KEYWORD_PROMPT = """从下面的应急问题里提取用于检索知识图谱的关键词。
只输出 2 到 5 个词，用顿号分隔，不要解释。

问题：{question}
关键词："""

# 论文 Appendix A 里 Decision Support 模板的中文版
ANSWER_PROMPT = """以下是表示实体之间关系的三元组数组：
{context}

请仅根据以上信息回答下面的问题：{question}
禁止使用以上信息之外的任何知识。如果三元组不足以回答问题，
直接回答"知识库中没有相关内容"，不要编造。"""

NO_HIT_ANSWER = "（知识图谱中没有检索到与本题相关的三元组，为避免编造，系统不给出回答。）"


def ask_keywords(question):
    """第 1 步：从问题里抽检索关键词"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": KEYWORD_PROMPT.format(question=question)}],
        temperature=0.1,
    )
    text = response.choices[0].message.content.strip()
    words = [w.strip(" 。，,、" "）)(") for w in re.split(r"[、,，]", text)]
    return [w for w in words if len(w) >= 2][:5]


def retrieve(question, keywords):
    """第 2 步：关键词命中 + 问题原文兜底 + 1 层邻域扩展，返回三元组列表"""
    return kg.expand(keywords, question=question, hops=1)


def triple_lines(triples):
    """把三元组拼成待会要进提示词的样子"""
    return "\n".join(f"({t['s']}, {t['r']}, {t['o']})" for t in triples)


def answer(question, triples):
    """第 3 步：拿着图谱证据让模型答题"""
    if not triples:
        return NO_HIT_ANSWER
    context = triple_lines(triples)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": ANSWER_PROMPT.format(context=context, question=question)},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def run(question, verbose=True):
    """整条管线，verbose 打开时会打印每一步，方便看推理过程"""
    keywords = ask_keywords(question)
    triples = retrieve(question, keywords)
    ans = answer(question, triples)

    if verbose:
        print(f"问题：{question}")
        print(f"第 1 步 关键词：{'、'.join(keywords)}")
        print(f"第 2 步 图谱检索到 {len(triples)} 条三元组：")
        for t in triples[:12]:
            print(f"    ({t['s']}, {t['r']}, {t['o']})")
        if len(triples) > 12:
            print(f"    ...还有 {len(triples) - 12} 条")
        print(f"第 3 步 答案：\n{ans}\n")
    return {"keywords": keywords, "triples": triples, "answer": ans}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "危险化学品仓库发生泄漏，泄漏气体为二氧化硫和丙烯，现场为毒性中等、危害较小的区域，应如何进行个体防护？"
    run(q)