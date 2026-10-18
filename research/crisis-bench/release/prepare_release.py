# -*- coding: utf-8 -*-
"""打包 CrisisBench v0.4 匿名发布材料。

用法：直接运行本脚本（python prepare_release.py），将在脚本同目录生成
crisisbench-v0.4-anonymized.zip，并打印包内文件清单与总大小。

匿名性保证：
  1. 压缩包内使用相对路径作为归档名，不含本机绝对路径 / 用户名等个人信息；
  2. scenarios.json 的 meta.标注人 等实名字段在打包时统一替换为 Anonymous。
"""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

RELEASE_DIR = Path(__file__).resolve().parent          # .../release/
BENCH_DIR = RELEASE_DIR.parent                          # .../crisis-bench/

# (源文件绝对路径, 包内归档相对路径)
FILES = [
    (BENCH_DIR / "scenarios" / "scenarios.json", "scenarios/scenarios.json"),
    (BENCH_DIR / "scenarios" / "rubric.md", "scenarios/rubric.md"),
    (BENCH_DIR / "experiments" / "verify_specs.json", "experiments/verify_specs.json"),
    (RELEASE_DIR / "README.md", "README.md"),
]

OUT_ZIP = RELEASE_DIR / "crisisbench-v0.4-anonymized.zip"

# 泄露个人信息的路径特征（用于自检，命中即报错）
_LEAK_HINTS = ("23572", "Users", "users", "Desktop", "Desktop")


def _assert_clean_arcname(arcname: str) -> None:
    for hint in _LEAK_HINTS:
        if hint in arcname:
            raise SystemExit(
                f"归档路径疑似含个人信息（命中特征: {hint!r}），已中止：{arcname}"
            )


def _anonymize_scenarios(src: Path) -> bytes:
    """读 scenarios.json，把 meta 中的实名标注字段替换为匿名，返回序列化字节。"""
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("meta", {})
    for key in ("标注人", "annotator", "author", "作者"):
        if key in meta:
            meta[key] = "Anonymous"
    # 全文兜底：出现常见姓名列表时替换（防止姓名散落在别处）
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    for name in ("徐向阳", "xuxiangyang", "Xuxiangyang"):
        raw = raw.replace(name, "Anonymous")
    return raw.encode("utf-8")


def main() -> None:
    missing = [src for src, _ in FILES if not src.is_file()]
    if missing:
        raise SystemExit("以下源文件不存在：\n  " + "\n  ".join(map(str, missing)))

    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arcname in FILES:
            _assert_clean_arcname(arcname)
            if src.name == "scenarios.json":
                zf.writestr(arcname, _anonymize_scenarios(src))
            else:
                zf.write(src, arcname=arcname)

    print("生成压缩包：", OUT_ZIP)
    print("总大小：%.2f KB（%.0f 字节）"
          % (OUT_ZIP.stat().st_size / 1024, OUT_ZIP.stat().st_size))
    print("\n包内文件清单：")
    with zipfile.ZipFile(OUT_ZIP, "r") as zf:
        for info in zf.infolist():
            print("  %-32s %8d 字节" % (info.filename, info.file_size))
    print("\n共 %d 个文件。" % len(FILES))


if __name__ == "__main__":
    main()