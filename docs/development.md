# Development workflow

Start with the [root README](../README.md) for repository status and commands,
and the [architecture](architecture.md) for the lesson application.
Agent-specific instructions live in [AGENTS.md](../AGENTS.md).

## Existing speech service

Work in `talker/`. Its Docker build context is that directory, and its
`.dockerignore` allows only the Dockerfile, server, and test page into the
build context. Rebuild the image and recreate the container after changing
runtime files. Build scripts can be called from the root; sample request paths
must be relative to the working directory used for `curl`.

Follow [the service README](../talker/README.md) for Windows/Linux builds,
replacement, API checks, and deployment. The Dockerfile checks that Natia can
produce a nonempty WAV during the build. Check `/health`, synthesize the sample
request, and listen to the audio to verify the actual voice.

For HTTP logic changes, cover invalid inputs and synthesis failures/timeouts
as well as successful WAV responses. A simulated synthesizer can verify API
behavior locally, but does not verify RHVoice or pronunciation. The speech
service has no committed test suite; quiz checks are in `web/test_app.py`.

## Lesson app

Implement in `web/`, with lesson JSON and trusted generators in `lessons/`.
The minimal app and private content are implemented. Use the
[chosen Flask, Jinja, and plain JavaScript stack](web-framework.md), and keep
install, run, and test commands current in `web/README.md`.

The single lesson randomly selects vocabulary and generated number sources,
without repeating correct texts within an attempt. It supports picture choices,
temporary attempts, feedback, explicit progression, and scores.
Run `python -m unittest discover -s web -p test_app.py -v` from the
root. Tests cover defaults and invalid definitions,
server-side scoring, duplicate/out-of-order answer and next requests, attempt
ownership/expiry, number intervals, speech overrides, private choice texts,
stable generated questions on replay, and audio cache
invalidation. No database or saved results are required for the basic version.
The synthesis service should remain independently buildable.

Compose is defined in `compose.yaml`, with internal RHVoice networking. Document volume paths,
configuration, temporary-state limits/cleanup, and HTTPS routing with the
deployment configuration. If persistent storage is added later, document its
volumes, migrations, and backup/restore then. Keep runtime SQLite, WAV caches,
and image archives out of Git.

## Documentation changes

Check links and example commands against the current tree and source. Keep
planned routes and features clearly marked until they exist. Documentation
changes alone do not require building images or restarting containers.
