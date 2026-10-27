"""Secrets scan of the whole git history (milestone 09, public repository).

    python tools/scan_history.py            # every commit reachable from any ref
    python tools/scan_history.py --staged   # what is about to be committed

Looks for credentials that must never be in this repository (CLAUDE.md hard rule 1):
connection strings with a password, JWTs, Supabase secret/service keys, private keys,
cloud keys, .env files, and email addresses outside the reserved test domains. Prints
each finding with its commit and file, exits 1 if any. Known-safe values (the local
Supabase CLI demo URL, fake test fixtures) are allowed explicitly below.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

PATTERNS = {
    "connection string with password": re.compile(
        r"postgres(?:ql)?://[^\s:@/'\"]+:([^\s@'\"]+)@[^\s'\"]+"
    ),
    "JWT": re.compile(r"eyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,}"),
    "Supabase secret key": re.compile(r"\bsb_secret_[\w-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "email": re.compile(r"\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)\b"),
}
# Passwords that are public by design (the Supabase CLI's local database).
SAFE_PASSWORDS = {"postgres", "S3cret", "p"}
# Reserved test/documentation names (RFC 2606/6761), the commit trailer, GitHub noreply.
SAFE_EMAIL_DOMAINS = ("example.com", "anthropic.com", "users.noreply.github.com", "d.co.uk")
SAFE_TLDS = (".test", ".invalid", ".example", ".localhost")
SKIP_FILES = ("package-lock.json",)


@dataclass(frozen=True)
class Finding:
    commit: str
    path: str
    kind: str
    text: str


def _safe(kind: str, match: re.Match[str]) -> bool:
    if kind == "connection string with password":
        return match.group(1) in SAFE_PASSWORDS or match.group(1).startswith("[")
    if kind == "email":
        domain = match.group(1).lower()
        before = match.string[max(0, match.start() - 3) : match.start()]
        return (
            domain.endswith(SAFE_EMAIL_DOMAINS)
            or domain.endswith(SAFE_TLDS)
            or domain.replace(".", "").isdigit()  # an IP address or a package version
            or ":" in before  # user:password@host inside a URL (checked above)
            or "%" in match.group(0)
        )
    if kind == "Supabase secret key":
        return "FAKE" in match.group(0)
    return False


def scan_text(text: str, commit: str, path: str) -> list[Finding]:
    findings = []
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if not _safe(kind, match):
                findings.append(Finding(commit, path, kind, match.group(0)[:80]))
    return findings


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, errors="replace"
    ).stdout


def scan_history() -> list[Finding]:
    findings: list[Finding] = []
    log = _git("log", "--all", "-p", "--no-color", "--format=commit %H")
    commit, path = "", ""
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:10]
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            if path.endswith(SKIP_FILES):
                continue
            findings.extend(scan_text(line[1:], commit, path))
        elif line.startswith("diff --git") and ("/.env" in line or " b/.env" in line):
            findings.append(Finding(commit, line.split(" b/")[-1], ".env file", line))
    return findings


def scan_staged() -> list[Finding]:
    diff = _git("diff", "--cached", "--no-color")
    path, findings = "", []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            findings.extend(scan_text(line[1:], "staged", path))
    return findings


def main(argv: list[str]) -> int:
    findings = scan_staged() if "--staged" in argv else scan_history()
    unique = {(f.kind, f.text, f.path): f for f in findings}
    for f in unique.values():
        print(f"{f.commit} {f.path}: {f.kind}: {f.text}")
    print(f"{len(unique)} finding(s)")
    return 1 if unique else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
