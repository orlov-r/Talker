# Lesson web app

Flask/Jinja and plain JavaScript implement anonymous listening lessons.
Waitress runs production as one process with four threads; no frontend build or
database is required.

Routes and HTTP responses live in `app.py`; `attempts.py` owns bounded storage
and transaction locking, and `quiz.py` owns selection and quiz transitions.
See [Python classes and data structures](../docs/python-data-model.md) for
record fields, locking requirements, and the content/audio modules.

## Lesson and levels

| Level | Speech rate | Question count |
|---|---|---|
| Easy | 80 | 7 |
| Medium | 100 | 10 |
| Hard | 120 | 15 |

Example lessons include «Приветствие», «Числа», and «Животные». Each attempt randomly
selects sources only from the chosen lesson; the level still sets 7/10/15 answers.
Easy selects level 1 sources. Unmarked sources default to level 1 when the
lesson has no explicit `level: 1` source, otherwise to level 2. Medium and Hard
include all sources. All lessons stay visible; Easy uses the first ten words
of each frequency lesson, numbers 1–10, and the greetings pool. Explicit higher levels
remain excluded on Easy. The additional everyday and grammar lessons use their
full static pools at every difficulty. The start API returns HTTP 400 if no
source is eligible.
Question JSON is resolved from
private references in `lessons/questions/`; generators remain unchanged.
Six thematic lessons each use four ten-word pools from the private
[word-frequency lists](../dev/word-frequencies/README.md), preserving their order.
They are curated selections sorted by recorded word-form frequency.
Animal illustrations use the style of Niko Pirosmani.
Correct answer texts do not repeat until the available answers are exhausted,
then a new uniqueness cycle begins. Generators use bounded retries, so an early
repeat has a small probability. Static vocabulary chooses
an unused correct choice at random; a generator marks its own correct choice.
Each question displays that choice and three sampled other choices, shuffled
once per occurrence. The original number lesson uses consecutive four-number intervals within 1–10
or 1–20. Additional lessons cover integers to 100/1000 and fractions to 9.99/99.99,
with semi-round sources at level 1 and all-number sources at level 2. Their
mutation pools stay within range; fractions combine mutations of both parts.
See [generator rules](../lessons/README.md#extended-number-and-fraction-generators).
Levels override source rates.
Failed or invalid generator output is retried once;
a second failure uses a random static pool from the lesson, ignoring difficulty
and repeated answers. Valid generated questions with one to three choices are
padded to four with duplicates. If no fallback exists, start returns HTTP 400
and keeps the active attempt. Static content and eligible sources are checked
before replacing an attempt.
`choiceLayout: "short"` uses four square buttons in a row; `"long"` (default)
uses a 2×2 grid. Buttons show a local image when supplied, otherwise the Russian
translation; translations also provide accessible image labels. Missing images
fall back to the Russian translation, including browser image-loading failures.

Three screens provide selection, listening/feedback, and final score.
Selection includes Eka (default) and Giorgi via Edge TTS and Natia via RHVoice.
The voice is fixed for each attempt. If Edge synthesis fails, times out, or
returns invalid audio, the app automatically tries RHVoice at the same rate.
If both services fail, audio stays unavailable and the question can be retried.
Edge TTS sends speech text to Microsoft's online service.
The interface, level and lesson names, accessibility labels, and API error
messages are in Russian. Georgian learning content and speech remain Georgian.
Audio tries autoplay with manual playback/replay as a fallback. Choices lock after
submission; the submitted button shows green with a tick or red with a cross.
The Georgian correct answer and its translation in parentheses stay visible until
Next. Hovering or focusing a picture choice shows its Russian translation between
Back and Next before answering. After answering, hovering, focusing, or tapping
a picture choice shows its Georgian word with the Russian translation in
parentheses; text choices show their Georgian text. That area reserves space
before answering.
Level cards put question count and speech rate on separate lines.
Replay and Next use compact controls. Audio failure leaves the current
question open and disables choices until playback preparation succeeds.
Audio preparation and playback messages occupy the correct-answer area, so
showing and clearing the preparation message does not shift the choices.
After answering, the correct answer remains visible during audio recovery.

Keyboard shortcuts use physical key positions, including with Russian or
Georgian keyboard layouts. On selection, 1/2/3 select Easy/Medium/Hard (including
the numeric keypad), with key numbers in the top-right corners of difficulty
cards. 4/5/6 select Eka/Giorgi/Natia, including the numeric keypad, with the same
corner labels. Q selects the previous list row and A the next, wrapping at
either end; Z/X select the previous/next lesson within the current group, also
wrapping. Vertical navigation retains the column where possible. Individual
lessons and groups form vertical rows; lessons inside a group remain horizontal,
with an optional group title first in the row and no extra surrounding padding,
with horizontal scrolling on narrow screens. The ordered list and optional title
and explanation overrides come from [the private catalog](../lessons/README.md#selection-catalog).
The start button appears before the lesson list. Every activated keyboard shortcut
scrolls its target control into view. Space or Enter starts the selected lesson and returns from results
to selection. These shortcuts also work while a selection radio has focus.
During a quiz: Z/X/C/V for the horizontal row, A/S/Z/X for the 2×2
grid (left to right, top to bottom). Small corner labels show the keys. R
replays at any time; Space replays before answering and advances after answering.
Enter advances only after answering. Small hints below Replay and Next show their
shortcuts; Replay's hint updates after answering to show R alone.
Held keys, modifier combinations, busy requests and text inputs do not trigger
quiz actions. After answering, option shortcuts inspect the Georgian text
without submitting again.

Choice images are 512×512 JPGs encoded at quality 75, named after the English
word (e.g. `dog.jpg`). Prompts live separately in
[`dev/image-prompts.json`](../dev/image-prompts.json); see
[image authoring](../lessons/README.md#image-assets).

## Local setup

Run commands from the repository root. Use Python 3.11+ and start the standalone
speech service using the [root instructions](../README.md).

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r web/requirements.txt
.\.venv\Scripts\python.exe -m flask --app web.app run --port 8070
```

Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r web/requirements.txt
.venv/bin/python -m flask --app web.app run --port 8070
```

Open [the lesson app](http://127.0.0.1:8070/). Flask's development server is for
local development. In production use one Waitress process behind an HTTPS proxy
(Windows uses `.venv\Scripts\waitress-serve.exe`):

```sh
.venv/bin/waitress-serve --host=127.0.0.1 --port=8070 --threads=4 web.app:app
```

## Compose

Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
Put it in an ignored `.env` file at the root; never commit secrets:

```text
SECRET_KEY=replace-with-generated-value
SYNTHESIS_VERSION=local-v1
COOKIE_SECURE=0
```

Run from the root on Windows or Linux:

```sh
docker compose up --build -d
```

The web app binds to host loopback port 8070. Speech is internal at
`http://rhvoice:8080`, `http://edge-eka:8080`, and `http://edge-giorgi:8080`,
with no published speech ports. The two Edge services use the same image with
different startup voices. All containers run non-root
with read-only filesystems and temporary `/tmp` mounts. Private `lessons/`
content is copied into the web image but never exposed as static files.
The first audio request may need a retry while the services start.
Edge requires outbound HTTPS/WebSocket access; RHVoice works offline.

Expose the web app through your HTTPS proxy and set `COOKIE_SECURE=1` there.
Keep it `0` for local HTTP. Do not add multiple web processes or replicas;
state is process-local.

## Configuration and state

| Environment variable | Default | Purpose |
|---|---|---|
| `SYNTHESIS_URL` | `http://127.0.0.1:8071` | Trusted speech base URL; Compose uses the internal URL |
| `EDGE_EKA_URL` | `http://127.0.0.1:8072` | Edge instance configured for `ka-GE-EkaNeural` |
| `EDGE_GIORGI_URL` | `http://127.0.0.1:8073` | Edge instance configured for `ka-GE-GiorgiNeural` |
| `SYNTHESIS_VERSION` | `local-v1` | Change when any engine/voice data or URL voice assignment changes |
| `SECRET_KEY` | Random per process | Cookie signing; explicitly required by Compose |
| `COOKIE_SECURE` | `0` | Set `1` for HTTPS-only cookies |

Attempts expire one hour after creation and are limited to 256 per process.
Expired state is removed lazily on attempt creation/access. Starting another
quiz replaces that browser's previous attempt. Refresh returns to selection.
Restart ends all attempts. No accounts, statistics, saved progress, or durable
results are implemented.

For local development, the standalone Edge scripts start one voice at a time
on port 8072; to use both voices together, use Compose or independently managed
instances at the configured URLs. RHVoice alone remains sufficient for fallback.

After fetching the current audio, the browser requests next-question precaching
in the background without waiting for it before playback or answering. The server
warms only the immediate next snapshot using the same voice, fallback, and cache
rules. Failures are silent in the UI; normal playback retries synthesis. Precaching
never marks audio as retrieved for answering and returns no future question data.
The last question needs no precache request.

Audio uses an in-memory LRU cache of at most 128 audio entries, each limited to 4 MiB.
Evicted audio is regenerated from its retained question snapshot. Keys hash
text, engine/voice selection, rate, and synthesis version. Misses are serialized.
Fallback WAVs use the RHVoice cache key, so an Edge error is not cached and later
requests can retry Edge. MP3 validation checks content type and an ID3/MPEG header;
it does not decode frames. WAV validation
checks headers and a nonzero declared frame count; rejecting truncated frame
data is a [future enhancement](../docs/todo.md). No runtime files or database
are created. A future persistent cache or SQLite database must use a volume.

## API

`GET /` sets a signed anonymous session cookie and renders a CSRF meta token.
Every POST requires `X-CSRF-Token` and a JSON object (4096-byte request limit).
The cookie contains only opaque owner and CSRF IDs, never answers or scores.

| Endpoint | Request / response |
|---|---|
| `GET /health` | Web HTTP health only |
| `GET /api/lessons` | `levels` settings, available flat `lessons`, grouped `lessonList` display metadata, and `voices` labels |
| `POST /api/attempts` | `{level, lessonId, voice?}` to question envelope, HTTP 201; voice is `edge-eka` (default), `edge-giorgi`, or `rhvoice` |
| `GET /api/attempts/{id}` | Current question/feedback or completion envelope |
| `POST /api/attempts/{id}/answers` | `{questionId, choiceId}` to `{isCorrect, correctAnswerText, selectedChoiceId, choiceTexts}` |
| `POST /api/attempts/{id}/next` | `{questionId}` to next/completion envelope |
| `POST /api/attempts/{id}/precache` | `{questionId}` for the current question; warms next audio, returns empty HTTP 204 (also for the last question); stale/completed requests return 409 |
| `GET /api/attempts/{id}/result` | Completed attempt envelope |
| `GET /audio/{key}?attempt={id}` | Current question MP3 or fallback WAV with ownership check; RHVoice URLs retain `.wav` |

Question envelopes contain `attemptId`, `complete: false`, `position`, `total`,
`question: {id, audioUrl, choiceLayout, choices: [{id, label, image?}]}`, and `feedback` (initially
null). Completion envelopes contain `attemptId`, `complete: true`, `score`,
and `total`. Choice `label` is the Russian translation. IDs are temporary button
identifiers,
assigned by the server; private choices need no IDs. Scoring compares trimmed
Georgian text, accepting every displayed choice with the correct text. Feedback
includes
`choiceTexts`, a map from the four displayed IDs to Georgian texts, only after
answering; current-state recovery includes the same map. Future questions,
speech overrides, and answer keys are not returned.

The first valid answer is final; retries return the original feedback without
rescoring. Next requires its answered current ID; duplicate next returns 409.
The UI recovers current state if a next response is lost. Successful audio
retrieval is required before answering; the server cannot prove a human listened.

Errors return `{error: message}`: 400 invalid JSON/selection, 403 CSRF, 404
unavailable/expired/non-owned attempt or audio, 409 invalid progression/choice,
413 oversized request, 502 synthesis failure/timeout, 503 attempt capacity.
All responses use `Cache-Control: no-store`.
Each lesson's `levels` lists only difficulties with eligible sources.

## Validation

Source formatting conventions and optional tool commands are documented in
[the development workflow](../docs/development.md#source-style).

With dependencies installed, run from the root:

```sh
python -m unittest discover -s web -p test_app.py -v
node --test web/test_shortcuts.js
```

Tests use simulated WAVs/MP3s for voice selection, fallback/recovery, format checks,
level mapping, private fields, schema defaults,
ownership, expiry, retries, ordering, scoring, audio failure/retry, and cache
identity/bounds/concurrency. They do not verify real voices or pronunciation.
Behavior tests use fixed in-memory lesson fixtures, so manual edits to authored
content do not change their expectations. Real content checks validate lesson,
question and catalog structure, require at least three selectable lessons, check
that the first catalog lesson whose ID starts with `numbers` returns a numeric
question, and that the first starting with `animals` contains `ძაღლი` translated
as `собака` (ignoring case). They do not freeze lesson order, titles, group counts,
vocabulary sizes, or the rest of the translations.
Build/start Compose and complete a lesson at each level while listening to
verify real voice playback, replay, feedback, and results.
