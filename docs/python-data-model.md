# Python classes and data structures

This describes the implemented Python application. Records are ordinary mutable
dictionaries, lists, and sets, not ORM models or dataclasses. They live in one
process and are not persisted. See [architecture](architecture.md) for service
boundaries and [the web API](../web/README.md#api) for HTTP envelopes.

## Modules and classes

| Module | Responsibility |
|---|---|
| [`web/app.py`](../web/app.py) | Flask factory, sessions, CSRF, request parsing, error/status mapping, public response projection, and audio HTTP orchestration |
| [`web/attempts.py`](../web/attempts.py) | `AttemptStore`, ownership, lazy expiry, capacity, replacement, and transaction locking |
| [`web/quiz.py`](../web/quiz.py) | Selection validation, question preparation, answer checking, scoring, progression, and completion rules |
| [`web/content.py`](../web/content.py) | Private catalog loading, validation, source selection, generator retry/fallback, and question snapshots |
| [`web/audio.py`](../web/audio.py) | `AudioCache`, cache identity, upstream requests, and audio validation |
| [`lessons/generators.py`](../lessons/generators.py) | Trusted generator functions and the `GENERATORS` name-to-callable registry |

`create_app(config)` creates a Flask application, one `AttemptStore`, and one
`AudioCache`. `app.extensions["attempt_store"]` exposes the store;
`app.extensions["attempts"]` retains the same backing dictionary for existing
inspection/tests. Direct inspection or mutation also requires the store lock
when concurrent requests are possible.

### AttemptStore

`attempts` maps opaque random attempt IDs (`str`) to attempt dictionaries.
`_lock` is a `threading.RLock`. `transaction()` is a context manager holding this
lock across a complete operation, including response projection. Call `owned()`
and `create()` inside that context; these methods do not acquire it themselves.

`owned(aid, owner)` removes expired records, then returns the matching owned
record or raises `AttemptUnavailable`. `create(owner, voice, snapshots, *, ttl,
capacity)` removes expired records and the owner's old attempt, checks capacity,
and returns `(aid, attempt)`. TTL and capacity come from current Flask config on
each creation; defaults are 3600 seconds and 256 attempts. Expiry uses
`time.monotonic()`, not a wall-clock timestamp, and is not refreshed on access.

All snapshots are prepared under the transaction lock before calling `create()`.
A preparation failure therefore preserves the previous attempt. Replacement and
expiry cleanup precede the capacity check, matching the existing behavior.

### Exceptions

These are plain `Exception` subclasses, independent of Flask. The route layer
returns their message as `{error: message}` and assigns the HTTP status.

| Class | Meaning | HTTP status |
|---|---|---|
| `AttemptUnavailable` | Missing, expired, or non-owned attempt | 404 |
| `AttemptCapacity` | Attempt capacity reached | 503 |
| `InvalidSelection` | Unknown or invalid voice, level, or lesson | 400 |
| `QuizConflict` | Invalid answer, progression, or completion request | 409 |

Question preparation raises `ValueError` for invalid content; the route logs it
and returns the existing Russian preparation error with status 400.

### AudioCache

`entries` is an `OrderedDict[str, bytes]`, from least to most recently used.
`limit` defaults to 128 entries. `lock` is a `threading.Lock` held throughout
`get(key, produce)`, including production on a miss. Hits move to the end;
overflow evicts from the beginning. If `produce()` raises, no entry is inserted.
The cache itself does not validate bytes: production synthesizer functions
validate response type, size (at most 4 MiB), and WAV/MP3 headers.

Keys are SHA-256 hex digests of UTF-8 JSON `[text, voice, rate, version]`.
RHVoice fallback uses its own key, so an Edge failure is retried on later
requests. WAV frame-payload validation and allowing hits during unrelated misses
remain [future work](todo.md).

## Private records

### Catalog and content

`LEVELS` maps difficulty names to `{label, rate, questionCount}` dictionaries.
`LESSONS` maps lesson IDs to loaded dictionaries with `id`, `title`, and `sources`.
`LESSON` aliases the basics lesson for the default `questions()` argument.
`VOICES` maps supported voice IDs to display labels in `web/app.py`.

Authored sources contain a `question` basename, inline question object, numeric
array, or a `generator` name, with optional positive integer `level`.
`studyOnly: true` excludes a source from quiz selection and fallback; it
defaults to false. `study_words()` projects static vocabulary in source order
with resolved levels and speech text; the HTTP projection excludes speech
overrides and adds indexed audio URLs. Loading replaces question references with
validated question dictionaries; generator references remain dictionaries. The
default level depends on the other sources in that lesson. See [lesson
authoring](../lessons/README.md) for the content contract.

A question contains `choices` (a list of dictionaries) and `choiceLayout`
(`"long"` or `"short"`, default `"long"`). Choice fields are:

| Field | Type and meaning |
|---|---|
| `text` | Nonempty Georgian string used for answer comparison |
| `translation` | Nonempty Russian string used as the visible label |
| `speechText` | Nonempty synthesis string; defaults to `text` |
| `image` | Optional local JPG basename |
| `isCorrect` | Optional boolean; generated questions must mark the correct text |

Validation deep-copies records, strips authored choice IDs, and keeps source
content separate from attempt mutations. Private authoring fields such as
`description` can remain in snapshots but are never projected to the client.

`questions()` returns a list of prepared snapshots. Each has exactly four
shuffled choices with temporary IDs `"0"` through `"3"`, plus:

| Field | Type and meaning |
|---|---|
| `id` | Attempt-local question ID such as `"q1"` |
| `rate` | Integer speech rate selected by difficulty |
| `correctChoiceId` | ID of the selected correct choice; scoring compares text |
| `correctText` | Trimmed Georgian answer string |
| `speechText` | Selected correct choice's speech string |
| `correctAnswerText` | Georgian answer followed by its Russian translation |

A local `used` set tracks trimmed correct texts during preparation; it is not
stored in the attempt. Generator output retries, fallback, and uniqueness cycles
are described in [architecture](architecture.md#lesson-flow-and-content).

### Attempt dictionary

| Field | Type and meaning |
|---|---|
| `owner` | Opaque session owner string |
| `voice` | Voice ID fixed at creation |
| `expires` | Monotonic deadline (`float`) |
| `questions` | List of private snapshots prepared once |
| `index` | Zero-based current position; equals list length when complete |
| `score` | Number of correct accepted answers (`int`) |
| `feedback` | `None` before an answer, otherwise the feedback dictionary |
| `audioReady` | Set of question IDs with successful audio retrieval |

`quiz.answer()` checks completion, current question and choice, and audio
readiness before accepting an answer. The first valid answer updates the score
and feedback. Valid retries return that feedback even if another displayed
choice is submitted; invalid IDs still fail. Duplicate choices with matching
trimmed Georgian text are accepted as correct.

`quiz.advance()` requires the answered current ID, increments `index`, and clears
feedback. Duplicate/out-of-order Next requests fail. `require_complete()` guards
results. All these operations run within the store transaction.

Audio authorization captures the current snapshot and checks its cache key
under the lock. Synthesis runs outside it. After success, ownership and expiry
are checked again before adding the captured question ID to `audioReady`.
Failure does not score or advance. A late successful replay can mark its earlier
question ready after progression; it cannot enable answering a different ID.

## Public records and session

The signed session contains only opaque `owner` and `csrf` strings. The active
question envelope exposes position, total, question ID, layout, translated
choices, available image URLs, and an authorized audio URL. It never serializes
the attempt dictionary directly.

Feedback contains `isCorrect` (`bool`), `correctAnswerText` (`str`),
`selectedChoiceId` (`str`), and `choiceTexts` (`dict[str, str]`). It is exposed
only after answering and returned unchanged by current-state recovery. Completed
envelopes contain `attemptId`, `complete: true`, `score`, and `total`.

## Speech service classes

Both [`RHVoice Handler`](../talker-rhvoice/server.py) and
[`Edge Handler`](../talker-edge-tts/server.py) subclass
`http.server.BaseHTTPRequestHandler`. Their `reply()` writes status, headers,
and bytes; `error()` encodes an error dictionary. `do_GET()` serves health/manual
pages; `do_POST()` validates a JSON dictionary with `text` and optional integer
`rate`, runs synthesis, and returns audio bytes. Each is served by a serial
`HTTPServer`, with temporary files scoped to `TemporaryDirectory`.
They have no attempt, score, or cache records. Natia is fixed in RHVoice;
Edge's module-level `VOICE` comes from startup configuration.
