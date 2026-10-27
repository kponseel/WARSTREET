"""Job logging: context fields, redaction, JSON lines, tick collector."""

from __future__ import annotations

import base64
import json
import logging

import pytest

from jobs.logs import (
    JsonFormatter,
    TextFormatter,
    TickCollector,
    log_context,
    redact,
    setup_logging,
)

# A made-up token with the shape of a JWT (base64url header.payload.signature).
FAKE_JWT = ".".join(
    base64.urlsafe_b64encode(part).decode().rstrip("=")
    for part in (b'{"fake":"header"}', b'{"fake":"payload"}', b"not-a-real-signature")
)


@pytest.mark.parametrize(
    ("text", "leak"),
    [
        (
            "connect postgresql://postgres.abc:S3cret@aws-0.pooler.supabase.com:5432/postgres",
            "S3cret",
        ),
        (f"token {FAKE_JWT}", "eyJmYWtl"),
        ("user jane.player@mail.example joined", "jane.player"),
        ("key sb_secret_FAKEfakeFAKEfake123", "FAKEfake"),
        ("PASSWORD=hunter2 in env", "hunter2"),
    ],
)
def test_redact_removes_secrets_and_emails(text: str, leak: str) -> None:
    assert leak not in redact(text)


def test_context_is_attached_and_nested(caplog: pytest.LogCaptureFixture) -> None:
    with TickCollector() as collector:
        log = logging.getLogger("jobs.test")
        with log_context(league="abcd1234", week="2026-11-09"), log_context(transition="lock"):
            log.info("done for a@b.test")
        log.info("outside")
    first, second = collector.entries
    assert first["league"] == "abcd1234" and first["transition"] == "lock"
    assert first["msg"] == "done for [email]"
    assert "league" not in second


def test_formatters() -> None:
    record = logging.LogRecord("jobs.x", logging.WARNING, __file__, 1, "price %s", ("late",), None)
    record.ctx = {"league": "l1"}
    entry = json.loads(JsonFormatter().format(record))
    assert entry["level"] == "warning" and entry["msg"] == "price late" and entry["league"] == "l1"
    assert TextFormatter().format(record).endswith("jobs.x: price late [league=l1]")


def test_setup_logging_replaces_handlers() -> None:
    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    try:
        setup_logging("json")
        assert len(root.handlers) == 1 and isinstance(root.handlers[0].formatter, JsonFormatter)
        setup_logging("text")
        assert isinstance(root.handlers[0].formatter, TextFormatter)
    finally:
        root.handlers[:] = saved
        root.setLevel(level)
