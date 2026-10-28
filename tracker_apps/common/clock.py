from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time

from django.utils import timezone


class Clock:
    """Single source of "today"/"now" so overdue logic and tests are deterministic."""

    _override_day: date | None = None

    @classmethod
    def today(cls) -> date:
        return cls._override_day or timezone.localdate()

    @classmethod
    def now(cls) -> datetime:
        if cls._override_day is None:
            return timezone.now()
        return timezone.make_aware(datetime.combine(cls._override_day, time.min))

    @classmethod
    @contextmanager
    def override(cls, day: date) -> Iterator[None]:
        previous = cls._override_day
        cls._override_day = day
        try:
            yield
        finally:
            cls._override_day = previous
