"""Logging for the jobs: context fields, text or JSON lines, redaction, tick journal.

- Every log line carries the current context (league, week, transition) set with
  `log_context(...)`, so a problem can be traced to one league and one transition.
- `--log-format json` gives one JSON object per line (GitHub Actions logs, grep, jq).
- Lines are redacted: no connection string, password, email or JWT ever reaches a log
  (CLAUDE.md hard rule 1).
- `TickCollector` keeps the lines of one tick; jobs/tick.py stores them in
  private.tick_runs with the outcome, and updates public.system_status (status page).
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

_CONTEXT: contextvars.ContextVar[tuple[tuple[str, str], ...]] = contextvars.ContextVar(
    "log_context", default=()
)

_REDACTIONS = (
    (re.compile(r"postgres(?:ql)?://[^\s'\"]+"), "postgresql://[redacted]"),
    (re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"), "[jwt]"),
    (re.compile(r"\bsb_(?:secret|publishable)_[\w-]+"), "[key]"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r"(?i)(password|passwd|pwd)=\S+"), r"\1=[redacted]"),
)


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


@contextlib.contextmanager
def log_context(**fields: object) -> Iterator[None]:
    """Adds fields (league=…, week=…, transition=…) to every line logged inside."""
    merged = {**dict(_CONTEXT.get()), **{k: str(v) for k, v in fields.items()}}
    token = _CONTEXT.set(tuple(merged.items()))
    try:
        yield
    finally:
        _CONTEXT.reset(token)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.ctx = dict(_CONTEXT.get())
        return True


def record_dict(record: logging.LogRecord) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="seconds"),
        "level": record.levelname.lower(),
        "logger": record.name,
        "msg": redact(record.getMessage()),
        **getattr(record, "ctx", {}),
    }
    if record.exc_info:
        entry["error"] = redact(logging.Formatter().formatException(record.exc_info))
    return entry


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(record_dict(record), ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = record_dict(record)
        ctx = " ".join(f"{k}={v}" for k, v in getattr(record, "ctx", {}).items())
        line = f"{entry['ts']} {record.levelname:<7} {record.name}: {entry['msg']}"
        if ctx:
            line += f" [{ctx}]"
        if "error" in entry:
            line += "\n" + entry["error"]
        return line


class _QuietTransitions(logging.Filter):
    """Console only: hides the per-transition 'done' lines (the tick journal keeps them)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name == "jobs.db" and record.levelno < logging.WARNING)


def setup_logging(fmt: str = "text", level: int = logging.INFO, quiet: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())
    handler.addFilter(_ContextFilter())
    if quiet:
        handler.addFilter(_QuietTransitions())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("yfinance", "urllib3", "peewee", "httpx"):
        # Quiet (dev): third-party chatter off; the providers log their own failures.
        logging.getLogger(noisy).setLevel(logging.CRITICAL if quiet else logging.WARNING)


class TickCollector(logging.Handler):
    """Keeps the `jobs.*` lines of one tick (bounded) for private.tick_runs."""

    def __init__(self, limit: int = 500) -> None:
        super().__init__(logging.INFO)
        self.limit = limit
        self.entries: list[dict[str, Any]] = []
        self.addFilter(_ContextFilter())

    def emit(self, record: logging.LogRecord) -> None:
        if len(self.entries) < self.limit:
            self.entries.append(record_dict(record))

    def __enter__(self) -> TickCollector:
        jobs = logging.getLogger("jobs")
        self._previous_level = jobs.level
        if jobs.getEffectiveLevel() > logging.INFO:
            jobs.setLevel(logging.INFO)
        jobs.addHandler(self)
        return self

    def __exit__(self, *_exc: object) -> None:
        jobs = logging.getLogger("jobs")
        jobs.removeHandler(self)
        jobs.setLevel(self._previous_level)
