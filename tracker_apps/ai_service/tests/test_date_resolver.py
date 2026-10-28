from datetime import date

from django.test import SimpleTestCase

from tracker_apps.ai_service.date_resolver import DateResolver

TUESDAY = date(2026, 7, 28)


class DateResolverTests(SimpleTestCase):
    def resolve(self, text: str, meeting_date: date = TUESDAY) -> date | None:
        return DateResolver.resolve(text, meeting_date)

    def test_bare_weekday_is_first_such_day_strictly_after_the_meeting(self) -> None:
        self.assertEqual(self.resolve("by Friday"), date(2026, 7, 31))
        self.assertEqual(self.resolve("by Wednesday"), date(2026, 7, 29))
        self.assertEqual(self.resolve("on Thursday afternoon"), date(2026, 7, 30))
        self.assertEqual(self.resolve("Monday"), date(2026, 8, 3))

    def test_same_weekday_as_the_meeting_means_a_week_later(self) -> None:
        self.assertEqual(self.resolve("Tuesday"), date(2026, 8, 4))

    def test_next_weekday_is_that_day_in_the_following_calendar_week(self) -> None:
        self.assertEqual(self.resolve("by next Tuesday"), date(2026, 8, 4))
        self.assertEqual(self.resolve("next Friday"), date(2026, 8, 7))
        self.assertEqual(self.resolve("next Monday"), date(2026, 8, 3))

    def test_next_weekday_from_a_sunday_meeting_uses_the_calendar_week_after(self) -> None:
        self.assertEqual(self.resolve("next Monday", date(2026, 8, 2)), date(2026, 8, 3))
        self.assertEqual(self.resolve("next Friday", date(2026, 8, 2)), date(2026, 8, 7))

    def test_today_and_tomorrow(self) -> None:
        self.assertEqual(self.resolve("today"), TUESDAY)
        self.assertEqual(self.resolve("tomorrow"), date(2026, 7, 29))

    def test_vague_phrases_are_not_resolved(self) -> None:
        for text in ("end of next week", "by the end of next week", "soon", "after the review is done", "next week",
                     "later", "when ready", "once the architecture is ready", "ASAP", "next month", "", "sometime"):
            with self.subTest(text=text):
                self.assertIsNone(self.resolve(text))

    def test_ambiguous_weekdays_are_not_resolved(self) -> None:
        self.assertIsNone(self.resolve("Monday or Tuesday"))

    def test_explicit_dates_are_taken_as_written(self) -> None:
        self.assertEqual(self.resolve("by 2026-08-15"), date(2026, 8, 15))
        self.assertEqual(self.resolve("on 5 August 2026"), date(2026, 8, 5))
        self.assertEqual(self.resolve("August 5, 2026"), date(2026, 8, 5))

    def test_impossible_or_multiple_explicit_dates_are_not_resolved(self) -> None:
        self.assertIsNone(self.resolve("2026-02-30"))
        self.assertIsNone(self.resolve("2026-08-01 or 2026-08-02"))

    def test_parse_iso_is_strict(self) -> None:
        self.assertEqual(DateResolver.parse_iso("2026-07-31"), date(2026, 7, 31))
        for bad in ("2026-02-30", "31-07-2026", "2026-7-3", "2026-07-31T00:00", "tomorrow", ""):
            with self.subTest(bad=bad):
                self.assertIsNone(DateResolver.parse_iso(bad))
