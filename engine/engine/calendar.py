"""Exchange calendars and the week's timestamps (GAME_RULES §2).

Market hours are never hardcoded: sessions, opens and closes come from
`exchange_calendars`, which knows holidays, half days and daylight-saving changes.
All returned instants are timezone-aware UTC datetimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from functools import cache
from typing import Any
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

from engine import config

MICS = ("XPAR", "XETR", "XAMS", "XMIL", "XMAD", "XHEL", "XCSE", "XNYS")
US_MIC = "XNYS"
CALENDAR_START = "2020-01-01"
CALENDAR_END = "2030-12-31"
THURSDAY = 3  # days after Monday


@cache
def _calendar(mic: str) -> Any:
    return xcals.get_calendar(mic, start=CALENDAR_START, end=CALENDAR_END)


def _utc(value: Any) -> datetime:
    return value.to_pydatetime().astimezone(UTC)


def check_monday(monday: date) -> None:
    if monday.weekday() != 0:
        raise ValueError(f"{monday} is not a Monday")


def week_sessions(mic: str, monday: date) -> list[date]:
    """Trading sessions of the exchange from Monday to Friday of that week."""
    check_monday(monday)
    sessions = _calendar(mic).sessions_in_range(monday, monday + timedelta(days=4))
    return [s.date() for s in sessions]


def session_open(mic: str, session: date) -> datetime:
    return _utc(_calendar(mic).session_open(session))


def session_close(mic: str, session: date) -> datetime:
    return _utc(_calendar(mic).session_close(session))


@dataclass(frozen=True, slots=True)
class SegmentSessions:
    """The sessions that give P0 (first open), P_mid (first open on or after Thursday) and
    P_end (last close) for one exchange and week. None when the exchange has no session."""

    p0: date | None
    p_mid: date | None
    p_end: date | None


def segment_sessions(mic: str, monday: date) -> SegmentSessions:
    sessions = week_sessions(mic, monday)
    thursday = monday + timedelta(days=THURSDAY)
    from_thursday = [s for s in sessions if s >= thursday]
    return SegmentSessions(
        p0=sessions[0] if sessions else None,
        p_mid=from_thursday[0] if from_thursday else None,
        p_end=sessions[-1] if sessions else None,
    )


def first_open(mic: str, monday: date) -> datetime | None:
    p0 = segment_sessions(mic, monday).p0
    return session_open(mic, p0) if p0 else None


def first_open_from_thursday(mic: str, monday: date) -> datetime | None:
    p_mid = segment_sessions(mic, monday).p_mid
    return session_open(mic, p_mid) if p_mid else None


def last_close(mic: str, monday: date) -> datetime | None:
    p_end = segment_sessions(mic, monday).p_end
    return session_close(mic, p_end) if p_end else None


def local_instant(day: date, local_time: str) -> datetime:
    """A Paris wall-clock time on a given day, as a UTC instant."""
    wall = datetime.combine(day, time.fromisoformat(local_time), ZoneInfo(config.TIMEZONE))
    return wall.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class PhaseTimestamps:
    lock_at: datetime
    resupply_opens_at: datetime
    resupply_closes_at: datetime
    debrief_at: datetime


def phase_timestamps(monday: date) -> PhaseTimestamps:
    """The four phase boundaries of a league week (GAME_RULES §2), in UTC."""
    check_monday(monday)
    us_sessions = week_sessions(US_MIC, monday)
    wednesday = monday + timedelta(days=THURSDAY - 1)
    early = [s for s in us_sessions if s <= wednesday]
    if early:
        resupply_opens = session_close(US_MIC, early[-1]) + timedelta(
            minutes=config.RESUPPLY_OPEN_DELAY_MIN
        )
    else:
        resupply_opens = local_instant(wednesday, config.RESUPPLY_OPEN_FALLBACK_LOCAL_TIME)
    if not us_sessions:
        raise ValueError(f"no {US_MIC} session in the week of {monday}")
    debrief = session_close(US_MIC, us_sessions[-1]) + timedelta(minutes=config.DEBRIEF_DELAY_MIN)
    return PhaseTimestamps(
        lock_at=local_instant(monday - timedelta(days=1), config.LOCK_LOCAL_TIME),
        resupply_opens_at=resupply_opens,
        resupply_closes_at=local_instant(
            monday + timedelta(days=THURSDAY), config.RESUPPLY_CLOSE_LOCAL_TIME
        ),
        debrief_at=debrief,
    )


def dividend_segment(sessions: SegmentSessions, ex_date: date) -> str | None:
    """Which segment a dividend belongs to: the one in which its price drop is observed,
    i.e. ex-date strictly after the segment's start session and on or before its end
    session (GAME_RULES §2). Returns "s1", "s2" or None (outside the week)."""
    if sessions.p0 is None or sessions.p_end is None:
        return None
    if sessions.p_mid is not None:
        if sessions.p0 < ex_date <= sessions.p_mid:
            return "s1"
        if sessions.p_mid < ex_date <= sessions.p_end:
            return "s2"
        return None
    # No session on or after Thursday: the whole week is S1.
    return "s1" if sessions.p0 < ex_date <= sessions.p_end else None


def week_monday(instant: datetime) -> date:
    """The Monday of the Paris-local week containing an instant."""
    local = instant.astimezone(ZoneInfo(config.TIMEZONE)).date()
    return local - timedelta(days=local.weekday())
