"""Cue vocabulary for the deterministic mock provider. Plain regexes: no model, no network, no randomness."""
import re

from tracker_apps.ai_service.date_resolver import WEEKDAYS

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"‘'(€])")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")

DEADLINE = re.compile(
    r"\b(?:(?:by|on|before|until)\s+)?(?:"
    r"(?:the\s+)?end of\s+(?:the\s+|next\s+|this\s+)?(?:week|month|day)"
    rf"|(?:next\s+)?(?:{'|'.join(WEEKDAYS)})(?:\s+(?:morning|afternoon|evening))?"
    r"|today|tomorrow|(?:next|this)\s+week)\b",
    re.IGNORECASE,
)
CONDITION_LEAD = re.compile(r"^(?P<lead>If|Once|When)\s+(?P<cond>[^,]+),\s*(?P<main>.+)$")
FIRST_PERSON = re.compile(r"^(?:(?:and|but|so|okay|ok|sure|yes)[, ]+)?(?P<who>I|We)(?:'ll|\s+(?:will|can|shall))\s+(?P<body>.+)$")
TEAM_SUBJECT = re.compile(r"^(?:Our|The|My)\s+(?P<team>[A-Za-z][A-Za-z ]*?)\s+team\s+will\s+(?P<body>.+)$")
NAMED_SUBJECT = "^(?P<who>{names})\\s+will\\s+(?P<body>.+)$"
CAN_MODAL = re.compile(r"^(?:(?:and|but|so|okay|ok|sure|yes)[, ]+)?(?:I|We)\s+can\b", re.IGNORECASE)

COMMIT_VERBS = {
    "arrange", "ask", "book", "build", "call", "check", "circulate", "collect", "compile", "confirm", "contact",
    "coordinate", "create", "define", "deliver", "design", "develop", "document", "draft", "email", "finalise",
    "finalize", "fix", "follow", "forward", "gather", "implement", "investigate", "look", "mask", "notify",
    "organise", "organize", "prepare", "prototype", "provide", "remove", "report", "research", "review", "schedule",
    "send", "set", "share", "submit", "summarise", "summarize", "test", "update", "write",
}
CONJUNCT_SPLIT = re.compile(r"\s+and\s+(?=(?:" + "|".join(sorted(COMMIT_VERBS)) + r")\b)")
PRONOUN_OBJECT = re.compile(r"^(?P<verb>\w+)\s+(?:that|this|it)$", re.IGNORECASE)
REQUESTED_ITEM = re.compile(r"\bI\s+(?:would\s+(?:also\s+)?like|want|need)\s+(?P<item>(?:a|an|the)\s+.+?)(?:\s+(?:once|when|as soon)\b|[.?!]|$)", re.IGNORECASE)

HIGH_PRIORITY = re.compile(r"\b(?:urgent(?:ly)?|asap|immediately|critical|top priority|high priority|no later than|hard deadline)\b", re.IGNORECASE)
LOW_PRIORITY = re.compile(r"\b(?:nice to have|low priority|when time permits|if time permits)\b", re.IGNORECASE)

ACKNOWLEDGEMENT = re.compile(
    r"^(?:agreed|i agree|okay|ok|all right|alright|fine|good point|good|perfect|exactly|understood|yes"
    r"|that sounds (?:good|reasonable|great)|sounds good|that matches(?: my understanding)?|that would (?:already )?help)\b",
    re.IGNORECASE,
)
DECISION_CUE = re.compile(
    r"\b(?:should|must|will)\b|\blet(?:'s| us)\b|\b(?:we|i) (?:recommend|suggest)\b|\bplease ensure\b|\b(?:we|the mvp|it) (?:can|could)\b",
    re.IGNORECASE,
)
CONTINUES_PREVIOUS = re.compile(r"^(?:It|They|This|That|These|Those)\b")
MIN_DECISION_WORDS = 6

RISK_CUE = re.compile(
    r"\brisks?\b|\brisky\b|\bconcerns?\b|\bnot sure\b|\bis tight\b|\bdependen(?:t|cy|cies)\b|\bmisunderstood?\b"
    r"|\bmay (?:\w+ )?(?:create|increase|cause|introduce|misunderstand)\b|\bcan introduce\b|\binaccurate\b"
    r"|\bresponse rates? (?:are|is) low\b|\bgdpr\b|\bdata protection\b",
    re.IGNORECASE,
)
RISK_NEGATED = re.compile(r"\b(?:(?:reduce|avoid|lower|mitigate|low|minimi[sz]e)[ -]|understand the )risks?\b", re.IGNORECASE)
MIN_RISK_WORDS = 6

OPEN_QUESTION_CUE = re.compile(
    r"\b(?:we|i) need to (?:know|confirm|find out|check)\b|\bnot sure\b|\bunsure\b|\bnot certain\b"
    r"|\bto be confirmed\b|\btbc\b|\btbd\b|\bif available\b|\b(?:will )?requires?\b.*\b(?:information|data)\b",
    re.IGNORECASE,
)
PENDING_REPLY = re.compile(r"\bI(?:'ll| will)\s+(?:check|confirm|find out|get back|look into|follow up)\b", re.IGNORECASE)
PURPOSE = re.compile(r"\bpurpose of (?:today.s|this|the) meeting\b", re.IGNORECASE)

MAX_DISCUSSION_POINTS_USED = 10
CONTENT_STOPWORDS = {
    "the", "and", "with", "our", "for", "that", "this", "from", "into", "will", "have", "about", "their", "your", "them",
}
