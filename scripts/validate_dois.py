#!/usr/bin/env python
"""Verify that DOIs in an analysis JSON resolve through the DOI handle API."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from common import load_json, normalize_doi, setup_logging

HANDLE = "https://doi.org/api/handles/{doi}"


def resolve(doi: str) -> dict:
    req = urllib.request.Request(
        HANDLE.format(doi=doi),
        headers={"User-Agent": "Litradar/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"doi": doi, "ok": False, "error": str(exc)}
    urls = [v.get("data", {}).get("value") for v in data.get("values", []) if v.get("type") == "URL"]
    return {
        "doi": doi,
        "ok": data.get("responseCode") == 1 and bool(urls),
        "url": urls[0] if urls else None,
        "response_code": data.get("responseCode"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DOI resolution")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    setup_logging("doi", verbose=False)
    analysis = load_json(Path(args.analysis)) or {}
    dois = [normalize_doi(d) for d in analysis.get("top_table", [])]
    results = [resolve(d) for d in dict.fromkeys(dois) if d]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(("OK  " if r["ok"] else "FAIL"), r["doi"], r.get("url") or r.get("error"))
    return 0 if results and all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
