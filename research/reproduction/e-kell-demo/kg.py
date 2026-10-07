"""kg.py —— 知识图谱查询

reason.py 靠它从 kg.json 里翻三元组。
论文里检索靠 LlamaIndex 向量库做相似度匹配，我们没有条件，
就换成"关键词命中 + 一层邻域扩展"，演示够用。

论文 3.2 节里的四个一阶逻辑操作（投影/交集/并集/补集）
也各放了一个简易版，对应 prompt 链里"让 LLM 在图谱上导航"的步骤。
"""

import json
import re


class KnowledgeGraph:
    def __init__(self, path="kg.json"):
        self.triples = json.load(open(path, encoding="utf-8"))["triples"]

    # ---- 四个逻辑操作 ----
    def project(self, entity, relation):
        """投影 p：问"(实体, 关系) -> 哪些客体"。比如 (二氧化硫, 沸点) -> -10℃"""
        return [t["o"] for t in self.triples if t["s"] == entity and t["r"] == relation]

    def neighbors(self, entity):
        """实体出现过的所有三元组（它的全部邻居）"""
        return [t for t in self.triples if t["s"] == entity or t["o"] == entity]

    def intersection(self, a, b):
        """交集：两个集合里都有的元素"""
        return list(set(a) & set(b))

    def union(self, a, b):
        """并集：两个集合里所有不重复的元素"""
        return list(set(a) | set(b))

    def negation(self, a, universe):
        """补集：全集里不属于 a 的元素"""
        return list(set(universe) - set(a))

    @staticmethod
    def _norm(text):
        """去掉标点和空格，方便比对自己写的问句和图谱里的实体名"""
        return re.sub(r"[\s、，。,]", "", text)

    # ---- 检索 ----
    def expand(self, keywords, question="", hops=1):
        """关键词命中 + 问题原文兜底匹配 + k 层邻域扩展。

        先用关键词粗筛一批三元组当"入口"；
        问题里的实体全名（比如"毒性中等、危害较小的区域"）会被标点
        卡住，所以再用"去标点后包含"的方式补一轮匹配；
        最后把命中的实体往邻居扩一层，把相关条文一起捞出来。
        这就是论文里 k-level neighborhood expansion 的裁剪版。
        """
        found = {}

        def take(t):
            found[(t["s"], t["r"], t["o"])] = t

        for kw in keywords:
            for t in self.triples:
                if kw in t["s"] or kw in t["o"]:
                    take(t)
        if question:
            q = self._norm(question)
            for t in self.triples:
                for name in (t["s"], t["o"]):
                    n = self._norm(name)
                    if len(n) >= 4 and n in q:
                        take(t)
        for _ in range(hops):
            for (s, _r, o) in list(found.keys()):
                for t in self.triples:
                    if t["s"] in (s, o) or t["o"] in (s, o):
                        found[(t["s"], t["r"], t["o"])] = t
        return list(found.values())


if __name__ == "__main__":
    kg = KnowledgeGraph()
    print(f"图谱规模：{len(kg.triples)} 个三元组")
    print("\n投影测试：二氧化硫 的 沸点 是？")
    print(" ", kg.project("二氧化硫", "沸点为"))
    print("\n投影测试：丙烯 的 化学式 是？")
    print(" ", kg.project("丙烯", "化学式为"))
    print("\n检索测试：关键词 [丙烯] 邻域扩展 1 层，命中多少条？")
    hits = kg.expand(["丙烯"], hops=1)
    print(f" {len(hits)} 条，前 5 条：")
    for t in hits[:5]:
        print("  (", t["s"], ",", t["r"], ",", t["o"], ")")