"""verify.py —— 验证闭环：生成完先查再收，不合规打回重生成

论文 Sim911 的第三个模块。论文的校验有三项：格式、对齐（用 BERT 比事件标签）、
事实（用 RoBERTa-QA 验地址 + Google Maps 地理编码），再加人工打分；不合规就
打回重生成，上限 3 轮。

我这里没有 BERT / RoBERTa 那些本地模型（也没显卡），就用 prompt 让 glm 自己当
裁判来做，具体的三项是：

1. 格式：三个必备字段（地点 / 呼救者原话 / 求助要点）齐不齐、空不空
2. 事实：地址在不在地址表里（这条是论文"地址真实性"的直接对应），
   并且这条地址有没有真的出现在呼救者原话里
3. 画像一致：把呼救者原话单独拎出来，不让模型知道我们想演谁，
   让它从 8 个画像里盲猜是哪一个，猜中就算一致（这条对应论文的"画像识别率"）

三项全过才算收，否则把失败原因拼成 feedback 打回重生成，最多 3 轮。
副作用得说清楚：因为画像一致也是门槛，最后一版的画像一致率基本是被"逼"出来的，
真正能反映生成质量的是**首轮**的画像一致率，所以结果表里两个数都给。
"""

import re

from generate import FIELDS, chat, generate_one

# ------------------------- 解析 -------------------------

_NAMES = [f.strip("【】") for f in FIELDS]


def parse_output(text):
    """把模型输出按【字段】拆成 dict。缺字段就是空字符串。"""
    res = {"raw": text}
    for name in _NAMES:
        # 从【name】一直取到下一个【xxx】之前，或字符串结尾
        m = re.search(r"【" + name + r"】\s*(.*?)(?=【[^】]+】|\Z)", text, re.S)
        res[name] = m.group(1).strip() if m else ""
    return res


# ------------------------- 地址归一 -------------------------

def norm_addr(s):
    """去掉空白和常见标点，只留中文数字字母，方便比对地址"""
    return re.sub(r"[\s　，。,.、；;：:（）()\-—_]", "", s or "")


class AddressIndex:
    """地址表索引：查某个地点文本是不是表里的地址，以及地址有没有被说出来"""

    def __init__(self, addresses):
        self.items = addresses
        self.norm_map = {norm_addr(a["full"]): a for a in addresses}
        # 小区名集合和路名集合，用来判断呼救者原话里有没有提到地点
        self.communities = {a["community"] for a in addresses}
        self.roads = {a["road"] for a in addresses}

    def match(self, location_text):
        """地点字段是否精确命中表里某条地址，命中返回该条，否则 None。
        （考地址真实性：模型自己编的地址一定对不上表）"""
        n = norm_addr(location_text)
        if not n:
            return None
        if n in self.norm_map:
            return self.norm_map[n]
        # 允许地点字段里多写了一点修饰（如"3栋502，4单元楼下"），
        # 只要表里某条地址完整地嵌在里面仍然算命中
        for full_n, item in self.norm_map.items():
            if full_n in n:
                return item
        return None

    def mentioned_in(self, utterance, addr_item):
        """呼救者原话里有没有真的把地点说出来（至少要提到小区名或路名）"""
        u = utterance or ""
        return (addr_item["community"] in u) or (addr_item["road"] in u)


# ------------------------- 三项校验 -------------------------

def check_format(parsed):
    """格式：三个必备字段都要有内容"""
    missing = [name for name in _NAMES if not parsed.get(name)]
    if missing:
        return False, "缺少字段：" + "、".join(f"【{m}】" for m in missing)
    return True, "字段齐全"


def check_fact(parsed, addr_index):
    """事实：地点必须命中地址表，且这条地址要出现在呼救者原话里"""
    loc = parsed.get("地点", "")
    hit = addr_index.match(loc)
    if not hit:
        return False, f"地点『{loc}』不在地址表里（地址瞎编了）"
    if not addr_index.mentioned_in(parsed.get("呼救者原话", ""), hit):
        return False, f"地址『{hit['full']}』没有出现在呼救者原话里"
    return True, f"地址命中：{hit['full']}"


JUDGE_TMPL = """下面是一段 120 呼救电话里"呼救者"说的话。请你当裁判，
从候选画像里挑出最像这个人说的一句话的画像。只依据说话的口吻、用词、
情绪、对地址的表述方式来判断，不要脑补剧情。

【呼救者原话】
{utt}

【候选画像】
{cands}

请严格按下面三行输出，不要多写别的：
【判定画像】<画像编号，如 P3>
【把握度】<0~100 的整数>
【理由】<一句话>
"""


def check_profile(parsed, profiles):
    """画像一致：把原话丢给模型盲猜画像。猜中 target 就算一致。
    注意这里不给模型看 target，是"识别"不是"打分自证"。"""
    utt = parsed.get("呼救者原话", "")
    if not utt:
        return None, 0, "没有原话可判"
    cands = "\n".join(f"{p['id']} {p['name']}：{p['style']}" for p in profiles)
    out = chat(JUDGE_TMPL.format(utt=utt, cands=cands), temperature=0)
    m = re.search(r"【判定画像】\s*(P\d+)", out)
    guess = m.group(1) if m else None
    ms = re.search(r"【把握度】\s*(\d+)", out)
    score = int(ms.group(1)) if ms else 0
    return guess, score, out


def verify(parsed, event, profile, kb, addr_index, profiles):
    """跑三项，返回 (ok, reasons, detail)。

    格式、事实两项是硬门槛。画像一致这项折腾了一下：一开始直接拿"裁判猜中没"
    当门槛，结果实测下来裁判自己就有噪声（同一段文字，它有时猜 P3 有时猜 P2），
    逼得样本 3 轮全用满还过不了，闭环直接被裁判噪声堵死。所以改成：
    裁判猜中 → 过；裁判没猜中但把握度低于 70 → 当"拿不准"，也算过；
    只有"猜成别的画像且 ≥70 把握度"才判失败打回。
    指标上仍然按严格猜中算（detail['profile_ok']），门槛另记一个 profile_gate。
    """
    reasons = []
    f_ok, f_msg = check_format(parsed)
    fact_ok, fact_msg = check_fact(parsed, addr_index)
    if not f_ok:
        reasons.append("格式不达标：" + f_msg)
    if not fact_ok:
        reasons.append("事实有误：" + fact_msg)

    guess, conf, raw = check_profile(parsed, profiles)
    prof_ok = (guess == profile["id"])
    prof_gate = prof_ok or conf < 70
    if not prof_gate:
        reasons.append(f"画像对不上：裁判判定为 {guess}（{conf}%），目标是 {profile['id']}")

    hard_ok = f_ok and fact_ok and prof_gate
    detail = {
        "format_ok": f_ok, "format_msg": f_msg,
        "fact_ok": fact_ok, "fact_msg": fact_msg,
        "profile_guess": guess, "profile_conf": conf,
        "profile_ok": prof_ok, "profile_gate": prof_gate,
    }
    return hard_ok, reasons, detail


def generate_with_retry(event, profile, kb, addr_index, profiles,
                        use_profile=True, use_kb=True, max_rounds=3):
    """受控生成 + 验证闭环：生成一版 → 校验 → 不过就把原因打回去重生成。
    最多 max_rounds 轮，轮数用满还不过就收下最后一版（结果里会记着没过）。"""
    rounds = []
    feedback = None
    for r in range(1, max_rounds + 1):
        text = generate_one(event, profile, kb,
                            use_profile=use_profile, use_kb=use_kb,
                            feedback=feedback)
        parsed = parse_output(text)
        ok, reasons, detail = verify(parsed, event, profile, kb,
                                     addr_index, profiles)
        rounds.append({"round": r, "text": text, "parsed": parsed,
                       "detail": detail, "reasons": reasons, "ok": ok})
        if ok:
            break
        feedback = "；".join(reasons)

    first = rounds[0]["detail"]
    final = rounds[-1]["detail"]
    return {
        "event_id": event["id"], "event_type": event["type"],
        "profile_id": profile["id"], "profile_name": profile["name"],
        "use_profile": use_profile, "use_kb": use_kb,
        "n_rounds": len(rounds),
        "passed": rounds[-1]["ok"],
        "final": final,
        "first": first,
        "rounds": rounds,
    }
