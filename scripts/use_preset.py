#!/usr/bin/env python
"""切换领域预设：把 presets/<name>/ 下的配置复制到 config/。

    python scripts/use_preset.py --list
    python scripts/use_preset.py --use ai-ml
    python scripts/use_preset.py --use ai-ml --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
PRESETS = ROOT / "presets"
FILES = ("journals.yaml", "keywords.yaml", "profile.yaml")


def list_presets() -> list[Path]:
    if not PRESETS.is_dir():
        return []
    return sorted(p for p in PRESETS.iterdir() if p.is_dir() and (p / "journals.yaml").exists())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="在 presets/ 之间切换领域配置")
    ap.add_argument("--list", action="store_true", help="列出可用预设")
    ap.add_argument("--use", metavar="NAME", help="应用某个预设")
    ap.add_argument("--dry-run", action="store_true", help="只显示将要改动的内容")
    args = ap.parse_args(argv)

    presets = list_presets()

    if args.list or not args.use:
        print("可用预设：")
        for preset in presets:
            extra = [f for f in FILES if (preset / f).exists()]
            print(f"  - {preset.name:<22} {', '.join(extra)}")
        print("\n用法：python scripts/use_preset.py --use <name>")
        return 0

    target = next((p for p in presets if p.name == args.use), None)
    if target is None:
        print(f"未找到预设 {args.use!r}；可选：{', '.join(p.name for p in presets)}", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for name in FILES:
        src = target / name
        if not src.exists():
            continue
        dst = CONFIG / name
        if args.dry_run:
            print(f"[dry-run] {src} -> {dst}")
            continue
        if dst.exists():
            backup = dst.with_name(f"{dst.name}.bak-{stamp}")
            shutil.copy2(dst, backup)
            print(f"备份 {dst.name} -> {backup.name}")
        shutil.copy2(src, dst)
        print(f"写入 {dst.name}")

    if not args.dry_run:
        print("\n完成。接着跑一次体检：python scripts/health_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
