# Lesson web app

Flask/Jinja and plain JavaScript implement one anonymous listening lesson.
Waitress runs production as one process with four threads; no frontend build or
database is required.

## Lesson and levels

| Level | Speech rate | Question count |
|---|---|---|
| Easy | 80 | 7 |
| Medium | 100 | 10 |
| Hard | 120 | 15 |

The lesson alternates two sources: a static Georgian greeting and a generated
number from 1 to 20. The greeting repeats; independently generated numbers may
also repeat. Each question displays four choices: the correct answer and three randomly
selected wrong answers, shuffled once per occurrence. Levels override source rates.
`choiceLayout: "short"` uses four square buttons in a row; `"long"` (default)
uses a 2×2 grid. Choices support text or local images with accessible labels.

Three screens provide selection, listening/feedback, and final score.
The interface, level and lesson names, accessibility labels, and API error
messages are in Russian. Georgian learning content and speech remain Georgian.
Audio tries autoplay with manual playback/replay as a fallback. Choices lock after
submission; the submitted button shows green with a tick or red with a cross.
Large correct-answer text stays visible until Next. Replay and Next use compact controls. Audio failure leaves the current
question open and disables choices until playback preparation succeeds.

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

The web app binds to host loopback port 8070. RHVoice is internal at
`http://rhvoice:8080` with no published speech port. Both containers run non-root
with read-only filesystems and temporary `/tmp` mounts. Private `lessons/`
content is copied into the web image but never exposed as static files.
The first audio request may need a retry while RHVoice starts.

Expose the web app through your HTTPS proxy and set `COOKIE_SECURE=1` there.
Keep it `0` for local HTTP. Do not add multiple web processes or replicas;
state is process-local.

## Configuration and state

| Environment variable | Default | Purpose |
|---|---|---|
| `SYNTHESIS_URL` | `http://127.0.0.1:8071` | Trusted speech base URL; Compose uses the internal URL |
| `SYNTHESIS_VERSION` | `local-v1` | Change when RHVoice/voice data changes |
| `SECRET_KEY` | Random per process | Cookie signing; explicitly required by Compose |
| `COOKIE_SECURE` | `0` | Set `1` for HTTPS-only cookies |

Attempts expire one hour after creation and are limited to 256 per process.
Expired state is removed lazily on attempt creation/access. Starting another
quiz replaces that browser's previous attempt. Refresh returns to selection.
Restart ends all attempts. No accounts, statistics, saved progress, or durable
results are implemented.

Audio uses an in-memory LRU cache of at most 128 WAVs, each limited to 4 MiB.
Evicted audio is regenerated from its retained question snapshot. Keys hash
text, Natia, rate, and synthesis version. Misses are serialized and only complete
validated WAVs are cached. No runtime files or database are created. A future
persistent cache or SQLite database must use a volume.

## API

`GET /` sets a signed anonymous session cookie and renders a CSRF meta token.
Every POST requires `X-CSRF-Token` and a JSON object (4096-byte request limit).
The cookie contains only opaque owner and CSRF IDs, never answers or scores.

| Endpoint | Request / response |
|---|---|
| `GET /health` | Web HTTP health only |
| `GET /api/lessons` | `levels` settings and available `lessons` |
| `POST /api/attempts` | `{level, lessonId}` to question envelope, HTTP 201 |
| `GET /api/attempts/{id}` | Current question/feedback or completion envelope |
| `POST /api/attempts/{id}/answers` | `{questionId, choiceId}` to `{isCorrect, correctAnswerText, selectedChoiceId}` |
| `POST /api/attempts/{id}/next` | `{questionId}` to next/completion envelope |
| `GET /api/attempts/{id}/result` | Completed attempt envelope |
| `GET /audio/{key}.wav?attempt={id}` | Current question WAV with ownership check |

Question envelopes contain `attemptId`, `complete: false`, `position`, `total`,
`question: {id, audioUrl, choiceLayout, choices: [{id, label, image?}]}`, and `feedback` (initially
null). Completion envelopes contain `attemptId`, `complete: true`, `score`,
and `total`. Future questions, speech text, and answer keys are not returned.

The first valid answer is final; retries return the original feedback without
rescoring. Next requires its answered current ID; duplicate next returns 409.
The UI recovers current state if a next response is lost. Successful audio
retrieval is required before answering; the server cannot prove a human listened.

Errors return `{error: message}`: 400 invalid JSON/selection, 403 CSRF, 404
unavailable/expired/non-owned attempt or audio, 409 invalid progression/choice,
413 oversized request, 502 synthesis failure/timeout, 503 attempt capacity.
All responses use `Cache-Control: no-store`.

## Validation

With dependencies installed, run from the root:

```sh
python -m unittest discover -s web -p test_app.py -v
```

Tests use simulated WAVs for level mapping, private fields, schema defaults,
ownership, expiry, retries, ordering, scoring, audio failure/retry, and cache
identity/bounds/concurrency. They do not verify Natia or pronunciation.
Build/start Compose and complete a lesson at each level while listening to
verify real voice playback, replay, feedback, and results.
