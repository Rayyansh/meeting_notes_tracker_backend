from datetime import date

from tracker.constants import Constants
from tracker_apps.common.sanitizer import HtmlSanitizer
from tracker_apps.common.tests_utils import ApiTestCase
from tracker_apps.meeting.choices import AnalysisStatus, MeetingType
from tracker_apps.meeting.models.meeting import Meeting

CREATE_URL = "/meeting/create/"
UPDATE_URL = "/meeting/update/"
GET_URL = "/meeting/get/"
GET_ALL_URL = "/meeting/get_all/"
DELETE_URL = "/meeting/delete/"
TRANSCRIPT = "Maria: We agreed to launch in August.\nJames: I will send the files by Wednesday."


class MeetingApiTestCase(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user(email="a@example.com")
        self.other = self.create_user(email="b@example.com")
        self.authenticate(self.user)

    def payload(self, **overrides: object) -> dict:
        payload = {
            "title": "Weekly sync",
            "meeting_date": "2026-07-28",
            "meeting_type": MeetingType.PROJECT,
            "participants": ["Maria", "James"],
            "transcript": TRANSCRIPT,
            "notes": "<p>Hello</p>",
        }
        payload.update(overrides)
        return payload

    def make_meeting(self, owner=None, **overrides: object) -> Meeting:
        fields = {
            "owner": owner or self.user,
            "title": "Weekly sync",
            "meeting_date": date(2026, 7, 28),
            "meeting_type": MeetingType.PROJECT,
            "participants": ["Maria"],
            "transcript": TRANSCRIPT,
        }
        fields.update(overrides)
        return Meeting.objects.create(**fields)

    def create(self, **overrides: object) -> dict:
        return self.assert_success_envelope(self.client.post(CREATE_URL, self.payload(**overrides), format="json"), 201)["data"]

    def titles(self, **query: object) -> list[str]:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL, query))
        return [item["title"] for item in body["data"]["data"]]


class MeetingAuthTests(MeetingApiTestCase):
    def test_every_endpoint_requires_authentication(self) -> None:
        meeting = self.make_meeting()
        self.client.force_authenticate(None)
        calls = [
            self.client.post(CREATE_URL, self.payload(), format="json"),
            self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id}, format="json"),
            self.client.get(GET_URL, {"meeting_id": meeting.meeting_id}),
            self.client.get(GET_ALL_URL),
            self.client.delete(f"{DELETE_URL}?meeting_id={meeting.meeting_id}"),
        ]
        for response in calls:
            self.assert_error_envelope(response, 401)
        self.assertTrue(Meeting.objects.filter(meeting_id=meeting.meeting_id).exists())


class MeetingOwnershipTests(MeetingApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.theirs = self.make_meeting(owner=self.other, title="Secret board meeting")

    def test_user_cannot_read_another_users_meeting(self) -> None:
        self.assert_error_envelope(self.client.get(GET_URL, {"meeting_id": self.theirs.meeting_id}), 404)

    def test_user_cannot_update_another_users_meeting(self) -> None:
        response = self.client.put(UPDATE_URL, {"meeting_id": self.theirs.meeting_id, "title": "Hacked"}, format="json")
        self.assert_error_envelope(response, 404)
        self.theirs.refresh_from_db()
        self.assertEqual(self.theirs.title, "Secret board meeting")

    def test_user_cannot_delete_another_users_meeting(self) -> None:
        self.assert_error_envelope(self.client.delete(f"{DELETE_URL}?meeting_id={self.theirs.meeting_id}"), 404)
        self.assertTrue(Meeting.objects.filter(meeting_id=self.theirs.meeting_id).exists())

    def test_user_cannot_see_another_users_meeting_in_list_or_search(self) -> None:
        self.assertEqual(self.titles(), [])
        self.assertEqual(self.titles(search_key="Secret"), [])

    def test_not_owned_and_nonexistent_are_indistinguishable(self) -> None:
        theirs = self.client.get(GET_URL, {"meeting_id": self.theirs.meeting_id})
        missing = self.client.get(GET_URL, {"meeting_id": 999999})
        self.assertEqual(theirs.status_code, missing.status_code)
        self.assertEqual(theirs.json(), missing.json())

    def test_owned_by_helper_scopes_queryset(self) -> None:
        mine = self.make_meeting()
        self.assertEqual(list(Meeting.objects.owned_by(self.user)), [mine])
        self.assertEqual(list(Meeting.objects.owned_by(self.user.pk)), [mine])

    def test_deleting_a_user_deletes_their_meetings(self) -> None:
        self.other.delete()
        self.assertFalse(Meeting.objects.filter(meeting_id=self.theirs.meeting_id).exists())

    def test_response_does_not_expose_owner(self) -> None:
        data = self.create()
        self.assertNotIn("owner", " ".join(data).lower())


class MeetingCrudTests(MeetingApiTestCase):
    def test_create_returns_full_detail_in_camel_case(self) -> None:
        data = self.create()
        self.assertEqual(data["title"], "Weekly sync")
        self.assertEqual(data["meetingDate"], "2026-07-28")
        self.assertEqual(data["meetingType"], "Project Meeting")
        self.assertEqual(data["participants"], ["Maria", "James"])
        self.assertEqual(data["transcript"], TRANSCRIPT)
        self.assertEqual(data["transcriptSource"], "text")
        self.assertIsNone(data["transcriptFilename"])
        self.assertEqual(data["analysisStatus"], AnalysisStatus.NOT_STARTED)
        self.assertFalse(data["transcriptChangedSinceAnalysis"])
        self.assertTrue(data["createdAt"] and data["updatedAt"])
        self.assertEqual(Meeting.objects.get(meeting_id=data["meetingId"]).owner, self.user)

    def test_create_without_optional_fields_uses_empty_defaults(self) -> None:
        payload = self.payload()
        del payload["participants"], payload["notes"]
        data = self.assert_success_envelope(self.client.post(CREATE_URL, payload, format="json"), 201)["data"]
        self.assertEqual((data["participants"], data["notes"]), ([], ""))

    def test_get_returns_full_stored_transcript(self) -> None:
        meeting_id = self.create()["meetingId"]
        data = self.assert_success_envelope(self.client.get(GET_URL, {"meeting_id": meeting_id}))["data"]
        self.assertEqual(data["transcript"], TRANSCRIPT)
        self.assertEqual(data["meetingId"], meeting_id)

    def test_update_changes_only_provided_fields_and_bumps_updated_at(self) -> None:
        meeting = self.make_meeting()
        before = meeting.updated_at
        response = self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, "title": "Renamed"}, format="json")
        data = self.assert_success_envelope(response)["data"]
        meeting.refresh_from_db()
        self.assertEqual((data["title"], meeting.title, meeting.transcript), ("Renamed", "Renamed", TRANSCRIPT))
        self.assertGreater(meeting.updated_at, before)

    def test_update_can_clear_participants_and_notes(self) -> None:
        meeting = self.make_meeting(notes="<p>x</p>")
        self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, "participants": [], "notes": ""}, format="json")
        meeting.refresh_from_db()
        self.assertEqual((meeting.participants, meeting.notes), ([], ""))

    def test_update_all_fields(self) -> None:
        meeting = self.make_meeting()
        body = self.payload(title="New", meeting_date="2026-08-01", meeting_type="Retrospective", participants=["Zed"], transcript="Zed: hi", notes="<p>n</p>")
        self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, **body}, format="json")
        meeting.refresh_from_db()
        self.assertEqual((meeting.title, meeting.meeting_date, meeting.meeting_type, meeting.participants, meeting.transcript), ("New", date(2026, 8, 1), "Retrospective", ["Zed"], "Zed: hi"))

    def test_delete_then_second_delete_is_404(self) -> None:
        meeting_id = self.create()["meetingId"]
        self.assert_success_envelope(self.client.delete(f"{DELETE_URL}?meeting_id={meeting_id}"))
        self.assertFalse(Meeting.objects.filter(meeting_id=meeting_id).exists())
        self.assert_error_envelope(self.client.delete(f"{DELETE_URL}?meeting_id={meeting_id}"), 404)

    def test_delete_via_json_body_also_works(self) -> None:
        meeting_id = self.create()["meetingId"]
        self.assert_success_envelope(self.client.delete(DELETE_URL, {"meeting_id": meeting_id}, format="json"))

    def test_get_and_update_of_missing_meeting_are_404(self) -> None:
        self.assert_error_envelope(self.client.get(GET_URL, {"meeting_id": 12345}), 404)
        self.assert_error_envelope(self.client.put(UPDATE_URL, {"meeting_id": 12345}, format="json"), 404)


class MeetingValidationTests(MeetingApiTestCase):
    def assert_field_error(self, payload: dict, field: str, message: str | None = None) -> None:
        body = self.assert_error_envelope(self.client.post(CREATE_URL, payload, format="json"), 400)
        fields = [error["field"] for error in body["error"]]
        self.assertIn(field, fields)
        if message:
            self.assertIn({"field": field, "message": message}, body["error"])
        self.assertEqual(Meeting.objects.count(), 0)

    def test_missing_or_blank_title(self) -> None:
        payload = self.payload()
        del payload["title"]
        self.assert_field_error(payload, "title", Constants.title_required)
        self.assert_field_error(self.payload(title="   "), "title", Constants.title_required)

    def test_title_longer_than_200_chars(self) -> None:
        self.assert_field_error(self.payload(title="x" * 201), "title", Constants.title_too_long)
        self.assert_success_envelope(self.client.post(CREATE_URL, self.payload(title="x" * 200), format="json"), 201)

    def test_bad_or_missing_meeting_date(self) -> None:
        for value in ("28-07-2026", "2026-13-40", "tomorrow", ""):
            with self.subTest(value=value):
                self.assert_field_error(self.payload(meeting_date=value), "meeting_date")
        payload = self.payload()
        del payload["meeting_date"]
        self.assert_field_error(payload, "meeting_date", Constants.meeting_date_required)

    def test_invalid_meeting_type(self) -> None:
        self.assert_field_error(self.payload(meeting_type="Party"), "meeting_type")
        payload = self.payload()
        del payload["meeting_type"]
        self.assert_field_error(payload, "meeting_type")

    def test_all_seven_meeting_types_are_accepted(self) -> None:
        for meeting_type in MeetingType.values:
            self.assert_success_envelope(self.client.post(CREATE_URL, self.payload(meeting_type=meeting_type), format="json"), 201)
        self.assertEqual(len(MeetingType.values), 7)

    def test_empty_or_whitespace_transcript(self) -> None:
        for value in ("", "   \n\t "):
            with self.subTest(value=value):
                self.assert_field_error(self.payload(transcript=value), "transcript", Constants.transcript_required)
        payload = self.payload()
        del payload["transcript"]
        self.assert_field_error(payload, "transcript", Constants.transcript_required)

    def test_participants_must_be_a_bounded_list_of_short_strings(self) -> None:
        self.assert_field_error(self.payload(participants="Maria"), "participants", Constants.participants_invalid)
        self.assert_field_error(self.payload(participants=[f"p{i}" for i in range(51)]), "participants")
        self.assert_field_error(self.payload(participants=["x" * 101]), "participants.0")
        self.assert_field_error(self.payload(participants=[1, {"a": 1}]), "participants.1")

    def test_participants_are_trimmed_blanks_dropped_and_deduplicated(self) -> None:
        data = self.create(participants=[" Maria ", "maria", "", "  ", "James", "MARIA", "José", "josé"])
        self.assertEqual(data["participants"], ["Maria", "James", "José"])

    def test_malformed_ids_are_400(self) -> None:
        for value in ("abc", "0", "-1", "1.5"):
            with self.subTest(value=value):
                self.assert_error_envelope(self.client.get(GET_URL, {"meeting_id": value}), 400)
        self.assert_error_envelope(self.client.get(GET_URL), 400)
        self.assert_error_envelope(self.client.put(UPDATE_URL, {"title": "x"}, format="json"), 400)

    def test_update_validates_fields_like_create(self) -> None:
        meeting = self.make_meeting()
        for field, value in (("title", ""), ("meeting_date", "bad"), ("meeting_type", "Nope"), ("transcript", " "), ("participants", "x")):
            with self.subTest(field=field):
                response = self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, field: value}, format="json")
                self.assertEqual(self.assert_error_envelope(response, 400)["error"][0]["field"], field)

    def test_error_messages_hide_internals(self) -> None:
        text = self.client.post(CREATE_URL, self.payload(title=""), format="json").content.decode()
        for leaked in ("Traceback", "serializer", "ValidationError", ".py"):
            self.assertNotIn(leaked, text)


class MeetingNotesSanitisingTests(MeetingApiTestCase):
    def test_script_and_event_handlers_are_stripped_on_create(self) -> None:
        dirty = '<p onclick="x()">Hi</p><script>alert(1)</script><img src=x onerror=alert(1)><a href="javascript:alert(1)">bad</a>'
        notes = self.create(notes=dirty)["notes"]
        for bad in ("<script", "alert(1)", "onclick", "onerror", "<img", "javascript:"):
            self.assertNotIn(bad, notes)
        self.assertIn("Hi", notes)
        self.assertIn("bad", notes)

    def test_allow_listed_formatting_is_kept(self) -> None:
        html = '<h1>T</h1><h4>S</h4><p><strong>b</strong> <em>i</em><br></p><ul><li>a</li></ul><ol><li>b</li></ol><blockquote>q</blockquote><a href="https://example.com/x">l</a><a href="mailto:a@b.com">m</a>'
        notes = self.create(notes=html)["notes"]
        for kept in ("<h1>", "<h4>", "<strong>", "<em>", "<br>", "<ul>", "<ol>", "<li>", "<blockquote>", 'href="https://example.com/x"', 'href="mailto:a@b.com"'):
            self.assertIn(kept, notes)

    def test_notes_are_sanitised_on_update_too(self) -> None:
        meeting = self.make_meeting()
        self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, "notes": "<p>ok</p><script>x</script>"}, format="json")
        meeting.refresh_from_db()
        self.assertNotIn("script", meeting.notes)

    def test_transcript_is_stored_as_plain_text_unmodified(self) -> None:
        text = "A: <b>not html</b> & stuff"
        self.assertEqual(self.create(transcript=text)["transcript"], text)

    def test_sanitiser_unit(self) -> None:
        self.assertEqual(HtmlSanitizer.clean("<style>p{}</style><p>x</p>"), "<p>x</p>")
        self.assertEqual(HtmlSanitizer.clean(""), "")

    def test_notes_too_long_is_400(self) -> None:
        response = self.client.post(CREATE_URL, self.payload(notes="x" * (Constants.notes_max_length + 1)), format="json")
        self.assertEqual(self.assert_error_envelope(response, 400)["error"][0]["field"], "notes")


class MeetingListTests(MeetingApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_meeting(title="Quarterly review", meeting_date=date(2026, 7, 1), meeting_type=MeetingType.CLIENT, participants=["Maria", "José"], notes="<p>budget</p>")
        self.make_meeting(title="Sprint retro", meeting_date=date(2026, 7, 15), meeting_type=MeetingType.RETROSPECTIVE, participants=["James"])
        self.make_meeting(title="Sales call", meeting_date=date(2026, 8, 1), meeting_type=MeetingType.SALES, participants=["Neha"])

    def test_default_order_is_newest_created_first(self) -> None:
        self.assertEqual(self.titles(), ["Sales call", "Sprint retro", "Quarterly review"])

    def test_sort_by_meeting_date_and_title_both_directions(self) -> None:
        self.assertEqual(self.titles(sort_by="meeting_date", sort_order="asc"), ["Quarterly review", "Sprint retro", "Sales call"])
        self.assertEqual(self.titles(sort_by="title", sort_order="desc"), ["Sprint retro", "Sales call", "Quarterly review"])

    def test_unknown_sort_field_is_rejected(self) -> None:
        for field in ("transcript", "owner", "password", "meeting_id; drop"):
            with self.subTest(field=field):
                self.assert_error_envelope(self.client.get(GET_ALL_URL, {"sort_by": field}), 400)

    def test_search_matches_title_participants_and_notes_case_insensitively(self) -> None:
        self.assertEqual(self.titles(search_key="QUARTERLY"), ["Quarterly review"])
        self.assertEqual(self.titles(search_key="james"), ["Sprint retro"])
        self.assertEqual(self.titles(search_key="budget"), ["Quarterly review"])

    def test_search_finds_accented_participant_names(self) -> None:
        self.assertEqual(self.titles(search_key="José"), ["Quarterly review"])

    def test_search_does_not_search_transcript(self) -> None:
        self.assertEqual(self.titles(search_key="Wednesday"), [])

    def test_search_wildcards_are_literal(self) -> None:
        self.assertEqual(self.titles(search_key="%"), [])
        self.assertEqual(self.titles(search_key="_"), [])

    def test_url_encoded_search(self) -> None:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL + "?search_key=quarterly%20review"))
        self.assertEqual(len(body["data"]["data"]), 1)

    def test_filter_by_meeting_type(self) -> None:
        self.assertEqual(self.titles(meeting_type="Sales Meeting"), ["Sales call"])
        self.assert_error_envelope(self.client.get(GET_ALL_URL, {"meeting_type": "Party"}), 400)

    def test_filter_by_meeting_date_range_is_inclusive(self) -> None:
        self.assertEqual(self.titles(from_date="2026-07-15", to_date="2026-08-01", sort_by="meeting_date", sort_order="asc"), ["Sprint retro", "Sales call"])
        self.assertEqual(self.titles(to_date="2026-07-01"), ["Quarterly review"])

    def test_filters_combine_with_and(self) -> None:
        self.assertEqual(self.titles(search_key="s", meeting_type="Sales Meeting", from_date="2026-07-20"), ["Sales call"])
        self.assertEqual(self.titles(search_key="Quarterly", meeting_type="Sales Meeting"), [])

    def test_no_match_is_200_with_empty_list_and_message(self) -> None:
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"search_key": "zzzz"}))
        self.assertEqual(body["data"]["data"], [])
        self.assertEqual((body["data"]["presentPage"], body["data"]["totalPage"]), (1, 1))
        self.assertEqual(body["message"], Constants.data_no_match)

    def test_user_with_no_meetings_gets_empty_200(self) -> None:
        self.authenticate(self.create_user(email="new@example.com"))
        body = self.assert_success_envelope(self.client.get(GET_ALL_URL))
        self.assertEqual(body["data"]["data"], [])

    def test_pagination_pages_and_urls(self) -> None:
        first = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"limit": 2, "sort_by": "title", "sort_order": "asc"}))["data"]
        self.assertEqual([m["title"] for m in first["data"]], ["Quarterly review", "Sales call"])
        self.assertEqual((first["presentPage"], first["totalPage"]), (1, 2))
        self.assertIn("page_num=2", first["nextPageUrl"])
        self.assertNotIn("previousPageUrl", first)
        second = self.assert_success_envelope(self.client.get(GET_ALL_URL, {"limit": 2, "page_num": 2, "sort_by": "title", "sort_order": "asc"}))["data"]
        self.assertEqual([m["title"] for m in second["data"]], ["Sprint retro"])
        self.assertNotIn("nextPageUrl", second)
        self.assertIn("page_num=1", second["previousPageUrl"])
        self.assertIn("limit=2", second["previousPageUrl"])

    def test_page_beyond_last_and_bad_limits_are_400(self) -> None:
        self.assert_error_envelope(self.client.get(GET_ALL_URL, {"page_num": 5}), 400)
        for query in ({"limit": 0}, {"limit": 101}, {"page_num": 0}, {"limit": "x"}):
            with self.subTest(query=query):
                self.assert_error_envelope(self.client.get(GET_ALL_URL, query), 400)

    def test_list_items_are_light_and_exclude_transcript_and_notes(self) -> None:
        item = self.client.get(GET_ALL_URL).json()["data"]["data"][0]
        self.assertEqual(set(item), {"meetingId", "title", "meetingDate", "meetingType", "participants", "analysisStatus", "createdAt", "updatedAt"})

    def test_values_projection_and_whitelist(self) -> None:
        item = self.client.get(GET_ALL_URL, {"values": "title,meeting_date"}).json()["data"]["data"][0]
        self.assertEqual(set(item), {"title", "meetingDate"})
        self.assert_error_envelope(self.client.get(GET_ALL_URL, {"values": "transcript"}), 400)

    def test_list_uses_two_queries_regardless_of_row_count(self) -> None:
        for index in range(10):
            self.make_meeting(title=f"Extra {index}")
        with self.assertNumQueries(2):
            self.client.get(GET_ALL_URL, {"limit": 100})

    def test_each_users_list_is_independent(self) -> None:
        self.make_meeting(owner=self.other, title="Other's")
        self.assertNotIn("Other's", self.titles())
        self.authenticate(self.other)
        self.assertEqual(self.titles(), ["Other's"])


class MeetingTranscriptChangeTests(MeetingApiTestCase):
    def analysed(self, status: str = AnalysisStatus.COMPLETED) -> Meeting:
        return self.make_meeting(analysis_status=status, analysis_error_code="AI_PROVIDER_ERROR" if status == AnalysisStatus.FAILED else None)

    def put(self, meeting: Meeting, **body: object):
        return self.client.put(UPDATE_URL, {"meeting_id": meeting.meeting_id, **body}, format="json")

    def test_changing_transcript_after_analysis_keeps_analysis_and_flags_it(self) -> None:
        meeting = self.analysed()
        data = self.assert_success_envelope(self.put(meeting, transcript="New text"))["data"]
        self.assertEqual(data["analysisStatus"], AnalysisStatus.COMPLETED)
        self.assertTrue(data["transcriptChangedSinceAnalysis"])
        self.assertEqual(data["transcript"], "New text")

    def test_reset_analysis_flag_returns_status_to_not_started(self) -> None:
        meeting = self.analysed(AnalysisStatus.FAILED)
        data = self.assert_success_envelope(self.put(meeting, transcript="New text", reset_analysis=True))["data"]
        self.assertEqual(data["analysisStatus"], AnalysisStatus.NOT_STARTED)
        self.assertFalse(data["transcriptChangedSinceAnalysis"])
        self.assertIsNone(data["analysisErrorCode"])
        self.assertIsNone(data["analyzedAt"])

    def test_unchanged_transcript_does_not_flag_anything(self) -> None:
        meeting = self.analysed()
        data = self.assert_success_envelope(self.put(meeting, transcript=TRANSCRIPT, title="Renamed"))["data"]
        self.assertFalse(data["transcriptChangedSinceAnalysis"])
        self.assertEqual(data["analysisStatus"], AnalysisStatus.COMPLETED)

    def test_changing_transcript_before_any_analysis_does_not_flag(self) -> None:
        meeting = self.make_meeting()
        data = self.assert_success_envelope(self.put(meeting, transcript="New text"))["data"]
        self.assertFalse(data["transcriptChangedSinceAnalysis"])

    def test_changing_transcript_while_processing_is_409(self) -> None:
        meeting = self.analysed(AnalysisStatus.PROCESSING)
        self.assert_error_envelope(self.put(meeting, transcript="New text"), 409)
        meeting.refresh_from_db()
        self.assertEqual(meeting.transcript, TRANSCRIPT)

    def test_non_transcript_edits_while_processing_are_allowed(self) -> None:
        meeting = self.analysed(AnalysisStatus.PROCESSING)
        self.assert_success_envelope(self.put(meeting, title="Renamed"))
