"""eval.py —— 评测：纯 LLM vs LLM+KG

复刻论文第 5 节的评测思路：10 道危化品泄漏决策题（就是论文
附录 B 那 10 类决策点，我翻译成了中文），两套方案各答一遍，
再用模型当评委按 4 个维度打分，外加一道"客观要点命中"检查。

原论文的评委是 19 位专家（14 名消防员 + 5 名指挥官），
我请不起专家团，就改用另一个 LLM 调用**代评**——会有偏差，
README 里如实说明。分数打分之前模型没见过的题目和答案组合。

结果缓存在 eval_answers.json，重复跑不会重新生成（省额度）。
想强制重跑：.venv\\Scripts\\python.exe eval.py --fresh
"""

import json
import os
import re
import sys

from dotenv import load_dotenv
from zhipuai import ZhipuAI

import reason

load_dotenv()
# 加个超时，不然碰到网络抖动会无限挂起（踩过坑）。
# 纯LLM的答案比较啰嗦，生成和评分都慢，超时给宽松点 180 秒
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"), timeout=180.0, max_retries=2)

MODEL = "glm-5.3-flash"
CACHE = "eval_answers.json"
TEMPERATURE = 0.3      # 生成答案时两个方案用同一个温度，保证对比公平

PLAIN_PROMPT = """你是应急管理专家，请直接回答下面的问题。
尽量给出准确、可操作、简洁的回答：
{question}"""

# 10 道题：(编号, 决策点, 问题, 客观检查关键词)
QUESTIONS = [
    ("Q1", "物资储备", "二级危险化学品单位应配备哪些应急装备器材？", ["有毒气体检测仪", "吸附垫", "1200"]),
    ("Q2", "现场指挥", "危险化学品泄漏事故中，应急人员进入现场开展保护与救援，应遵循什么程序？", ["防护装备", "救生器材", "安全区域"]),
    ("Q3", "事故调查", "危险化学品仓库发生泄漏，经检查确认泄漏源为管道泄漏，且已排除自然灾害和人为因素，事故可能的原因有哪些？", ["管道腐蚀", "防腐缺陷", "安装缺陷"]),
    ("Q4", "危险源辨识", "危险化学品仓库泄漏的气体为二氧化硫和丙烯，这两种物质的理化性质是什么？是否存在燃烧爆炸危险？", ["C3H6", "相对密度", "爆炸极限"]),
    ("Q5", "灭火", "危险化学品仓库泄漏物为二氧化硫和丙烯并发生火灾，应如何灭火？有哪些注意事项？", ["冷却容器", "严禁将水射入"]),
    ("Q6", "个体防护", "危险化学品仓库泄漏气体为二氧化硫和丙烯，现场为毒性中等、危害较小的区域，应如何进行个体防护？", ["化学防护服", "防毒面具"]),
    ("Q7", "救援急救", "危险化学品仓库泄漏气体为二氧化硫和丙烯，现场有人吸入了这些气体，应如何进行现场急救？", ["新鲜空气", "脱去污染衣物", "立即就医"]),
    ("Q8", "隔离疏散", "危险化学品仓库发生泄漏（气体含二氧化硫和丙烯），应如何隔离和疏散周边群众？", ["500", "1500", "1600"]),
    ("Q9", "危险源控制", "危险化学品仓库发生泄漏后，应如何处置和控制泄漏源？", ["关闭阀门", "堵漏", "雾状水"]),
    ("Q10", "报告汇编", "灭火战斗情况的报告（战评材料）中应当包含哪些信息？", ["灭火行动", "消防水源", "蔓延范围"]),
]


def ask_plain(question):
    """纯 LLM：不带任何图谱，直接答"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PLAIN_PROMPT.format(question=question)}],
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content.strip()


def ask_kg(question):
    """LLM+KG：走 reason.py 的完整管线"""
    return reason.run(question, verbose=False)["answer"]


JUDGE_PROMPT = """你是应急管理领域的评委。请给下面的回答按 4 个维度打分，
每项 1 到 10 的整数。维度：
- comprehensibility 可理解性：表达是否清楚易懂
- accuracy 准确性：有没有事实错误
- conciseness 简洁性：有没有冗余废话
- instructiveness 指导性：能不能直接照着执行

问题：{question}

回答：
{answer}

只输出一个 JSON，不要任何解释文字：
{{"可理解性": 9, "准确性": 9, "简洁性": 9, "指导性": 9}}"""

# 评委可能会用中文键或英文键，都认
KEY_ALIASES = {
    "comprehensibility": "comprehensibility", "可理解性": "comprehensibility",
    "accuracy": "accuracy", "准确性": "accuracy",
    "conciseness": "conciseness", "简洁性": "conciseness",
    "instructiveness": "instructiveness", "指导性": "instructiveness",
}


def judge(question, answer):
    """模型代评，返回四维分数 dict。解析失败重试一次。"""
    for attempt in range(2):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer[:1500])}],
            temperature=0,
        )
        text = response.choices[0].message.content.strip()
        m = re.search(r"\{[^{}]*\}", text)
        if m:
            try:
                raw = json.loads(m.group(0))
                scores = {}
                for k, v in raw.items():
                    if k in KEY_ALIASES:
                        scores[KEY_ALIASES[k]] = int(v)
                wanted = ["comprehensibility", "accuracy", "conciseness", "instructiveness"]
                if all(k in scores for k in wanted):
                    return {k: scores[k] for k in wanted}
            except (ValueError, TypeError):
                pass
        print(f"  [警告] 评分解码失败（第 {attempt+1} 次），原文：{text[:100]}")
    return {"comprehensibility": 0, "accuracy": 0, "conciseness": 0, "instructiveness": 0}


def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(data):
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    sys.stdout.reconfigure(line_buffering=True)   # 让打印即时出现在日志里，方便看卡在哪
    fresh = "--fresh" in sys.argv
    data = load_cache()
    data.setdefault("answers", {})
    data.setdefault("scores", {})

    # ---- 生成答案 ----
    for qid, topic, q, checks in QUESTIONS:
        for mode, fn in [("纯LLM", ask_plain), ("LLM+KG", ask_kg)]:
            if fresh or qid not in data["answers"].get(mode, {}):
                print(f"生成 {mode} 答案：{qid} {topic}", flush=True)
                try:
                    data["answers"].setdefault(mode, {})[qid] = fn(q)
                    save_cache(data)   # 边跑边存，断了不心疼
                except Exception as e:
                    print(f"  [异常] {qid} {mode}：{e}；跳过，下次重跑会补")

    # ---- 打分 ----
    for qid, topic, q, checks in QUESTIONS:
        for mode in ["纯LLM", "LLM+KG"]:
            if fresh or qid not in data["scores"].get(mode, {}):
                if qid not in data["answers"].get(mode, {}):
                    print(f"跳过评分 {mode} {qid}：答案还没生成")
                    continue
                ans = data["answers"][mode][qid]
                print(f"评分 {mode}：{qid} {topic}", flush=True)
                try:
                    data["scores"].setdefault(mode, {})[qid] = judge(q, ans)
                    save_cache(data)
                except Exception as e:
                    print(f"  [异常] {qid} {mode}：{e}；跳过，下次重跑会补")

    # ---- 客观要点命中 ----
    print("\n" + "=" * 100)
    print("评测结果（评分 1-10，客观命中为答案里出现检查关键词的个数）")
    print("=" * 100)
    header = f"{'题目':<6}{'方案':<8}{'可理解':<8}{'准确':<8}{'简洁':<8}{'指导':<8}{'客观命中':<10}"
    print(header)
    print("-" * 100)

    sums = {"纯LLM": [0, 0, 0, 0], "LLM+KG": [0, 0, 0, 0]}
    counts = {"纯LLM": 0, "LLM+KG": 0}
    hit_sums = {"纯LLM": 0, "LLM+KG": 0}
    total_checks = 0
    dims = ["comprehensibility", "accuracy", "conciseness", "instructiveness"]

    for qid, topic, q, checks in QUESTIONS:
        total_checks += len(checks)
        for mode in ["纯LLM", "LLM+KG"]:
            s = data["scores"][mode].get(qid, {})
            vals = [s.get(d, 99) for d in dims]   # 99 表示还没评分
            ans = data["answers"].get(mode, {}).get(qid, "")
            hits = sum(1 for k in checks if k in ans)
            hit_sums[mode] += hits
            if max(vals) <= 10:
                counts[mode] += 1
                for i in range(4):
                    sums[mode][i] += vals[i]
            print(f"{qid+'-'+topic[:2]:<6}{mode:<8}{vals[0]:<10}{vals[1]:<10}{vals[2]:<10}{vals[3]:<10}{str(hits)+'/'+str(len(checks)):<10}")

    print("-" * 100)
    for mode in ["纯LLM", "LLM+KG"]:
        n = max(counts[mode], 1)
        avg = [round(x / n, 2) for x in sums[mode]]
        print(f"{mode:<8}平均分：可理解 {avg[0]} / 准确 {avg[1]} / 简洁 {avg[2]} / 指导 {avg[3]}"
              f"   客观要点命中 {hit_sums[mode]}/{total_checks}")
    print("\n答案全文存在 eval_answers.json 里。")


if __name__ == "__main__":
    main()