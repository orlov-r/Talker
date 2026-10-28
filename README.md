# Talker

Talker is a Georgian listening practice project using Edge TTS (Eka/Giorgi)
and RHVoice (Natia). The experience is to choose a lesson, listen to speech, answer
multiple-choice questions, and see a final score.

## Current status

The speech service and minimal lesson app are implemented, with Docker Compose
configuration. Example lessons include greetings, numbers, and illustrated
animal, city, and produce vocabulary. Five additional lessons cover everyday street/shop
expressions, personal pronouns, possessive and dative forms, question words, and
short words. Their full vocabulary is available at every difficulty. Additional
number lessons cover integers to 100 and 1000 and fractions to 9.99 and 99.99,
with semi-round and all-number sources. Six thematic lessons each provide 40
words in four pools ordered by the private [word-frequency
lists](dev/word-frequencies/README.md); Easy uses their first ten words. The
selected lesson randomly draws from its own pools, avoiding repeated correct
answer texts until the available answers are exhausted. Easy gives 7 questions
at speech rate 80, Medium gives 10 at 100, and Hard gives 15 at 120. The app
checks answers and calculates scores on the server by Georgian text, accepting
duplicate correct choices. Lesson start validates questions; broken generators
retry once and fall back to static content when available. Missing pictures show
Russian text. Easy includes level 1 sources; Medium and Hard include all
positive-level sources. Unmarked sources default to level 1 if the lesson has no
explicit `level: 1` quiz source, otherwise to level 2. All lessons remain visible at
every difficulty.

The app provides lesson selection, a vocabulary study page, listening questions
with four answer choices and feedback, and a final score. The «Обучение» button
opens all static words for the selected topic with pictures, Georgian text,
translations, and individual playback. Level 1 words are green when study words
have different levels; sources marked `studyOnly: true` appear only in study,
including static vocabulary added to integer number lessons. Accounts,
statistics, and persistent attempts/results are outside the basic scope. The
lesson interface is in Russian; learning content and speech are in Georgian. The
first page offers Eka (the default), Giorgi, and Natia. The ordered selection
list is configured in [lessons/catalog.json](lessons/catalog.json), with
individual lessons and horizontal lesson groups. Selection shortcuts include 1–3
for difficulty, 4–6 for voice, Q/A for rows, and Z/X within a group. Edge TTS
requires internet and sends speech text to Microsoft; errors automatically fall
back to RHVoice/Natia. The chosen voice stays fixed for the lesson. While each
question is presented, the app warms the next question’s audio in the server
cache.

## Repository layout

| Path | Purpose |
|---|---|
| [talker-rhvoice/](talker-rhvoice/README.md) | Existing RHVoice/Natia service, Docker image, and build/run scripts |
| [talker-edge-tts/](talker-edge-tts/README.md) | Alternative online Edge TTS service and manual MP3 test page |
| [web/](web/README.md) | Flask lesson app, UI, API, Dockerfile, and tests |
| [lessons/](lessons/README.md) | Private lesson JSON and trusted number generator |
| [lessons/questions/](lessons/questions/README.md) | Private reusable question definitions referenced by lessons |
| [dev/](dev/README.md) | Development resources, including private image-generation prompts |
| [docs/architecture.md](docs/architecture.md) | Container boundaries, API, storage, and quiz flow |
| [docs/python-data-model.md](docs/python-data-model.md) | Python classes, private records, public projections, and synchronization |
| [docs/web-framework.md](docs/web-framework.md) | Chosen web stack and framework comparison |
| [docs/development.md](docs/development.md) | Development workflow and implementation sequence |
| [docs/todo.md](docs/todo.md) | Future enhancements from the project review |
| [AGENTS.md](AGENTS.md) | Repository guidance for coding agents |

## Run the existing speech service

Requirements: Docker with Linux containers and a Linux/amd64 image target.
The image build needs internet access; synthesis works offline afterward.
Run these commands from the repository root.

Windows (PowerShell):

```powershell
.\talker-rhvoice\build.ps1
.\talker-rhvoice\run.ps1
```

Linux:

```sh
sh talker-rhvoice/build.sh
sh talker-rhvoice/run.sh
```

Continue to the run command only after the build succeeds. Open the
[speech test page](http://127.0.0.1:8071/) and click **Read aloud**.
This page tests synthesis; it does not run lessons.

Health and synthesis checks from the repository root:

```powershell
curl.exe --fail http://127.0.0.1:8071/health
curl.exe --fail http://127.0.0.1:8071/synthesize -H "Content-Type: application/json" --data-binary "@talker-rhvoice/sample.json" --output hello.wav
```

On Linux, use `curl` instead of `curl.exe`. Listen to `hello.wav` to assess
pronunciation. See the [service README](talker-rhvoice/README.md) for API limits,
container replacement, image transfer, source pinning, and voice license notes.

## Try Edge TTS separately

An alternative [Edge TTS container](talker-edge-tts/README.md) is implemented for
manual voice comparisons. It requires internet for synthesis and returns MP3
directly. The default voice is Georgian Eka; Giorgi can be selected at startup.
Run from the root on Windows:

```powershell
.\talker-edge-tts\build.ps1
.\talker-edge-tts\run.ps1
```

On Linux use `sh talker-edge-tts/build.sh`, followed by
`sh talker-edge-tts/run.sh`. After a successful build/start, open
[the Edge speech test page](http://127.0.0.1:8072/). RHVoice remains on port 8071.
Compose runs separate Eka and Giorgi instances of this image for the lesson app.

## Run the lesson app

Follow [web setup](web/README.md#local-setup) for Python/Flask on Windows or Linux,
then open [the lesson app](http://127.0.0.1:8070/). It uses the standalone speech
service above by default. The speech test page remains separate on port 8071.

Alternatively, set a random `SECRET_KEY` in an ignored `.env` file following
[Compose setup](web/README.md#compose), then run from the root:

```sh
docker compose up --build -d
```

Compose exposes only the web app on loopback port 8070 and keeps all three speech
containers internal. The app handles Edge MP3 and RHVoice WAV, including fallback.
Attempts and audio use bounded process memory. No database or saved results are
used; restart loses quizzes and attempts expire after one hour. Use an HTTPS
proxy for remote deployment. See [architecture](docs/architecture.md).

With web dependencies installed, run quiz checks from the root:

```sh
python -m unittest discover -s web -p test_app.py -v
```

Tests use simulated audio; they do not validate real voices or pronunciation.
