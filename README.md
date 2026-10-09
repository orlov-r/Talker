# Talker

Talker is a Georgian listening practice project using RHVoice and the Natia
voice. The intended experience is to choose a lesson, listen to speech, answer
multiple-choice questions, and see a final score.

## Current status

The speech service is implemented. It accepts Georgian text and returns WAV
audio, and includes a browser page for manually testing speech. The lesson web
app, lesson content, scoring, and Docker Compose setup are
planned; they are not implemented yet.

The basic app has three screens: skill level and lesson selection, a listening
question with five answer choices and feedback, and a final score. Accounts,
statistics, and persistent attempts/results are outside the basic scope.

## Repository layout

| Path | Purpose |
|---|---|
| [talker/](talker/README.md) | Existing RHVoice/Natia service, Docker image, and build/run scripts |
| [web/](web/README.md) | Placeholder for the lesson web app and its API |
| [lessons/](lessons/README.md) | Placeholder for server-side lesson JSON and question generators |
| [docs/architecture.md](docs/architecture.md) | Proposed container boundaries, API, storage, and quiz flow |
| [docs/web-framework.md](docs/web-framework.md) | Chosen web stack and framework comparison |
| [docs/development.md](docs/development.md) | Development workflow and implementation sequence |
| [AGENTS.md](AGENTS.md) | Repository guidance for coding agents |

## Run the existing speech service

Requirements: Docker with Linux containers and a Linux/amd64 image target.
The image build needs internet access; synthesis works offline afterward.
Run these commands from the repository root.

Windows (PowerShell):

```powershell
.\talker\build.ps1
.\talker\run.ps1
```

Linux:

```sh
sh talker/build.sh
sh talker/run.sh
```

Continue to the run command only after the build succeeds. Open the
[speech test page](http://127.0.0.1:8071/) and click **Read aloud**.
This page tests synthesis; it does not run lessons.

Health and synthesis checks from the repository root:

```powershell
curl.exe --fail http://127.0.0.1:8071/health
curl.exe --fail http://127.0.0.1:8071/synthesize -H "Content-Type: application/json" --data-binary "@talker/sample.json" --output hello.wav
```

On Linux, use `curl` instead of `curl.exe`. Listen to `hello.wav` to assess
pronunciation. See the [service README](talker/README.md) for API limits,
container replacement, image transfer, source pinning, and voice license notes.

## Planned deployment

Start with two containers: the web app and RHVoice/Natia. Only the web app is
exposed to users; it calls `http://rhvoice:8080/synthesize` over the internal
Docker network. Questions come from server-side JSON or trusted generators.
Active attempts and reusable audio need only temporary storage for the basic
version; no database is required. Reuse the server's HTTPS proxy, or add a third
container for one if needed.

Docker Compose will be added when the web app has a runnable entry point.
Flask with Jinja templates and plain JavaScript is the
[chosen web stack](docs/web-framework.md). No framework
or dependencies have been added. The [architecture document](docs/architecture.md)
describes the proposed behavior and boundaries for that implementation.
