# Development workflow

Start with the [root README](../README.md) for repository status and commands,
and the [architecture](architecture.md) for the lesson application.
Agent-specific instructions live in [AGENTS.md](../AGENTS.md).

## Existing speech service

Work in `talker-rhvoice/`. Its Docker build context is that directory, and its
`.dockerignore` allows only the Dockerfile, server, and test page into the
build context. Rebuild the image and recreate the container after changing
runtime files. Build scripts can be called from the root; sample request paths
must be relative to the working directory used for `curl`.

Follow [the service README](../talker-rhvoice/README.md) for Windows/Linux builds,
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

Each lesson randomly selects from its own vocabulary or generated sources,
avoiding repeated correct texts until the available answers are exhausted.
Generators use bounded retries and may rarely repeat early. It supports picture choices,
temporary attempts, feedback, explicit progression, and scores.
Run `python -m unittest discover -s web -p test_app.py -v` from the
root. Tests cover defaults and invalid definitions,
server-side scoring, duplicate/out-of-order answer and next requests, attempt
ownership/expiry, number intervals, speech overrides, private choice texts,
stable generated questions on replay, and audio cache
invalidation. No database or saved results are required for the basic version.
The synthesis service should remain independently buildable.

`lessons/questions/` is reserved for separate question definitions in the next
content migration. Current lesson JSON files still embed their sources; the
loader does not read that directory yet. Development resources belong in `dev/`,
including `dev/image-prompts.json`, and are excluded from the Docker build context.
See [future enhancements](todo.md) for the remaining review proposals.

Compose is defined in `compose.yaml`, with internal RHVoice networking. Document volume paths,
configuration, temporary-state limits/cleanup, and HTTPS routing with the
deployment configuration. If persistent storage is added later, document its
volumes, migrations, and backup/restore then. Keep runtime SQLite, WAV caches,
and image archives out of Git.

## Documentation changes

Check links and example commands against the current tree and source. Keep
planned routes and features clearly marked until they exist. Documentation
changes alone do not require building images or restarting containers.
Use three or four content examples in READMEs instead of exhaustive catalogs;
keep schema and operational instructions complete.
