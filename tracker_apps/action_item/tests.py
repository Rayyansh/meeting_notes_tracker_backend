from datetime import date, datetime, timedelta, timezone as dt_timezone

from tracker.constants import Constants
from tracker_apps.action_item.choices import Priority, Source, Status
from tracker_apps.action_item.models.action_item import ActionItem
from tracker_apps.action_item.overdue import Overdue
from tracker_apps.ai_service.tests.helpers import SAMPLE_DATE, SAMPLE_PARTICIPANTS, SAMPLE_TRANSCRIPT
from tracker_apps.common.clock import Clock
from tracker_apps.common.tests_utils import ApiTestCase
from tracker_apps.meeting.models.meeting import Meeting

CREATE_URL = "/action_item/create/"
UPDATE_URL = "/action_item/update/"
GET_URL = "/action_item/get/"
GET_ALL_URL = "/action_item/get_all/"
DELETE_URL = "/action_item/delete/"
TODAY = date(2026, 7, 28)


class ActionItemApiTestCase(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user(email="a@example.com")
        self.other = self.create_user(email="b@example.com")
        self.authenticate(self.user)
        self.meeting = self.make_meeting(title="Weekly sync")

    def make_meeting(self, owner=None, **overrides: object) -> Meeting:
        fields = {"owner": owner or self.user, "title": "Meeting", "meeting_date": TODAY, "meeting_type": "Other", "participants": ["Ana"], "transcript": "Ana: hello"}
        fields.update(overrides)
        return Meeting.objects.create(**fields)

    def make_item(self, meeting: Meeting | None = None, **overrides: object) -> ActionItem:
        fields = {"meeting": meeting or self.meeting, "description": "Do the thing", "source": Source.MANUAL}
        fields.update(overrides)
        return ActionItem.objects.create(**fields)

    def payload(self, **overrides: object) -> dict:
        body = {"meeting_id": self.meeting.meeting_id, "description": "Send the report", "owner_name": "Ana", "due_date": "2026-08-01", "due_date_text": "by Saturday", "priority": "High", "status": "In Progress"}
        body.update(overrides)
        return body

    def create(self, **overrides: object) -> dict:
        return self.assert_success_envelope(self.client.post(CREATE_URL, self.payload(**overrides), format="json"), 201)["data"]

    def put(self, item: ActionItem, **body: object):
        return self.client.put(UPDATE_URL, {"action_item_id": item.action_item_id, **body}, format="json")

    def update_ok(self, item: ActionItem, **body: object) -> dict:
        return self.assert_success_envelope(self.put(item, **body))["data"]

    def listed(self, **query: object) -> list[dict]:
        return self.assert_success_envelope(self.client.get(GET_ALL_URL, query))["data"]["data"]

    def descriptions(self, **query: object) -> list[str]:
        return [item["description"] for item in self.listed(**query)]


class ActionItemAuthAndOwnershipTests(ActionItemApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.theirs_meeting = self.make_meeting(owner=self.other, title="Secret board meeting")
        self.theirs = self.make_item(self.theirs_meeting, description="Their secret task", owner_name="Bob")

    def test_every_endpoint_requires_authentication(self) -> None:
        mine = self.make_item()
        self.client.force_authenticate(None)
        calls = [
            self.client.post(CREATE_URL, self.payload(), format="json"),
            self.client.put(UPDATE_URL, {"action_item_id": mine.action_item_id, "description": "x"}, format="json"),
            self.client.get(GET_URL, {"action_item_id": mine.action_item_id}),
            self.client.get(GET_ALL_URL),
            self.client.delete(f"{DELETE_URL}?action_item_id={mine.action_item_id}"),
        ]
        for response in calls:
            self.assert_error_envelope(response, 401)
        self.assertEqual(ActionItem.objects.count(), 2)

    def test_user_cannot_read_another_users_item(self) -> None:
        self.assert_error_envelope(self.client.get(GET_URL, {"action_item_id": self.theirs.action_item_id}), 404)

    def test_user_cannot_update_another_users_item(self) -> None:
        self.assert_error_envelope(self.put(self.theirs, description="Hacked", status="Completed"), 404)
        self.theirs.refresh_from_db()
        self.assertEqual((self.theirs.description, self.theirs.status, self.theirs.is_edited), ("Their secret task", "Open", False))

    def test_user_cannot_delete_another_users_item(self) -> None:
        self.assert_error_envelope(self.client.delete(f"{DELETE_URL}?action_item_id={self.theirs.action_item_id}"), 404)
        self.assertTrue(ActionItem.objects.filter(pk=self.theirs.pk).exists())

    def test_user_cannot_list_or_search_another_users_items(self) -> None:
        self.assertEqual(self.listed(), [])
        self.assertEqual(self.listed(search_key="secret"), [])
        self.assertEqual(self.listed(owner="Bob"), [])

    def test_smuggled_foreign_meeting_id_in_list_returns_empty_not_their_data(self) -> None:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"meeting_id": self.theirs_meeting.meeting_id}))
        self.assertEqual(body["data"]["data"], [])

    def test_cannot_create_an_item_on_another_users_meeting(self) -> None:
        response = self.client.post(CREATE_URL, self.payload(meeting_id=self.theirs_meeting.meeting_id), format="json")
        self.assert_error_envelope(response, 404)
        self.assertEqual(ActionItem.objects.filter(meeting=self.theirs_meeting).count(), 1)

    def test_nonexistent_and_not_owned_ids_are_indistinguishable(self) -> None:
        theirs = self.client.get(GET_URL, {"action_item_id": self.theirs.action_item_id})
        missing = self.client.get(GET_URL, {"action_item_id": 999999})
        self.assertEqual((theirs.status_code, theirs.json()), (missing.status_code, missing.json()))
        a = self.client.post(CREATE_URL, self.payload(meeting_id=self.theirs_meeting.meeting_id), format="json")
        b = self.client.post(CREATE_URL, self.payload(meeting_id=999999), format="json")
        self.assertEqual((a.status_code, a.json()), (b.status_code, b.json()))

    def test_update_cannot_move_an_item_to_another_meeting(self) -> None:
        mine = self.make_item()
        self.update_ok(mine, description="Renamed", meeting_id=self.theirs_meeting.meeting_id)
        mine.refresh_from_db()
        self.assertEqual(mine.meeting_id, self.meeting.meeting_id)

    def test_owned_by_helper_scopes_through_the_meeting_owner(self) -> None:
        mine = self.make_item()
        self.assertEqual(list(ActionItem.objects.owned_by(self.user)), [mine])
        self.assertEqual(list(ActionItem.objects.owned_by(self.other.pk)), [self.theirs])

    def test_meeting_detail_never_includes_another_users_items(self) -> None:
        self.make_item()
        detail = self.client.get("/meeting/get/", {"meeting_id": self.meeting.meeting_id}).json()["data"]
        self.assertEqual([i["description"] for i in detail["actionItems"]], ["Do the thing"])


class ActionItemCrudTests(ActionItemApiTestCase):
    def test_manual_create_returns_camel_case_detail(self) -> None:
        data = self.create()
        self.assertEqual((data["description"], data["ownerName"], data["dueDate"], data["dueDateText"]), ("Send the report", "Ana", "2026-08-01", "by Saturday"))
        self.assertEqual((data["priority"], data["status"], data["source"], data["isEdited"]), ("High", "In Progress", "manual", False))
        self.assertEqual((data["meetingId"], data["meetingTitle"], data["evidenceQuote"], data["completedAt"]), (self.meeting.meeting_id, "Weekly sync", None, None))
        self.assertTrue(data["createdAt"] and data["updatedAt"])

    def test_create_with_only_a_description_uses_sensible_defaults_and_nulls(self) -> None:
        response = self.client.post(CREATE_URL, {"meeting_id": self.meeting.meeting_id, "description": "Just this"}, format="json")
        data = self.assert_success_envelope(response, 201)["data"]
        self.assertEqual((data["priority"], data["status"]), ("Medium", "Open"))
        self.assertEqual((data["ownerName"], data["dueDate"], data["dueDateText"], data["isOverdue"]), (None, None, None, False))

    def test_creating_a_completed_item_sets_completed_at(self) -> None:
        with Clock.override(TODAY):
            data = self.create(status="Completed")
        self.assertEqual(data["completedAt"][:10], "2026-07-28")

    def test_get_returns_the_item(self) -> None:
        item = self.make_item(owner_name="Ana")
        data = self.assert_success_envelope(self.client.get(GET_URL, {"action_item_id": item.action_item_id}))["data"]
        self.assertEqual((data["actionItemId"], data["ownerName"]), (item.action_item_id, "Ana"))

    def test_delete_then_second_delete_is_404(self) -> None:
        item = self.make_item()
        self.assert_success_envelope(self.client.delete(f"{DELETE_URL}?action_item_id={item.action_item_id}"))
        self.assertFalse(ActionItem.objects.filter(pk=item.pk).exists())
        self.assert_error_envelope(self.client.delete(f"{DELETE_URL}?action_item_id={item.action_item_id}"), 404)

    def test_delete_via_json_body_works(self) -> None:
        item = self.make_item()
        self.assert_success_envelope(self.client.delete(DELETE_URL, {"action_item_id": item.action_item_id}, format="json"))

    def test_client_supplied_timestamps_and_source_are_ignored_on_create(self) -> None:
        data = self.create(created_at="2001-01-01T00:00:00Z", updated_at="2001-01-01T00:00:00Z", source="ai", is_edited=True, evidence_quote="x")
        self.assertEqual((data["source"], data["isEdited"], data["evidenceQuote"]), ("manual", False, None))
        self.assertTrue(data["createdAt"].startswith("2026"))

    def test_deleting_a_meeting_removes_its_items(self) -> None:
        self.make_item()
        self.client.delete(f"/meeting/delete/?meeting_id={self.meeting.meeting_id}")
        self.assertEqual(ActionItem.objects.count(), 0)


class ActionItemValidationTests(ActionItemApiTestCase):
    def assert_field_error(self, body: dict, field: str, message: str | None = None) -> None:
        response = self.assert_error_envelope(self.client.post(CREATE_URL, body, format="json"), 400)
        self.assertIn(field, [error["field"] for error in response["error"]])
        if message:
            self.assertIn({"field": field, "message": message}, response["error"])
        self.assertEqual(ActionItem.objects.count(), 0)

    def test_description_required_and_bounded(self) -> None:
        body = self.payload()
        del body["description"]
        self.assert_field_error(body, "description", Constants.action_description_required)
        self.assert_field_error(self.payload(description="   "), "description", Constants.action_description_required)
        self.assert_field_error(self.payload(description="x" * 501), "description", Constants.action_description_too_long)
        self.create(description="x" * 500)

    def test_meeting_id_required_and_well_formed(self) -> None:
        body = self.payload()
        del body["meeting_id"]
        self.assert_field_error(body, "meeting_id")
        for value in ("abc", 0, -1, "1.5"):
            with self.subTest(value=value):
                self.assert_field_error(self.payload(meeting_id=value), "meeting_id")

    def test_bad_enum_values_are_rejected_with_the_allowed_choices(self) -> None:
        self.assert_field_error(self.payload(priority="Urgent"), "priority")
        self.assert_field_error(self.payload(status="Done"), "status")
        self.assert_field_error(self.payload(priority="medium"), "priority")
        response = self.client.post(CREATE_URL, self.payload(status="Done"), format="json").json()
        self.assertIn("In Progress", response["error"][0]["message"])

    def test_bad_dates_are_rejected(self) -> None:
        for value in ("01-08-2026", "2026-13-01", "tomorrow", "2026-02-30"):
            with self.subTest(value=value):
                self.assert_field_error(self.payload(due_date=value), "due_date")

    def test_owner_and_due_text_length_limits(self) -> None:
        self.assert_field_error(self.payload(owner_name="x" * 101), "owner_name", Constants.action_owner_too_long)
        self.assert_field_error(self.payload(due_date_text="x" * 101), "due_date_text", Constants.action_due_text_too_long)

    def test_null_and_blank_optional_fields_are_accepted(self) -> None:
        data = self.create(owner_name="", due_date=None, due_date_text="")
        self.assertEqual((data["ownerName"], data["dueDate"], data["dueDateText"]), (None, None, None))

    def test_update_requires_a_valid_id_and_at_least_one_field(self) -> None:
        item = self.make_item()
        self.assert_error_envelope(self.client.put(UPDATE_URL, {"description": "x"}, format="json"), 400)
        self.assert_error_envelope(self.client.put(UPDATE_URL, {"action_item_id": "abc", "description": "x"}, format="json"), 400)
        body = self.assert_error_envelope(self.client.put(UPDATE_URL, {"action_item_id": item.action_item_id}, format="json"), 400)
        self.assertEqual(body["error"][0]["message"], Constants.action_nothing_to_update)

    def test_update_validates_each_field_like_create(self) -> None:
        item = self.make_item()
        for field, value in (("description", ""), ("priority", "Urgent"), ("status", "Done"), ("due_date", "bad"), ("owner_name", "x" * 101)):
            with self.subTest(field=field):
                body = self.assert_error_envelope(self.put(item, **{field: value}), 400)
                self.assertEqual(body["error"][0]["field"], field)
        item.refresh_from_db()
        self.assertEqual((item.description, item.priority, item.status, item.is_edited), ("Do the thing", "Medium", "Open", False))

    def test_get_and_delete_need_a_valid_id(self) -> None:
        for value in ("abc", "0", "-3"):
            with self.subTest(value=value):
                self.assert_error_envelope(self.client.get(GET_URL, {"action_item_id": value}), 400)
                self.assert_error_envelope(self.client.delete(f"{DELETE_URL}?action_item_id={value}"), 400)
        self.assert_error_envelope(self.client.get(GET_URL), 400)

    def test_validation_messages_hide_internals(self) -> None:
        text = self.client.post(CREATE_URL, self.payload(description=""), format="json").content.decode()
        for leaked in ("Traceback", "serializer", "ValidationError", ".py"):
            self.assertNotIn(leaked, text)


class ActionItemUpdateRuleTests(ActionItemApiTestCase):
    def test_each_field_can_be_updated_and_marks_the_item_edited(self) -> None:
        for field, value in (("description", "New"), ("owner_name", "Zed"), ("due_date", "2026-09-01"), ("due_date_text", "soon"), ("priority", "High"), ("status", "Blocked")):
            with self.subTest(field=field):
                item = self.make_item()
                data = self.update_ok(item, **{field: value})
                item.refresh_from_db()
                self.assertTrue(item.is_edited)
                self.assertTrue(data["isEdited"])
                self.assertEqual(str(getattr(item, field)), value)

    def test_updating_with_identical_values_does_not_mark_edited(self) -> None:
        item = self.make_item(description="Same", priority="Medium", status="Open")
        self.update_ok(item, description="Same", priority="Medium", status="Open")
        item.refresh_from_db()
        self.assertFalse(item.is_edited)

    def test_untouched_fields_stay_as_they_were(self) -> None:
        item = self.make_item(owner_name="Ana", due_date=date(2026, 8, 5), priority="High")
        self.update_ok(item, description="Renamed")
        item.refresh_from_db()
        self.assertEqual((item.owner_name, item.due_date, item.priority), ("Ana", date(2026, 8, 5), "High"))

    def test_completing_sets_completed_at_and_reopening_clears_it(self) -> None:
        item = self.make_item()
        with Clock.override(date(2026, 7, 30)):
            done = self.update_ok(item, status="Completed")
        self.assertEqual(done["completedAt"][:10], "2026-07-30")
        reopened = self.update_ok(item, status="Open")
        self.assertIsNone(reopened["completedAt"])

    def test_other_edits_do_not_move_completed_at(self) -> None:
        item = self.make_item()
        with Clock.override(date(2026, 7, 30)):
            first = self.update_ok(item, status="Completed")["completedAt"]
        with Clock.override(date(2026, 8, 15)):
            second = self.update_ok(item, description="Tidy wording", status="Completed")["completedAt"]
        self.assertEqual(first, second)

    def test_moving_between_open_states_leaves_completed_at_empty(self) -> None:
        item = self.make_item()
        self.assertIsNone(self.update_ok(item, status="In Progress")["completedAt"])
        self.assertIsNone(self.update_ok(item, status="Blocked")["completedAt"])

    def test_explicit_null_clears_the_due_date_and_its_wording(self) -> None:
        item = self.make_item(due_date=date(2026, 8, 5), due_date_text="by Wednesday")
        data = self.update_ok(item, due_date=None)
        self.assertEqual((data["dueDate"], data["dueDateText"]), (None, None))

    def test_changing_the_date_drops_wording_that_no_longer_matches(self) -> None:
        item = self.make_item(due_date=date(2026, 8, 5), due_date_text="by Wednesday")
        data = self.update_ok(item, due_date="2026-08-12")
        self.assertEqual((data["dueDate"], data["dueDateText"]), ("2026-08-12", None))

    def test_changing_the_date_with_new_wording_keeps_the_wording(self) -> None:
        item = self.make_item(due_date=date(2026, 8, 5), due_date_text="by Wednesday")
        data = self.update_ok(item, due_date="2026-08-12", due_date_text="after the demo")
        self.assertEqual(data["dueDateText"], "after the demo")

    def test_blank_owner_clears_it_and_is_returned_as_null(self) -> None:
        item = self.make_item(owner_name="Ana")
        self.assertIsNone(self.update_ok(item, owner_name="")["ownerName"])

    def test_source_and_evidence_cannot_be_changed(self) -> None:
        item = self.make_item(source=Source.AI, evidence_quote="Ana: I will do it by Friday")
        self.update_ok(item, description="Edited", source="manual", evidence_quote="forged")
        item.refresh_from_db()
        self.assertEqual((item.source, item.evidence_quote), (Source.AI, "Ana: I will do it by Friday"))

    def test_client_supplied_timestamps_are_ignored_on_update(self) -> None:
        item = self.make_item()
        created = item.created_at
        self.update_ok(item, description="x", created_at="2001-01-01T00:00:00Z")
        item.refresh_from_db()
        self.assertEqual(item.created_at, created)

    def test_updating_status_bumps_updated_at(self) -> None:
        item = self.make_item()
        before = item.updated_at
        self.update_ok(item, status="In Progress")
        item.refresh_from_db()
        self.assertGreater(item.updated_at, before)


class ActionItemRegenerationInteractionTests(ActionItemApiTestCase):
    def test_a_status_change_on_an_ai_item_survives_re_running_the_analysis(self) -> None:
        meeting = self.make_meeting(title="Discovery", meeting_date=SAMPLE_DATE, transcript=SAMPLE_TRANSCRIPT, participants=list(SAMPLE_PARTICIPANTS))
        self.assert_success_envelope(self.client.post("/meeting/analyze/", {"meeting_id": meeting.meeting_id}, format="json"))
        ai_item = ActionItem.objects.filter(meeting=meeting, source=Source.AI).first()
        self.update_ok(ai_item, status="Completed")
        self.client.post("/meeting/analyze/", {"meeting_id": meeting.meeting_id}, format="json")
        kept = ActionItem.objects.get(pk=ai_item.pk)
        self.assertEqual((kept.status, kept.is_edited, kept.source), ("Completed", True, Source.AI))
        # the edited item is kept, and the run regenerates all 7 AI items (including a fresh twin of the kept one)
        self.assertEqual(ActionItem.objects.filter(meeting=meeting).count(), 1 + 7)


class ActionItemOverdueTests(ActionItemApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        yesterday, tomorrow = TODAY - timedelta(days=1), TODAY + timedelta(days=1)
        self.open_yesterday = self.make_item(description="open yesterday", due_date=yesterday, status=Status.OPEN)
        self.progress_yesterday = self.make_item(description="in progress yesterday", due_date=yesterday, status=Status.IN_PROGRESS)
        self.blocked_last_month = self.make_item(description="blocked last month", due_date=TODAY - timedelta(days=30), status=Status.BLOCKED)
        self.done_yesterday = self.make_item(description="done yesterday", due_date=yesterday, status=Status.COMPLETED)
        self.open_today = self.make_item(description="open today", due_date=TODAY)
        self.open_tomorrow = self.make_item(description="open tomorrow", due_date=tomorrow)
        self.no_date = self.make_item(description="no date")
        self.expected_overdue = {"open yesterday", "in progress yesterday", "blocked last month"}

    def test_overdue_definition_with_an_injected_clock(self) -> None:
        with Clock.override(TODAY):
            flags = {i["description"]: i["isOverdue"] for i in self.listed(limit=100)}
        self.assertEqual({d for d, flag in flags.items() if flag}, self.expected_overdue)
        self.assertFalse(flags["done yesterday"] or flags["open today"] or flags["no date"] or flags["open tomorrow"])

    def test_overdue_filter_true_returns_exactly_the_overdue_items(self) -> None:
        with Clock.override(TODAY):
            self.assertEqual(set(self.descriptions(is_overdue="true", limit=100)), self.expected_overdue)

    def test_overdue_filter_false_returns_everything_else_including_undated(self) -> None:
        with Clock.override(TODAY):
            names = set(self.descriptions(is_overdue="false", limit=100))
        self.assertEqual(names, {"done yesterday", "open today", "open tomorrow", "no date"})

    def test_filter_and_flag_never_disagree(self) -> None:
        with Clock.override(TODAY):
            for flag in ("true", "false"):
                for item in self.listed(is_overdue=flag, limit=100):
                    self.assertEqual(item["isOverdue"], flag == "true", item["description"])

    def test_overdue_and_not_overdue_partition_the_table(self) -> None:
        with Clock.override(TODAY):
            overdue, rest = ActionItem.objects.overdue().count(), ActionItem.objects.not_overdue().count()
        self.assertEqual((overdue, overdue + rest), (3, ActionItem.objects.count()))

    def test_the_same_data_changes_state_as_the_clock_moves(self) -> None:
        with Clock.override(TODAY - timedelta(days=1)):
            self.assertEqual(set(self.descriptions(is_overdue="true", limit=100)), {"blocked last month"})
        with Clock.override(TODAY + timedelta(days=2)):
            names = set(self.descriptions(is_overdue="true", limit=100))
        self.assertEqual(names, self.expected_overdue | {"open today", "open tomorrow"})

    def test_completing_an_overdue_item_clears_its_overdue_state(self) -> None:
        with Clock.override(TODAY):
            data = self.update_ok(self.open_yesterday, status="Completed")
            self.assertFalse(data["isOverdue"])
            self.assertNotIn("open yesterday", self.descriptions(is_overdue="true", limit=100))

    def test_boolean_query_spellings(self) -> None:
        with Clock.override(TODAY):
            for value in ("true", "True", "1"):
                self.assertEqual(set(self.descriptions(is_overdue=value, limit=100)), self.expected_overdue)
            self.assertEqual(len(self.descriptions(is_overdue="0", limit=100)), 4)
            self.assert_error_envelope(self.client.get(GET_ALL_URL, {"is_overdue": "maybe"}), 400)

    def test_overdue_helper_unit(self) -> None:
        self.assertTrue(Overdue.is_overdue(date(2026, 7, 27), "Open", TODAY))
        self.assertFalse(Overdue.is_overdue(date(2026, 7, 27), "Completed", TODAY))
        self.assertFalse(Overdue.is_overdue(TODAY, "Open", TODAY))
        self.assertFalse(Overdue.is_overdue(None, "Open", TODAY))

    def test_meeting_detail_uses_the_same_overdue_rule(self) -> None:
        with Clock.override(TODAY):
            items = self.client.get("/meeting/get/", {"meeting_id": self.meeting.meeting_id}).json()["data"]["actionItems"]
        self.assertEqual({i["description"] for i in items if i["isOverdue"]}, self.expected_overdue)


class ActionItemListTests(ActionItemApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.second = self.make_meeting(title="Second meeting")
        self.make_item(description="Write report", owner_name="Maria Lopez", due_date=date(2026, 8, 3), priority="High", status="Open")
        self.make_item(description="Book venue", owner_name="James", due_date=date(2026, 8, 1), priority="Low", status="In Progress")
        self.make_item(description="Send invoice", owner_name="", priority="Medium", status="Blocked")
        self.make_item(self.second, description="Review budget", owner_name="Maria", due_date=date(2026, 8, 10), priority="Medium", status="Completed")
        self.make_item(self.second, description="Hire designer", owner_name="Riya", due_date=date(2026, 8, 2), priority="High", status="Open")

    def test_default_sort_is_due_date_ascending_with_undated_last(self) -> None:
        self.assertEqual(self.descriptions(), ["Book venue", "Hire designer", "Write report", "Review budget", "Send invoice"])

    def test_descending_due_date_still_puts_undated_last(self) -> None:
        self.assertEqual(self.descriptions(sort_order="desc"), ["Review budget", "Write report", "Hire designer", "Book venue", "Send invoice"])

    def test_priority_sorts_by_meaning_not_alphabetically(self) -> None:
        order = [i["priority"] for i in self.listed(sort_by="priority", sort_order="asc")]
        self.assertEqual(order, ["Low", "Medium", "Medium", "High", "High"])
        self.assertEqual([i["priority"] for i in self.listed(sort_by="priority", sort_order="desc")][:2], ["High", "High"])

    def test_status_sorts_in_workflow_order(self) -> None:
        self.assertEqual([i["status"] for i in self.listed(sort_by="status")], ["Open", "Open", "In Progress", "Blocked", "Completed"])

    def test_other_whitelisted_sorts_work(self) -> None:
        self.assertEqual(self.descriptions(sort_by="description")[0], "Book venue")
        for field in ("created_at", "updated_at", "owner_name"):
            self.assertEqual(len(self.listed(sort_by=field)), 5)

    def test_unknown_sort_fields_are_rejected(self) -> None:
        for field in ("meeting__owner", "evidence_quote", "password", "meeting_id", "due_date; drop table"):
            with self.subTest(field=field):
                self.assert_error_envelope(self.client.get(GET_ALL_URL, {"sort_by": field}), 400)

    def test_filter_by_meeting_status_and_priority(self) -> None:
        self.assertEqual(set(self.descriptions(meeting_id=self.second.meeting_id)), {"Review budget", "Hire designer"})
        self.assertEqual(set(self.descriptions(status="Open")), {"Write report", "Hire designer"})
        self.assertEqual(set(self.descriptions(priority="High")), {"Write report", "Hire designer"})

    def test_filter_by_owner_is_partial_and_case_insensitive(self) -> None:
        self.assertEqual(set(self.descriptions(owner="maria")), {"Write report", "Review budget"})
        self.assertEqual(self.descriptions(owner="Riya"), ["Hire designer"])

    def test_due_date_range_is_inclusive_and_excludes_undated(self) -> None:
        self.assertEqual(set(self.descriptions(from_date="2026-08-02", to_date="2026-08-03")), {"Hire designer", "Write report"})
        self.assertNotIn("Send invoice", self.descriptions(from_date="2026-01-01"))

    def test_search_matches_description_and_owner(self) -> None:
        self.assertEqual(self.descriptions(search_key="venue"), ["Book venue"])
        self.assertEqual(set(self.descriptions(search_key="MARIA")), {"Write report", "Review budget"})

    def test_search_wildcards_are_literal(self) -> None:
        self.assertEqual(self.descriptions(search_key="%"), [])
        self.assertEqual(self.descriptions(search_key="_"), [])

    def test_url_encoded_search(self) -> None:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL + "?search_key=write%20report"))
        self.assertEqual(len(body["data"]["data"]), 1)

    def test_filters_combine_with_and(self) -> None:
        self.assertEqual(self.descriptions(priority="High", status="Open", meeting_id=self.second.meeting_id), ["Hire designer"])
        self.assertEqual(self.descriptions(priority="High", status="Blocked"), [])
        self.assertEqual(self.descriptions(owner="maria", status="Completed", search_key="budget", from_date="2026-08-05"), ["Review budget"])

    def test_invalid_filter_values_are_400(self) -> None:
        for query in ({"status": "Done"}, {"priority": "Urgent"}, {"meeting_id": "abc"}, {"meeting_id": 0}, {"from_date": "01-08-26"}, {"from_date": "2026-09-01", "to_date": "2026-08-01"}):
            with self.subTest(query=query):
                self.assert_error_envelope(self.client.get(GET_ALL_URL, query), 400)

    def test_no_match_is_200_with_empty_list_and_message(self) -> None:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"search_key": "zzzz"}))
        self.assertEqual(body["data"]["data"], [])
        self.assertEqual((body["data"]["presentPage"], body["data"]["totalPage"], body["message"]), (1, 1, Constants.data_no_match))

    def test_pagination(self) -> None:
        first = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"limit": 2}))["data"]
        self.assertEqual((first["presentPage"], first["totalPage"], len(first["data"])), (1, 3, 2))
        self.assertIn("limit=2", first["nextPageUrl"])
        self.assertNotIn("previousPageUrl", first)
        last = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"limit": 2, "page_num": 3}))["data"]
        self.assertEqual(len(last["data"]), 1)
        self.assertNotIn("nextPageUrl", last)
        self.assert_error_envelope(self.client.get(GET_ALL_URL, {"page_num": 9}), 400)
        for query in ({"limit": 0}, {"limit": 101}, {"page_num": 0}):
            self.assert_error_envelope(self.client.get(GET_ALL_URL, query), 400)

    def test_values_projection_and_whitelist(self) -> None:
        item = self.listed(values="description,status")[0]
        self.assertEqual(set(item), {"description", "status"})
        self.assert_error_envelope(self.client.get(GET_ALL_URL, {"values": "meeting__owner__password"}), 400)

    def test_list_items_carry_meeting_title_and_overdue_flag(self) -> None:
        item = self.listed(search_key="budget")[0]
        self.assertEqual((item["meetingTitle"], item["isOverdue"], item["source"]), ("Second meeting", False, "manual"))

    def test_list_query_count_does_not_grow_with_rows(self) -> None:
        for index in range(20):
            self.make_item(description=f"Extra {index}")
        with self.assertNumQueries(2):
            self.client.get(GET_ALL_URL, {"limit": 100})

    def test_each_users_list_is_independent(self) -> None:
        other_meeting = self.make_meeting(owner=self.other)
        self.make_item(other_meeting, description="Other's task")
        self.assertNotIn("Other's task", self.descriptions(limit=100))
        self.authenticate(self.other)
        self.assertEqual(self.descriptions(), ["Other's task"])
