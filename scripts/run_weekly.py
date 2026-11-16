#!/usr/bin/env python
"""One-command weekly pipeline: fetch -> filter -> analysis worksheet.

This script deliberately stops before writing the final report. The Agent must
read the papers, fill the analysis JSON, validate it, and call
generate_report.py --finalize. That separation prevents an unattended script
from inventing scientific claims.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from common import (
    ANALYSIS_DIR,
    CANDIDATE_DIR,
    ROOT,
    STATE_DIR,
    atomic_write_json,
    load_json,
    now_iso,
    setup_logging,
    today,
)

STATE_PATH = STATE_DIR / "last_run.json"
LOCK_PATH = STATE_DIR / "run.lock"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weekly literature radar pipeline")
    p.add_argument("--since")
    p.add_argument("--until")
    p.add_argument("--days", type=int)
    p.add_argument("--journals")
    p.add_argument("--reuse", action="store_true", help="Reuse latest candidates; skip fetch/filter")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def acquire_lock(logger) -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age < 6 * 3600:
            logger.error("Another run is active (lock age %.0f min): %s", age / 60, LOCK_PATH)
            return False
        logger.warning("Removing stale lock (age %.1f h)", age / 3600)
        LOCK_PATH.unlink(missing_ok=True)
    LOCK_PATH.write_text(json.dumps({"pid": os.getpid(), "started": now_iso()}), encoding="utf-8")
    return True


def release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


def set_state(**changes) -> None:
    state = load_json(STATE_PATH, default={}) or {}
    state.update(changes)
    state["schema_version"] = 1
    atomic_write_json(STATE_PATH, state)


def run_step(args: list[str], logger) -> int:
    cmd = [sys.executable] + args
    logger.info("Running: %s", " ".join(cmd))
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return int(proc.returncode)


def latest_candidate() -> Path | None:
    files = sorted(CANDIDATE_DIR.glob("*.json"))
    return files[-1] if files else None


def main() -> int:
    args = parse_args()
    logger = setup_logging("weekly", verbose=not args.quiet)
    if not acquire_lock(logger):
        return 2
    set_state(
        status="running",
        last_attempt=now_iso(),
        last_error=None,
    )
    try:
        if not args.reuse:
            fetch_cmd = [str(ROOT / "scripts" / "fetch_literature.py")]
            for key in ("since", "until", "days", "journals"):
                val = getattr(args, key)
                if val is not None:
                    fetch_cmd.extend([f"--{key}", str(val)])
            if run_step(fetch_cmd, logger) != 0:
                raise RuntimeError("fetch_literature.py failed")
            if run_step([str(ROOT / "scripts" / "filter_papers.py")], logger) != 0:
                raise RuntimeError("filter_papers.py failed")
        cand_path = latest_candidate()
        if not cand_path:
            raise RuntimeError("No candidate file produced")
        cand = load_json(cand_path)

        prep_cmd = [str(ROOT / "scripts" / "prepare_analysis.py"), "--candidates", str(cand_path)]
        if run_step(prep_cmd, logger) != 0:
            raise RuntimeError("prepare_analysis.py failed")
        until = cand.get("window", {}).get("until") or today().isoformat()
        template = ANALYSIS_DIR / f"{until}.template.json"
        analysis_file = ANALYSIS_DIR / f"{until}.json"
        set_state(
            status="candidates_ready",
            last_candidate_file=str(cand_path),
            last_candidate_window=cand.get("window"),
            last_template=str(template),
            last_error=None,
        )
        result = {
            "ok": True,
            "status": "candidates_ready",
            "candidate_file": str(cand_path),
            "analysis_template": str(template),
            "analysis_target": str(analysis_file),
            "stats": cand.get("stats", {}),
            "top5": [
                {
                    "rank": p.get("rank"),
                    "doi": p.get("doi"),
                    "title": p.get("title"),
                    "journal": p.get("journal"),
                    "score": p.get("score", {}).get("total"),
                }
                for p in cand.get("ranked", [])[:5]
            ],
            "next": (
                "阅读候选论文，把模板复制为 analysis_target 并填写；"
                "运行 validate_analysis.py，再运行 generate_report.py --finalize。"
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        logger.error("Weekly pipeline failed: %s", exc, exc_info=True)
        state = load_json(STATE_PATH, default={}) or {}
        set_state(
            status="failed",
            last_error=str(exc),
            consecutive_failures=int(state.get("consecutive_failures", 0)) + 1,
        )
        return 1
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
