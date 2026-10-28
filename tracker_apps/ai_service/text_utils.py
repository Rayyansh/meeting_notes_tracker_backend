import re

QUOTE_TABLE = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
SPEAKER_LINE = re.compile(r"^([A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*){0,2}):[ \t]*(.*)$")
PARTICIPANT_SPLIT = re.compile(r"\s+[—–-]\s+|\s*\(|,")
MIN_SPEAKER_TURNS = 2


def normalise(text: str) -> str:
    """Whitespace, quote-style and case insensitive form used for every grounding comparison."""
    return re.sub(r"\s+", " ", text.translate(QUOTE_TABLE)).strip().casefold()


def participant_name(entry: str) -> str:
    """'Arjun - Zignuts Technical Lead' -> 'Arjun'."""
    return PARTICIPANT_SPLIT.split(entry.strip(), maxsplit=1)[0].strip()


def participant_role(entry: str) -> str:
    parts = PARTICIPANT_SPLIT.split(entry.strip(), maxsplit=1)
    return parts[1].strip(" )") if len(parts) > 1 else ""


def speaker_labels(transcript: str) -> list[str]:
    """Labels that open a line ('Maria: ...') and occur at least twice, so header lines like 'Date:' are ignored."""
    counts: dict[str, int] = {}
    for line in transcript.splitlines():
        match = SPEAKER_LINE.match(line.strip())
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return [label for label, count in counts.items() if count >= MIN_SPEAKER_TURNS]


def known_names(participants: tuple[str, ...] | list[str], transcript: str) -> set[str]:
    """Normalised names an action-item owner may legitimately have: declared participants or transcript speakers."""
    names = [participant_name(entry) for entry in participants] + speaker_labels(transcript)
    known: set[str] = set()
    for name in filter(None, names):
        known.add(normalise(name))
        known.add(normalise(name.split()[0]))
    return known
