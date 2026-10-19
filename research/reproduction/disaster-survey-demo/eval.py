"""eval.py —— 拿 testset.json 跑一遍，统计阶段判定准确率和子任务命中率

做的事：
1. 逐条把测试文本喂给 extract.py 的抽取函数，结果缓存到 results/predictions.json，
   跑挂了重跑会跳过已完成的条目。
2. 把模型输出的中文名，按 taxonomy.json 归一化成 key，再跟 gold 比对。
3. 算三个数：阶段准确率、子任务命中率、阶段且子任务都对的比例；
   另外单独看"灾害态势评估"三小细分判对没有。
4. 把每条原始输出和结果落到 results/predictions.json，用不着编。

用法：.venv\\Scripts\\python.exe eval.py
"""

import json
import os

from extract import load_taxonomy, build_system_prompt, extract

TAX = load_taxonomy()
SYSTEM_PROMPT = build_system_prompt(TAX)

PRED_FILE = os.path.join("results", "predictions.json")

# ---- 建几个中文名 -> key 的查表 ----
STAGE_CN2KEY = {st["cn"]: st["key"] for st in TAX["stages"]}
TASK_CN2KEY = {}      # 任务的 cn -> (阶段 key, 任务 key)
SUBTYPE_CN2PARENT = {}  # 细分的 cn -> 父任务 key
SUBTYPE_CN2KEY = {}     # 细分的 cn -> 细分 key
for st in TAX["stages"]:
    for tk in st["tasks"]:
        TASK_CN2KEY[tk["cn"]] = (st["key"], tk["key"])
        for sub in tk.get("subtasks", []):
            SUBTYPE_CN2PARENT[sub["cn"]] = tk["key"]
            SUBTYPE_CN2KEY[sub["cn"]] = sub["key"]
MODEL_KEYS = {m["key"] for m in TAX["model_types"]}
MODEL_CN2KEY = {m["cn"]: m["key"] for m in TAX["model_types"]}


def _match_by_contain(pred, table):
    """pred 里包含某个中文名就算命中，取最长的那个（避免"灾害"这类前缀误伤）"""
    hits = [k for k in table if k and k in pred]
    if not hits:
        return None
    return max(hits, key=len)


def norm_stage(pred):
    p = str(pred or "")
    if p in STAGE_CN2KEY:
        return STAGE_CN2KEY[p]
    for k, v in STAGE_CN2KEY.items():
        if v in p.lower():
            return v
    hit = _match_by_contain(p, STAGE_CN2KEY)
    return STAGE_CN2KEY[hit] if hit else None


def norm_task(pred):
    """返回 (父任务 key)。先看是不是细分（态势分类等），再退回五个大任务"""
    p = str(pred or "")
    hit = _match_by_contain(p, SUBTYPE_CN2PARENT)
    if hit:
        return SUBTYPE_CN2PARENT[hit]
    hit = _match_by_contain(p, TASK_CN2KEY)
    return TASK_CN2KEY[hit][1] if hit else None


def norm_subtype(pred):
    p = str(pred or "")
    hit = _match_by_contain(p, SUBTYPE_CN2KEY)
    return SUBTYPE_CN2KEY[hit] if hit else None


def norm_model(pred):
    p = str(pred or "")
    for k in MODEL_KEYS:
        if k in p.upper():
            return k
    hit = _match_by_contain(p, MODEL_CN2KEY)
    return MODEL_CN2KEY[hit] if hit else None


def load_preds():
    if os.path.exists(PRED_FILE):
        with open(PRED_FILE, encoding="utf-8") as f:
            return {r["id"]: r for r in json.load(f)}
    return {}


def save_preds(store):
    # 按 testset 顺序排一下，方便看
    with open(PRED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(store.values()), f, ensure_ascii=False, indent=1)


def run_all(items, store):
    for it in items:
        if it["id"] in store and store[it["id"]].get("pred"):
            print(f"[{it['id']}] 已有缓存，跳过")
            continue
        print(f"[{it['id']}] 调用 GLM ...")
        try:
            pred, raw = extract(it["text"], TAX, SYSTEM_PROMPT)
        except Exception as e:
            pred, raw = {"阶段": "ERROR", "子任务": "ERROR", "建议模型类型": "ERROR", "依据": str(e)}, str(e)
        store[it["id"]] = {"id": it["id"], "text": it["text"], "pred": pred, "raw": raw, "gold": it["gold"]}
        save_preds(store)
        print(f"    -> 阶段={pred.get('阶段')} 子任务={pred.get('子任务')} 模型={pred.get('建议模型类型')}")


def main():
    with open("testset.json", encoding="utf-8") as f:
        testset = json.load(f)
    items = testset["items"]

    store = load_preds()
    run_all(items, store)

    n = len(items)
    stage_ok = task_ok = both_ok = model_ok = 0
    rows = []
    sa_items = []  # 态势评估的三条，单独看细分
    for it in items:
        r = store[it["id"]]
        pred = r["pred"]
        g = it["gold"]
        ps, pt = norm_stage(pred.get("阶段")), norm_task(pred.get("子任务"))
        psub = norm_subtype(pred.get("子任务"))
        pm = norm_model(pred.get("建议模型类型"))
        s_ok = ps == g["stage"]
        t_ok = pt == g["task"]
        m_ok = pm == g["model"]
        stage_ok += s_ok
        task_ok += t_ok
        both_ok += s_ok and t_ok
        model_ok += m_ok
        rows.append((it["id"], g["stage"], g["task"], g.get("subtype"), ps, pt, psub, s_ok, t_ok, m_ok))
        if g["task"] == "disaster_situation_assessment":
            sa_items.append((it["id"], g.get("subtype"), psub))

    print("\n" + "=" * 78)
    print(f"GLM({testset['model']}) x 自制测试集 N={n}")
    print("=" * 78)
    print(f"{'id':<6}{'gold阶段':<12}{'pred阶段':<12}{'gold子任务':<28}{'pred子任务':<28}{'阶段':<5}{'子任务':<6}")
    print("-" * 78)
    for (rid, gs, gt, gsub, ps, pt, psub, s_ok, t_ok, m_ok) in rows:
        print(f"{rid:<6}{gs:<12}{str(ps):<12}{gt:<28}{str(pt):<28}{'√' if s_ok else '×':<5}{'√' if t_ok else '×':<6}")

    print("-" * 78)
    print(f"阶段判定准确率   : {stage_ok}/{n} = {stage_ok / n:.3f}")
    print(f"子任务命中率     : {task_ok}/{n} = {task_ok / n:.3f}")
    print(f"阶段且子任务都对 : {both_ok}/{n} = {both_ok / n:.3f}")
    print(f"模型类型一致(参考): {model_ok}/{n} = {model_ok / n:.3f}")

    if sa_items:
        ok = sum(1 for _, gsub, psub in sa_items if gsub == psub)
        print(f"态势评估细分命中  : {ok}/{len(sa_items)} = {ok / len(sa_items):.3f}")
        for rid, gsub, psub in sa_items:
            print(f"    {rid}: gold={gsub} pred={psub} {'√' if gsub == psub else '×'}")

    print(f"\n明细已写入 {PRED_FILE}")


if __name__ == "__main__":
    main()
