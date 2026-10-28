import html
import re
from dataclasses import dataclass
from datetime import date

from tracker.constants import Constants
from tracker_apps.ai_service import schemas
from tracker_apps.ai_service.date_resolver import DateResolver
from tracker_apps.ai_service.providers import mock_rules as rules
from tracker_apps.ai_service.providers.base import AnalysisRequest, MeetingAnalysisProvider
from tracker_apps.ai_service.text_utils import SPEAKER_LINE, normalise, participant_name, participant_role, speaker_labels


@dataclass(frozen=True)
class Turn:
    index: int
    speaker: str
    text: str

    @property
    def sentences(self) -> list[str]:
        return [sentence.strip() for sentence in rules.SENTENCE_SPLIT.split(self.text) if sentence.strip()]


def clip(text: str, limit: int) -> str:
    """Cut at a word boundary. Used on our own wording (descriptions), never on evidence quotes."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")


def content_words(text: str) -> set[str]:
    return {word.lower() for word in rules.WORD.findall(text) if len(word) > 3 and word.lower() not in rules.CONTENT_STOPWORDS}


class MockProvider(MeetingAnalysisProvider):
    """Deterministic, rule-based analysis. It abstains when no cue is present: no cue, no item.

    Same input gives byte-identical output; the only date it reads is the meeting date it was given.
    """

    name = Constants.ai_provider_mock
    model = Constants.mock_provider_model

    def analyze(self, request: AnalysisRequest) -> dict:
        turns = self.parse_turns(request)
        roles = {participant_name(entry): participant_role(entry) for entry in request.participants}
        commitments = self.find_commitments(turns, request.meeting_date, roles)
        action_items = self.merge_restatements(commitments, request.meeting_date)
        commitment_sentences = {item["evidence"] for item in commitments}
        decisions = self.extract_decisions(turns, commitment_sentences)
        risks = self.extract_risks(turns)
        unanswered = self.extract_unanswered(turns)
        discussion_points = self.extract_discussion_points(turns)
        return {
            "summary": self.build_summary(turns, discussion_points, decisions, risks, action_items),
            "discussion_points": discussion_points,
            "decisions": decisions[: schemas.MAX_DECISIONS],
            "action_items": action_items[: schemas.MAX_ACTION_ITEMS],
            "risks": risks[: schemas.MAX_RISKS],
            "unanswered_questions": unanswered[: schemas.MAX_QUESTIONS],
        }

    # ---- parsing -----------------------------------------------------------------------------

    @staticmethod
    def parse_turns(request: AnalysisRequest) -> list[Turn]:
        speakers = {participant_name(entry) for entry in request.participants if participant_name(entry)}
        speakers |= {name.split()[0] for name in list(speakers)}
        speakers |= set(speaker_labels(request.transcript))
        turns: list[Turn] = []
        speaker, parts = "", []

        def close() -> None:
            if speaker and parts:
                turns.append(Turn(len(turns), speaker, " ".join(parts)))

        for line in request.transcript.splitlines():
            stripped = line.strip()
            match = SPEAKER_LINE.match(stripped)
            if match and match.group(1) in speakers:
                close()
                speaker, parts = match.group(1), [match.group(2).strip()]
            elif speaker and stripped and not stripped.isdigit():
                parts.append(stripped)
        close()
        return turns

    # ---- action items ------------------------------------------------------------------------

    def find_commitments(self, turns: list[Turn], meeting_date: date, roles: dict[str, str]) -> list[dict]:
        names = sorted({turn.speaker for turn in turns} | {name for name in roles if name}, key=len, reverse=True)
        named_subject = re.compile(rules.NAMED_SUBJECT.format(names="|".join(re.escape(name) for name in names))) if names else None
        found: list[dict] = []
        for position, turn in enumerate(turns):
            previous = turns[position - 1] if position else None
            for sentence in turn.sentences:
                found.extend(self.items_from_sentence(sentence, turn, previous, meeting_date, roles, named_subject))
        return found

    def items_from_sentence(self, sentence, turn, previous, meeting_date, roles, named_subject) -> list[dict]:
        if sentence.endswith("?"):
            return []
        condition = ""
        main = sentence
        lead = rules.CONDITION_LEAD.match(sentence)
        if lead:
            condition, main = f"{lead.group('lead').lower()} {lead.group('cond').strip()}", lead.group("main")
        owner, body = self.subject_and_body(main, turn, roles, named_subject)
        if body is None:
            return []
        needs_deadline = bool(rules.CAN_MODAL.match(main))
        items = []
        for segment in rules.CONJUNCT_SPLIT.split(body.rstrip(".!")):
            item = self.build_item(segment, owner, condition, sentence, previous, meeting_date, needs_deadline)
            if item:
                items.append(item)
        return items

    @staticmethod
    def subject_and_body(main: str, turn: Turn, roles: dict[str, str], named_subject) -> tuple[str | None, str | None]:
        first_person = rules.FIRST_PERSON.match(main)
        if first_person:
            return turn.speaker, first_person.group("body")
        team = rules.TEAM_SUBJECT.match(main)
        if team:
            return MockProvider.owner_for_team(team.group("team"), roles), team.group("body")
        named = named_subject.match(main) if named_subject else None
        if named:
            return named.group("who"), named.group("body")
        return None, None

    @staticmethod
    def owner_for_team(team: str, roles: dict[str, str]) -> str | None:
        """A team phrase maps to a person only when exactly one declared role mentions it."""
        wanted = {word.lower() for word in rules.WORD.findall(team)}
        matches = [name for name, role in roles.items() if name and wanted & {word.lower() for word in rules.WORD.findall(role)}]
        return matches[0] if len(matches) == 1 else None

    def build_item(self, segment, owner, condition, sentence, previous, meeting_date, needs_deadline) -> dict | None:
        deadline = rules.DEADLINE.search(segment)
        if needs_deadline and deadline is None:
            return None
        due_text = deadline.group(0).strip() if deadline else None
        action = (segment[: deadline.start()] + " " + segment[deadline.end() :]).strip(" ,;") if deadline else segment.strip(" ,;")
        action = re.sub(r"\s+", " ", action)
        words = action.split()
        if not words or words[0].lower() not in rules.COMMIT_VERBS:
            return None
        pronoun = rules.PRONOUN_OBJECT.match(action)
        if pronoun:
            action = self.resolve_pronoun_object(pronoun.group("verb"), previous)
            if action is None:
                return None
        description = action[0].upper() + action[1:]
        if condition:
            description = f"{description} ({condition})"
        due_date = DateResolver.resolve(due_text, meeting_date) if due_text else None
        return {
            "description": clip(description, schemas.MAX_TEXT),
            "owner": owner,
            "due_date_text": clip(due_text, schemas.MAX_DUE_TEXT) if due_text else None,
            "due_date": due_date.isoformat() if due_date else None,
            "priority": self.priority_for(sentence),
            "evidence": sentence[: schemas.MAX_EVIDENCE],
        }

    @staticmethod
    def resolve_pronoun_object(verb: str, previous) -> str | None:
        """'We can provide that ...' only counts when the previous turn asked for something specific."""
        requested = rules.REQUESTED_ITEM.search(previous.text) if previous else None
        return f"{verb.lower()} {requested.group('item').strip()}" if requested else None

    @staticmethod
    def priority_for(sentence: str) -> str:
        if rules.HIGH_PRIORITY.search(sentence):
            return "High"
        if rules.LOW_PRIORITY.search(sentence):
            return "Low"
        return "Medium"

    @staticmethod
    def merge_restatements(items: list[dict], meeting_date: date) -> list[dict]:
        """A later restatement of the same task (same owner, same due date, shared wording) is one item:
        keep the more detailed description and the more specific due text."""
        merged: list[dict] = []
        for item in items:
            twin = next((other for other in merged if MockProvider.same_task(other, item)), None)
            if twin is None:
                merged.append(dict(item))
                continue
            if len(item["description"]) > len(twin["description"]):
                twin.update(description=item["description"], evidence=item["evidence"], priority=item["priority"])
            if len(item["due_date_text"] or "") > len(twin["due_date_text"] or ""):
                twin["due_date_text"] = item["due_date_text"]
        return merged

    @staticmethod
    def same_task(first: dict, second: dict) -> bool:
        if (first["owner"] or "") != (second["owner"] or "") or first["due_date"] != second["due_date"]:
            return False
        if first["due_date"] is None and normalise(first["due_date_text"] or "") != normalise(second["due_date_text"] or ""):
            return False
        return bool(content_words(first["description"]) & content_words(second["description"]))

    # ---- decisions ---------------------------------------------------------------------------

    def extract_decisions(self, turns: list[Turn], commitment_sentences: set[str]) -> list[dict]:
        """A decision is a proposal that another speaker explicitly accepted in the very next turn.
        Wishes nobody accepted, questions, and task commitments are never decisions."""
        decisions: list[dict] = []
        seen: set[str] = set()
        for position in range(1, len(turns)):
            turn, proposer = turns[position], turns[position - 1]
            if turn.speaker == proposer.speaker or not rules.ACKNOWLEDGEMENT.match(turn.text):
                continue
            for group in self.proposal_groups(proposer, commitment_sentences):
                text = " ".join(group)
                if normalise(text) not in seen:
                    seen.add(normalise(text))
                    decisions.append({"text": clip(text, schemas.MAX_TEXT), "evidence": text[: schemas.MAX_EVIDENCE]})
        return decisions

    @staticmethod
    def proposal_groups(turn: Turn, commitment_sentences: set[str]) -> list[list[str]]:
        groups: list[list[str]] = []
        previous_was_proposal = False
        for sentence in turn.sentences:
            is_proposal = (
                not sentence.endswith("?")
                and sentence not in commitment_sentences
                and len(sentence.split()) >= rules.MIN_DECISION_WORDS
                and bool(rules.DECISION_CUE.search(sentence))
            )
            if is_proposal and previous_was_proposal and rules.CONTINUES_PREVIOUS.match(sentence):
                groups[-1].append(sentence)
            elif is_proposal:
                groups.append([sentence])
            previous_was_proposal = is_proposal
        return groups

    # ---- risks, open questions, discussion points ----------------------------------------------

    @staticmethod
    def extract_risks(turns: list[Turn]) -> list[dict]:
        risks, seen = [], set()
        for turn in turns:
            for sentence in turn.sentences:
                if sentence.endswith("?") or len(sentence.split()) < rules.MIN_RISK_WORDS:
                    continue
                if rules.RISK_CUE.search(sentence) and not rules.RISK_NEGATED.search(sentence) and normalise(sentence) not in seen:
                    seen.add(normalise(sentence))
                    risks.append({"text": clip(sentence, schemas.MAX_TEXT), "evidence": sentence[: schemas.MAX_EVIDENCE]})
        return risks

    @staticmethod
    def extract_unanswered(turns: list[Turn]) -> list[dict]:
        found, seen = [], set()

        def add(sentence: str) -> None:
            if normalise(sentence) not in seen:
                seen.add(normalise(sentence))
                found.append({"text": clip(sentence, schemas.MAX_TEXT), "evidence": sentence[: schemas.MAX_EVIDENCE]})

        for position, turn in enumerate(turns):
            reply = turns[position + 1] if position + 1 < len(turns) else None
            for sentence in turn.sentences:
                if sentence.endswith("?"):
                    if reply and reply.speaker != turn.speaker and rules.PENDING_REPLY.search(reply.text):
                        add(sentence)
                elif rules.OPEN_QUESTION_CUE.search(sentence):
                    add(sentence)
        return found

    @staticmethod
    def extract_discussion_points(turns: list[Turn]) -> list[str]:
        points: list[str] = []
        for turn in turns:
            for sentence in turn.sentences:
                if sentence.endswith("?") and len(sentence.split()) >= 5 and sentence not in points:
                    points.append(clip(sentence, schemas.MAX_TEXT))
        return points[: rules.MAX_DISCUSSION_POINTS_USED]

    # ---- summary -----------------------------------------------------------------------------

    @staticmethod
    def build_summary(turns, discussion_points, decisions, risks, action_items) -> str:
        sections: list[str] = []
        purpose = next((s for t in turns[:3] for s in t.sentences if rules.PURPOSE.search(s)), None)
        if purpose:
            sections.append(f"<h3>Purpose</h3><p>{html.escape(purpose)}</p>")
        for title, entries in (
            ("Key discussion points", discussion_points[:5]),
            ("Outcomes", [decision["text"] for decision in decisions[:6]]),
            ("Concerns", [risk["text"] for risk in risks[:5]]),
            ("Next steps", [MockProvider.describe_action(item) for item in action_items[:8]]),
        ):
            if entries:
                items = "".join(f"<li>{html.escape(entry)}</li>" for entry in entries)
                sections.append(f"<h3>{title}</h3><ul>{items}</ul>")
        body = "".join(sections) or "<p>No decisions, action items or concerns could be identified in this transcript.</p>"
        return clip(body, schemas.MAX_SUMMARY) if len(body) <= schemas.MAX_SUMMARY else MockProvider.shrink_summary(sections)

    @staticmethod
    def shrink_summary(sections: list[str]) -> str:
        kept: list[str] = []
        for section in sections:
            if len("".join(kept + [section])) > schemas.MAX_SUMMARY:
                break
            kept.append(section)
        return "".join(kept)

    @staticmethod
    def describe_action(item: dict) -> str:
        owner = item["owner"] or "Unassigned"
        due = item["due_date_text"] or "no due date"
        return f"{owner}: {item['description']} ({due})"
