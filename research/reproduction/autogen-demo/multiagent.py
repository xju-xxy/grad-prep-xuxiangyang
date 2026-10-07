"""multiagent.py —— 多智能体应急会议主程序

会议流程：
    [信息官 → 分析师 → 顾问] 开两轮，最后顾问出终稿报告。
    信息官可以喊 Search[关键词]，主持程序会真实执行搜索并把结果塞回会议记录。
"""

import os
import re

from dotenv import load_dotenv
from zhipuai import ZhipuAI

from tools import search
from roles import ROLES

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

MODEL_NAME = "glm-5.3-flash"
TOTAL_ROUNDS = 2            # 每个角色发言几轮
MAX_SEARCH = 2              # 信息官单个回合最多连续搜几次
SEARCH_PATTERN = re.compile(r"Search\s*\[([^\]]+)\]")


def speak(role_name: str, task: str, meeting_log: str) -> str:
    """让某个角色就当前会议记录发言一次，返回它的发言内容"""
    system = ROLES[role_name]
    user_content = f"任务背景：{task}\n\n===== 会议记录 =====\n{meeting_log}\n===== 记录结束 =====\n\n现在轮到你发言。"
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def log_text(meeting_log: list) -> str:
    if not meeting_log:
        return "（会议刚开始，还没有任何人发言）"
    return "\n\n".join(f"【{tag}】{body}" for tag, body in meeting_log)


def run_meeting(question: str) -> str:
    meeting_log = []   # 每条是 (角色, 内容)

    print("=" * 70)
    print("任务：", question)
    print("=" * 70)

    for rnd in range(1, TOTAL_ROUNDS + 1):
        print(f"\n########## 第 {rnd} 轮会议 ##########\n")

        # --- 信息官发言（可能要先搜索） ---
        search_count = 0
        while True:
            text = speak("信息官", question, log_text(meeting_log))
            m = SEARCH_PATTERN.search(text)
            if m and search_count < MAX_SEARCH:
                query = m.group(1).strip()
                print(f"[信息官] {text}")
                print(f"  >>> 程序执行搜索：{query}")
                result = search(query)
                print(f"  >>> 搜索结果（预览）：{result[:120]}...")
                meeting_log.append(("系统备注", f"信息官搜索了「{query}」，结果如下：\n{result}"))
                search_count += 1
                continue
            if m:
                # 搜索次数用完了还在搜，让主持人提醒它
                print(f"[信息官] {text}")
                meeting_log.append(("系统备注", "搜索次数已用完，请基于现有资料直接发言。"))
                continue
            meeting_log.append(("信息官", text))
            print(f"[信息官] {text}")
            break

        # --- 分析师发言 ---
        text = speak("分析师", question, log_text(meeting_log))
        meeting_log.append(("分析师", text))
        print(f"\n[分析师] {text}")

        # --- 顾问发言 ---
        text = speak("顾问", question, log_text(meeting_log))
        meeting_log.append(("顾问", text))
        print(f"\n[顾问] {text}")

    # --- 会议结束，让顾问出终稿 ---
    final = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": ROLES["顾问"] + "\n\n会议已结束，现在请你综合全部会议记录，输出一份《最终决策建议报告》。报告要求：结构化，分「灾情摘要 / 态势研判 / 优先级行动清单 / 24小时分工 / 风险提示」五部分，语言精炼。"},
            {"role": "user", "content": f"任务背景：{question}\n\n===== 会议记录 =====\n{log_text(meeting_log)}\n===== 记录结束 =====\n\n请输出最终报告。"},
        ],
        temperature=0.3,
    )
    report = final.choices[0].message.content.strip()

    print("\n" + "=" * 70)
    print("【最终决策建议报告】")
    print("=" * 70)
    print(report)
    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "假设四川某山区县刚刚发生6.8级地震，县政府应急指挥部需要第一时间研判灾情并部署响应。请通过联网搜索获取参考信息，给出态势研判和行动建议。"
    run_meeting(q)