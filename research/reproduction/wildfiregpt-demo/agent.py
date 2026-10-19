"""
agent.py —— WildfireGPT 三阶段 Agent 复现

论文（arXiv:2402.07877）里整个系统是一个 LLM Agent 套 RAG，交互分三阶段：
  1. 用户画像 User Profile：先问诊，弄清用户背景/关注点/地点/时间线
  2. 规划 Planning：根据画像生成行动计划，跟用户确认
  3. 分析师 Analyst：按计划检索资料，生成带引用的分析建议

论文文献检索用 all-MiniLM-L6-v2 + Faiss，这里换成智谱 embedding（或退化成关键词检索），
详见 kb.py 和 README。

运行：
  .venv\\Scripts\\python.exe agent.py                # 交互模式
  .venv\\Scripts\\python.exe agent.py --auto         # 非交互，跑固定案例，方便留痕
  .venv\\Scripts\\python.exe agent.py --auto --log results/auto_log.md
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from zhipuai import ZhipuAI

import kb

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

MODEL_NAME = "glm-4-flash"

# 非交互模式用的固定案例（对应论文里"景观管理员控制烧"那个案例）
AUTO_SCENARIO = (
    "我是某林场负责营林的，林场里有一片以栎类/橡树为主的次生林，"
    "林下有多年堆积的枯落物。我们想安排一次春季计划烧（控制烧），"
    "既维护橡树的更新，又担心火控制不住影响山下的居民区，想知道怎么平衡。"
)
# 自动模式下，替用户回答问诊问题。
# 第一版是按提问顺序硬塞答案，结果模型提问顺序不固定，答非所问（问时间线却答了地点）。
# 改成按问题里的关键词路由：命中哪个关键词就回对应答案，都没命中就用兜底答案。
AUTO_ANSWERS = [
    (("经验", "背景", "了解", "专业", "几年", "从事"), "林场营林技术员，有林火管理基础，不是外行。"),
    (("担心", "顾虑", "风险"), "最担心计划烧失控，烟和飞火影响山下最近的居民区。"),
    (("区域", "地方", "哪里", "位置", "地点"), "华北某山区林场，林场南侧大约 2 公里有村庄。"),
    (("时间", "什么时候", "多久", "安排", "计划"), "想赶在春季返青前做，大概还有一个月的准备时间。"),
    (("了解", "方面", "关注", "想知"), "想了解计划烧窗口期怎么选、气象条件门槛、居民区一侧要怎么防护。"),
]
AUTO_FALLBACK = "想了解计划烧窗口期怎么选、气象条件门槛、居民区一侧要怎么防护。"


def auto_answer(question, used):
    """根据问题关键词挑一个预设答案，同一个答案不重复用。"""
    for keys, ans in AUTO_ANSWERS:
        if ans in used:
            continue
        if any(k in question for k in keys):
            used.add(ans)
            return ans
    return AUTO_FALLBACK


def chat(messages, temperature=0.3):
    """统一封装一次对话调用。"""
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def extract_json(text):
    """从模型输出里抠出 JSON 对象/数组，防止它包一层 ```json。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise ValueError(f"没找到 JSON：{text[:120]}")
    # 从第一个括号开始，逐步找能配对收尾的位置
    for opener, closer in (("{", "}"), ("[", "]")):
        if text[start] == opener:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == opener:
                    depth += 1
                elif text[i] == closer:
                    depth -= 1
                    if depth == 0:
                        return json.loads(text[start : i + 1])
    raise ValueError(f"JSON 不完整：{text[:120]}")


# ---------------------------------------------------------------------------
# 阶段一：用户画像
# ---------------------------------------------------------------------------
PROFILE_SYS = """你是 WildfireGPT，一名野火/林火风险分析助手。现在处于【用户画像】阶段。

你的任务是通过提问了解用户，一次只问一个问题，问完等用户回答再问下一个。
需要弄清这几件事（不必按顺序，问到就够）：
1. 用户的专业背景/身份（决定回答的专业程度）
2. 用户最担心什么风险
3. 关注哪个地方/区域
4. 时间线（这事急不急、什么时候要做决定）
5. 想了解的方面

规则：
- 一次只问一个问题，简短口语化，不要罗列多个问题。
- 最多问 5 个问题。信息够了就停止提问。
- 信息够了的时候，直接输出下面这个格式（不再提问）：
PROFILE_READY
{"role":"...","concern":"...","location":"...","timeline":"...","focus":"..."}
- 不要编造用户没说的信息，用户说不知道就记"未提供"。"""


def stage_profile(auto, log):
    log("", "## 阶段一：用户画像（问诊）\n")
    messages = [{"role": "system", "content": PROFILE_SYS}]
    if auto:
        messages.append({"role": "user", "content": f"我的情况：{AUTO_SCENARIO}"})
        log(f"**用户开场**：{AUTO_SCENARIO}\n")
    else:
        print("\n" + "=" * 70)
        print("阶段一：用户画像（直接说说你的情况，或按提示一个个答）")
        print("=" * 70)
        first = input("你：").strip()
        messages.append({"role": "user", "content": first})
        log(f"**用户开场**：{first}\n")

    used_answers = set()
    for turn in range(6):
        reply = chat(messages, temperature=0.4)
        messages.append({"role": "assistant", "content": reply})

        if "PROFILE_READY" in reply:
            body = reply.split("PROFILE_READY", 1)[1]
            profile = extract_json(body)
            log(f"\n**画像汇总**：\n\n```json\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n```\n")
            if not auto:
                print("\n[已收集到足够信息]")
            return profile

        # 模型在提问
        print(f"\nWildfireGPT：{reply}")
        log(f"\n**Agent 提问**：{reply}\n")
        if auto:
            ans = auto_answer(reply, used_answers)
            print(f"【自动回答】{ans}")
            log(f"**用户回答**：{ans}\n")
        else:
            ans = input("你：").strip()
            log(f"**用户回答**：{ans}\n")
        messages.append({"role": "user", "content": ans})

    # 问了 6 轮还没 ready，兜底让它总结
    messages.append({"role": "user", "content": "信息够了，请按 PROFILE_READY + JSON 的格式输出画像汇总。"})
    reply = chat(messages, temperature=0.2)
    profile = extract_json(reply.split("PROFILE_READY", 1)[-1])
    log(f"\n**画像汇总（兜底）**：\n\n```json\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n```\n")
    return profile


# ---------------------------------------------------------------------------
# 阶段二：规划
# ---------------------------------------------------------------------------
PLAN_SYS = """你是 WildfireGPT，现在处于【规划】阶段。
根据用户画像，给出一个简洁的行动计划，说明你打算怎么做这次分析。
必须包含：
- 打算参考哪几类知识（比如火险指标、气象地形、植被燃料、控制烧、社区防护、应急物资等）
- 分析打算分几步走
- 最后会给出什么样的建议

用中文，分点写，控制在 250 字内，不要写具体结论（结论留到分析阶段）。"""


def stage_plan(profile, auto, log):
    log("", "## 阶段二：规划\n")
    messages = [
        {"role": "system", "content": PLAN_SYS},
        {"role": "user", "content": f"用户画像：{json.dumps(profile, ensure_ascii=False)}"},
    ]
    plan = chat(messages, temperature=0.4)
    print("\n" + "=" * 70)
    print("阶段二：行动计划")
    print("=" * 70)
    print(plan)
    log(f"**行动计划**：\n\n{plan}\n")

    if auto:
        print("\n【自动确认】用户确认按此计划执行。")
        log("\n**用户确认**：确认执行。\n")
    else:
        ok = input("\n是否按这个计划执行？(直接回车=同意，输入修改意见则调整)：").strip()
        if ok:
            messages.append({"role": "assistant", "content": plan})
            messages.append({"role": "user", "content": f"用户有意见：{ok}，请据此修订计划。"})
            plan = chat(messages, temperature=0.4)
            print("\n" + plan)
            log(f"\n**修订后计划**：\n\n{plan}\n")
    return plan


# ---------------------------------------------------------------------------
# 阶段三：分析师（带引用的 RAG）
# ---------------------------------------------------------------------------
STEPS_SYS = """你是 WildfireGPT 的分析师模块。根据用户画像和已确认的行动计划，
把这次分析拆成 3 个分析步骤（子问题）。每个步骤要给一个用于检索知识库的查询词。

注意：步骤要针对具体问题（比如窗口期怎么选、居民区怎么防），不要写"收集资料""整理数据"这类空步骤。

只输出 JSON 数组，格式：
[{"step":"这一步要分析什么","query":"用于检索知识库的中文查询词"}, ...]
不要输出别的解释。"""

SECTION_SYS = """你是 WildfireGPT 的分析师模块。根据给定的【分析步骤】和【检索到的知识条目】，
写一段专业但看得懂的分析。

硬性要求：
- 只能使用检索到的知识条目里的信息，不许自己编数据、标准或结论。
- 每个关键判断后面用方括号标出引用来源的条目编号，比如 [FWI-06]、[BURN-02] 这种写法。
- 如果不同条目的说法之间有冲突，要明确指出来，不要硬把它们捏成一致。
- 如果检索到的资料不足以支撑这一步，就明说"现有知识库没有覆盖这一点"。
- 分点写，300 字以内。"""

SUMMARY_SYS = """你是 WildfireGPT，现在做最后的综合。基于前面各步骤的分析，
给用户一段可落地的建议，包含：可以怎么做 / 需要注意的条件 / 什么情况下不要做。
用中文，分点，400 字以内，依据仍然用方括号标条目编号（例如 [BURN-02]）。"""


def stage_analyst(profile, plan, auto, log):
    log("", "## 阶段三：分析师（检索 + 带引用分析）\n")
    base = [
        {"role": "system", "content": STEPS_SYS},
        {
            "role": "user",
            "content": f"用户画像：{json.dumps(profile, ensure_ascii=False)}\n行动计划：\n{plan}",
        },
    ]
    raw = chat(base, temperature=0.3)
    try:
        steps = extract_json(raw)
    except Exception:
        steps = [
            {"step": "计划烧窗口期与气象条件", "query": "计划烧 窗口期 气象条件 FWI"},
            {"step": "居民区一侧的风险与防护", "query": "居民区周边可燃物清理 防御空间"},
            {"step": "控制烧的操作与安全准备", "query": "计划烧 安全线 审批 装备"},
        ]

    print("\n" + "=" * 70)
    print("阶段三：分析师")
    print("=" * 70)
    log(f"**分析步骤**：\n\n```json\n{json.dumps(steps, ensure_ascii=False, indent=2)}\n```\n")

    section_texts = []
    for i, s in enumerate(steps, 1):
        query = s.get("query", s.get("step", ""))
        hits = kb.search(query, top_k=4)
        print(f"\n--- 第 {i} 步：{s.get('step')} ---")
        print(f"[程序检索] 查询「{query}」→ 命中 {len(hits)} 条（{kb.MODE} 检索）")
        for e, sc in hits:
            print(f"    [{sc}] {e['id']} {e['title']}")

        context = "\n\n".join(
            f"[{e['id']}]（{e['category']}）{e['title']}：{e['content']}" for e, _ in hits
        )
        msgs = [
            {"role": "system", "content": SECTION_SYS},
            {
                "role": "user",
                "content": f"分析步骤：{s.get('step')}\n\n检索到的知识条目：\n{context}",
            },
        ]
        section = chat(msgs, temperature=0.3)
        print("\n" + section + "\n")
        section_texts.append((s.get("step"), hits, section))
        log(
            f"### 第 {i} 步：{s.get('step')}\n\n"
            f"检索查询：`{query}`（{kb.MODE} 检索，命中 {len(hits)} 条）\n\n"
            f"命中条目：" + "、".join(f"[{e['id']}] {e['title']}" for e, _ in hits) + "\n\n"
            f"分析输出：\n\n{section}\n"
        )

    joined = "\n\n".join(f"【{t}】\n{c}" for t, _, c in section_texts)
    summary = chat(
        [
            {"role": "system", "content": SUMMARY_SYS},
            {"role": "user", "content": f"用户画像：{json.dumps(profile, ensure_ascii=False)}\n各步分析：\n{joined}"},
        ],
        temperature=0.3,
    )
    print("=" * 70)
    print("综合建议")
    print("=" * 70)
    print(summary)
    log(f"\n### 综合建议\n\n{summary}\n")
    return summary


def main():
    auto = "--auto" in sys.argv
    log_path = None
    if "--log" in sys.argv:
        log_path = Path(sys.argv[sys.argv.index("--log") + 1])

    lines = []
    if log_path:
        lines.append(f"# WildfireGPT 三阶段运行记录（{'自动' if auto else '交互'}模式）\n")
        lines.append(f"模型：{MODEL_NAME}\n")

    def log(head, body=""):
        text = (head + "\n" + body) if head else body
        if log_path:
            lines.append(text)

    profile = stage_profile(auto, log)
    print("\n画像：", json.dumps(profile, ensure_ascii=False))

    plan = stage_plan(profile, auto, log)
    summary = stage_analyst(profile, plan, auto, log)

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n[记录已写入] {log_path}")

    return summary


if __name__ == "__main__":
    main()
