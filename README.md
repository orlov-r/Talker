# Talker

Talker is a Georgian listening practice project using RHVoice and the Natia
voice. The intended experience is to choose a lesson, listen to speech, answer
multiple-choice questions, and see a final score.

## Current status

The speech service and minimal lesson app are implemented, with Docker Compose
configuration. Example lessons include greetings, numbers, and illustrated animals.
The selected lesson randomly draws from its own pools, avoiding repeated correct
answer texts until the available answers are exhausted. Easy gives 7 questions
at speech rate 80, Medium gives 10 at 100, and Hard gives 15 at 120. The app checks answers and
calculates scores on the server.

The basic app has three screens: skill level and lesson selection, a listening
question with four answer choices and feedback, and a final score. Accounts,
statistics, and persistent attempts/results are outside the basic scope.
The lesson interface is in Russian; learning content and speech are in Georgian.

## Repository layout

| Path | Purpose |
|---|---|
| [talker-rhvoice/](talker-rhvoice/README.md) | Existing RHVoice/Natia service, Docker image, and build/run scripts |
| [web/](web/README.md) | Flask lesson app, UI, API, Dockerfile, and tests |
| [lessons/](lessons/README.md) | Private lesson JSON and trusted number generator |
| [lessons/questions/](lessons/questions/README.md) | Reserved for separate questions in the next content migration |
| [dev/](dev/README.md) | Development resources, including private image-generation prompts |
| [docs/architecture.md](docs/architecture.md) | Container boundaries, API, storage, and quiz flow |
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

## Run the lesson app

Follow [web setup](web/README.md#local-setup) for Python/Flask on Windows or Linux,
then open [the lesson app](http://127.0.0.1:8070/). It uses the standalone speech
service above by default. The speech test page remains separate on port 8071.

Alternatively, set a random `SECRET_KEY` in an ignored `.env` file following
[Compose setup](web/README.md#compose), then run from the root:

```sh
docker compose up --build -d
```

Compose exposes only the web app on loopback port 8070 and keeps RHVoice internal.
Attempts and audio use bounded process memory. No database or saved results are
used; restart loses quizzes and attempts expire after one hour. Use an HTTPS
proxy for remote deployment. See [architecture](docs/architecture.md).

With web dependencies installed, run quiz checks from the root:

```sh
python -m unittest discover -s web -p test_app.py -v
```

Tests use simulated audio; they do not validate the real Natia voice.
