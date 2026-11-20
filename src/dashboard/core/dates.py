"""Dates the household's way: typed and shown as 20/05/27 or 05/20/27, always stored as 2027-05-20.

The household's country decides the order (decision 0052). Stored dates never change when the
country does; only how they are typed and shown. A date written the international way
(2027-05-20) is understood in every country.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date

DAY_FIRST, MONTH_FIRST, YEAR_FIRST = "dmy", "mdy", "ymd"
MONTH_FIRST_COUNTRIES = {"United States"}
YEAR_FIRST_COUNTRIES = {"Canada"}  # Canada's official advice is the international order
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
HINTS = {DAY_FIRST: "Day / month / year (DD/MM/YY)", MONTH_FIRST: "Month / day / year (MM/DD/YY)",
         YEAR_FIRST: "Year-month-day (YYYY-MM-DD)"}
SHORT = {DAY_FIRST: "DD/MM/YY", MONTH_FIRST: "MM/DD/YY", YEAR_FIRST: "YYYY-MM-DD"}
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_TYPED = re.compile(r"^(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2}|\d{4})$")


def style_for(country: str | None) -> str:
    """How a household in this country writes dates. Anywhere else, day first, like most of the world."""
    if country in MONTH_FIRST_COUNTRIES:
        return MONTH_FIRST
    if country in YEAR_FIRST_COUNTRIES:
        return YEAR_FIRST
    return DAY_FIRST


def household_style(conn: sqlite3.Connection) -> str:
    from dashboard.core import settings  # here, so this module stays usable without a database
    return style_for(settings.get(conn, "household.country"))


def problem(style: str) -> str:
    return f"Enter a real date in {SHORT[style]} format."


def parse(text: str, style: str) -> str:
    """The stored form (2027-05-20) of a typed date, or ValueError with a plain message.

    Two-digit years mean 2000 to 2099 (27 is 2027, never 1927); type four digits for other years.
    Impossible dates such as 31/04/27 are refused, never rolled over into the next month."""
    text = (text or "").strip()
    match = _ISO.match(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
    else:
        match = _TYPED.match(text)
        if not match or style == YEAR_FIRST:  # 05/06/27 is a guess either way where neither order is usual
            raise ValueError(problem(style))
        first, second, year_text = match.groups()
        day, month = (int(first), int(second)) if style != MONTH_FIRST else (int(second), int(first))
        year = int(year_text) + (2000 if len(year_text) == 2 else 0)
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        raise ValueError(problem(style)) from None


def ambiguous(text: str, style: str) -> str | None:
    """The stored date a short typed date is read as, when the other order would give a different real date.

    "1/2/27" is 1 February day first and 2 January month first, so it is returned (as 2027-02-01 day first); "20/05/27"
    and "5/5/27" are never in doubt, and neither is the international form 2027-05-20. Otherwise None."""
    match = _TYPED.match((text or "").strip())
    if not match or style == YEAR_FIRST:
        return None
    first, second = int(match.group(1)), int(match.group(2))
    if first == second or not (1 <= first <= 12 and 1 <= second <= 12):
        return None
    try:
        return parse(text, style)
    except ValueError:
        return None


def show(value, style: str) -> str:
    """A stored date as the household reads it: 20/05/27, 05/20/27 or 2027-05-20."""
    when = value if isinstance(value, date) else _stored(value)
    if when is None:
        return str(value or "")
    if style == YEAR_FIRST:
        return when.isoformat()
    first, second = (when.day, when.month) if style == DAY_FIRST else (when.month, when.day)
    return f"{first:02d}/{second:02d}/{when.year % 100:02d}" if 2000 <= when.year <= 2099 else \
        f"{first:02d}/{second:02d}/{when.year}"


def long(value, style: str) -> str:
    """A date in words, with no doubt about the order: 1 February 2027, or February 1, 2027 in the US."""
    when = value if isinstance(value, date) else _stored(value)
    if when is None:
        return ""
    if style == MONTH_FIRST:
        return f"{MONTHS[when.month - 1]} {when.day}, {when.year}"
    return f"{when.day} {MONTHS[when.month - 1]} {when.year}"


def _stored(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def is_stored(text: str) -> bool:
    """True for a date already in the stored form, 2027-05-20."""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", text.strip()))


REPEAT_UNITS = ("weeks", "months", "years")


def add_period(start, count: int, unit: str) -> str:
    """The stored date `count` weeks, months or years after `start`, on the calendar (decision 0091).

    Weeks are seven days each. Months and years keep the day of the month, or use the month's last day
    when it has no such day: 31 January plus one month is 28 February (29 in a leap year), and 29 February
    plus one year is 28 February. Only dates are involved, so no time of day or time zone can move it."""
    when = start if isinstance(start, date) else date.fromisoformat(str(start)[:10])
    if unit == "weeks":
        return date.fromordinal(when.toordinal() + 7 * count).isoformat()
    months = count * (12 if unit == "years" else 1) if unit in ("months", "years") else None
    if months is None:
        raise ValueError(f"'{unit}' is not weeks, months or years.")
    index = when.year * 12 + (when.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    following = date(year + (month == 12), month % 12 + 1, 1)
    last = date.fromordinal(following.toordinal() - 1).day
    return date(year, month, min(when.day, last)).isoformat()
