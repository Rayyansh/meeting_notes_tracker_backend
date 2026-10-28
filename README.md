# AI Meeting Notes & Action Tracker: Backend

A Django REST API for the **post-meeting** workflow: register and log in, create a meeting, supply a transcript (pasted text or a `.txt` upload), generate a structured analysis, review and edit the action items, track them across meetings, and see dashboard statistics.

The AI part runs through a replaceable provider interface. The only provider that exists is a **deterministic, rule-based mock** that works offline with no key. No real LLM is connected (see [Not completed](#not-completed)).

> **Status:** the API surface is complete and covered by 402 automated tests. A security and error-handling hardening pass, Docker packaging, the AI usage report and the demo script are **not done yet**; see [Not completed](#not-completed).

## Contents

1. [Stack](#stack)
2. [Setup](#setup)
3. [Environment variables](#environment-variables)
4. [Architecture](#architecture)
5. [Database design](#database-design)
6. [API overview](#api-overview)
7. [How the AI analysis works](#how-the-ai-analysis-works)
8. [Adding a real AI provider](#adding-a-real-ai-provider)
9. [Assumptions](#assumptions)
10. [Completed](#completed)
11. [Not completed](#not-completed)
12. [Limitations](#limitations)
13. [Future improvements](#future-improvements)

## Stack

| Concern | Choice |
|---|---|
| Language / framework | Python 3.12, Django 5.2, Django REST Framework 3.16 |
| Database | SQLite 3 only (WAL mode, busy timeout, `IMMEDIATE` transactions) |
| Auth | Email + password, `djangorestframework-simplejwt` (15 min access token, 7 day rotating refresh token, logout blacklists the refresh token) |
| API docs | `drf-spectacular` (OpenAPI schema + Swagger UI) |
| Config | `python-decouple` (everything from environment variables) |
| Other | `django-cors-headers`, `jsonschema` (AI output validation), `nh3` (HTML sanitiser), `python-dateutil`, `gunicorn` |

Versions are pinned in [requirements.txt](requirements.txt). The project does not use pandas, numpy, Pillow, PostgreSQL, Redis or Celery. AI analysis runs synchronously inside the request.

## Setup

Requires Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: SECRET_KEY is required and has no default
python -c "import secrets; print(secrets.token_urlsafe(50))"   # use the output as SECRET_KEY

python manage.py migrate
python manage.py runserver
```

- API root: `http://127.0.0.1:8000/`
- OpenAPI schema: `/api/schema/`, Swagger UI: `/api/schema/swagger-ui/`. These are **public only when `DEBUG=True`**; otherwise they require a bearer token.
- For local development set `DEBUG=True` in `.env`. The default is `False`.

Run the tests (no network, no key needed):

```bash
python manage.py test
```

Last recorded result: `Ran 402 tests ... OK`, with `manage.py check`, `makemigrations --check` and `spectacular` all clean.

## Environment variables

All settings are read in [tracker/config.py](tracker/config.py). Copy [.env.example](.env.example) to `.env` (git-ignored). Never commit `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | none, **required** | Django signing key |
| `DEBUG` | `False` | Debug mode. Also makes the OpenAPI pages public |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated origins. "Allow all" is never enabled |
| `DB_PATH` | `db.sqlite3` | SQLite file (relative paths resolve against the project root) |
| `DB_TIMEOUT_SECONDS` | `20` | SQLite busy timeout |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | `15` / `7` | Token lifetimes |
| `LOGIN_THROTTLE_RATE` / `REGISTER_THROTTLE_RATE` | `10/min` / `5/min` | Per-client throttles (login also covers token refresh) |
| `PAGINATION_COUNT` / `MAX_PAGE_SIZE` | `10` / `100` | Default and maximum page size |
| `UPLOAD_MAX_BYTES` | `1048576` | Maximum transcript size, in bytes for files and characters for pasted text |
| `AI_PROVIDER` | `mock` | Only `mock` is implemented. Any other value makes an analysis fail cleanly (it never falls back to the mock) |
| `AI_TIMEOUT_SECONDS` | `30` | Used for the stale-`processing` window (timeout + 60 s) |
| `AI_MAX_TRANSCRIPT_CHARS` | `100000` | Longer transcripts are rejected with 400 before analysis |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | empty | Read by the config but **unused**: there is no Gemini provider |
| `LOG_LEVEL` | `INFO` | Python log level |
| `SECURE_SSL_REDIRECT` | `False` | When true (and `DEBUG` is off) also marks session and CSRF cookies secure |

## Architecture

The project follows the layout and request lifecycle of an existing internal Django codebase (project package `tracker/`, apps under `tracker_apps/`), without that codebase's known defects: no hardcoded secrets, `DEBUG` off by default, authentication required by default, unknown errors never echoed to the client, no plaintext-password fallback, whitelisted sort and filter fields.

```
tracker/                 settings, config (env), constants (messages), urls
tracker_apps/
  common/                envelope, pagination, exception mapping, request validation, clock, sanitiser
  authentication/        user model, JWT auth, register/login/logout/refresh/me
  meeting/               meetings, transcript input, analysis endpoints, MeetingAnalysis model
  action_item/           action items, filters, the shared overdue rule
  ai_service/            provider interface, mock provider, validators, analysis service
  dashboard/             summary statistics
```

Inside each app: `models/`, `controllers/` (routing + OpenAPI only), `views/` (business logic), `serializers/{request,response}/`, `dataclasses/request/`, `utils.py` (column to camelCase mapping), `urls.py`, `tests`.

**Request lifecycle** (identical for every endpoint):

1. `urls.py` maps `<resource>/<action>/` to a controller method.
2. The controller is decorated with `@extend_schema`, `@api_view`, `@permission_classes` and `@SerializerValidations(...)`. It only calls the view.
3. `SerializerValidations` merges the URL-decoded query string and the body into a new dict (it never mutates `request.data`), validates it, and attaches a typed dataclass as `request.params` together with `user_id`.
4. The view method (`*_extract`) is wrapped by `Common(...).exception_handler` and calls static methods on the model.
5. The response uses one envelope. Unknown exceptions are logged server-side and returned as a generic 500, whatever `DEBUG` is.

**Response envelope** (every endpoint, including auth and errors):

```jsonc
{ "status": true,  "message": "...", "data": ... }
{ "status": false, "message": "...", "error": [ {"field": "title", "message": "Meeting title is required."} ] }
```

Request bodies use `snake_case`; response fields use `camelCase`. Lists return `data: {"data": [...], "presentPage", "totalPage", "nextPageUrl"?, "previousPageUrl"?}`. An empty list or a search with no matches is `200` with `data: []`, never an error. Dates are ISO `YYYY-MM-DD`.

**Ownership.** Every query on meetings, analyses and action items is built from an owner-scoped helper (`Meeting.objects.owned_by(user)`, `ActionItem.objects.owned_by(user)`, which scopes through `meeting.owner`). A record that belongs to someone else returns `404`, identical to a record that does not exist. Foreign ids on writes (for example `meeting_id` when creating an action item) are re-verified.

## Database design

SQLite, created by committed migrations. Primary keys are explicit (`<entity>_id`) and tables have explicit `db_table` names. `meetings`, `meeting_analyses` and `action_items` carry `created_at` and `updated_at`; `users` has `created_at` only.

| Table | Purpose and notable columns |
|---|---|
| `users` | `user_id`, unique lower-cased `email`, `name`, hashed `password`, `is_active`, `created_at` |
| `meetings` | `meeting_id`, `owner` FK (cascade), `title` (200), `meeting_date`, `meeting_type` (7 fixed values), `participants` (JSON list), `transcript`, `transcript_source` (`text`/`file`), `transcript_filename`, `notes` (sanitised HTML), `analysis_status` (`not_started`/`processing`/`completed`/`failed`), `analysis_error_code`, `analyzed_at`, `transcript_changed_since_analysis`, timestamps. Indexes on `(owner, -created_at)` and `(owner, meeting_date)` |
| `meeting_analyses` | One row per meeting (latest only): sanitised-HTML `summary`, JSON `discussion_points`, `decisions`, `risks`, `unanswered_questions`, `provider_name`, `provider_model`, timestamps |
| `action_items` | `meeting` FK (cascade), `description` (500), `owner_name` (blank allowed), `due_date`, `due_date_text` (the phrase as spoken), `priority`, `status`, `source` (`ai`/`manual`), `evidence_quote`, `is_edited`, `completed_at`, timestamps. Indexes on `(meeting, status)` and `due_date` |
| `token_blacklist_*` | simplejwt's tables for blacklisted refresh tokens |

Design decisions worth knowing:

- **Overdue is never stored.** It is `due_date < today AND status != Completed`, defined once in [overdue.py](tracker_apps/action_item/overdue.py). The list filter, the `isOverdue` flag in responses and the dashboard all use that definition, and "today" comes from an injectable clock so tests are deterministic.
- **Missing values stay missing.** Unknown owners and dates are stored blank/NULL and returned as `null`; the API never stores invented placeholders. (A UI is expected to show "Unassigned" / "Not specified".)
- **Action items have no owner column of their own.** Access flows through `meeting.owner`.
- `transcript_changed_since_analysis` is one column added beyond the original model so a transcript edit after analysis can be flagged without discarding the analysis.

## API overview

All endpoints except register and login need `Authorization: Bearer <access token>`. The full contract is in the Swagger UI.

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register/` | `email`, `name`, `password`, `confirm_password`. 201, no tokens (log in next). Password rules use Django's validators |
| POST | `/auth/login/` | Returns `access`, `refresh`, `user`. One identical 401 for unknown email, wrong password and inactive user. Throttled |
| POST | `/auth/logout/` | Blacklists the given `refresh` token (must belong to the caller) |
| POST | `/auth/token/refresh/` | Rotates the refresh token; the old one is blacklisted |
| GET | `/auth/me/` | Current user |
| POST | `/meeting/create/` | JSON (`transcript`) **or** multipart (`transcript_file`, `.txt` only); exactly one transcript source |
| PUT | `/meeting/update/` | Partial update. Changing the transcript after an analysis keeps the analysis and sets `transcriptChangedSinceAnalysis`, or resets it with `reset_analysis=true`; 409 while an analysis is running |
| GET | `/meeting/get/?meeting_id=` | Full detail: full transcript, notes, analysis, action items |
| GET | `/meeting/get_all/` | `search_key` (title, participants, notes), `meeting_type`, `from_date`/`to_date`, `sort_by`, `sort_order`, `page_num`, `limit`, `values` |
| DELETE | `/meeting/delete/?meeting_id=` | Hard delete; cascades to analysis and action items. A second delete is 404 |
| POST | `/meeting/analyze/` | `{meeting_id}`. Runs the analysis synchronously; 409 if one is already running |
| GET | `/meeting/analysis/get/?meeting_id=` | Analysis plus status, so a client can show processing / failed states |
| PUT | `/meeting/analysis/update/` | Edit the summary (sanitised). The other analysis fields are read-only |
| POST | `/action_item/create/` | Manual action item; `meeting_id` must be yours |
| PUT | `/action_item/update/` | Partial update. Any real change sets `isEdited`; moving to or from `Completed` sets or clears `completedAt` |
| GET | `/action_item/get/?action_item_id=` | One item |
| GET | `/action_item/get_all/` | Filters `meeting_id`, `status`, `priority`, `owner`, `is_overdue`, `from_date`/`to_date` (due date), `search_key`; sort `due_date` (default, undated last), `created_at`, `updated_at`, `priority`, `status`, `description`, `owner_name` |
| DELETE | `/action_item/delete/?action_item_id=` | |
| GET | `/dashboard/summary/` | Counts (total meetings and items, open, in progress, blocked, completed, unfinished, overdue), counts by priority, 5 newest meetings, 5 soonest-due unfinished items with a due date (overdue ones come first) |
| GET | `/api/schema/`, `/api/schema/swagger-ui/` | OpenAPI (public only when `DEBUG=True`) |

Sort fields and `values` are whitelisted per resource; unknown names return `400`. Meeting types: Client Meeting, Sales Meeting, Project Meeting, Internal Meeting, Requirement Discussion, Retrospective, Other.

**Transcript uploads.** Only `.txt` (any letter case). The size is checked before the file is read (413), the content must be UTF-8 without NUL bytes (415; a UTF-8 BOM is accepted), empty files are rejected (400), the client's `Content-Type` is never trusted, and the client filename is stored only as a sanitised display label, never used as a path.

**Dashboard counts add up:** `open + inProgress + blocked + completed == totalActionItems`, and `open` means status exactly `Open`. The by-priority counts cover all items and sum to the total.

## How the AI analysis works

`POST /meeting/analyze/` runs, in order: ownership check, transcript length check, an atomic switch of the meeting to `processing` (a second concurrent call gets 409), the provider call, validation, and a single atomic save.

**Provider output** is a JSON object with `summary` (HTML), `discussion_points`, `decisions`, `action_items`, `risks` and `unanswered_questions`. Every decision, risk, question and action item carries an `evidence` quote.

**Validation** (applied to every provider, before anything is saved):

- *Structural failure rejects the whole result* and saves nothing: wrong types, unknown keys, bad enums, over-length strings or lists, a missing or empty summary, malformed output. The meeting becomes `failed` with `AI_INVALID_OUTPUT`.
- *Item-level problems affect only that item*: an item whose `evidence` is not found in the transcript (after whitespace, quote-style and case normalisation) is **dropped**; an owner who is not a declared participant or a transcript speaker is set to **null**; a due date that is not a real date, or disagrees with the wording ("by Friday"), is set to **null** while the wording is kept. Counts of drops and nullings are logged, never the content.
- If decisions and action items were offered but every one was dropped, the whole result is rejected.
- The summary is sanitised with an allow-list (`p br h1-h4 strong em ul ol li a[href] blockquote`).

**Failure handling.** A provider error, timeout, malformed output or database error sets `analysis_status=failed` with a short code (`AI_PROVIDER_ERROR`, `AI_INVALID_OUTPUT`, `AI_TIMEOUT`, `AI_RATE_LIMITED`, `AI_INTERNAL_ERROR`) and returns a generic message plus that code (`502`, `504` for a timeout, `429` for a rate limit). The previously saved analysis and action items are left untouched. A run that died while `processing` stops blocking after `AI_TIMEOUT_SECONDS + 60` seconds.

**Regeneration** replaces the stored analysis and replaces only action items with `source=ai AND is_edited=False`. Manual items and AI items you have edited (including just changing their status) are kept.

**The mock provider** is rule-based and deterministic (same input, byte-identical output). It abstains rather than guesses: no cue, no item.

- *Action items*: first-person commitments (`I will ...`), `<Name> will ...`, or `We/I can ...` only when a deadline is stated; a short list of commitment verbs; `will need` / `will be` are not tasks; a leading condition ("If we receive X, I can ...") is kept in the description; restatements of the same task merge. Priority is `High` or `Low` only on explicit words (urgent, asap, nice to have, ...); otherwise `Medium`. Owner and due date are null when not stated.
- *Decisions*: a proposal that another speaker explicitly accepts in the next turn ("Agreed", "Okay", "I agree", ...). Questions, unaccepted wishes and task commitments are never decisions; an empty list stays empty.
- *Risks* and *unanswered questions*: cue-word lexicons (for example "may create ... risk", "dependent", "not sure", "we need to know whether", or a question answered with "I will check ... by Friday").

Measured against the supplied sample transcript (Project Discovery meeting, 28 July 2026): 7 of 7 expected action items with the right owners and resolved dates, 10 of 11 expected decisions, 8 of 8 risks, 5 of 5 open questions, and none of the three overruled wishes (replace Zendesk completely, answer every message automatically, automatic individual assignment) appears as a decision. The missed decision is the confidence-based auto-reply, because nobody explicitly accepted it in the following turn. Some cue phrases were added after reading this transcript, so this is not an independent benchmark; it will do worse on transcripts written in a different style.

## Adding a real AI provider

1. Create `tracker_apps/ai_service/providers/<name>.py` with a class that subclasses `MeetingAnalysisProvider` ([base.py](tracker_apps/ai_service/providers/base.py)), sets `name` and `model`, and implements `analyze(request: AnalysisRequest) -> dict`. `AnalysisRequest` holds only the transcript, meeting date, meeting type and participant names: nothing that identifies the user.
2. Return a dict matching [schemas.py](tracker_apps/ai_service/schemas.py). Raise `ProviderTimeout`, `ProviderRateLimited` or `ProviderError` (from [exceptions.py](tracker_apps/ai_service/exceptions.py)) for expected failures; any other exception is mapped to `AI_PROVIDER_ERROR`.
3. Register it in `get_provider()` in [registry.py](tracker_apps/ai_service/providers/registry.py) under a new `AI_PROVIDER` value.
4. Read credentials only from environment variables through `tracker/config.py`; never hardcode a key.

Nothing else changes: the service validates the provider's output with the same schema, evidence, owner and date checks and persists it the same way. Constrained or structured output from a provider is **not** a substitute for that validation.

**Privacy note.** With the mock provider nothing leaves the system. A real hosted provider would send the transcript, meeting date, type and participant names to that vendor; the sample transcript itself raises exactly this GDPR concern, so that decision belongs with whoever deploys this.

## Assumptions

- **Relative dates** are resolved from the *meeting date*, never from the clock:
  - "today" is the meeting date and "tomorrow" the day after.
  - A bare weekday ("by Friday") is the first such weekday *strictly after* the meeting date.
  - "next Tuesday" is that weekday in the *following calendar week* (weeks start on Monday).
  - "end of next week", "soon", "after X is ready" are not resolvable: the date is `null` and the wording is kept.
- A person with only a team named ("our technical team will ...") is assigned only if exactly one declared participant's role mentions that team; otherwise the owner is left unassigned.
- Login is by email (case-insensitive). Duplicate registration returns a deliberately neutral validation message.
- Dates in requests and responses are ISO `YYYY-MM-DD`, not `DD-MM-YY`.
- Deleting is a hard delete; asking the user to confirm is the client's job.
- Rich text (meeting notes and the analysis summary) is stored as sanitised HTML; the transcript is plain text and is never treated as HTML.
- Search is case-insensitive substring matching (see Limitations for SQLite's ASCII-only case folding).

## Completed

- Registration, login, logout, token refresh and "me"; protected endpoints; login/register throttling.
- Meeting create, list, detail, edit, delete and search; filtering by type and date range; sorting; pagination.
- Transcript by pasted text or `.txt` upload, with the validation described above.
- AI analysis through a replaceable provider interface with a deterministic mock: summary, discussion points, decisions, action items, risks and unanswered questions, validated and stored.
- Action items: view all, per meeting, manual add, edit, delete, filter by status / priority / owner / due date, search, overdue detection.
- Dashboard statistics.
- Server-side ownership enforcement on every resource.
- Input validation with field-level messages and a single structured error envelope.
- OpenAPI schema and Swagger UI.
- 402 automated tests, including ownership and 401 checks for every resource, upload edge cases, AI failure injection (provider errors, malformed output, ungrounded evidence, invented owners, impossible dates) and dashboard-versus-ORM count checks. For the action-item and dashboard code the tests were also checked by deliberately breaking the code and confirming they fail.

## Not completed

- **Real AI provider (Gemini).** Deliberately skipped. `AI_PROVIDER=gemini` is accepted by the config but makes an analysis fail with `AI_PROVIDER_ERROR`; it does not fall back to the mock. Nothing about a real LLM has been run or verified.
- **Docker.** There is no `Dockerfile` or `docker-compose.yml` yet, and Docker is not installed on the development machine, so container behaviour is untested.
- **Hardening pass.** A systematic review of every endpoint against the security checklist, a logging audit and an error-response audit have not been done as a separate step. The behaviours above are individually tested, but this has not been audited end to end.
- **AI usage report, demo script and demo data command.** `AI_USAGE_REPORT.md`, `DEMO.md` and a `seed_demo` management command do not exist yet. Notes on how AI was used and the mistakes caught along the way are being kept in `CLAUDE.md` and will be turned into the report.
- **PDF / DOCX / Markdown transcript upload.** Only `.txt` is supported.
- **Frontend.** This repository is the backend only.
- Not planned: video or audio, live transcription, calendar integration, roles beyond "owner of the record", other databases, queues.

## Limitations

- **Mock quality.** It is cue-based. It misses commitments phrased without its cue words (for example an offer such as "I can ask each team lead ..." with no deadline), keeps lead-in words in some decision texts ("Yes, although ..."), does not resolve pronouns in decision text, and builds "discussion points" from the meeting's questions rather than true topics.
- **Duplicates after regeneration.** If you edited an AI action item and then re-run the analysis, the AI may produce a fresh copy of the same task next to your edited one. Manual items are never touched, so a task you re-added by hand that the AI also finds will appear twice.
- **Throttling is per process.** Counters live in each process's memory, so with several gunicorn workers the effective limit is per worker.
- **SQLite concurrency.** Writes are serialised. Use few workers; this is suited to a single-node deployment, not heavy concurrent writing.
- **Synchronous analysis.** The request blocks while the provider runs. Fine for the mock; a slow real provider would need a queue (out of scope here).
- **Search quirks.** SQLite's case-insensitive matching is ASCII-only (`josé` does not match `JOSÉ`); searching notes also matches HTML tag names; participants are matched against their stored JSON text, so a search for `"` or `[` matches everything.
- **Upload size.** The size limit is enforced by the application, but the web server streams the upload to a temporary file first. Put a request-size limit on any reverse proxy in front of this service.
- **Stale `processing` recovery** relies on the meeting's `updated_at`; any edit to the meeting refreshes it.
- **No cap** on the number of action items per meeting.
- The OpenAPI pages are public when `DEBUG=True`, so never run with `DEBUG=True` in production.

## Future improvements

- Implement and verify a real LLM provider behind the existing interface, with structured output, a prompt that treats the transcript strictly as data, and retries for malformed output.
- Run analysis in a background worker with progress reporting instead of inside the request.
- Shared throttle storage (for example a cache backend) so limits hold across workers.
- Fuzzy de-duplication of regenerated action items against edited or manual ones.
- PDF, DOCX and Markdown transcript import.
- Stronger search (full-text index, accent-insensitive matching).
- Dockerfile and Compose setup with a named volume for the SQLite file, health check and migrate-on-start; then the planned hardening audit and an end-to-end demo script.
- Per-meeting sharing and roles, if multi-user collaboration is wanted later.
