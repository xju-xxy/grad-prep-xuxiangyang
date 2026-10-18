# -*- coding: utf-8 -*-
"""
CrisisBench 实验调度器：等主实验（v0.4 全量 single/multi）完成后，
串行补跑 A2/A3/A4/A7 四组实验，全程自动、断点友好、失败不阻断队列。

队列设计（对应论文 roadmap §八）：
  STEP0  等待主实验完成（results 目录出现新的 single/multi 全量结果与 plus 重裁判，且无 partial）
  STEP1  A3 消融：multi-noaudit 全量（被测 flash，裁判 flash）→ 再 rescore plus
  STEP2  A4 对照：multi-verify 全量（被测 flash，裁判 flash）→ 再 rescore plus
  STEP3  A2 双模型：被测换 glm-4-plus 跑 single/multi 全量（裁判仍 flash）→ 再 rescore plus
  STEP4  A7 自一致：主实验 single/multi 的同批答案用 flash 裁判重打一次（比主跑 flash 判分）

用法：
  python run_all_experiments.py          # 从头排（等待中可 ctrl-c，重新启动自动跳过已完成步骤）
  python run_all_experiments.py --nowait # 不等主实验（一般不用）
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
ENV_FILE = os.path.join(BASE_DIR, "..", "..", "reproduction", "autogen-demo", ".env")
STATE_FILE = os.path.join(BASE_DIR, "queue_state.json")
STAMP_CUTOFF = "20261018-220000"  # 只认此时间之后的结果文件（v0.4 全量）

CUTOFF_T = datetime.datetime.strptime(STAMP_CUTOFF, "%Y%m%d-%H%M%S")


def log(msg):
    print("[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def read_api_key():
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            if line.startswith("ZHIPUAI_API_KEY="):
                return line.strip().split("=", 1)[1]
    return None


def latest_file(keyword, exclude=("partial", "rescore")):
    """results 目录中 stamp 在截止线之后、文件名含 keyword、不含 exclude 的最新 json。"""
    best = None
    for name in os.listdir(RESULTS_DIR):
        if not name.endswith(".json") or not keyword in name:
            continue
        if any(x in name for x in exclude):
            continue
        m = re.search(r"(\d{8}-\d{6})\.json$", name)
        if not m:
            continue
        try:
            t = datetime.datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
        except ValueError:
            continue
        if t < CUTOFF_T:
            continue
        if best is None or t > best[0]:
            best = (t, name)
    return best[1] if best else None


def any_partial():
    return [n for n in os.listdir(RESULTS_DIR) if n.endswith(".partial.json")]


def wait_main_done(timeout_h=14):
    """STEP0：主实验四步全部完成才放行。"""
    deadline = time.time() + timeout_h * 3600
    while time.time() < deadline:
        parts = any_partial()
        s = latest_file("exp-all-single-")
        m = latest_file("exp-all-multi-")
        if not parts and s and m:
            log("主实验完成：%s / %s" % (s, m))
            return s, m
        log("等待主实验完成……（partial=%s，single=%s，multi=%s）"
            % (parts or "无", s or "无", m or "无"))
        time.sleep(90)
    raise TimeoutError("等待主实验超时（%dh），请人工检查。" % timeout_h)


def run_cmd(args, step_name):
    """跑一步子命令；失败回退一次 resume（若存在 partial）；返回 (ok, 结果文件名或None)。"""
    env = dict(os.environ)
    key = read_api_key()
    if key:
        env["ZHIPUAI_API_KEY"] = key
    for attempt in (0, 1):
        cmd = [sys.executable, os.path.join(BASE_DIR, "run_experiment.py")] + args
        tag = " ".join(str(x) for x in args[:6])
        if attempt == 1:
            # 找该配置的 partial 文件恢复
            cfg = args[args.index("--config") + 1] if "--config" in args else "single"
            parts = [n for n in any_partial() if cfg in n]
            if not parts:
                log("  步骤 %s 失败且无 partial 可恢复，跳过" % step_name)
                return False, None
            cmd += ["--resume", os.path.join(RESULTS_DIR, parts[0])]
            log("  步骤 %s 失败，用 %s 恢复重试" % (step_name, parts[0]))
        log("  执行：python run_experiment.py %s" % tag)
        r = subprocess.run(cmd, cwd=BASE_DIR, env=env)
        if r.returncode == 0:
            return True, None
        log("  步骤 %s 退出码 %d" % (step_name, r.returncode))
    return False, None


def rescore_of(main_file, judge_model):
    """对 main_file 用 judge_model 重裁判，返回输出文件句柄 none（文件名动态）。"""
    env = dict(os.environ)
    key = read_api_key()
    if key:
        env["ZHIPUAI_API_KEY"] = key
    cmd = [sys.executable, os.path.join(BASE_DIR, "run_experiment.py"),
           "--rescore", os.path.join(RESULTS_DIR, main_file),
           "--judge-model", judge_model]
    log("  执行：rescore %s → %s" % (main_file, judge_model))
    r = subprocess.run(cmd, cwd=BASE_DIR, env=env)
    return r.returncode == 0


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(st):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def main():
    nowait = "--nowait" in sys.argv
    st = load_state()
    log("调度器启动。已完成步骤：%s" % (st or "（空）"))

    # ---------- STEP0：等主实验 ----------
    if not st.get("step0"):
        if nowait:
            s_file = latest_file("exp-all-single-")
            m_file = latest_file("exp-all-multi-")
            if not (s_file and m_file):
                raise SystemExit("--nowait 但主实验未完成，退出。")
        else:
            s_file, m_file = wait_main_done()
        st["step0"] = {"single": s_file, "multi": m_file}
        save_state(st)
    else:
        s_file, m_file = st["step0"]["single"], st["step0"]["multi"]
    log("STEP0 完成。single=%s multi=%s" % (s_file, m_file))

    # ---------- STEP1：A3 消融 ----------
    if not st.get("step1"):
        ok, _ = run_cmd(["--scene", "all", "--config", "multi-noaudit",
                         "--model", "glm-4-flash", "--judge", "both",
                         "--judge-model", "glm-4-flash"], "A3 主跑")
        a3_file = latest_file("multi-noaudit") if ok else None
        if a3_file and rescore_of(a3_file, "glm-4-plus"):
            st["step1"] = {"main": a3_file}
            save_state(st)
            log("STEP1（A3）完成：%s" % a3_file)
        else:
            log("STEP1（A3）失败，继续后续步骤")
    else:
        log("STEP1（A3）已做过：%s" % st["step1"])

    # ---------- STEP2：A4 multi-verify ----------
    if not st.get("step2"):
        ok, _ = run_cmd(["--scene", "all", "--config", "multi-verify",
                         "--model", "glm-4-flash", "--judge", "both",
                         "--judge-model", "glm-4-flash"], "A4 主跑")
        a4_file = latest_file("multi-verify") if ok else None
        if a4_file and rescore_of(a4_file, "glm-4-plus"):
            st["step2"] = {"main": a4_file}
            save_state(st)
            log("STEP2（A4）完成：%s" % a4_file)
        else:
            log("STEP2（A4）失败，继续后续步骤")
    else:
        log("STEP2（A4）已做过：%s" % st["step2"])

    # ---------- STEP3：A2 双模型（被测 plus） ----------
    if not st.get("step3"):
        a2_files = {}
        for cfg in ("single", "multi"):
            ok, _ = run_cmd(["--scene", "all", "--config", cfg,
                             "--model", "glm-4-plus", "--judge", "both",
                             "--judge-model", "glm-4-flash"], "A2 %s" % cfg)
            f = latest_file("exp-all-%s-" % cfg) if ok else None
            if f and not f.endswith(".partial.json") and rescore_of(f, "glm-4-plus"):
                a2_files[cfg] = f
        if a2_files:
            st["step3"] = a2_files
            save_state(st)
            log("STEP3（A2）完成：%s" % a2_files)
        else:
            log("STEP3（A2）失败，继续后续步骤")
    else:
        log("STEP3（A2）已做过：%s" % st["step3"])

    # ---------- STEP4：A7 自一致（同批答案 flash 再打一次） ----------
    if not st.get("step4"):
        a7 = {}
        for cfg, f in (("single", s_file), ("multi", m_file)):
            if f and rescore_of(f, "glm-4-flash"):
                # 找新产生的 "rescore-glm-4-flash" 文件
                a7[cfg] = latest_file("rescore-glm-4-flash", exclude=("partial",))
        if a7:
            st["step4"] = a7
            save_state(st)
            log("STEP4（A7）完成：%s" % a7)
        else:
            log("STEP4（A7）失败")
    else:
        log("STEP4（A7）已做过：%s" % st["step4"])

    log("调度器全部步骤结束。state=%s" % json.dumps(st, ensure_ascii=False))


if __name__ == "__main__":
    main()