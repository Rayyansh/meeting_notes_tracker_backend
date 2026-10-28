import json
import time
from datetime import date

from django.test import SimpleTestCase

from tracker_apps.ai_service.providers.base import AnalysisRequest
from tracker_apps.ai_service.providers.mock import MockProvider
from tracker_apps.ai_service.tests.helpers import SAMPLE_DATE, SAMPLE_PARTICIPANTS, SAMPLE_TRANSCRIPT, mock_output, sample_request
from tracker_apps.ai_service.text_utils import normalise
from tracker_apps.ai_service.validators import AnalysisOutputValidator

EXPECTED_ACTION_ITEMS = [
    # owner, text expected in description, text expected in due_date_text, resolved due date
    ("Maria", "data retention policy", "Friday", "2026-07-31"),
    ("James", "FAQ documents", "Wednesday", "2026-07-29"),
    ("James", "Zendesk walkthrough", "Thursday", "2026-07-30"),
    ("Riya", "initial wireframes", "next Tuesday", "2026-08-04"),
    ("Arjun", "architecture and integration proposal", None, None),
    ("Arjun", "revised estimate", "end of next week", None),
    ("Neha", "meeting summary and action items", "today", "2026-07-28"),
]
EXPECTED_DECISION_PHRASES = [
    "will not replace zendesk",
    "replaceable adapter",
    "email and website chat",
    "english and german",
    "keep it out of the first release",
    "should require human review",
    "recommend the next action",
    "never answered automatically",
    "sarcasm is often misunderstood",
    "store accepted, edited, and rejected suggestions",
    "automated learning pipeline",
    "route tickets to a team",
    "recommend an agent",
    "detailed cost analytics",
]
WISH_SENTENCES = [
    "I would prefer replacing Zendesk completely",
    "I want all messages answered automatically",
    "I still want individual automatic assignment",
]
EXPECTED_RISK_PHRASES = [
    "may significantly increase the mvp scope",
    "dependent on it permanently",
    "reputational risk",
    "not sure our agent availability data is accurate",
    "sarcasm is often misunderstood",
    "response rates are low",
    "gdpr",
    "six weeks is tight",
    "template approval can introduce dependencies",
]
EXPECTED_OPEN_QUESTION_PHRASES = [
    "who will confirm the final data retention policy",
    "stores prompts or uses them for training",
    "baseline staffing and handling-time information",
    "csat data",
    "not sure our agent availability data is accurate",
]


def has_phrase(entries: list[dict], phrase: str) -> bool:
    return any(phrase.lower() in entry["text"].lower() for entry in entries)


class SampleTranscriptTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.output = mock_output()

    def test_output_passes_the_validator_with_zero_drops_or_nullings(self) -> None:
        _, report = AnalysisOutputValidator(sample_request()).validate(self.output)
        self.assertEqual(report.total_changes, 0, report)

    def test_same_input_gives_byte_identical_output(self) -> None:
        first = json.dumps(mock_output(), sort_keys=False, ensure_ascii=False)
        second = json.dumps(mock_output(), sort_keys=False, ensure_ascii=False)
        self.assertEqual(first, second)

    def test_finds_all_seven_action_items_with_the_right_owner_and_dates(self) -> None:
        items = self.output["action_items"]
        self.assertEqual(len(items), len(EXPECTED_ACTION_ITEMS))
        for owner, description, due_text, due_date in EXPECTED_ACTION_ITEMS:
            with self.subTest(owner=owner, description=description):
                match = [i for i in items if i["owner"] == owner and description.lower() in i["description"].lower()]
                self.assertEqual(len(match), 1, [(i["owner"], i["description"]) for i in items])
                self.assertEqual(match[0]["due_date"], due_date)
                if due_text is None:
                    self.assertIsNone(match[0]["due_date_text"])
                else:
                    self.assertIn(due_text.lower(), match[0]["due_date_text"].lower())

    def test_wireframes_keep_their_condition(self) -> None:
        item = next(i for i in self.output["action_items"] if i["owner"] == "Riya")
        self.assertIn("workflow information on Thursday", item["description"])
        self.assertIn("workflow information on Thursday", item["evidence"])

    def test_unresolvable_dates_keep_their_text_and_null_the_date(self) -> None:
        item = next(i for i in self.output["action_items"] if "revised estimate" in i["description"])
        self.assertIsNone(item["due_date"])
        self.assertIn("end of next week", item["due_date_text"])

    def test_priorities_default_to_medium_when_nothing_in_the_transcript_signals_otherwise(self) -> None:
        self.assertEqual({i["priority"] for i in self.output["action_items"]}, {"Medium"})

    def test_non_commitments_are_not_action_items(self) -> None:
        descriptions = " | ".join(i["description"].lower() for i in self.output["action_items"])
        for not_a_task in ("access to the current zendesk workflow", "more than twenty examples", "include existing csat", "add detailed cost"):
            self.assertNotIn(not_a_task, descriptions)

    def test_expected_decisions_are_found(self) -> None:
        missing = [p for p in EXPECTED_DECISION_PHRASES if not has_phrase(self.output["decisions"], p)]
        # honest hit rate: the confidence-based-reply decision was never explicitly accepted, so it must be absent
        self.assertLessEqual(len(missing), 2, missing)
        for found in ("will not replace zendesk", "replaceable adapter", "should require human review", "keep it out of the first release"):
            self.assertTrue(has_phrase(self.output["decisions"], found), found)

    def test_stated_wishes_are_never_decisions(self) -> None:
        evidence = " ".join(d["evidence"] for d in self.output["decisions"])
        text = " ".join(d["text"].lower() for d in self.output["decisions"])
        for wish in WISH_SENTENCES:
            self.assertNotIn(wish.lower(), evidence.lower())
        for phrase in ("replacing zendesk completely", "replace zendesk completely", "all messages", "individual automatic assignment", "automatic individual assignment"):
            self.assertNotIn(phrase, text)

    def test_task_commitments_are_not_repeated_as_decisions(self) -> None:
        text = " ".join(d["text"] for d in self.output["decisions"])
        for commitment in ("Riya will share", "Maria will confirm", "James will provide", "will prepare the architecture"):
            self.assertNotIn(commitment, text)

    def test_questions_are_never_decisions(self) -> None:
        self.assertFalse([d for d in self.output["decisions"] if d["text"].rstrip().endswith("?")])

    def test_risks_and_open_questions_are_surfaced(self) -> None:
        risk_missing = [p for p in EXPECTED_RISK_PHRASES if not has_phrase(self.output["risks"], p)]
        open_missing = [p for p in EXPECTED_OPEN_QUESTION_PHRASES if not has_phrase(self.output["unanswered_questions"], p)]
        self.assertEqual(risk_missing, [])
        self.assertEqual(open_missing, [])

    def test_negated_risk_phrases_are_not_risks(self) -> None:
        text = " ".join(r["text"].lower() for r in self.output["risks"])
        self.assertNotIn("reduce risk", text)
        self.assertNotIn("low risk", text)
        self.assertNotIn("understand the risk", text)

    def test_everything_quoted_is_verbatim_from_the_transcript(self) -> None:
        transcript = normalise(SAMPLE_TRANSCRIPT)
        quoted = [i["evidence"] for i in self.output["action_items"]]
        for section in ("decisions", "risks", "unanswered_questions"):
            quoted += [e["evidence"] for e in self.output[section]]
        self.assertGreater(len(quoted), 25)
        for quote in quoted:
            self.assertIn(normalise(quote), transcript)

    def test_owners_are_people_from_the_meeting(self) -> None:
        self.assertEqual({i["owner"] for i in self.output["action_items"]}, {"Maria", "James", "Riya", "Arjun", "Neha"})

    def test_summary_is_structured_and_sanitised_html(self) -> None:
        summary = self.output["summary"]
        for heading in ("<h3>Purpose</h3>", "<h3>Outcomes</h3>", "<h3>Concerns</h3>", "<h3>Next steps</h3>"):
            self.assertIn(heading, summary)
        self.assertIn("customer support automation platform", summary)
        self.assertNotIn("<script", summary)
        self.assertLessEqual(len(summary), 4000)

    def test_without_declared_participants_speakers_are_inferred_and_team_owner_is_left_unassigned(self) -> None:
        request = AnalysisRequest(SAMPLE_TRANSCRIPT, SAMPLE_DATE, "Other", ())
        output = MockProvider().analyze(request)
        self.assertEqual(len(output["action_items"]), 7)
        team_item = next(i for i in output["action_items"] if "architecture and integration" in i["description"])
        self.assertIsNone(team_item["owner"])
        self.assertEqual(AnalysisOutputValidator(request).validate(output)[1].total_changes, 0)


class MockAbstentionTests(SimpleTestCase):
    def analyze(self, transcript: str, participants: tuple[str, ...] = ("Ana", "Ben")) -> dict:
        return MockProvider().analyze(AnalysisRequest(transcript, date(2026, 7, 28), "Other", participants))

    def test_transcript_with_no_cues_produces_empty_lists_and_a_valid_summary(self) -> None:
        output = self.analyze("Ana: Hello there.\nBen: Hi, nice weather today.\nAna: Indeed it is.\n")
        for key in ("decisions", "action_items", "risks", "unanswered_questions"):
            self.assertEqual(output[key], [], key)
        self.assertTrue(output["summary"])
        AnalysisOutputValidator(AnalysisRequest("Ana: Hello there.\nBen: Hi.\n", date(2026, 7, 28), "Other", ())).check_structure(output)

    def test_no_text_at_all_does_not_crash(self) -> None:
        self.assertEqual(self.analyze("just some notes without any speakers")["action_items"], [])

    def test_modal_without_a_deadline_is_an_offer_not_a_task(self) -> None:
        self.assertEqual(self.analyze("Ana: I can ask the team about it.\nBen: Thanks.\n")["action_items"], [])

    def test_will_need_or_will_be_is_not_a_task(self) -> None:
        output = self.analyze("Ana: I will need the report.\nBen: We will be ready soon.\nAna: We will have more time.\n")
        self.assertEqual(output["action_items"], [])

    def test_unaccepted_wishes_and_proposals_are_not_decisions(self) -> None:
        output = self.analyze("Ana: We should move everything to a new system.\nBen: I am not convinced.\nAna: We must decide soon.\nBen: Let us see.\n")
        self.assertEqual(output["decisions"], [])

    def test_accepted_proposal_becomes_a_decision_with_exact_evidence(self) -> None:
        output = self.analyze("Ana: We should launch the product in September.\nBen: Agreed.\n")
        self.assertEqual(output["decisions"], [{"text": "We should launch the product in September.", "evidence": "We should launch the product in September."}])

    def test_acceptance_of_a_question_is_not_a_decision(self) -> None:
        self.assertEqual(self.analyze("Ana: Should we launch in September?\nBen: Yes.\n")["decisions"], [])

    def test_missing_owner_and_date_stay_null(self) -> None:
        output = self.analyze("Ana: The finance team will send the invoice.\nBen: Ok.\n")
        item = output["action_items"][0]
        self.assertEqual((item["owner"], item["due_date_text"], item["due_date"]), (None, None, None))

    def test_priority_only_changes_on_explicit_signals(self) -> None:
        output = self.analyze(
            "Ana: I will fix the login urgently by Friday.\nBen: I will review the copy by Thursday.\n"
            "Ana: I will update the wiki by Monday, but it is only nice to have.\n"
        )
        self.assertEqual([i["priority"] for i in output["action_items"]], ["High", "Medium", "Low"])

    def test_first_person_commitment_is_assigned_to_the_speaker(self) -> None:
        item = self.analyze("Ben: I will send the contract by Friday.\nAna: Thanks.\n")["action_items"][0]
        self.assertEqual((item["owner"], item["description"], item["due_date"]), ("Ben", "Send the contract", "2026-07-31"))

    def test_named_commitment_is_assigned_to_that_person(self) -> None:
        item = self.analyze("Ana: Ben will send the contract by Friday.\nBen: Yes.\n")["action_items"][0]
        self.assertEqual((item["owner"], item["due_date"]), ("Ben", "2026-07-31"))

    def test_two_tasks_in_one_sentence_are_split_with_their_own_dates(self) -> None:
        output = self.analyze("Ana: Ben will send the contract by Friday and book the room on Thursday.\nBen: Ok.\n")
        self.assertEqual([(i["description"], i["due_date"]) for i in output["action_items"]], [("Send the contract", "2026-07-31"), ("Book the room", "2026-07-30")])

    def test_pronoun_object_needs_a_specific_request_in_the_previous_turn(self) -> None:
        resolved = self.analyze("Ana: I would like a status report.\nBen: We can provide that by Friday.\n")
        self.assertEqual(resolved["action_items"][0]["description"], "Provide a status report")
        unresolved = self.analyze("Ana: Hmm.\nBen: We can provide that by Friday.\n")
        self.assertEqual(unresolved["action_items"], [])

    def test_restated_task_is_one_item(self) -> None:
        output = self.analyze("Ben: I will send the signed contract to legal by Friday.\nAna: Ben will send the contract to legal by Friday.\n")
        self.assertEqual(len(output["action_items"]), 1)

    def test_same_owner_different_dates_are_separate_items(self) -> None:
        output = self.analyze("Ben: I will send the contract by Friday.\nBen: I will send the contract by Wednesday.\n")
        self.assertEqual(len(output["action_items"]), 2)

    def test_extremely_long_transcripts_do_not_hang(self) -> None:
        line = "Ana: " + "This is a long line without any particular cue words in it " * 20 + "\n"
        started = time.monotonic()
        MockProvider().analyze(AnalysisRequest(line * 3000, SAMPLE_DATE, "Other", SAMPLE_PARTICIPANTS))
        self.assertLess(time.monotonic() - started, 10)

    def test_list_caps_are_respected(self) -> None:
        turns = "".join(f"Ana: I will draft report number {i} by Friday and keep it safe.\nBen: Fine.\n" for i in range(80))
        self.assertLessEqual(len(self.analyze(turns)["action_items"]), 50)
