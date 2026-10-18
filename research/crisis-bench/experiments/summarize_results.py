# -*- coding: utf-8 -*-
"""
CrisisBench 结果汇总脚本
干什么：扫描 results/ 目录下所有实验结果 JSON，输出一张"文件×场景×层"的得分率对照表
（Markdown 格式）。论文里的消融矩阵和主结果表都从这张表整理。
用法：
  python summarize_results.py                # 全部结果文件
  python summarize_results.py --latest       # 只看每个 (config×judge) 最新一次
"""
import argparse
import glob
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
LAYERS = ["事实层", "推理层", "决策层"]


def pick_scores(rec, key):
    """从一个记录里取某一裁判（rule/llm）的三层得分字典。"""
    block = rec.get(key, {}) or {}
    out = {}
    for layer in LAYERS:
        if layer in block:
            out[layer] = block[layer]
    return out


def file_table(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta", {})
    rows = []
    for rec in data.get("records", []):
        row = {
            "scene": rec.get("scene_id", "?"),
            "config": rec.get("config") or meta.get("config", "?"),
            "judge": meta.get("judge") or rec.get("judge_mode"),
            "judge_model": meta.get("judge_model") or rec.get("rescore_judge") or meta.get("model"),
            "rule": pick_scores(rec, "rule"),
            "llm": pick_scores(rec, "llm"),
        }
        rows.append(row)
    return meta, rows


def rate_cell(block):
    if not block:
        return "—"
    parts = [("%d/%d" % (block[k]["得分"], block[k]["总数"])) for k in LAYERS if k in block]
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest", action="store_true", help="每种 (config×judge×judge_model) 只取最新文件")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json")),
                   key=os.path.getmtime, reverse=True)

    printed = set()
    for f in files:
        try:
            meta, rows = file_table(f)
        except Exception as e:
            print("- 无法解析 %s：%s" % (os.path.basename(f), str(e)[:60]))
            continue
        # 分类这文件是什么版本/什么裁判
        note = meta.get("note", "")
        if "只重打分" in note:
            series = "rescore"
        else:
            series = "main"
        stamp = meta.get("时间", "")
        key = (series, rows[0]["config"] if rows else "?", meta.get("judge"), meta.get("judge_model"))
        if args.latest and key in printed:
            continue
        printed.add(key)

        print("\n### %s（%s）" % (os.path.basename(f), ", ".join(str(x) for x in key)))
        print("| 场景 | 配置 | 规则 事实/推理/决策 | LLM 事实/推理/决策 |")
        print("|---|---|---|---|")
        for r in rows:
            print("| %s | %s | %s | %s |" % (
                r["scene"], r["config"], rate_cell(r["rule"]), rate_cell(r["llm"])))


if __name__ == "__main__":
    main()