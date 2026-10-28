from datetime import date, timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext

from tracker.constants import Constants
from tracker_apps.action_item.choices import Priority, Source, Status
from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.common.clock import Clock
from tracker_apps.common.tests_utils import ApiTestCase
from tracker_apps.meeting.models.meeting import Meeting

SUMMARY_URL = "/dashboard/summary/"
TODAY = date(2026, 7, 28)
COUNT_KEYS = (
    "totalMeetings", "totalActionItems", "openActionItems", "inProgressActionItems", "blockedActionItems",
    "completedActionItems", "unfinishedActionItems", "overdueActionItems",
)


class DashboardTestCase(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user(email="a@example.com")
        self.other = self.create_user(email="b@example.com")
        self.authenticate(self.user)

    def make_meeting(self, owner=None, **overrides: object) -> Meeting:
        fields = {"owner": owner or self.user, "title": "Meeting", "meeting_date": TODAY, "meeting_type": "Other", "participants": [], "transcript": "Ana: hi"}
        fields.update(overrides)
        return Meeting.objects.create(**fields)

    def make_item(self, meeting: Meeting, **overrides: object) -> ActionItem:
        fields = {"meeting": meeting, "description": "Task", "source": Source.MANUAL}
        fields.update(overrides)
        return ActionItem.objects.create(**fields)

    def summary(self) -> dict:
        return self.assert_success_envelope(self.client.get(SUMMARY_URL))["data"]

    def seed(self) -> Meeting:
        """A mixed set of items for the caller, plus a larger set that belongs to someone else."""
        meeting = self.make_meeting(title="Mine")
        yesterday, tomorrow = TODAY - timedelta(days=1), TODAY + timedelta(days=1)
        self.make_item(meeting, description="open overdue", status=Status.OPEN, due_date=yesterday, priority=Priority.HIGH)
        self.make_item(meeting, description="in progress overdue", status=Status.IN_PROGRESS, due_date=TODAY - timedelta(days=10), priority=Priority.MEDIUM)
        self.make_item(meeting, description="blocked future", status=Status.BLOCKED, due_date=tomorrow, priority=Priority.LOW)
        self.make_item(meeting, description="completed past", status=Status.COMPLETED, due_date=yesterday, priority=Priority.HIGH)
        self.make_item(meeting, description="open today", status=Status.OPEN, due_date=TODAY)
        self.make_item(meeting, description="open undated", status=Status.OPEN)
        theirs = self.make_meeting(owner=self.other, title="Theirs")
        for index in range(8):
            self.make_item(theirs, description=f"their {index}", status=Status.OPEN, due_date=yesterday, priority=Priority.HIGH)
        return meeting


class DashboardAccessTests(DashboardTestCase):
    def test_requires_authentication(self) -> None:
        self.client.force_authenticate(None)
        self.assert_error_envelope(self.client.get(SUMMARY_URL), 401)

    def test_only_get_is_allowed(self) -> None:
        for method in (self.client.post, self.client.put, self.client.delete):
            self.assert_error_envelope(method(SUMMARY_URL), 405)

    def test_empty_account_is_200_with_zeros_and_empty_lists(self) -> None:
        data = self.summary()
        for key in COUNT_KEYS:
            self.assertEqual(data[key], 0, key)
        self.assertEqual(data["actionItemsByPriority"], {"Low": 0, "Medium": 0, "High": 0})
        self.assertEqual((data["recentMeetings"], data["upcomingActionItems"]), ([], []))

    def test_envelope_and_message(self) -> None:
        body = self.assert_success_envelope(self.client.get(SUMMARY_URL))
        self.assertEqual(body["message"], Constants.dashboard_success)


class DashboardCountTests(DashboardTestCase):
    def test_counts_match_direct_orm_counts(self) -> None:
        self.seed()
        with Clock.override(TODAY):
            data = self.summary()
        mine = ActionItem.objects.owned_by(self.user)
        self.assertEqual(data["totalMeetings"], Meeting.objects.filter(owner=self.user).count())
        self.assertEqual(data["totalActionItems"], mine.count())
        self.assertEqual(data["openActionItems"], mine.filter(status="Open").count())
        self.assertEqual(data["inProgressActionItems"], mine.filter(status="In Progress").count())
        self.assertEqual(data["blockedActionItems"], mine.filter(status="Blocked").count())
        self.assertEqual(data["completedActionItems"], mine.filter(status="Completed").count())
        self.assertEqual(data["unfinishedActionItems"], mine.exclude(status="Completed").count())
        for priority in ("Low", "Medium", "High"):
            self.assertEqual(data["actionItemsByPriority"][priority], mine.filter(priority=priority).count())

    def test_known_values_for_the_seeded_data(self) -> None:
        self.seed()
        with Clock.override(TODAY):
            data = self.summary()
        self.assertEqual(
            {key: data[key] for key in COUNT_KEYS},
            {"totalMeetings": 1, "totalActionItems": 6, "openActionItems": 3, "inProgressActionItems": 1, "blockedActionItems": 1,
             "completedActionItems": 1, "unfinishedActionItems": 5, "overdueActionItems": 2},
        )
        self.assertEqual(data["actionItemsByPriority"], {"Low": 1, "Medium": 3, "High": 2})

    def test_status_counts_add_up_to_the_total(self) -> None:
        self.seed()
        data = self.summary()
        status_sum = data["openActionItems"] + data["inProgressActionItems"] + data["blockedActionItems"] + data["completedActionItems"]
        self.assertEqual(status_sum, data["totalActionItems"])
        self.assertEqual(data["unfinishedActionItems"] + data["completedActionItems"], data["totalActionItems"])
        self.assertEqual(sum(data["actionItemsByPriority"].values()), data["totalActionItems"])

    def test_open_means_status_exactly_open_not_unfinished(self) -> None:
        meeting = self.make_meeting()
        self.make_item(meeting, status=Status.OPEN)
        self.make_item(meeting, status=Status.IN_PROGRESS)
        self.make_item(meeting, status=Status.BLOCKED)
        data = self.summary()
        self.assertEqual((data["openActionItems"], data["unfinishedActionItems"]), (1, 3))

    def test_overdue_follows_the_shared_rule_with_the_injected_clock(self) -> None:
        self.seed()
        with Clock.override(TODAY - timedelta(days=1)):
            self.assertEqual(self.summary()["overdueActionItems"], 1)  # only the item 10 days late
        with Clock.override(TODAY):
            self.assertEqual(self.summary()["overdueActionItems"], 2)
        with Clock.override(TODAY + timedelta(days=2)):
            self.assertEqual(self.summary()["overdueActionItems"], 4)  # + today's, + tomorrow's blocked

    def test_overdue_count_equals_the_action_item_list_filter(self) -> None:
        self.seed()
        with Clock.override(TODAY):
            dashboard = self.summary()["overdueActionItems"]
            listed = self.client.get("/action_item/get_all/", {"is_overdue": "true", "limit": 100}).json()["data"]["data"]
            queryset_count = ActionItem.objects.owned_by(self.user).overdue().count()
        self.assertEqual((dashboard, len(listed)), (2, 2))
        self.assertEqual(dashboard, queryset_count)

    def test_completed_items_are_never_overdue(self) -> None:
        meeting = self.make_meeting()
        self.make_item(meeting, status=Status.COMPLETED, due_date=TODAY - timedelta(days=30))
        with Clock.override(TODAY):
            self.assertEqual(self.summary()["overdueActionItems"], 0)

    def test_numbers_update_when_data_changes(self) -> None:
        meeting = self.seed()
        item = ActionItem.objects.get(meeting=meeting, description="open overdue")
        with Clock.override(TODAY):
            before = self.summary()
            self.client.put("/action_item/update/", {"action_item_id": item.action_item_id, "status": "Completed"}, format="json")
            after = self.summary()
            self.client.delete(f"/action_item/delete/?action_item_id={item.action_item_id}")
            deleted = self.summary()
        self.assertEqual((before["openActionItems"], after["openActionItems"]), (3, 2))
        self.assertEqual((before["completedActionItems"], after["completedActionItems"]), (1, 2))
        self.assertEqual((before["overdueActionItems"], after["overdueActionItems"]), (2, 1))
        self.assertEqual((after["totalActionItems"], deleted["totalActionItems"]), (6, 5))

    def test_counts_after_ai_analysis_include_ai_items(self) -> None:
        from tracker_apps.ai_service.tests.helpers import SAMPLE_DATE, SAMPLE_PARTICIPANTS, SAMPLE_TRANSCRIPT

        meeting = self.make_meeting(meeting_date=SAMPLE_DATE, transcript=SAMPLE_TRANSCRIPT, participants=list(SAMPLE_PARTICIPANTS))
        self.client.post("/meeting/analyze/", {"meeting_id": meeting.meeting_id}, format="json")
        data = self.summary()
        self.assertEqual((data["totalActionItems"], data["openActionItems"], data["unfinishedActionItems"]), (7, 7, 7))


class DashboardScopeTests(DashboardTestCase):
    def test_other_users_data_is_never_counted_or_listed(self) -> None:
        self.seed()
        self.authenticate(self.create_user(email="c@example.com"))
        data = self.summary()
        for key in COUNT_KEYS:
            self.assertEqual(data[key], 0, key)
        self.assertEqual((data["recentMeetings"], data["upcomingActionItems"]), ([], []))

    def test_each_user_sees_only_their_own_totals(self) -> None:
        self.seed()
        mine = self.summary()
        self.authenticate(self.other)
        theirs = self.summary()
        self.assertEqual((mine["totalActionItems"], theirs["totalActionItems"]), (6, 8))
        self.assertEqual((mine["totalMeetings"], theirs["totalMeetings"]), (1, 1))
        self.assertEqual([m["title"] for m in theirs["recentMeetings"]], ["Theirs"])
        self.assertTrue(all(i["description"].startswith("their") for i in theirs["upcomingActionItems"]))


class DashboardListTests(DashboardTestCase):
    def test_recent_meetings_are_the_five_newest_first(self) -> None:
        for index in range(7):
            self.make_meeting(title=f"Meeting {index}")
        self.make_meeting(owner=self.other, title="Not mine")
        recent = self.summary()["recentMeetings"]
        self.assertEqual([m["title"] for m in recent], [f"Meeting {i}" for i in (6, 5, 4, 3, 2)])
        self.assertEqual(self.summary()["totalMeetings"], 7)

    def test_recent_meeting_items_have_the_list_shape_without_transcript(self) -> None:
        self.make_meeting()
        item = self.summary()["recentMeetings"][0]
        self.assertEqual(set(item), {"meetingId", "title", "meetingDate", "meetingType", "participants", "analysisStatus", "createdAt", "updatedAt"})

    def test_upcoming_are_the_five_soonest_due_unfinished_items(self) -> None:
        meeting = self.make_meeting(title="Planning")
        for day in (9, 3, 7, 1, 5, 8, 2):
            self.make_item(meeting, description=f"due {day}", due_date=date(2026, 8, day))
        self.make_item(meeting, description="done soon", due_date=date(2026, 7, 1), status=Status.COMPLETED)
        self.make_item(meeting, description="undated")
        upcoming = self.summary()["upcomingActionItems"]
        self.assertEqual([i["description"] for i in upcoming], ["due 1", "due 2", "due 3", "due 5", "due 7"])

    def test_upcoming_includes_overdue_items_first_and_flags_them(self) -> None:
        meeting = self.make_meeting(title="Planning")
        self.make_item(meeting, description="late", due_date=TODAY - timedelta(days=3))
        self.make_item(meeting, description="soon", due_date=TODAY + timedelta(days=3))
        with Clock.override(TODAY):
            upcoming = self.summary()["upcomingActionItems"]
        self.assertEqual([(i["description"], i["isOverdue"]) for i in upcoming], [("late", True), ("soon", False)])
        self.assertEqual(upcoming[0]["meetingTitle"], "Planning")

    def test_upcoming_ties_are_stable(self) -> None:
        meeting = self.make_meeting()
        for index in range(3):
            self.make_item(meeting, description=f"same day {index}", due_date=TODAY)
        self.assertEqual([i["description"] for i in self.summary()["upcomingActionItems"]], ["same day 0", "same day 1", "same day 2"])


class DashboardPerformanceAndSafetyTests(DashboardTestCase):
    def test_query_count_is_constant_regardless_of_data_size(self) -> None:
        self.seed()
        for index in range(30):
            self.make_item(self.make_meeting(title=f"M{index}"), due_date=TODAY + timedelta(days=index))
        with CaptureQueriesContext(connection) as queries:
            self.summary()
        self.assertLessEqual(len(queries), 4, [q["sql"][:80] for q in queries.captured_queries])

    def test_response_leaks_no_internals(self) -> None:
        self.seed()
        text = self.client.get(SUMMARY_URL).content.decode()
        for leaked in ("Traceback", "password", "owner_id", "a@example.com", "transcript"):
            self.assertNotIn(leaked, text)
