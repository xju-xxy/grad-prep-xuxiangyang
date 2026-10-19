"""
detector.py —— LLM 判零件

对应论文里的三类语义函数：
  - SCENE / TYPE / CRITICAL：判定响应部门、事件类型、致命情形 -> classify_call()
  - DETECT / SCAN：判定某个动作是否在（时间窗内）出现 -> detect_actions()

大模型在这里只当"判断零件"，不做规程推理、不做结论聚合——那是 stl.py 和 debrief.py 的活。
所有输出都要求是 JSON，解析时做兜底，避免模型啰嗦导致整通崩掉。
"""

import json
import re
import time

MODEL_NAME = "glm-4-flash"


def _extract_json(text):
    """从模型回复里抠出第一个 JSON 对象，容忍 ```json 围栏和前后废话。"""
    if text is None:
        return None
    s = text.strip()
    if "```" in s:
        # 去掉代码围栏
        s = re.sub(r"```[a-zA-Z]*", "", s).replace("```", "")
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None
    try:
        return json.loads(s[i:j + 1])
    except json.JSONDecodeError:
        return None


def _chat_json(client, system, user, retries=3, temperature=0.0):
    """带重试的 JSON 调用。重试仍失败返回 {}。"""
    last_err = None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            text = resp.choices[0].message.content
            obj = _extract_json(text)
            if obj is not None:
                return obj, text
            last_err = f"JSON解析失败: {str(text)[:200]}"
        except Exception as e:  # 网络/超时都走这里，单条失败不中断整体
            last_err = f"API异常: {e}"
            time.sleep(1.5)
    print(f"    [warn] 调用失败（已重试{retries}次）：{last_err}")
    return {}, ""


def _render_transcript(turns):
    lines = []
    for idx, turn in enumerate(turns, start=1):
        who = "接线员" if turn["role"] == "operator" else "呼救者"
        lines.append(f"[{idx}] {turn['t']}s {who}：{turn['text']}")
    return "\n".join(lines)


CLASSIFY_SYSTEM = """你是急救接警复盘系统里的语义判断零件，只负责给这通电话打标签，不做别的。
严格只输出一个 JSON 对象，不要写任何解释文字。"""

CLASSIFY_USER = """请阅读下面这通 120 接警通话记录，判断它的属性。

【通话记录】
{transcript}

【判断要求】
返回 JSON，字段如下：
- "call_type"：只能是 {call_types} 之一
- "event_type"：用四到六个字概括事件（例如"心搏骤停""车祸外伤""临产""燃气泄漏"）
- "fatal_category"：这通电话涉及哪类致命情形，只能是 {fatal_tags} 之一，都不涉及则填 null
- "response_unit"：需要哪些响应力量，从 ["救护","救护+消防"] 二选一

只输出 JSON，例如：
{{"call_type": "CARDIAC", "event_type": "心搏骤停", "fatal_category": "CPR", "response_unit": "救护"}}"""


def classify_call(client, call, protocol):
    turns = call["turns"]
    user = CLASSIFY_USER.format(
        transcript=_render_transcript(turns),
        call_types="、".join(protocol["call_types"].keys()),
        fatal_tags="、".join(protocol["fatal_tags"].keys()),
    )
    obj, raw = _chat_json(client, CLASSIFY_SYSTEM, user)
    return {
        "call_type": obj.get("call_type"),
        "event_type": obj.get("event_type"),
        "fatal_category": obj.get("fatal_category"),
        "response_unit": obj.get("response_unit"),
        "_raw": raw,
    }


DETECT_SYSTEM = """你是急救接警复盘系统里的语义判断零件，只负责判断"某个规定动作在通话里有没有出现"，不做规程推理。
判断必须严格依据通话记录原话，不能脑补。严格只输出一个 JSON 对象，不要写任何解释文字。"""

DETECT_USER = """请判断下面列出的每个"规定动作"是否在这通 120 接警通话中出现。

【通话记录】（每轮前的方括号数字是轮次编号，后面是相对秒数）
{transcript}

【规定动作清单】（动作 id：含义）
{action_list}

【判断规则】
对每个动作给出三选一的状态：
- "present"：接线员确实做了这件事（例如他明确问了、明确指导了）
- "absent"：整通电话里没有出现这个动作
- "refused"：接线员提出了要求/询问，但呼救者明确拒绝回答或表示无法提供（只对"询问类"动作适用）

另外给出证据：
- "turn"：若是 present，填最能证明的轮次编号（上面方括号里的整数）；否则填 null
- "quote"：证明的原话片段，不超过 20 个字；否则填空字符串 ""

只输出一个 JSON 对象，key 是动作 id，value 是 {{"status":..., "turn":..., "quote":...}}。例如：
{{"ask_address": {{"status": "present", "turn": 2, "quote": "把地址告诉我"}}, "cpr_instruction": {{"status": "absent", "turn": null, "quote": ""}}}}"""


def detect_actions(client, call, protocol):
    actions = protocol["actions"]
    action_list = "\n".join(f"{aid}：{meta['name_zh']}（{meta['desc']}）" for aid, meta in actions.items())
    user = DETECT_USER.format(
        transcript=_render_transcript(call["turns"]),
        action_list=action_list,
    )
    obj, raw = _chat_json(client, DETECT_SYSTEM, user)

    # 规范化：没给的动作一律按 absent，字段缺失补默认
    out = {}
    for aid in actions:
        info = obj.get(aid) if isinstance(obj, dict) else None
        if not isinstance(info, dict):
            out[aid] = {"status": "absent", "turn": None, "quote": ""}
            continue
        status = str(info.get("status", "absent")).strip().lower()
        if status not in ("present", "absent", "refused"):
            status = "absent"
        turn = info.get("turn")
        if not isinstance(turn, int):
            turn = None
        out[aid] = {"status": status, "turn": turn, "quote": str(info.get("quote", ""))[:40]}
    out["_raw"] = raw
    return out
