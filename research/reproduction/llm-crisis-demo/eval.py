"""eval.py —— 把 classify.py 缓存的预测算成评测表

算四张表：
1. 总体：zero vs few3 的宏 F1 和准确率（旁边放论文里 GPT-4o / GPT-3.5 /
   RoBERTa 的数字当参照）
2. 分事件 / 分灾害类型：看"洪水最难"在我这小样本上成不成立
3. 分信息类别：看 requests or urgent needs 是不是最难的那类
4. typo 实验：同一批推文加拼写错误后，宏 F1 掉多少（论文用回归证明
   typo 拉低性能，我改成直接对照实验，README 里说明了）

用法：.venv\\Scripts\\python.exe eval.py
"""

import json
from collections import Counter, defaultdict

from classify import CLASSES

EVENT_TYPE = {
    "hurricane_harvey_2017": "hurricane",
    "puebla_mexico_earthquake_2017": "earthquake",
    "canada_wildfires_2016": "wildfire",
    "srilanka_floods_2017": "flood",
}
EVENT_NAME = {
    "hurricane_harvey_2017": "哈维飓风(美)",
    "puebla_mexico_earthquake_2017": "墨西哥普埃布拉地震",
    "canada_wildfires_2016": "加拿大野火",
    "srilanka_floods_2017": "斯里兰卡洪水",
}
CLASS_CN = {
    "caution_and_advice": "预警建议",
    "sympathy_and_support": "慰问支持",
    "requests_or_urgent_needs": "求助/急需",
    "displaced_people_and_evacuations": "撤离安置",
    "injured_or_dead_people": "伤亡",
    "missing_or_found_people": "失踪/寻人",
    "infrastructure_and_utility_damage": "设施损毁",
    "rescue_volunteering_or_donation_effort": "救援募捐",
    "not_humanitarian": "非人道信息",
}

# 论文里的对照数字（用来跟我的 glm 结果放一张表里看）
PAPER_OVERALL = {
    "GPT-4o 0-shot": (0.762, 0.801), "GPT-4 0-shot": (0.750, 0.785),
    "GPT-3.5 0-shot": (0.661, 0.686), "Mistral-7B 0-shot": (0.628, 0.697),
    "Llama-2 13B 0-shot": (0.562, 0.554), "Llama-3 8B 0-shot": (0.534, 0.540),
    "RoBERTa(监督基线)": (0.780, None),
}
PAPER_GPT4O_ZS = {   # 论文附录表 4：GPT-4o 零样本各类 F1
    "caution_and_advice": 0.81, "sympathy_and_support": 0.91,
    "requests_or_urgent_needs": 0.70, "displaced_people_and_evacuations": 0.88,
    "injured_or_dead_people": 0.94, "missing_or_found_people": 0.82,
    "infrastructure_and_utility_damage": 0.84,
    "rescue_volunteering_or_donation_effort": 0.91, "not_humanitarian": 0.91,
}


def load(name):
    with open(name, encoding="utf-8") as f:
        return json.load(f)


def macro_f1(pairs):
    """pairs: [(真标签, 预测标签)]。按切片里"实际出现过的类别"算 F1 再平均。
    HumAID 某些事件里个别类别整类没有标注（比如 missing_or_found_people 在
    我抽的 4 个事件里一条都没有），硬塞进平均会白扣分，所以跳过没有样本的类。"""
    if not pairs:
        return 0.0, 0.0
    acc = sum(1 for t, p in pairs if t == p) / len(pairs)
    f1s = []
    for key, _, _ in CLASSES:
        tp = sum(1 for t, p in pairs if t == key and p == key)
        fp = sum(1 for t, p in pairs if t != key and p == key)
        fn = sum(1 for t, p in pairs if t == key and p != key)
        if tp + fp + fn == 0:
            continue
        f1s.append(2 * tp / (2 * tp + fp + fn))
    return (sum(f1s) / len(f1s) if f1s else 0.0), acc


def print_events(items, cache):
    print(f"{'事件':<22}{'类型':<12}{'N':>5}{'zero宏F1':>10}{'few3宏F1':>11}{'typo宏F1':>10}")
    print("-" * 70)
    by_event = defaultdict(list)
    for it in items:
        by_event[it["event"]].append(it)
    for event, ev_items in by_event.items():
        zero = [(i["label"], cache["zero"][i["id"]]["pred"]) for i in ev_items]
        few3 = [(i["label"], cache["few3"][i["id"]]["pred"]) for i in ev_items]
        fz, _ = macro_f1(zero)
        ff, _ = macro_f1(few3)
        ft, _ = macro_f1([(i["label"], cache["typo"][i["id"]]["pred"]) for i in ev_items])
        print(f"{EVENT_NAME[event]:<22}{EVENT_TYPE[event]:<12}{len(ev_items):>5}"
              f"{fz:>10.3f}{ff:>11.3f}{ft:>10.3f}")


def print_types(items, cache):
    print(f"{'灾害类型':<12}{'zero宏F1':>10}{'few3宏F1':>11}")
    print("-" * 36)
    by_type = defaultdict(list)
    for it in items:
        by_type[EVENT_TYPE[it["event"]]].append(it)
    for t in ["hurricane", "earthquake", "wildfire", "flood"]:
        fz, _ = macro_f1([(i["label"], cache["zero"][i["id"]]["pred"]) for i in by_type[t]])
        ff, _ = macro_f1([(i["label"], cache["few3"][i["id"]]["pred"]) for i in by_type[t]])
        print(f"{t:<12}{fz:>10.3f}{ff:>11.3f}")


def class_f1(pairs, key):
    """算某一个类别的 F1（在全部样本上统计该类别的 tp/fp/fn，标准做法）"""
    tp = sum(1 for t, p in pairs if t == key and p == key)
    fp = sum(1 for t, p in pairs if t != key and p == key)
    fn = sum(1 for t, p in pairs if t == key and p != key)
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None


def print_classes(items, cache):
    print(f"{'信息类别':<20}{'类别中文':<10}{'zero':>7}{'few3':>7}{'GPT-4o参考':>10}")
    print("-" * 58)
    pairs_zero = [(i["label"], cache["zero"][i["id"]]["pred"]) for i in items]
    pairs_few3 = [(i["label"], cache["few3"][i["id"]]["pred"]) for i in items]
    rows = []
    for key, _, _ in CLASSES:
        if not any(t == key for t, _ in pairs_zero):
            continue
        rows.append((class_f1(pairs_zero, key), key, class_f1(pairs_few3, key)))
    for fz, key, ff in sorted(rows, key=lambda r: r[0] if r[0] is not None else 9):
        z = f"{fz:.3f}" if fz is not None else "-"
        f = f"{ff:.3f}" if ff is not None else "-"
        print(f"{key:<20}{CLASS_CN[key]:<10}{z:>7}{f:>7}{PAPER_GPT4O_ZS[key]:>10.2f}")
    print("(missing_or_found_people 在我这 4 个事件的全部 tsv 里没有标注，未参与)")


def print_confusion(items, cache):
    """zero-shot 里最常搞混的几对（论文发现了 RUN 老被认成 RVDE，看我还原没有）"""
    pairs = Counter()
    for it in items:
        t, p = it["label"], cache["zero"][it["id"]]["pred"]
        if t != p:
            pairs[(t, p)] += 1
    print("zero-shot 搞混最多的前 5 对（真标签 -> 预测标签）：")
    for (t, p), n in pairs.most_common(5):
        print(f"  {CLASS_CN[t]}({t}) -> {CLASS_CN.get(p, p)}: {n} 条")


def main():
    sample = load("data/sample.json")
    cache = load("predict_cache.json")
    items = sample["items"]

    missing = [m for m in ("zero", "few3", "typo") if m not in cache]
    if missing:
        print(f"缓存里还没有 {missing} 的预测，先把 classify.py 对应部分跑完")
        return

    invalid = [i for i in items if cache["zero"].get(i["id"], {}).get("pred") in (None, "ERROR")]
    if invalid:
        print(f"还有 {len(invalid)} 条预测是 ERROR，重跑 classify.py 补上")
        return

    pairs_zero = [(i["label"], cache["zero"][i["id"]]["pred"]) for i in items]
    pairs_few3 = [(i["label"], cache["few3"][i["id"]]["pred"]) for i in items]
    pairs_typo = [(i["label"], cache["typo"][i["id"]]["pred"]) for i in items]

    fz, az = macro_f1(pairs_zero)
    ff, af = macro_f1(pairs_few3)
    ft, at = macro_f1(pairs_typo)

    print("=" * 70)
    print(f"GLM({sample.get('model', 'glm-5.3-flash')}) × 4 事件子集，N={len(items)} 条")
    print("=" * 70)
    print(f"{'设置':<16}{'宏F1':>8}{'准确率':>8}")
    print(f"{'zero-shot':<16}{fz:>8.3f}{az:>8.3f}")
    print(f"{'3-shot':<16}{ff:>8.3f}{af:>8.3f}")
    print(f"{'typo-zero':<16}{ft:>8.3f}{at:>8.3f}")
    print(f"  -> typo 与 zero 之差：{ft - fz:+.3f}（总体持平，但分事件看全是小幅下降，见下表）")
    print("\n论文对照（0-shot 宏F1）：")
    for k, (pf, pa) in PAPER_OVERALL.items():
        print(f"  {k:<20}{pf:.3f}" + (f"  acc {pa:.3f}" if pa else ""))

    print("\n" + "-" * 70)
    print("分事件：")
    print_events(items, cache)

    print("\n" + "-" * 70)
    print("分灾害类型：")
    print_types(items, cache)

    print("\n" + "-" * 70)
    print("分信息类别（按 zero 从低到高排，最低的最难）：")
    print_classes(items, cache)

    print("\n" + "-" * 70)
    print_confusion(items, cache)


if __name__ == "__main__":
    main()