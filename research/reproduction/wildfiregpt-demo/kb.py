"""
kb.py —— 知识库加载 + 检索（复现 WildfireGPT 的 RAG 检索那一环）

论文里这一步是：用 all-MiniLM-L6-v2 把文献转成向量，存进 Faiss，query 时做 k 近邻搜索。
我这里做了裁剪：
  - 优先用智谱的 embedding 接口（embedding-3）算向量，用 numpy 自己做余弦相似度（相当于 Faiss 的 kNN）；
  - 如果 API 不通或没装 numpy，自动退化成"关键词 + 字符重合度"的朴素检索。
裁剪原因写在 README 里。
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
KB_PATH = DATA_DIR / "wildfire_kb.json"
VEC_PATH = DATA_DIR / "kb_vectors.json"

EMBED_MODEL = "embedding-3"

_entries = None
_vectors = None
_client = None
MODE = "unknown"  # 最后到底是向量检索还是朴素检索，跑起来才知道


def get_entries():
    """读知识库 json，返回条目列表。"""
    global _entries
    if _entries is None:
        with open(KB_PATH, encoding="utf-8") as f:
            _entries = json.load(f)["entries"]
    return _entries


def _entry_text(entry):
    """把条目拼成一段可检索的文本。"""
    return f"{entry['title']}。{entry['content']}"


def _get_client():
    global _client
    if _client is None:
        from zhipuai import ZhipuAI

        _client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))
    return _client


def _embed(texts):
    """调智谱 embedding 接口。一次最多几十条，够我们的小库用。"""
    client = _get_client()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    # resp.data 的顺序和输入一致
    return [d.embedding for d in resp.data]


def _build_vector_index():
    """给每条知识算向量。带本地缓存，第二次跑就不用再调接口了。"""
    global _vectors
    if _vectors is not None:
        return _vectors

    entries = get_entries()
    texts = [_entry_text(e) for e in entries]

    if VEC_PATH.exists():
        with open(VEC_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("model") == EMBED_MODEL and len(cached.get("vectors", [])) == len(entries):
            _vectors = cached["vectors"]
            return _vectors

    try:
        vecs = _embed(texts)
    except Exception as e:
        print(f"[kb] embedding 接口失败，退化成朴素检索。原始错误：{e}")
        _vectors = None
        return None

    _vectors = vecs
    with open(VEC_PATH, "w", encoding="utf-8") as f:
        json.dump({"model": EMBED_MODEL, "vectors": vecs}, f)
    return _vectors


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _bigrams(text):
    """中文按连续两字的片段切，用来算朴素重合度。"""
    text = "".join(ch for ch in text if ch.strip())
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _naive_score(query, entry):
    """朴素检索打分：查询和条目文本的字符二元组重合度 + 标题命中加分。"""
    q_grams = _bigrams(query)
    t_grams = _bigrams(_entry_text(entry))
    if not q_grams:
        return 0.0
    overlap = len(q_grams & t_grams)
    score = overlap / len(q_grams)
    # 标题里出现查询里的词，额外加点分
    for w in query:
        if w.strip() and w in entry["title"]:
            score += 0.15
    return score


def search(query, top_k=4):
    """
    返回 [(条目, 分数), ...]，按分数从高到低。分数会做归一化，方便看。
    优先向量检索，失败退化成朴素检索。
    """
    global _vectors, MODE
    entries = get_entries()

    if _vectors is None and MODE != "naive":
        _build_vector_index()

    if _vectors:
        MODE = "vector"
        qv = _embed([query])[0]
        scored = [(_cosine(qv, v), e) for e, v in zip(entries, _vectors)]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        return [(e, round(s, 4)) for s, e in top]

    # 朴素检索
    MODE = "naive"
    scored = [(_naive_score(query, e), e) for e in entries]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for s in scored if s[0] > 0][:top_k]
    if not top:
        top = scored[:top_k]
    return [(e, round(s, 4)) for s, e in top]


if __name__ == "__main__":
    # 单独测检索：python kb.py "春季控制烧 居民区风险"
    import sys

    q = " ".join(sys.argv[1:]) or "春季控制烧怎么平衡生态和居民区风险"
    print("检索方式：", end="")
    hits = search(q, top_k=5)
    print(MODE)
    print(f"查询：{q}\n")
    for e, s in hits:
        print(f"[{s}] {e['id']} {e['title']}（{e['category']}）")
