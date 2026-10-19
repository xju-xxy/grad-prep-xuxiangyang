"""
stl.py —— 时间窗判断（LogiDebrief 里 STL 的朴素替身）

论文里的做法是把规程离线翻译成信号时序逻辑（STL）公式，运行时只做求值，
不靠大模型现场推理。真正的 STL 需要装求解器（RTAMT、stlpy 之类），太重，
我这里用一个"规则 + 时间窗"的简化版本来顶替，语义上对应论文的：

    G( (适用类型 ∧ 触发条件) -> F_[0, T] 要求动作 )

翻成大白话："只要这通电话属于某类型、并且触发条件成立，那么在锚点之后
T 秒的窗口内，要求的动作必须出现过。"

- 锚点（anchor）三种：call_start（通话开始）、call_end（通话结束）、
  或某个动作 id（比如"判定没呼吸"发生的那一刻）。
- 动作是否出现、出现在第几轮，由 detector.py 里的大模型零件判断，
  这里只做时间窗的机械比较——这正是论文"结构正确由形式化保证、
  语义判断交给 LLM"的分工。
"""


def load_protocol(path="protocol.json"):
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _window_bounds(req, call_end_t, action_status):
    """算出某条需求的时间窗 [lo, hi]（秒）。返回 None 表示无法确定（应按 NA 处理）。"""
    anchor = req["window"]["anchor"]
    seconds = req["window"]["seconds"]

    if anchor == "call_start":
        return 0.0, float(seconds)
    if anchor == "call_end":
        return float(call_end_t - seconds), float(call_end_t)

    # 锚点是某个动作：取它第一次出现的时间
    a = action_status.get(anchor)
    if not a or a.get("status") != "present" or a.get("time") is None:
        return None
    lo = float(a["time"])
    return lo, lo + float(seconds)


def _ev(action_status, aid):
    """把动作状态整理成给质检单用的证据字典。"""
    st = action_status.get(aid)
    if not st or st.get("status") != "present":
        return None
    return {
        "action": aid,
        "turn": st.get("turn"),
        "time": st.get("time"),
        "quote": st.get("quote", ""),
    }


def eval_requirement(req, call_type, call_end_t, action_status):
    """
    对单条需求给出 Yes / No / Refused / NA。
    返回 (verdict, reason, evidence)
    """
    # 1) 适用范围：通话类型不在 applies_to 里 -> NA（论文的 SCENE/TYPE 筛掉不适用项）
    if call_type not in req["applies_to"]:
        return "NA", f"该需求仅适用于 {('/'.join(req['applies_to']))}，本通话类型为 {call_type}", None

    # 2) 触发条件：如"判定没呼吸"没出现，则 CPR 需求不适用 -> NA
    trig = req.get("requires_trigger")
    if trig:
        t = action_status.get(trig)
        if not t or t.get("status") != "present":
            return "NA", f"前置触发条件未满足（未判定出现「{trig}」）", None

    # 3) 时间窗
    bounds = _window_bounds(req, call_end_t, action_status)
    if bounds is None:
        return "NA", f"时间窗锚点动作「{req['window']['anchor']}」未出现，无法评估", None
    lo, hi = bounds

    # 4) 要求动作
    tgt = action_status.get(req["required_action"])
    if tgt is None:
        return "No", f"通话中未出现要求动作「{req['required_action']}」，违反「{req['title']}」", None

    if tgt.get("status") == "refused":
        return "Refused", f"接线员已提出要求，但呼救者拒绝或无法提供（{req['title']}）", _ev(action_status, req["required_action"])

    if tgt.get("status") == "present":
        t = tgt.get("time")
        if t is None:
            # 模型判了出现但没给轮次，退化处理：记下并当作落在窗口内
            return "Yes", f"要求动作「{req['required_action']}」出现（证据轮次缺失，按窗口内计）", _ev(action_status, req["required_action"])
        if lo <= float(t) <= hi:
            return "Yes", f"要求动作在时间窗 [{lo:.0f}, {hi:.0f}]s 内出现（实际 {float(t):.0f}s）", _ev(action_status, req["required_action"])
        else:
            return "No", f"要求动作出现于 {float(t):.0f}s，超出时间窗 [{lo:.0f}, {hi:.0f}]s，违反「{req['title']}」", _ev(action_status, req["required_action"])

    # status == absent
    return "No", f"通话中未出现要求动作「{req['required_action']}」，违反「{req['title']}」", None
