"""litradar 各脚本共用的工具函数。"""

from __future__ import annotations

import gzip
import html
import io
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML 未安装。请保留 vendor/ 目录（本项目已内置 PyYAML 6.0.2），"
        "或将其放到 Python 的 site-packages。原始错误: %s" % exc
    )

TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
DEFAULT_USER_AGENT = (
    "Litradar/1.0 (mailto:radar@example.org; academic literature monitoring)"
)
_UA_CACHE: str | None = None


def user_agent() -> str:
    """User-Agent 由 config/profile.yaml 的 meta.user_agent 决定。"""
    global _UA_CACHE
    if _UA_CACHE is None:
        try:
            _UA_CACHE = str(load_profile().get("meta", {}).get("user_agent") or DEFAULT_USER_AGENT)
        except Exception:
            _UA_CACHE = DEFAULT_USER_AGENT
    return _UA_CACHE

CONFIG_DIR = ROOT / "config"
DATABASE_DIR = ROOT / "database"
REPORTS_DIR = ROOT / "reports"
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"
ANALYSIS_DIR = ROOT / "database" / "analysis"
RAW_DIR = DATABASE_DIR / "raw"
CANDIDATE_DIR = DATABASE_DIR / "candidates"


def ensure_dirs() -> None:
    for d in (DATABASE_DIR, REPORTS_DIR, LOGS_DIR, STATE_DIR, ANALYSIS_DIR, RAW_DIR, CANDIDATE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def today() -> date:
    return datetime.now(TZ).date()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_yaml(name: str) -> dict[str, Any]:
    with (CONFIG_DIR / name).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def setup_logging(name: str, verbose: bool = True) -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logfile = LOGS_DIR / f"{name}-{today().isoformat()}.log"
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    if verbose:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(sh)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    return logger


def request_json(
    url: str,
    *,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
    retries: int = 3,
    logger: logging.Logger | None = None,
    accept: str = "application/json",
) -> Any:
    """HTTP JSON helper with conservative retries, no paywall bypass."""
    hdrs = {
        "User-Agent": user_agent(),
        "Accept": accept,
    }
    if headers:
        hdrs.update(headers)
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                return json.loads(text)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 20)
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                if logger:
                    logger.warning("HTTP %s on %s; retry in %.1fs", exc.code, url[:120], wait)
                time.sleep(wait)
                continue
            break
        except Exception as exc:  # network / JSON errors
            last_exc = exc
            if attempt < retries:
                wait = min(2 ** attempt, 15)
                if logger:
                    logger.warning("Request failed (%s); retry in %ss: %s", exc, wait, url[:120])
                time.sleep(wait)
                continue
            break
    raise RuntimeError(f"Request failed: {url}: {last_exc}") from last_exc


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)


def clean_markup(text: str | None) -> str:
    if not text:
        return ""
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\u00ad", "")
    return WS_RE.sub(" ", text).strip()


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = DOI_PREFIX_RE.sub("", doi.strip())
    return doi.strip().rstrip(".,;").lower()


def normalize_title(title: str | None) -> str:
    text = clean_markup(title).lower()
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return WS_RE.sub(" ", text).strip()


def normalize_for_match(text: str) -> str:
    text = clean_markup(text).lower()
    text = text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def term_present(text: str, term: str) -> bool:
    """Case-insensitive whole-token match; hyphen/space variants equivalent."""
    if not text or not term:
        return False
    hay = normalize_for_match(text)
    needle = normalize_for_match(term)
    if not needle:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    return re.search(pattern, hay) is not None


def matched_terms(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if term_present(text, t)]


def parse_date_parts(obj: Any) -> str | None:
    if not obj:
        return None
    parts = obj.get("date-parts") if isinstance(obj, dict) else None
    if not parts or not parts[0]:
        return None
    p = parts[0]
    try:
        y = int(p[0])
        m = int(p[1]) if len(p) > 1 and p[1] else 1
        d = int(p[2]) if len(p) > 2 and p[2] else 1
        return date(y, m, d).isoformat()
    except Exception:
        return None


def crossref_dates(item: dict[str, Any]) -> dict[str, str | None]:
    return {
        "published_online": parse_date_parts(item.get("published-online")),
        "published_print": parse_date_parts(item.get("published-print")),
        "issued": parse_date_parts(item.get("issued")),
        "created": parse_date_parts(item.get("created")),
    }


def effective_date(paper: dict[str, Any]) -> str | None:
    for key in ("published_online", "issued", "published_print", "created"):
        val = paper.get(key)
        if val:
            return val
    return None


def date_in_window(value: str | None, since: date, until: date) -> bool:
    if not value:
        return False
    try:
        d = date.fromisoformat(value[:10])
    except Exception:
        return False
    return since <= d <= until


def paper_any_date_in_window(paper: dict[str, Any], since: date, until: date) -> bool:
    return any(date_in_window(paper.get(k), since, until) for k in
               ("published_online", "issued", "published_print", "created"))


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for idx in idxs:
            positions.append((int(idx), word))
    positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in positions)


def short_authors(authors: list[str], limit: int = 3) -> str:
    if not authors:
        return "作者未披露"
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + ", et al."


def journal_index() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    cfg = load_yaml("journals.yaml")
    journals = [j for j in cfg["journals"] if j.get("enabled", True)]
    return {j["id"]: j for j in journals}, journals


def load_keywords() -> dict[str, Any]:
    return load_yaml("keywords.yaml")


def load_scoring() -> dict[str, Any]:
    return load_yaml("scoring.yaml")


def load_profile() -> dict[str, Any]:
    """领域档案：报告标题、文件名前缀、参数表列名等。"""
    return load_yaml("profile.yaml") or {}


def doi_url(doi: str) -> str:
    return "https://doi.org/" + normalize_doi(doi)


def safe_slug(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")
    return text[:max_len] or "paper"


def issue_number() -> int:
    ensure_dirs()
    prefix = (load_profile().get("report") or {}).get("prefix", "Literature_Radar_Weekly_Report")
    return len(list(REPORTS_DIR.glob(f"{prefix}_*.md"))) + 1
