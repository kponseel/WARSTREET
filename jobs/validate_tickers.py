"""Checks every ticker of data/instruments.csv against the price provider.

    python -m jobs.validate_tickers [--days 10]

Prints one line per ticker (OK / MISSING / WRONG CURRENCY) and a summary. Never drops a
ticker: a failure is reported and the exit code is 1.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date, timedelta

from jobs.market import CatalogueEntry, load_catalogue
from jobs.prices import PriceProvider, default_provider


def check(
    provider: PriceProvider, entries: list[CatalogueEntry], end: date, days: int
) -> list[str]:
    lines = []
    for entry in entries:
        history = provider.history(entry.ticker, end - timedelta(days=days), end)
        source = getattr(provider, "last_source", provider.name)
        if history is None or not history.closes:
            status, detail = "MISSING", "no daily bars"
        elif history.currency and history.currency.upper() != entry.currency.upper():
            status, detail = (
                "WRONG CURRENCY",
                f"provider {history.currency}, catalogue {entry.currency}",
            )
        else:
            last_day = max(history.closes)
            status, detail = "OK", f"{len(history.closes)} bars, last {last_day} via {source}"
        lines.append(f"{entry.ticker:<11} {entry.calendar_mic:<5} {status:<15} {detail}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the instrument catalogue")
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    lines = check(default_provider(), load_catalogue(), args.end, args.days)
    print("\n".join(lines))
    failures = [line for line in lines if " OK " not in line]
    print(f"\n{len(lines) - len(failures)} OK, {len(failures)} problem(s) out of {len(lines)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
