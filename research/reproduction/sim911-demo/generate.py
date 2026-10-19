"""generate.py —— 受控生成：让 GLM 扮演"呼救者"，按事件规格 + 来电者画像开口

对应论文 Sim911（arXiv:2412.16844，AAAI 2025）里的"受控生成"那一环。
论文的三件套是：离线知识构建 → 受控生成 → 验证闭环，这里做的是中间那块。

论文用 GPT-4o，我这里换成智谱 glm-4-flash（国产、便宜、国内好调）。
论文用的是美国 911 的真实呼叫记录，我这里没有那份数据，也没有办法拿到，
所以退一步：自己手搓一份小型知识库（事件规格 / 来电者画像 / 处置协议 / 地址表），
把它换成国内的 120 急救场景。核心机制——查库、注入画像风格、限定地址、
生成完必须校验——是照论文来的。

用法见 run_eval.py，本文件主要提供 build_prompt / generate_one 给上层调。
"""

import json
import os
import threading
import time

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()

MODEL = "glm-4-flash"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 调太猛会被 429 限流（前一个项目 6 线程被打脸过），这里全局节流
MIN_GAP = 0.6
_rate_lock = threading.Lock()
_last_call = {"t": 0.0}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_kb():
    """把 data/ 下的小知识库整套读进来"""
    return {
        "events": load_json(os.path.join(DATA_DIR, "events.json"))["items"],
        "profiles": load_json(os.path.join(DATA_DIR, "profiles.json"))["items"],
        "protocols": {p["type_key"]: p for p in load_json(
            os.path.join(DATA_DIR, "protocols.json"))["items"]},
        "addresses": load_json(os.path.join(DATA_DIR, "addresses.json"))["items"],
    }


def throttle():
    with _rate_lock:
        gap = MIN_GAP - (time.time() - _last_call["t"])
        if gap > 0:
            time.sleep(gap)
        _last_call["t"] = time.time()


# 每个线程自己一个 client，ZhipuAI client 不保证线程安全
_local = threading.local()


def get_client():
    if not hasattr(_local, "client"):
        _local.client = ZhipuAI(
            api_key=os.getenv("ZHIPUAI_API_KEY"), timeout=120.0, max_retries=2)
    return _local.client


def chat(prompt, temperature=0.7):
    """调一次对话接口。撞上 429 就睡一会儿重试，三次不行才抛。"""
    client = get_client()
    last = None
    for _ in range(3):
        throttle()
        try:
            resp = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}],
                temperature=temperature)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last = e
            if "429" in str(e) or "1302" in str(e):
                time.sleep(20)
                continue
            raise
    raise RuntimeError(f"连续三次调用失败：{last}")


# 输出的三个必备字段（格式校验就查这三个在不在）
FIELDS = ["【地点】", "【呼救者原话】", "【求助要点】"]


def build_prompt(event, profile, kb, use_profile=True, use_kb=True):
    """拼提示词。三个开关对应后面的消融：
    use_profile=False 就是不注入画像（论文说的"关掉画像/知识注入"）；
    use_kb=False 就是把地址表和处置协议也拿掉（论文说的"关掉知识构建"）。
    """
    lines = [
        "你现在要扮演一位拨打 120 急救电话的呼救者，配合调度员做一次接警陪练。",
        "先在心里想一下：这个人此刻是什么状态、他最急着说什么、他会怎么描述位置，然后再开口。",
        "",
        "# 事件规格（你必须按这个场景来，不能改事件类型）",
        f"事件类型：{event['type']}",
        f"典型情境：{event['situation']}",
        f"特殊请求：{event['special']}",
        "",
    ]

    if use_kb:
        proto = kb["protocols"].get(event["type_key"])
        if proto:
            lines.append("# 处置协议（这个场景调度员大致会走这些步骤，供你把握该报哪些信息点，不要照着念）")
            for i, s in enumerate(proto["steps"], 1):
                lines.append(f"{i}. {s}")
            lines.append("")

    if use_profile and profile:
        lines += [
            "# 来电者画像（你必须演出这个人的说话特征，不要平铺直叙地报信息）",
            f"画像：{profile['name']}",
            f"说话风格：{profile['style']}",
            f"说话风格样例（这是别人的话，只用来体会口吻）：\"{profile['sample']}\"",
            "注意：样例里出现过的任何完整短句都不许出现在你的原话里，"
            "情节、句子、地址全部按上面的事件规格重新写，只模仿口吻。",
            "",
        ]

    if use_kb:
        lines.append("# 地址表（事发地点必须从下表里挑一条，原样抄写，绝对禁止自己编地址）")
        for a in kb["addresses"]:
            lines.append(f"- {a['full']}")
        lines.append("")

    lines += [
        "# 输出格式（必须严格按下面三行输出，不要多写任何解释、不要加标题以外的内容）",
        "【地点】<从地址表里原样抄一条地址>",
        "【呼救者原话】<呼救者开口说的第一段话，1~4 句；要能听出画像的说话特征，"
        "并且必须把上面那条地址说出来（至少说清小区名或路名）>",
        "【求助要点】<呼救者最想让调度员知道的一个关键信息>",
    ]
    return "\n".join(lines)


def generate_one(event, profile, kb, use_profile=True, use_kb=True, feedback=None):
    """生成一版呼救开场白。feedback 不为空时是"打回重生成"，
    会把上一轮不合规的原因一并塞进提示词。"""
    prompt = build_prompt(event, profile, kb, use_profile, use_kb)
    if feedback:
        prompt += ("\n\n# 上一版被打回，请重写\n上一版不合规的原因："
                   + feedback + "\n这一版务必改正。")
    return chat(prompt, temperature=0.7)
