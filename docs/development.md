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

Implement in `web/`, with lesson JSON in `lessons/`. These directories contain
documentation only. Select a framework when implementation begins and record
its install, run, and test commands in `web/README.md`.

Develop a small complete lesson first: schema validation, prepared audio,
attempt creation, answer checking, and score display. Test server-side scoring,
duplicate submissions, out-of-order answers, attempt ownership, and cache
invalidation. The synthesis service should remain independently buildable.

Add Docker Compose once the web app is runnable. Document volume paths,
configuration, migrations, backup/restore, and HTTPS routing with the deployment
configuration. Keep runtime SQLite, WAV caches, and image archives out of Git.

## Documentation changes

Check links and example commands against the current tree and source. Keep
planned routes and features clearly marked until they exist. Documentation
changes alone do not require building images or restarting containers.
