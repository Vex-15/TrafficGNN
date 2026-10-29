"""Small text/date helpers shared by the extraction and template engines."""

import re
from datetime import date, datetime
from difflib import SequenceMatcher

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

DATE_PATTERNS = [
    r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b",
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b",
    r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
]


def clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    return re.sub(r"\s+", " ", str(value)).strip()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def similarity(a: str, b: str) -> float:
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _month(name: str):
    return MONTHS.get(name.lower().rstrip("."))


def _safe_date(y, m, d):
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except (TypeError, ValueError):
        return None


def parse_date(text: str):
    """Return an ISO date string if `text` contains a recognisable date."""
    text = clean(text)
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue
        g = m.groups()
        if pattern == DATE_PATTERNS[0]:
            return _safe_date(g[0], g[1], g[2])
        if pattern == DATE_PATTERNS[1]:
            day, month, year = int(g[0]), int(g[1]), int(g[2])
            if day > 12 and month <= 12:
                return _safe_date(year, month, day)
            return _safe_date(year, month, day)
        if pattern == DATE_PATTERNS[2]:
            month = _month(g[1])
            return _safe_date(g[2], month, g[0]) if month else None
        month = _month(g[0])
        return _safe_date(g[2], month, g[1]) if month else None
    return None


def parse_date_range(text: str):
    """Return (start, end) for values like '10-14 August 2026' or 'Aug 10-14, 2026'."""
    text = clean(text)
    if not text:
        return None, None

    m = re.search(
        r"\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})", text
    )
    if m:
        month = _month(m.group(3))
        return _safe_date(m.group(4), month, m.group(1)), _safe_date(m.group(4), month, m.group(2))

    m = re.search(
        r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2}),?\s+(\d{4})", text
    )
    if m:
        month = _month(m.group(1))
        return _safe_date(m.group(4), month, m.group(2)), _safe_date(m.group(4), month, m.group(3))

    single = parse_date(text)
    return single, single


def parse_number(text):
    m = re.search(r"\b(\d{1,5})\b", clean(text))
    return int(m.group(1)) if m else None


def initials_name(text: str) -> str:
    """Pull 'Dr. A. Sharma' style names out of free text."""
    m = re.search(
        r"\b(?:Dr|Prof|Mr|Ms|Mrs|Sri|Smt)\.?\s+[A-Z][A-Za-z.]*"
        r"(?:\s+[A-Z][A-Za-z.]*){0,3}",
        text,
    )
    return m.group(0).strip() if m else ""


def human_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return iso


def format_range(start, end):
    if start and end and start != end:
        return f"{human_date(start)} – {human_date(end)}"
    return human_date(start or end or "")
