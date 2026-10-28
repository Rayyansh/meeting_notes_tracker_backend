import copy
from datetime import date

from django.test import SimpleTestCase

from tracker_apps.ai_service.exceptions import InvalidAnalysisOutput
from tracker_apps.ai_service.providers.base import AnalysisRequest
from tracker_apps.ai_service.validators import AnalysisOutputValidator

TRANSCRIPT = (
    "Maria: I will send the budget report by Friday.\n"
    "James: Agreed, we will ship in August.\n"
    "Sarah: I am not sure about the timeline.\n"
    "Maria: Thanks “team”, that   is   all.\n"
    "Sarah: Sure.\n"
)
MEETING_DATE = date(2026, 7, 28)  # Tuesday
REQUEST = AnalysisRequest(TRANSCRIPT, MEETING_DATE, "Other", ("Maria", "James"))


def good_output() -> dict:
    return {
        "summary": "<h3>Purpose</h3><p>Plan the release.</p>",
        "discussion_points": ["Release timing"],
        "decisions": [{"text": "Ship in August", "evidence": "we will ship in August"}],
        "action_items": [
            {
                "description": "Send the budget report",
                "owner": "Maria",
                "due_date_text": "by Friday",
                "due_date": "2026-07-31",
                "priority": "Medium",
                "evidence": "I will send the budget report by Friday.",
            }
        ],
        "risks": [{"text": "Timeline unclear", "evidence": "I am not sure about the timeline."}],
        "unanswered_questions": [{"text": "Timeline", "evidence": "not sure about the timeline"}],
    }


class ValidatorTestCase(SimpleTestCase):
    def validate(self, output: object, request: AnalysisRequest = REQUEST):
        return AnalysisOutputValidator(request).validate(output)

    def mutated(self, mutate) -> dict:
        output = good_output()
        mutate(output)
        return output


class StructuralFailureTests(ValidatorTestCase):
    def assert_rejected(self, output: object) -> None:
        with self.assertRaises(InvalidAnalysisOutput):
            self.validate(output)

    def test_good_output_passes_untouched(self) -> None:
        cleaned, report = self.validate(good_output())
        self.assertEqual(report.total_changes, 0)
        self.assertEqual(cleaned["action_items"][0]["due_date"], "2026-07-31")

    def test_empty_lists_are_valid(self) -> None:
        output = good_output()
        for key in ("discussion_points", "decisions", "action_items", "risks", "unanswered_questions"):
            output[key] = []
        cleaned, report = self.validate(output)
        self.assertEqual((cleaned["decisions"], cleaned["action_items"], report.total_changes), ([], [], 0))

    def test_non_object_results_are_rejected(self) -> None:
        for value in (None, [], "text", 5, '{"summary": "x"}'):
            with self.subTest(value=value):
                self.assert_rejected(value)

    def test_missing_required_key_is_rejected(self) -> None:
        for key in good_output():
            with self.subTest(key=key):
                self.assert_rejected(self.mutated(lambda o: o.pop(key)))

    def test_unknown_top_level_key_is_rejected(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o.update(extra="x")))

    def test_unknown_key_inside_an_item_is_rejected(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(status="Open")))
        self.assert_rejected(self.mutated(lambda o: o["decisions"][0].update(owner="Maria")))

    def test_wrong_types_are_rejected(self) -> None:
        cases = [
            lambda o: o.update(summary=5),
            lambda o: o.update(discussion_points="a"),
            lambda o: o.update(action_items="none"),
            lambda o: o.update(decisions=["plain string"]),
            lambda o: o["action_items"][0].update(owner=7),
            lambda o: o["action_items"][0].update(description=None),
            lambda o: o["decisions"][0].update(evidence=None),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                self.assert_rejected(self.mutated(mutate))

    def test_bad_enum_and_date_format_are_rejected(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(priority="Urgent")))
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(priority="medium")))
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(due_date="31/07/2026")))

    def test_summary_must_be_present_and_within_limits(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o.update(summary="")))
        self.assert_rejected(self.mutated(lambda o: o.update(summary="x" * 4001)))

    def test_summary_that_is_empty_after_sanitising_is_rejected(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o.update(summary="<script>alert(1)</script>")))

    def test_oversized_items_and_lists_are_rejected(self) -> None:
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(description="x" * 501)))
        self.assert_rejected(self.mutated(lambda o: o["action_items"][0].update(owner="x" * 101)))
        self.assert_rejected(self.mutated(lambda o: o["decisions"][0].update(evidence="x" * 1001)))
        self.assert_rejected(self.mutated(lambda o: o.update(discussion_points=["p"] * 31)))
        self.assert_rejected(self.mutated(lambda o: o.update(action_items=[copy.deepcopy(good_output()["action_items"][0]) for _ in range(51)])))

    def test_rejection_reasons_contain_paths_only_never_content(self) -> None:
        output = self.mutated(lambda o: o["action_items"][0].update(description="SECRET-PAYLOAD" * 100))
        with self.assertRaises(InvalidAnalysisOutput) as caught:
            self.validate(output)
        self.assertNotIn("SECRET", " ".join(caught.exception.reasons))

    def test_everything_dropped_from_a_non_empty_result_is_rejected(self) -> None:
        def ungrounded(output: dict) -> None:
            output["decisions"][0]["evidence"] = "something nobody said at all"
            output["action_items"][0]["evidence"] = "another invented sentence here"

        self.assert_rejected(self.mutated(ungrounded))

    def test_dropping_only_risks_or_questions_is_not_a_rejection(self) -> None:
        output = self.mutated(lambda o: o["risks"][0].update(evidence="an invented risk sentence"))
        cleaned, report = self.validate(output)
        self.assertEqual((cleaned["risks"], report.dropped), ([], {"risks": 1}))
        self.assertEqual(len(cleaned["action_items"]), 1)


class GroundingTests(ValidatorTestCase):
    def test_ungrounded_item_is_dropped_and_the_rest_kept(self) -> None:
        output = good_output()
        output["decisions"].append({"text": "Hire two people", "evidence": "We decided to hire two people"})
        cleaned, report = self.validate(output)
        self.assertEqual([d["text"] for d in cleaned["decisions"]], ["Ship in August"])
        self.assertEqual(report.dropped, {"decisions": 1})

    def test_paraphrased_evidence_is_dropped(self) -> None:
        output = self.mutated(lambda o: o["risks"][0].update(evidence="Sarah doubts the schedule"))
        cleaned, report = self.validate(output)
        self.assertEqual((cleaned["risks"], report.dropped), ([], {"risks": 1}))

    def test_every_evidence_section_is_checked(self) -> None:
        def ungrounded_everywhere(output: dict) -> None:
            for section in ("risks", "unanswered_questions"):
                output[section][0]["evidence"] = "completely invented evidence"

        cleaned, report = self.validate(self.mutated(ungrounded_everywhere))
        self.assertEqual(report.dropped, {"risks": 1, "unanswered_questions": 1})
        self.assertEqual((cleaned["risks"], cleaned["unanswered_questions"]), ([], []))

    def test_ungrounded_action_item_is_dropped(self) -> None:
        output = good_output()
        extra = copy.deepcopy(output["action_items"][0])
        extra.update(description="Book a venue", evidence="Maria will book the venue by Monday")
        output["action_items"].append(extra)
        cleaned, report = self.validate(output)
        self.assertEqual(len(cleaned["action_items"]), 1)
        self.assertEqual(report.dropped, {"action_items": 1})

    def test_whitespace_case_and_quote_style_do_not_defeat_grounding(self) -> None:
        output = self.mutated(lambda o: o["decisions"][0].update(evidence="WE WILL   SHIP\nin august"))
        self.assertEqual(self.validate(output)[1].total_changes, 0)
        output = self.mutated(lambda o: o["risks"][0].update(evidence='Thanks "team", that is all.'))
        self.assertEqual(self.validate(output)[1].total_changes, 0)

    def test_very_short_evidence_is_not_trusted(self) -> None:
        output = self.mutated(lambda o: o["risks"][0].update(evidence="Sarah"))
        self.assertEqual(self.validate(output)[1].dropped, {"risks": 1})

    def test_blank_text_is_dropped_even_with_valid_evidence(self) -> None:
        output = self.mutated(lambda o: o["decisions"][0].update(text="   "))
        self.assertEqual(self.validate(output)[1].dropped, {"decisions": 1})

    def test_report_is_logged_with_counts_only(self) -> None:
        output = self.mutated(lambda o: o["risks"][0].update(evidence="confidential merger plans with Acme"))
        with self.assertLogs("tracker_apps.ai_service.validators", level="WARNING") as logs:
            self.validate(output)
        text = "\n".join(logs.output)
        self.assertIn("risks", text)
        for leaked in ("merger", "Acme", "budget", "Maria"):
            self.assertNotIn(leaked, text)


class OwnerTests(ValidatorTestCase):
    def owner_result(self, owner: str | None, request: AnalysisRequest = REQUEST):
        output = self.mutated(lambda o: o["action_items"][0].update(owner=owner))
        return self.validate(output, request)

    def test_declared_participant_is_kept(self) -> None:
        self.assertEqual(self.owner_result("Maria")[0]["action_items"][0]["owner"], "Maria")
        self.assertEqual(self.owner_result("maria")[0]["action_items"][0]["owner"], "maria")

    def test_speaker_found_in_transcript_is_kept_even_if_not_declared(self) -> None:
        self.assertEqual(self.owner_result("Sarah")[0]["action_items"][0]["owner"], "Sarah")

    def test_first_name_matches_a_full_declared_name_with_role(self) -> None:
        request = AnalysisRequest(TRANSCRIPT, MEETING_DATE, "Other", ("Maria Lopez — Founder", "James"))
        self.assertEqual(self.owner_result("Maria", request)[0]["action_items"][0]["owner"], "Maria")
        self.assertEqual(self.owner_result("Maria Lopez", request)[0]["action_items"][0]["owner"], "Maria Lopez")

    def test_invented_owner_is_nulled_not_dropped(self) -> None:
        cleaned, report = self.owner_result("Bob")
        self.assertIsNone(cleaned["action_items"][0]["owner"])
        self.assertEqual(len(cleaned["action_items"]), 1)
        self.assertEqual(report.owners_nulled, 1)

    def test_null_and_blank_owner_stay_unassigned_without_counting(self) -> None:
        for owner in (None, "", "   "):
            with self.subTest(owner=owner):
                cleaned, report = self.owner_result(owner)
                self.assertIsNone(cleaned["action_items"][0]["owner"])
                self.assertEqual(report.owners_nulled, 0)

    def test_header_labels_are_not_treated_as_people(self) -> None:
        transcript = "Date: 28 July\nMaria: I will send it by Friday.\nMaria: Done.\n"
        request = AnalysisRequest(transcript, MEETING_DATE, "Other", ())
        output = good_output()
        output["action_items"][0].update(owner="Date", evidence="I will send it by Friday.")
        output["decisions"], output["risks"], output["unanswered_questions"] = [], [], []
        cleaned, report = self.validate(output, request)
        self.assertIsNone(cleaned["action_items"][0]["owner"])
        self.assertEqual(report.owners_nulled, 1)


class DateTests(ValidatorTestCase):
    def date_result(self, **fields: object):
        output = self.mutated(lambda o: o["action_items"][0].update(**fields))
        cleaned, report = self.validate(output)
        return cleaned["action_items"][0], report

    def test_consistent_date_is_kept(self) -> None:
        item, report = self.date_result()
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), ("2026-07-31", "by Friday", 0))

    def test_impossible_date_is_nulled_and_text_kept(self) -> None:
        item, report = self.date_result(due_date="2026-02-30")
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), (None, "by Friday", 1))

    def test_date_that_disagrees_with_the_text_is_nulled(self) -> None:
        item, report = self.date_result(due_date="2026-08-07")
        self.assertEqual((item["due_date"], report.dates_nulled), (None, 1))

    def test_unresolvable_text_forces_null_date_and_keeps_text(self) -> None:
        item, report = self.date_result(due_date_text="by the end of next week", due_date="2026-08-07")
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), (None, "by the end of next week", 1))

    def test_valid_date_without_text_is_kept(self) -> None:
        item, report = self.date_result(due_date_text=None, due_date="2026-08-07")
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), ("2026-08-07", None, 0))

    def test_missing_date_and_text_stay_null_without_counting(self) -> None:
        item, report = self.date_result(due_date_text=None, due_date=None)
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), (None, None, 0))

    def test_text_without_date_is_kept_as_is(self) -> None:
        item, report = self.date_result(due_date=None)
        self.assertEqual((item["due_date"], item["due_date_text"], report.dates_nulled), (None, "by Friday", 0))


class SummaryAndCleaningTests(ValidatorTestCase):
    def test_summary_html_is_sanitised(self) -> None:
        output = self.mutated(lambda o: o.update(summary='<h3>Purpose</h3><p onclick="x()">Hi</p><script>bad()</script><img src=x onerror=y>'))
        summary = self.validate(output)[0]["summary"]
        self.assertEqual(summary, "<h3>Purpose</h3><p>Hi</p>")

    def test_blank_discussion_points_are_removed(self) -> None:
        output = self.mutated(lambda o: o.update(discussion_points=["Real point", "   ", "Another"]))
        self.assertEqual(self.validate(output)[0]["discussion_points"], ["Real point", "Another"])

    def test_empty_due_text_becomes_null(self) -> None:
        output = self.mutated(lambda o: o["action_items"][0].update(due_date_text="  ", due_date=None))
        self.assertIsNone(self.validate(output)[0]["action_items"][0]["due_date_text"])
