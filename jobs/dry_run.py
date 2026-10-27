"""Fetches one real week of reference prices and next week's stats into a local JSON file
(not committed, no database).

    python -m jobs.dry_run --week 2026-10-19 --out /tmp/week.json
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from engine.calendar import phase_timestamps
from jobs.market import as_dicts, load_catalogue, reference_week, week_stats
from jobs.prices import default_provider


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--week", type=date.fromisoformat, required=True, help="Monday")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    catalogue, provider = load_catalogue(), default_provider()
    reference = reference_week(provider, catalogue, args.week)
    stats = week_stats(provider, catalogue, args.week + timedelta(days=7))
    timestamps = phase_timestamps(args.week)
    payload = {
        "week": args.week.isoformat(),
        "phase_timestamps": {k: v.isoformat() for k, v in asdict(timestamps).items()},
        "reference_prices": as_dicts(reference),
        "next_week_stats": as_dicts(stats),
    }
    args.out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    missing = [r for r in reference if r.missing]
    zone = [s.ticker for s in stats if s.in_conflict_zone]
    sources = sorted({r.source or "none" for r in reference})
    print(f"{len(reference)} instruments, {len(missing)} with missing prices, sources {sources}")
    print(f"next week's Conflict Zone: {', '.join(zone)}")
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
