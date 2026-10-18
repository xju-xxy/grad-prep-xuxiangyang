# -*- coding: utf-8 -*-
"""CrisisBench 场景质检脚本（v0.4 扩容用）。

用法：
  python validate_scenarios.py <base.json> <batch1.json> [batch2.json ...] [--merge-out <path>] [--print-md-table]
- 逐个场景做结构与设计规范检查，输出问题清单。
- --merge-out path：把 base 的 meta 升级为 v0.4 并合并全部场景写入 path。
- --print-md-table：打印"逐场景要点数"markdown 表格（供 rubric 更新）。

检查项：id 唯一；情报 8-11 条；资源 4-6 项且含"无"否定项；
事实 8-9 / 推理 4-5 / 决策 6-7、合计 18-21；
推理要点含 起点/机制/终点；事实+推理至少 1 条含"推算"；
match 词表 3-10 个；类别为 单灾种/链式/信息矛盾 之一。
"""
import json
import sys
from collections import Counter


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_scenario(s, problems, stats):
    sid = s.get("id", "?")
    err = lambda m: problems.append(f"[{sid}] {m}")
    legacy = sid.startswith("S") and int(sid[1:]) <= 5  # v0.3 旧 5 场景：历史数字已入论文，不再回改
    if s.get("类别") not in ("单灾种", "链式", "信息矛盾"):
        err("类别非法: %r" % s.get("类别"))

    qb = s.get("情报") or []
    if not (8 <= len(qb) <= 11):
        err("情报条数 %d（应 8-11）" % len(qb))

    res = s.get("资源") or []
    if not (4 <= len(res) <= 6):
        err("资源项数 %d（应 4-6）" % len(res))
    if not legacy and not any("无" in r for r in res):
        err("资源缺少否定项（无X）")

    rb = s.get("rubric") or {}
    nF, nR, nD = len(rb.get("事实层") or []), len(rb.get("推理层") or []), len(rb.get("决策层") or [])
    stats[sid] = (s.get("类别"), s.get("灾种"), nF, nR, nD, nF + nR + nD)
    if not (8 <= nF <= 9):
        err("事实层 %d 条（应 8-9）" % nF)
    if not (4 <= nR <= 5):
        err("推理层 %d 条（应 4-5）" % nR)
    if not (6 <= nD <= 7):
        err("决策层 %d 条（应 6-7）" % nD)
    total = nF + nR + nD
    if not (18 <= total <= 21):
        err("要点合计 %d（应 18-21）" % total)

    calc = 0
    for layer, items in (("事实层", rb.get("事实层") or []), ("推理层", rb.get("推理层") or []), ("决策层", rb.get("决策层") or [])):
        for i, p in enumerate(items, 1):
            if p.get("要点", "").startswith("推算"):
                calc += 1
            m = p.get("match") or []
            if not (3 <= len(m) <= 12):
                err("%s#%d match 词表 %d 个（应 3-12）" % (layer, i, len(m)))
            if layer == "推理层":
                for field in ("起点", "机制", "终点"):
                    if not p.get(field):
                        err("推理层#%d 缺字段 %s" % (i, field))
    if not legacy and calc < 1:
        err("缺少数值推算型要点（<1 条）")
    elif not legacy and calc > 2:
        err("数值推算型要点 %d 条（应 1-2）" % calc)
    stats_calc[sid] = calc

    if s.get("类别") == "信息矛盾":
        text_all = "".join(p.get("要点", "") for layer in rb.values() for p in layer)
        if "保守" not in text_all or "核" not in text_all:
            err("信息矛盾类缺少‘保守口径+核灾’要点表述")


def main():
    args = sys.argv[1:]
    merge_out = None
    print_md = False
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--merge-out":
            merge_out = args[i + 1]
            i += 2
            continue
        if a == "--print-md-table":
            print_md = True
            i += 1
            continue
        if not a.startswith("--"):
            files.append(a)
        i += 1

    base_meta = None
    all_scenarios = []
    for path in files:
        data = load(path)
        if base_meta is None:
            base_meta = data.get("meta")
        all_scenarios.extend(data.get("scenarios") or [])

    ids = [s.get("id") for s in all_scenarios]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    problems = []
    if dup:
        problems.append("id 重复: %s" % dup)
    if len(set(ids)) != len(ids):
        problems.append("id 集合不唯一")

    global stats_calc
    stats = {}
    stats_calc = {}
    for s in all_scenarios:
        check_scenario(s, problems, stats)

    print("== 场景总数: %d ==" % len(all_scenarios))
    print("== 要点数统计（含推算条数）==")
    for sid in sorted(stats):
        cat, zz, nF, nR, nD, total = stats[sid]
        print(f"{sid} {cat}/{zz}: F{nF} R{nR} D{nD} 合计{total} 推算{stats_calc[sid]}")

    cat_count = Counter(v[0] for v in stats.values())
    print("== 类别分布 ==", dict(cat_count))

    if problems:
        print("== 发现 %d 个问题 ==" % len(problems))
        for p in problems:
            print(" -", p)
        sys.exit(1)
    else:
        print("== 全部通过 ==")

    if print_md:
        print("\n## 逐场景要点数（v0.4）\n")
        print("| 场景 | 类别 | 事实层 | 推理层 | 决策层 | 合计 |")
        print("|---|---|---|---|---|---|")
        for sid in sorted(stats):
            cat, zz, nF, nR, nD, total = stats[sid]
            print(f"| {sid} | {cat}/{zz} | {nF} | {nR} | {nD} | {total} |")

    if merge_out:
        base_meta["benchmark"] = "CrisisBench v0.4（36 场景扩容版）"
        base_meta["难度设计"] = (base_meta.get("难度设计", "") +
            " v0.4 扩容：场景 5→36（单灾种 14 / 链式 14 / 信息矛盾 8），每场景保留 1-2 条数值推算型要点与至少 1 个陷阱。")
        out = {"meta": base_meta, "scenarios": all_scenarios}
        with open(merge_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"== 已合并写出: {merge_out}（{len(all_scenarios)} 场景）==")


if __name__ == "__main__":
    main()