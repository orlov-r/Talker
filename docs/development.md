# Development workflow

Start with the [root README](../README.md) for repository status and commands,
and the [architecture](architecture.md) for the planned lesson application.
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
behavior locally, but does not verify RHVoice or pronunciation. The repository
currently has no committed automated test suite; add focused tests as behavior
is implemented or changed.

## Future lesson app

Implement in `web/`, with lesson JSON and trusted generators in `lessons/`.
These directories contain documentation only. Use the
[chosen Flask, Jinja, and plain JavaScript stack](web-framework.md), and record
actual install, run, and test commands in `web/README.md` when implementation
begins.

Develop a small complete lesson first: schema validation, prepared audio,
temporary attempt creation, answer checking, feedback, explicit next-question
advancement, and score display across the three screens. Add a generated number
question and a picture-choice example. Test defaults and invalid definitions,
server-side scoring, duplicate/out-of-order answer and next requests, attempt
ownership/expiry, stable generated questions on replay, and audio cache
invalidation. No database or saved results are required for the basic version.
The synthesis service should remain independently buildable.

Add Docker Compose once the web app is runnable. Document volume paths,
configuration, temporary-state limits/cleanup, and HTTPS routing with the
deployment configuration. If persistent storage is added later, document its
volumes, migrations, and backup/restore then. Keep runtime SQLite, WAV caches,
and image archives out of Git.

## Documentation changes

Check links and example commands against the current tree and source. Keep
planned routes and features clearly marked until they exist. Documentation
changes alone do not require building images or restarting containers.
