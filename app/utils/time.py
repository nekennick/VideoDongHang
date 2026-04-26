from __future__ import annotations

from datetime import datetime, timezone, timedelta


LOCAL_TZ = timezone(timedelta(hours=7))


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def iso_now() -> str:
    return now_local().isoformat(timespec="seconds")


def today_text() -> str:
    return now_local().date().isoformat()

