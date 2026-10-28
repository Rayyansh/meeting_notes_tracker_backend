import re
from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({'|'.join(MONTHS)})\s+(\d{{4}})\b")
MONTH_DAY_YEAR = re.compile(rf"\b({'|'.join(MONTHS)})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b")
UNRESOLVABLE = re.compile(r"\bend of\b|\bafter\b|\bonce\b|\bwhen\b|\bsoon\b|\blater\b|\beventually\b|\basap\b|\b(?:next|this) (?:week|month)\b|\bnext (?:phase|release)\b")
WEEKDAY_WORD = re.compile(rf"\b({'|'.join(WEEKDAYS)})\b")


class DateResolver:
    """Deterministic relative-date rules. Anything not covered here returns None; it is never guessed.

    - "today" is the meeting date, "tomorrow" the day after.
    - A bare weekday is the first such weekday strictly after the meeting date.
    - "next <weekday>" is that weekday in the following calendar week (weeks start on Monday).
    - Explicit dates (YYYY-MM-DD, "5 August 2026", "August 5, 2026") are taken as written.
    - "end of next week", "soon", "after X is ready" and similar are not resolvable.
    """

    @staticmethod
    def resolve(text: str, meeting_date: date) -> date | None:
        lowered = text.lower()
        explicit = DateResolver.explicit_date(lowered)
        if explicit is not None:
            return explicit
        if UNRESOLVABLE.search(lowered):
            return None
        if re.search(r"\btoday\b", lowered):
            return meeting_date
        if re.search(r"\btomorrow\b", lowered):
            return meeting_date + timedelta(days=1)
        weekdays = WEEKDAY_WORD.findall(lowered)
        if len(set(weekdays)) != 1:
            return None
        target = WEEKDAYS.index(weekdays[0])
        if re.search(r"\bnext\s+" + weekdays[0], lowered):
            monday_of_next_week = meeting_date - timedelta(days=meeting_date.weekday()) + timedelta(days=7)
            return monday_of_next_week + timedelta(days=target)
        return meeting_date + timedelta(days=(target - meeting_date.weekday()) % 7 or 7)

    @staticmethod
    def explicit_date(lowered: str) -> date | None:
        candidates: list[tuple[int, int, int]] = []
        for match in ISO_DATE.finditer(lowered):
            candidates.append((int(match.group(1)), int(match.group(2)), int(match.group(3))))
        for match in DAY_MONTH_YEAR.finditer(lowered):
            candidates.append((int(match.group(3)), MONTHS.index(match.group(2)) + 1, int(match.group(1))))
        for match in MONTH_DAY_YEAR.finditer(lowered):
            candidates.append((int(match.group(3)), MONTHS.index(match.group(1)) + 1, int(match.group(2))))
        if len(candidates) != 1:
            return None
        year, month, day = candidates[0]
        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def parse_iso(value: str) -> date | None:
        """Strict YYYY-MM-DD that is a real calendar date."""
        match = ISO_DATE.fullmatch(value)
        if match is None:
            return None
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
