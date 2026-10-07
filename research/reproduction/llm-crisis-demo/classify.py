"""classify.py —— GLM 对灾害推文做"人文信息类别"分类（论文零样本/少样本的复现）

复刻论文：Evaluating Robustness of LLMs on Crisis-Related Microblogs across
Events, Information Types, and Linguistic Features（arXiv:2412.10413，WWW'25）
- 原论文拿 6 个模型（GPT-3.5/4/4o 加三个开源小模型）在 HumAID 测试集上
  测 0/1/3/5/10-shot；我这里只有智谱 GLM 一个 API 模型，测 0-shot 和 3-shot
  两种，模型差异和裁剪都在 README 里写明了。
- 提示词是论文 3.2 节给出的原文（9 个类别 + 定义），要求只输出类别名。
- 论文温度设 0，我也设 0。
- 每条预测缓存在 predict_cache.json 里，中断或网络出错重跑会自动补漏
  （踩过 glm 偶发超时的坑，不设超时整个脚本会无限挂起）。

用法：
  .venv\\Scripts\\python.exe classify.py          # 跑 zero-shot + 3-shot（清洁文本）
  .venv\\Scripts\\python.exe classify.py --typos  # 跑加拼写错误的 zero-shot（鲁棒性实验）
  .venv\\Scripts\\python.exe classify.py --all    # 三块一起跑
  .venv\\Scripts\\python.exe classify.py --fresh  # 丢掉缓存全部重跑
"""

import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
MODEL = "glm-5.3-flash"
TEMPERATURE = 0
THREADS = 3           # 调太猛会吃 429 限流（试过 6 线程被打脸）
MIN_GAP = 0.6         # 相邻两次调用至少隔 0.6 秒，再配合下面的退避基本不会再 429
CACHE = "predict_cache.json"

# 全局调用节流：不管开几个线程，两次 API 调用之间强制拉开间隔
_rate_lock = threading.Lock()
_last_call = {"t": 0.0}


def throttle():
    with _rate_lock:
        gap = MIN_GAP - (time.time() - _last_call["t"])
        if gap > 0:
            time.sleep(gap)
        _last_call["t"] = time.time()

# 论文里的 9 个类别：(标签键, 显示名, 定义)。定义照抄论文提示词原文
CLASSES = [
    ("caution_and_advice", "Caution and advice",
     "Reports of warnings issued or lifted, guidance and tips related to the disaster."),
    ("sympathy_and_support", "Sympathy and support",
     "Tweets with prayers, thoughts, and emotional support."),
    ("requests_or_urgent_needs", "Requests or urgent needs",
     "Reports of urgent needs or supplies such as food, water, clothing, money..."),
    ("displaced_people_and_evacuations", "Displaced people and evacuations",
     "People who have relocated due to the crisis, even for a short time..."),
    ("injured_or_dead_people", "Injured or dead people",
     "Reports of injured or dead people due to the disaster."),
    ("missing_or_found_people", "Missing or found people",
     "Reports of missing or found people due to the disaster."),
    ("infrastructure_and_utility_damage", "Infrastructure and utility damage",
     "Reports of any type of damage to infrastructure such as buildings, houses..."),
    ("rescue_volunteering_or_donation_effort", "Rescue volunteering or donation effort",
     "Reports of any type of rescue, volunteering, or donation efforts..."),
    ("not_humanitarian", "Not humanitarian",
     "If the tweet does not convey humanitarian aid-related information."),
]

NAME2KEY = {name: key for key, name, _ in CLASSES}
# 模型可能输出全名，也可能输出 CA/SS/RUN 这种缩写，都认
ABBR2KEY = {
    "ca": "caution_and_advice", "ss": "sympathy_and_support",
    "run": "requests_or_urgent_needs", "dpe": "displaced_people_and_evacuations",
    "idp": "injured_or_dead_people", "mfp": "missing_or_found_people",
    "iud": "infrastructure_and_utility_damage",
    "rvde": "rescue_volunteering_or_donation_effort", "nh": "not_humanitarian",
}

PROMPT_HEAD = (
    "Read the category names and their definitions below, then classify the following "
    "tweet into the appropriate category. In your response, mention only the category name.\n"
    + "\n".join(f"- {name}: {defn}" for _, name, defn in CLASSES)
)

# 每个线程自己建一个 client。ZhipuAI client 不保证线程安全，各用各的最稳
_local = threading.local()


def get_client():
    if not hasattr(_local, "client"):
        _local.client = ZhipuAI(
            api_key=os.getenv("ZHIPUAI_API_KEY"), timeout=120.0, max_retries=2)
    return _local.client


def clean(s):
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def parse_label(out):
    """把模型输出转成标签键；对不上就返回 None"""
    s = clean(out)
    if s in ABBR2KEY:
        return ABBR2KEY[s]
    for name, key in NAME2KEY.items():
        if clean(name) == s:
            return key
    return None


def build_prompt(text, examples=None):
    """examples 是要在 Tweet 前插入的示例列表 [(显示名, 示例文本), ...]"""
    parts = [PROMPT_HEAD]
    if examples:
        parts.append("Here are some example tweets with their categories:")
        for name, ex in examples:
            parts.append(f"Tweet: {ex}\nCategory: {name}")
    parts.append(f"Tweet: {text}\nCategory:")
    return "\n".join(parts)


def _chat(prompt):
    """调 glm 对话接口：先节流，再调；撞上 429 限流就睡 25 秒重试，
    三次都不行才抛异常（外层会记 ERROR，重跑时自动补）"""
    client = get_client()
    for attempt in range(3):
        throttle()
        try:
            resp = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) or "1302" in str(e):
                time.sleep(25)
                continue
            raise
    raise RuntimeError("连续三次 429 限流")


def ask(label_text, examples=None):
    """调一次 API。输出对不上类别名就追问一次，还不行记 PARSE_FAIL"""
    prompt = build_prompt(label_text, examples)
    out = _chat(prompt)
    key = parse_label(out)
    if key:
        return key, out
    # 追问一次：下死命令只给类别名
    out2 = _chat(prompt + " (Only answer with one of the nine category names.)")
    key2 = parse_label(out2)
    return (key2, out2) if key2 else ("PARSE_FAIL", out2)


def make_typos(text, tid):
    """给推文人为加拼写错误：4 个字母以上的纯字母词，50% 概率被改一处
    （相邻字母对调/删一个字母/字母重复一遍），并保证每条至少改出一个错。
    改了两版：第一版 25% 太轻，typo 和干净版 F1 一模一样；第二版 35%+保底，
    还是不降反升。这是第三版，下重手。论文把 typo 列为 LLM 脆弱点，
    但它表 1/2 里 typo 的回归系数 p 值其实没过显著性线，所以这里用
    更强的直接对照去验证。用推文 id 当种子，每次跑改出来的错都一样。"""
    rng = random.Random(abs(int(tid)))
    words = text.split()
    prob = 0.5
    made = False
    out = []
    for w in words:
        if re.fullmatch(r"[a-zA-Z]{4,}", w) and (not made or rng.random() < prob):
            i = rng.randint(1, len(w) - 2)   # 不动首尾字母，不然没法读
            op = rng.choice(["swap", "drop", "double"])
            if op == "swap":
                w = w[:i] + w[i + 1] + w[i] + w[i + 2:]
            elif op == "drop":
                w = w[:i] + w[i + 1:]
            else:
                w = w[:i] + w[i] + w[i:]
            made = True
        out.append(w)
    return " ".join(out)


def classify_one(item, mode, examples_by_class):
    """给一条推文分类。异常不往外抛，记成 ERROR，下次重跑会补"""
    try:
        if mode == "typo":
            text = make_typos(item["text"], item["id"])
            pred, raw = ask(text)
        elif mode == "few3":
            ex = []
            for key, name, _ in CLASSES:
                for t in examples_by_class[key]:
                    ex.append((name, t))
            pred, raw = ask(item["text"], ex)
        else:   # zero
            pred, raw = ask(item["text"])
        return {"pred": pred, "raw": raw}
    except Exception as e:
        return {"pred": "ERROR", "raw": str(e)[:200]}


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    sys.stdout.reconfigure(line_buffering=True)   # 让进度即时刷出来
    args = sys.argv[1:]
    fresh = "--fresh" in args
    run_typos = "--typos" in args or "--all" in args

    sample = load_json("data/sample.json")
    examples_obj = load_json("data/fewshot_examples.json")
    examples_by_class = examples_obj.get("examples", {})

    cache = {} if fresh else load_json(CACHE)
    modes = ["zero", "few3"] + (["typo"] if run_typos else [])
    items = sample["items"]
    total = len(items) * len(modes)

    lock = threading.Lock()
    state = {"n": 0, "err": 0}

    for mode in modes:
        cache.setdefault(mode, {})
        cache_mode = cache[mode]
        # 缓存里有但结果是 ERROR 的也算"待补"，重跑会把它们救回来
        pending = [it for it in items
                   if fresh or cache_mode.get(it["id"], {}).get("pred") in (None, "ERROR")]
        print(f"[{mode}] 待预测 {len(pending)} 条 / 共 {len(items)} 条")
        if not pending:
            continue

        def work(it):
            return it, classify_one(it, mode, examples_by_class)

        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            for it, result in pool.map(work, pending):
                with lock:
                    cache_mode[it["id"]] = result
                    state["n"] += 1
                    if result["pred"] in ("PARSE_FAIL", "ERROR"):
                        state["err"] += 1
                    if state["n"] % (THREADS * 2) == 0:
                        save_json(CACHE, cache)   # 边跑边存，断了不心疼
                        print(f"  已跑 {state['n']}/{total}，异常 {state['err']} 条", flush=True)
        save_json(CACHE, cache)

    save_json(CACHE, cache)
    print(f"全部跑完，共 {total} 次调用，结果在 {CACHE}")


if __name__ == "__main__":
    main()