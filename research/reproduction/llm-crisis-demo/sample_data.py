"""sample_data.py —— 从 HumAID set1 里抽评测样本

论文在 19 个事件、7.7 万条推文上跑 6 个模型。我 API 额度有限，
按 README 里写明的裁剪方案：取 4 个代表性事件（飓风/地震/野火/洪水各一个，
洪水是论文里公认最难的类型，专门拿来对照），每个事件每个类别抽 14 条
（test 集不够就从同事件 dev/train 补，样本里标了来源），总共几百条。
固定随机种子 42，谁重跑都得到一样的样本。

few-shot 示例：论文是从训练集里挑示例，这里也一样——从"不参与评测"的
其他事件训练集里每类挑 3 条，保证示例和评测样本完全不重叠。

输入：data/events_set1/ 下的原始 tsv（去 crisisnlp.qcri.org 官网下载 set1）
输出：data/sample.json（评测样本）、data/fewshot_examples.json（少样本示例）
"""

import csv
import glob
import json
import random
from collections import defaultdict
from pathlib import Path

# 参与评测的 4 个事件，后面的英文是论文里的灾害类型划分
EVENTS = {
    "hurricane_harvey_2017": "hurricane",
    "puebla_mexico_earthquake_2017": "earthquake",
    "canada_wildfires_2016": "wildfire",
    "srilanka_floods_2017": "flood",
}

# 只用来挑 few-shot 示例的事件（不会进评测集，避免示例泄露答案）
EXAMPLE_EVENTS = [
    "cyclone_idai_2019",
    "italy_earthquake_aug_2016",
    "ecuador_earthquake_2016",
    "kaikoura_earthquake_2016",
]

PER_CLASS = 14   # 每个事件每类最多抽 14 条
SHOTS = 3        # few-shot 每类 3 条示例
SEED = 42

# 论文里用的 9 个类别（它把 other_relevant_information 丢掉了，我也照做）
CLASSES = [
    "caution_and_advice",
    "sympathy_and_support",
    "requests_or_urgent_needs",
    "displaced_people_and_evacuations",
    "injured_or_dead_people",
    "missing_or_found_people",
    "infrastructure_and_utility_damage",
    "rescue_volunteering_or_donation_effort",
    "not_humanitarian",
]


def read_tsv(path):
    """读 tsv，返回 (tweet_id, tweet_text, class_label) 列表，跳过表头"""
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if len(r) >= 3 and r[2] and r[2] != "class_label":
                rows.append((r[0], r[1], r[2]))
    return rows


def main():
    random.seed(SEED)
    data_dir = Path("data/events_set1")

    # ---- 第一步：抽评测样本 ----
    # 某些类别在每个事件的 test 集里少得可怜（比如 missing_or_found_people），
    # 只抽 test 会整类缺席。所以：优先从 test 抽，不足 14 条就从同一事件的
    # dev/train 补，并在样本里标出来源（split 字段），保持透明。
    items = []
    for event, etype in EVENTS.items():
        test_rows = read_tsv(data_dir / event / f"{event}_test.tsv")
        test_rows = [r for r in test_rows if r[2] in CLASSES]
        backup = []
        seen_ids = {r[0] for r in test_rows}
        for split in ("dev", "train"):
            for r in read_tsv(data_dir / event / f"{event}_{split}.tsv"):
                if r[2] in CLASSES and r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    backup.append(r)
        by_class_test = defaultdict(list)
        for r in test_rows:
            by_class_test[r[2]].append(r)
        by_class_backup = defaultdict(list)
        for r in backup:
            by_class_backup[r[2]].append(r)
        for cls in CLASSES:
            pick = random.sample(by_class_test[cls], min(PER_CLASS, len(by_class_test[cls])))
            need = PER_CLASS - len(pick)
            if need > 0:
                extra = random.sample(by_class_backup[cls], min(need, len(by_class_backup[cls])))
                pick += extra
            for tid, text, label in pick:
                is_test = any(tid == t[0] for t in by_class_test[cls])
                items.append({"id": tid, "event": event, "text": text,
                              "label": label,
                              "split": "test" if is_test else "dev_train"})

    sample = {
        "seed": SEED,
        "source": "HumAID events_set1（crisisnlp.qcri.org 官网下载）",
        "note": "优先取各事件 test 集；某类不足 14 条时从同事件 dev/train 补足，"
                "样本里 split 字段标了实际来源。论文在全量测试集上跑，这是裁剪后的子集",
        "items": items,
    }
    with open("data/sample.json", "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=1)

    # ---- 第二步：挑 few-shot 示例（来自别的训练合格集） ----
    examples = defaultdict(list)
    for cls in CLASSES:
        pool = []
        for event in EXAMPLE_EVENTS:
            rows = read_tsv(data_dir / event / f"{event}_train.tsv")
            pool += [text for _, text, label in rows if label == cls]
        examples[cls] = random.sample(pool, SHOTS)
    with open("data/fewshot_examples.json", "w", encoding="utf-8") as f:
        json.dump({"shots": SHOTS, "from": EXAMPLE_EVENTS, "examples": examples}, f, ensure_ascii=False, indent=1)

    # ---- 打印一遍，确认抽了啥 ----
    final_n = defaultdict(int)
    backup_n = 0
    for it in items:
        final_n[it["event"]] += 1
        if it["split"] != "test":
            backup_n += 1
    print(f"评测样本共 {len(items)} 条（其中 {backup_n} 条来自 dev/train 补足，其余来自 test）：")
    print(f"{'事件':<34}{'类型':<12}{'条数':>5}")
    for event, etype in EVENTS.items():
        print(f"{event:<34}{etype:<12}{final_n[event]:>5}")
    print("\n注：missing_or_found_people 在这 4 个事件的全部 tsv 里没有标注，")
    print("所以每事件只有 7~8 个类别；宏 F1 按切片里实际存在的类别平均（见 eval.py）")
    print(f"\nfew-shot 示例：每类 {SHOTS} 条，来自 {EXAMPLE_EVENTS} 的训练集")


if __name__ == "__main__":
    main()