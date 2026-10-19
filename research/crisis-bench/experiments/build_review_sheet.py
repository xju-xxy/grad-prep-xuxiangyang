# -*- coding: utf-8 -*-
"""A6 裁定复核表生成：把 71 条机审终裁底稿转成标注人可直接勾选的 Excel。

输入：results/adjudication.json（机审终裁底稿）
      results/exp-all-multi-20261018-230557.json（被测报告原文，multi@glm-4-flash）
输出：results/A6-复核表.xlsx
      results/A6-复核-高风险清单.md

复核口径：确认列留白 = 采纳机审终裁；如需改判，在该行「你的裁定」列填 0 或 1，并在「备注」写明依据。
"""
import json
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "..", "results")
ADJ = os.path.join(RES, "adjudication.json")
MAIN = os.path.join(RES, "exp-all-multi-20261018-230557.json")
OUT_XLSX = os.path.join(RES, "A6-复核表.xlsx")
OUT_MD = os.path.join(RES, "A6-复核-高风险清单.md")

STOP = ("结论：", "结论:", "必须", "须", "并", "、", "，", "。", "（", "）", "(", ")", "的", "与", "或")

# 机审二次复核建议：仅覆盖"多数票≠机审终裁"这 15 条真分歧（逐条回查被测报告原文后给出），
# 供标注人快速确认；未列出的条目默认认可机审终裁。值为建议裁定，"依据"说明回查结果。
SUG = {
    ("S002", "D5"): (0, "报告全文无「优先/次序/先后」类表述，未给出抢险优先级排定；机审=1 依据不足。"),
    ("S015", "F8"): (0, "报告仅列 450 人与 4 辆×50 人两条原始情报，全文无「批」字，未给出推算批次数。"),
    ("S015", "F7"): (0, "报告只复述 1.5 米/秒、5.4 公里/小时、约 9 公里，未算出到达时间（无「100 分钟/1 小时 40 分」）。"),
    ("S015", "D5"): (0, "报告未出现「客车/增援/上级」请求；救生衣只出现在资源清单，非「配发」措施。"),
    ("S016", "D4"): (0, "报告无「家属/买水者/下落」表述，未见清点失联并通知家属的措施。"),
    ("S018", "F8"): (0, "报告只复述泄漏速率与空间体积，未算出达到爆炸下限时间（无「6 分钟/3 立方米」）。"),
    ("S018", "R2"): (0, "报告把「先灭火再关阀」原样引述为居民提议，未作否决（无「先关总阀/否决」表述）。"),
    ("S005", "R1"): (0, "报告只写「两部门倒塌房屋数存在差异，需进一步核实」，未表达「按保守（更严重）口径处置」。"),
    ("S005", "R2"): (1, "报告明确「全镇可用仅 2 艘、每艘 10 人、单程 20 分钟」并请求邻近区域支援冲锋舟，运力不足须增援的结论成立。"),
    ("S002", "D3"): (0, "报告仅列抽水泵在受淹仓库，未给出绕行取用或替代排涝方案。"),
    ("S002", "D4"): (0, "报告无「澄清传言/管控民间救援」，只有监测泄洪与发布预警，未回应传言本身。"),
    ("S004", "R1"): (0, "要点要求「推算到达时间 + 立即疏散」结论，报告仅复述风速风向与通知关窗，无疏散结论。"),
    ("S004", "D1"): (0, "报告无疏散/撤离措施，只有广播短信通知关窗。"),
    ("S015", "D4"): (0, "无「首批立即发车/连续接驳」表述。"),
    ("S024", "D2"): (0, "报告未提停水与备用水源。"),
}


def bigrams(text):
    t = text
    for s in STOP:
        t = t.replace(s, "")
    t = re.sub(r"\s+", "", t)
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else set()


def sentences(answer):
    parts = re.split(r"[。\n]", answer or "")
    return [p.strip() for p in parts if len(p.strip()) >= 8]


def top_evidence(point, answer, k=2):
    pb = bigrams(point)
    if not pb:
        return "", 0.0
    scored = []
    for s in sentences(answer):
        sb = bigrams(s)
        if not sb:
            continue
        scored.append((len(pb & sb) / len(pb), s))
    scored.sort(reverse=True)
    best = scored[:k]
    score = best[0][0] if best else 0.0
    return " ／ ".join(s for _, s in best), round(score, 2)


def main():
    with open(ADJ, encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    with open(MAIN, encoding="utf-8") as f:
        recs = {r["scene_id"]: r for r in json.load(f)["records"]}
    answers = {sid: recs[sid].get("answer") or "" for sid in recs}

    wb = Workbook()
    ws = wb.active
    ws.title = "A6复核表"
    head = ["场景", "编号", "要点", "规则", "flash", "plus", "多数票", "机审终裁",
            "终裁理由", "报告相关片段（自动检索，仅供定位）", "证据相似度", "风险标记",
            "机审复核建议（仅 15 条分歧项，待你确认）", "建议依据",
            "你的复核（留白=采纳建议；改判填0/1）", "备注（改判依据）"]
    ws.append(head)

    hfill = PatternFill("solid", fgColor="DDEBF7")
    red = PatternFill("solid", fgColor="FCE4E4")
    yellow = PatternFill("solid", fgColor="FFF2CC")
    green = PatternFill("solid", fgColor="E2EFDA")
    for c in range(1, len(head) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True)
        cell.fill = hfill
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    # 先算全部相似度，用中位数作"证据弱"提示线（该指标只反映字面重合，不宜当结论用）
    scores = [top_evidence(r["要点"], answers.get(r["场景"], ""))[1] for r in rows]
    scores.sort()
    line = scores[len(scores) // 2] if scores else 0.0

    risky = []
    for r in rows:
        point = r["要点"]
        ev, score = top_evidence(point, answers.get(r["场景"], ""))
        maj_mismatch = str(r["多数票"]) != str(r["裁定"])
        weak = score < line
        flags = []
        if maj_mismatch:
            flags.append("多数票≠终裁")
        if weak:
            flags.append("证据弱")
        flag = "；".join(flags) if flags else "—"
        sug = SUG.get((r["场景"], r["编号"]))
        ws.append([r["场景"], r["编号"], point, r["规则"], r["flash"], r["plus"],
                   r["多数票"], r["裁定"], r["理由"], ev, score, flag,
                   sug[0] if sug else "—", sug[1] if sug else "—", None, None])
        i = ws.max_row
        fill = None
        if maj_mismatch and weak:
            fill = red
        elif weak:
            fill = yellow
        elif maj_mismatch:
            fill = green
        if fill:
            for c in range(1, len(head) + 1):
                ws.cell(row=i, column=c).fill = fill
        if maj_mismatch or weak:
            risky.append({**r, "片段": ev, "相似度": score, "标记": flag})

    widths = [7, 7, 46, 6, 6, 6, 8, 9, 40, 60, 9, 18, 15, 46, 16, 20]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for i in range(2, ws.max_row + 1):
        for c in range(1, len(head) + 1):
            ws.cell(row=i, column=c).alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(head)), ws.max_row)

    note = ws.max_row + 2
    ws.cell(row=note, column=1, value="复核说明：唯一硬信号是「多数票≠终裁」（绿/红底行）——这是协议口径与终裁口径的真实分歧，"
                                      "直接决定论文里 78.9% 的人-机一致率与 15 条误差分解是否成立。黄底行仅表示「证据相似度低于中位数"
                                      "(" + ("%.2f" % line) + ")」——该列是关键词自动检索的字面重合度，只帮你快速定位报告原文，不代表终裁有错。")
    ws.cell(row=note, column=1).font = Font(italic=True)

    wb.save(OUT_XLSX)

    lines = ["# A6 复核：需要重点确认的条目", "",
             "统计：共 %d 条；**多数票≠终裁 %d 条**（协议口径与终裁口径的真实分歧，决定论文 78.9%% 一致率与 15 条误差分解）；"
             "证据相似度低于中位数 %.2f 的 %d 条。" % (
                 len(rows),
                 sum(1 for r in rows if str(r["多数票"]) != str(r["裁定"])),
                 line,
                 sum(1 for r in risky if r["相似度"] < line)),
             "",
             "> 复核表：`results/A6-复核表.xlsx`。留白 = 认可机审终裁；改判请在表内填 0/1 并写依据。", "",
             "先看「多数票≠终裁」的条目：机审终裁把多数票的判定推翻了，若你不同意，论文里的 A6 一致率数字要跟着改。",
             "其余条目按关注度抽看即可，「证据相似度」只是关键词字面重合度，不代表终裁有错。", ""]
    risky = [r for r in risky if str(r["多数票"]) != str(r["裁定"])]
    order = {"多数票≠终裁；证据弱": 0, "多数票≠终裁": 1}
    risky.sort(key=lambda r: order.get(r["标记"], 9))

    def rate(field, data=None, adjkey="裁定"):
        data = rows if data is None else data
        same = sum(1 for r in data if str(r[field]) == str(r[adjkey]))
        return "%d/%d = %.1f%%" % (same, len(data), 100.0 * same / len(data))

    proj = []
    for r in rows:
        sug = SUG.get((r["场景"], r["编号"]))
        proj.append({**r, "adj": sug[0] if sug else r["裁定"]})
    n_chg = sum(1 for r in rows
                if SUG.get((r["场景"], r["编号"])) and str(SUG[(r["场景"], r["编号"])][0]) != str(r["裁定"]))
    lines += ["## 若按机审建议全部采纳（%d 条改判）后的 A6 口径变化" % n_chg, "",
              "| 口径 | 现状（机审终裁） | 采纳建议后 |", "|---|---|---|",
              "| 终裁 =1 条数 | %d | %d |" % (
                  sum(1 for r in rows if str(r["裁定"]) == "1"),
                  sum(1 for r in proj if str(r["adj"]) == "1"))]
    for field in ("flash", "plus", "规则", "多数票"):
        lines.append("| 与 %s 一致 | %s | %s |" % (field, rate(field), rate(field, proj, "adj")))
    lines += ["",
              "**注意**：采纳建议后「与多数票一致」会升到约 90%，而「与 flash 一致」会降到 80% 左右——"
              "即修正后三裁判多数票比单一 flash 裁判更接近人工裁定。这会改变论文 §6.5 的结论方向"
              "（原稿写的是 flash 更接近人，那是在机审终裁整体偏严的条件下得出的）。确认后我同步改稿。", ""]

    for r in risky:
        lines.append("## %s %s（%s）" % (r["场景"], r["编号"], r["标记"]))
        lines.append("")
        lines.append("- 要点：%s" % r["要点"])
        lines.append("- 三裁判：规则=%s / flash=%s / plus=%s → 多数票=%s；**机审终裁=%s**" % (
            r["规则"], r["flash"], r["plus"], r["多数票"], r["裁定"]))
        lines.append("- 终裁理由：%s" % r["理由"])
        sug = SUG.get((r["场景"], r["编号"]))
        if sug:
            lines.append("- **机审复核建议：%s** ｜ 依据：%s" % (sug[0], sug[1]))
        lines.append("- 报告片段（相似度 %.2f）：%s" % (r["相似度"], r["片段"]))
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("XLSX ->", OUT_XLSX)
    print("MD   ->", OUT_MD)
    print("rows=%d risky=%d" % (len(rows), len(risky)))


if __name__ == "__main__":
    main()
