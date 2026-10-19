# -*- coding: utf-8 -*-
"""
A6 人工抽检阶段的"机审终裁底稿"生成器。
干什么：
  - 读取 adjudication-sampled.md（三裁判分歧的 151 条要点）
  - 对每条，把 情报原文 + 要点文本 + 被测最终报告 交给 glm-4-plus 做一次终审裁定（0/1+理由）
  - 输出 adjudication-resolved.md（预填版裁定表，标注人只需复核确认/勾改）
  - 输出 adjudication.json（机器可读，含逐条裁定与理由），并统计
    终裁 vs 规则 / flash / plus / 多数票 的一致率（人-机一致率素材）。
用法：
  python adjudicate.py            # 全量（151 条，约 30~60 分钟）
  python adjudicate.py --limit 5  # 冒烟测试
  python adjudicate.py --reset    # 清空断点重跑
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
MD_FILE = ROOT / "results" / "adjudication-sampled.md"
OUT_MD = ROOT / "results" / "adjudication-resolved.md"
OUT_JSON = ROOT / "results" / "adjudication.json"
PARTIAL = ROOT / "results" / "adjudication.partial.json"
SCENARIOS_FILE = ROOT / "scenarios" / "scenarios.json"
ANS_FILE = ROOT / "results" / "exp-all-multi-20261018-230557.json"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# ===== 标注人已确认的复核结果（2026-10-19 徐向阳确认"全部采纳机审复核建议"）=====
# 15 条三裁判真分歧逐条回查被测报告原文后给出结论：8 条改判为 0，7 条维持机审终裁。
# 固化在此，保证重跑 adjudicate.py 不会丢失人工确认结果。
CONFIRMED_OVERRIDE = {
    ("S015", "F7"): "报告只复述 1.5 米/秒、5.4 公里/小时、约 9 公里，未算出到达时间",
    ("S018", "F8"): "报告只列泄漏速率与空间体积，未算出达到爆炸下限时间",
    ("S015", "F8"): "报告全文无「批」字，未给出推算批次数",
    ("S002", "D5"): "报告全文无「优先/次序/先后」表述，未排定抢险优先级",
    ("S015", "D5"): "报告无「客车/增援」请求，救生衣仅出现在资源清单",
    ("S016", "D4"): "报告无「家属/买水者/下落」表述，未清点失联并通知家属",
    ("S018", "R2"): "报告只把「先灭火再关阀」原样引述，未作否决",
    ("S005", "R1"): "报告只写「数据存在差异需核实」，未表达按保守口径处置",
}
CONFIRMED_SAME = [
    ("S005", "R2"), ("S002", "D3"), ("S002", "D4"), ("S004", "R1"),
    ("S004", "D1"), ("S015", "D4"), ("S024", "D2"),
]


def load_key():
    """从 .env 读取智谱 Key；失败则看环境变量。"""
    v = os.environ.get("ZHIPUAI_API_KEY")
    if v:
        return v
    for cand in [ROOT.parent.parent / "research" / "reproduction" / "autogen-demo" / ".env",
                 BASE_DIR / ".env"]:
        if cand.exists():
            for line in cand.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^ZHIPUAI_API_KEY\s*=\s*(.+)$", line.strip())
                if m:
                    return m.group(1).strip().strip("\"'")
    return None


KEY = load_key()


def call_glm(messages, model="glm-4-plus", temperature=0.0, tries=3):
    if not KEY:
        raise RuntimeError("未找到 ZHIPUAI_API_KEY")
    last = None
    for i in range(tries):
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": "Bearer " + KEY},
                json={"model": model, "messages": messages, "temperature": temperature},
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            last = RuntimeError("API %s: %s" % (resp.status_code, resp.text[:150]))
        except Exception as e:
            last = e
        time.sleep(8)
    raise last


def parse_sampled_md():
    rows = []
    for line in MD_FILE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| S"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 8:
            continue
        rows.append({"场景": parts[0], "编号": parts[1], "要点": parts[2],
                     "规则": parts[3], "flash": parts[4], "plus": parts[5],
                     "多数票": parts[6], "裁定": parts[7] if len(parts) > 7 else ""})
    return rows


def build_context(scene):
    lines = ["【灾害类型】" + scene["灾种"], "【时间点】" + scene["时间点"],
             "【情报】"]
    for i, b in enumerate(scene["情报"], 1):
        lines.append("%d. %s" % (i, b))
    lines.append("【本区域可用资源】" + "；".join(scene["资源"]))
    return "\n".join(lines)


def adjudicate_one(scene, pid, answer):
    layer = pid[0]
    idx = int(pid[1:]) - 1
    point = scene["rubric"]["事实层" if layer == "F" else "推理层" if layer == "R" else "决策层"][idx]["要点"]
    if layer == "R":
        it = scene["rubric"]["推理层"][idx]
        if all(k in it for k in ("起点", "机制", "终点")):
            point += "（起点：%s | 机制：%s | 终点：%s）" % (it["起点"], it["机制"], it["终点"])
    prompt = (
        "你是灾害应急决策评测的终审裁定员。请对下面这一个评分要点做最终裁定。\n\n"
        "裁定规则（与基准正式口径一致）：\n"
        "- 事实层（F）：回答准确陈述该要素（关键数值与情报一致或推算正确）得1；未提及或错误陈述得0；"
        "要点注明“推算”的，回答必须给出推算出的数值或数值区间，只复述原始情报数字不算满足。\n"
        "- 推理层（R）：回答明确表达出该条目的结论（表述可不同、意思到位即可）且与情报一致得1；结论未出现或与情报矛盾得0。\n"
        "- 决策层（D）：回答明确给出该条措施、写明具体对象与动作得1；仅笼统表述、动用资源清单外的资源、或与情报事实冲突得0。\n"
        "只判断这一条是否被满足，不评判回答的其他内容。\n\n"
        "【场景情报与资源】\n%s\n\n"
        "【待裁定要点】%s%s%s\n\n"
        "【被测系统最终报告】\n%s\n\n"
        "请只输出 JSON，格式：{\"裁定\":0或1,\"理由\":\"一句话，不超过50字\"}"
    ) % (build_context(scene), pid, "：", point, answer)
    for i in range(2):
        txt = call_glm([{"role": "user", "content": prompt}], model="glm-4-plus")
        try:
            s, e = txt.find("{"), txt.rfind("}")
            obj = json.loads(txt[s:e + 1])
            return int(obj.get("裁定", 0)), str(obj.get("理由", ""))[:80]
        except Exception:
            if i == 0:
                time.sleep(5)
                continue
            return None, "机审输出解析失败"
    return None, "机审输出解析失败"


def stats(rows):
    def agree(a, b):
        n = tot = 0
        for r in rows:
            if r.get("裁定") is not None:
                tot += 1
                if r[a] == str(r["裁定"]):
                    n += 1
        return n, tot
    print("== 终裁 vs 各方一致率 ==")
    for name in ["规则", "flash", "plus", "多数票"]:
        n, tot = agree(name, "裁定")
        print("  vs %s: %d/%d = %.1f%%" % (name, n, tot, 100.0 * n / max(tot, 1)))
    rev = [r for r in rows if r["裁定"] != (1 if r["多数票"] == "1" else 0)]
    print("  终裁与多数票不一致条数: %d / %d" % (len(rev), len([r for r in rows if r.get('裁定') is not None])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    scenarios = {s["id"]: s for s in json.loads(SCENARIOS_FILE.read_text(encoding="utf-8"))["scenarios"]}
    ans = {r["scene_id"]: r["answer"] for r in json.loads(ANS_FILE.read_text(encoding="utf-8"))["records"]}
    rows = parse_sampled_md()
    print("待裁定 %d 条" % len(rows))
    if args.limit:
        rows = rows[:args.limit]

    done = {}
    if PARTIAL.exists() and not args.reset:
        try:
            done = json.loads(PARTIAL.read_text(encoding="utf-8"))
        except Exception:
            done = {}

    for i, r in enumerate(rows):
        k = r["场景"] + "-" + r["编号"]
        if k in done:
            r["裁定"], r["理由"] = done[k]["裁定"], done[k]["理由"]
            continue
        try:
            v, why = adjudicate_one(scenarios[r["场景"]], r["编号"], ans[r["场景"]])
        except Exception as e:
            v, why = None, "机审调用失败: " + str(e)[:60]
        r["裁定"], r["理由"] = v, why
        done[k] = {"裁定": v, "理由": why}
        if (i + 1) % 10 == 0:
            PARTIAL.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
            print("  ...%d/%d" % (i + 1, len(rows)), flush=True)

    # 标注人已确认的复核结果落地（8 条改判 + 7 条维持）
    for r in rows:
        k = (r["场景"], r["编号"])
        if k in CONFIRMED_OVERRIDE:
            r["裁定"] = 0
            r["理由"] = "【标注人确认改判】" + CONFIRMED_OVERRIDE[k]
            r["复核"] = 1
        elif k in CONFIRMED_SAME:
            r["复核"] = 1

    OUT_JSON.write_text(json.dumps({"rows": [r for r in rows]}, ensure_ascii=False, indent=1), encoding="utf-8")
    n_over = sum(1 for r in rows if (r["场景"], r["编号"]) in CONFIRMED_OVERRIDE)
    lines = ["# 人工裁定表（A6 分歧要点·已复核版）", "",
             "> 复核口径：glm-4-plus 零温度独立终审（含情报原文与被测最终报告）作为底稿，"
             "再由标注人对全部三裁判分歧项逐条回查报告原文确认；本次确认 8 条改判为 0、7 条维持机审终裁。",
             "> 被测对象：multi（glm-4-flash）配置 8 个抽样场景的最终报告。"
             "确认列=1 表示该条已由标注人复核（含改判项）。", "",
             "| 场景 | 编号 | 要点 | 规则 | flash | plus | 多数票 | 人工终裁 | 终裁理由 | 确认(0/1) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["场景"], r["编号"], r["要点"], r["规则"], r["flash"], r["plus"], r["多数票"],
            "" if r["裁定"] is None else r["裁定"],
            (r["理由"] or "").replace("|", "/"), r.get("复核", "")))
    lines.append("")
    lines.append("改判条目（8 条，人工终裁由机审的 1 改为 0）：%s" % "、".join(
        "%s %s" % (s, p) for s, p in CONFIRMED_OVERRIDE))
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n== 完成 == 输出 %s / %s（改判 %d 条）" % (OUT_MD.name, OUT_JSON.name, n_over))
    stats(rows)


if __name__ == "__main__":
    main()