"""S38 — the ONE definition of "what date is it, and which dates may a human type".

Two separate problems live here, and they are only in the same module because the
second one is unanswerable without the first.

--------------------------------------------------------------------------------
1. WHAT DATE IS IT
--------------------------------------------------------------------------------

The clinic is in Bangladesh; the server stores UTC. Between 18:00 and 23:59 UTC it is
already TOMORROW in Dhaka, so "today" is a different day depending on which clock you
ask. The doctor portal was asking the wrong one: the prescription form stamped
``new Date().toISOString().slice(0, 10)``, which is the **UTC** date — so a
prescription written between 00:00 and 06:00 Dhaka time was dated YESTERDAY, on the
document a patient carries to a pharmacy. Every date a human sees or types is a Dhaka
date from here on.

⚠ Why a fixed +06:00 offset and not ``ZoneInfo("Asia/Dhaka")``: Windows ships no IANA
tz database, and ``zoneinfo`` raises ``ZoneInfoNotFoundError`` on this project's own
Windows dev machine unless the optional ``tzdata`` package is installed. Adding a
dependency to learn a constant would be the wrong trade: Bangladesh Standard Time is
UTC+06:00 with **no DST** — the single DST experiment ran in 2009 and was abandoned in
2010. A fixed offset is therefore exact, not an approximation, and it works identically
on Windows and Arch with nothing installed.

--------------------------------------------------------------------------------
2. WHICH DATES MAY A HUMAN TYPE  (the S38 date policy)
--------------------------------------------------------------------------------

The human's requirement was "cannot use previous date anywhere". Applied literally that
would corrupt the record, so it is applied by CATEGORY instead. Every date in the system
falls into exactly one of these three, and the category decides the rule:

  A. **SYSTEM / HISTORICAL timestamps** — ``visits.started_at``, ``submitted_at``,
     ``completed_at``, ``audit_log.created_at``, ``prescriptions.created_at``,
     ``documents.created_at``, every date shown in the doctor's timeline.
     → **Never validated, never defaulted, never rewritten.** They record when
     something happened. A past value there is not an error, it is the point. Nothing
     in this module touches them, and no route added in S38 writes one by hand.

  B. **AUTHORED-NOW dates** — the date printed on a prescription.
     → **Must be today** (Dhaka). Backdating is refused (``PAST_DATE``) because a
     prescription is a legal document dated by the act of writing it, and post-dating
     is refused too (``FUTURE_DATE``) — a prescription dated next Tuesday is either a
     typo or an attempt to make one document look like two visits.

  C. **SCHEDULED-FORWARD dates** — a follow-up date, a recall due date.
     → **Must not be in the past** (``PAST_DATE``). Today is allowed (a same-day
     recheck is real). There is no upper bound: a twelve-month recall is legitimate.

The validators return a machine code, never a sentence, so the two portals can render
the message bilingually from their own label maps — the same codes-on-the-wire rule the
risk tiers follow (ADR-0030 f).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

#: Bangladesh Standard Time. Fixed, exact, and dependency-free — see the module
#: docstring for why this is not ``ZoneInfo("Asia/Dhaka")``.
DHAKA_TZ = timezone(timedelta(hours=6), name="Asia/Dhaka")

#: Machine codes returned by the validators. Bilingual sentences live in the portals.
PAST_DATE = "past_date"
FUTURE_DATE = "future_date"
INVALID_DATE = "invalid_date"

#: The three policy categories, named so a reader of a route can say which one applies.
CATEGORY_SYSTEM = "system"        # never validated (A)
CATEGORY_AUTHORED_NOW = "authored_now"  # must equal today (B)
CATEGORY_SCHEDULED = "scheduled"  # must not be in the past (C)


def dhaka_now(*, now: datetime | None = None) -> datetime:
    """The current moment as a Dhaka-local aware datetime.

    ``now`` is injectable so every date rule in the project is testable without
    freezing the system clock.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        # An offset-less value from SQLite is UTC by construction everywhere in this
        # codebase (see services/triage._as_utc for the same pin).
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(DHAKA_TZ)


def dhaka_today(*, now: datetime | None = None) -> date:
    """Today's calendar date in Dhaka — the only "today" a human-facing date uses."""
    return dhaka_now(now=now).date()


def dhaka_today_iso(*, now: datetime | None = None) -> str:
    """``YYYY-MM-DD`` for today in Dhaka; the value a date input is defaulted to."""
    return dhaka_today(now=now).isoformat()


def parse_iso_date(value: str | None) -> date | None:
    """Parse ``YYYY-MM-DD`` leniently. Returns None for blank; raises for garbage.

    Blank is not an error: an optional follow-up date that the doctor left empty is a
    legitimate, common answer, and turning that into a 400 would make the field
    effectively mandatory.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # ``fromisoformat`` also accepts a full timestamp; take the date half so a
        # client that sends "2026-08-14T00:00:00" is not punished for being precise.
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(INVALID_DATE) from exc


def check_authored_now(value: str | None, *, now: datetime | None = None) -> str | None:
    """Category B. Returns a violation code, or None when the date is acceptable.

    A blank value is acceptable here and means "the caller did not supply one" — the
    route stamps today rather than rejecting, so an older client that never sent a date
    keeps working and simply gets the correct one.
    """
    try:
        parsed = parse_iso_date(value)
    except ValueError:
        return INVALID_DATE
    if parsed is None:
        return None
    today = dhaka_today(now=now)
    if parsed < today:
        return PAST_DATE
    if parsed > today:
        return FUTURE_DATE
    return None


def check_scheduled(value: str | None, *, now: datetime | None = None) -> str | None:
    """Category C. Returns a violation code, or None. Today counts as valid."""
    try:
        parsed = parse_iso_date(value)
    except ValueError:
        return INVALID_DATE
    if parsed is None:
        return None
    return PAST_DATE if parsed < dhaka_today(now=now) else None
