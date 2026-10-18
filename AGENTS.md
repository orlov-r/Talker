# Agent development guidance

## Scope and project state

This file applies to the whole repository. Read `README.md` and
`docs/architecture.md` before changing project boundaries. Read the relevant
subproject README before editing its files.

`talker/` is the implemented RHVoice/Natia service. `web/` and `lessons/` are
placeholders. Architecture and lesson API documentation describe planned
behavior, not existing endpoints. Keep that distinction explicit in docs.

## Ownership and boundaries

- Keep synthesis code, the voice image, and its manual test page in `talker/`.
- Put the future lesson UI and API in `web/`. Do not turn `talker/index.html`
  into the lesson application or add scoring to the synthesis service.
- Put lesson source content in `lessons/`. Correct answers must remain on the
  server; never serve these files directly to browsers.
- Keep architecture and workflow documentation in `docs/`.
- Preserve existing directory names and script entry points unless the task
  calls for a migration; update all affected paths when moving files.

## Implementation conventions

- Prefer small changes with dependencies justified by the task. The synthesis
  server currently uses only Python's standard library.
- Preserve the speech contract: `POST /synthesize` accepts `text` and optional
  integer `rate` (50–200, default 100), and returns `audio/wav`. Natia is fixed
  by the service; voice and version are not request fields.
- Preserve request bounds, the synthesis timeout, serialized synthesis,
  non-root runtime, read-only filesystem, and temporary-file cleanup unless
  deliberately changing them with corresponding documentation and validation.
- In the future web app, check answers and calculate scores on the server.
  Validate attempt ownership, current question, and submitted choice; prevent
  repeated submissions from incrementing the score again.
- Use persistent storage for SQLite and cached audio. Do not commit generated
  WAV files, database files, Docker image archives, secrets, or runtime caches.
- Keep RHVoice internal in the planned Compose deployment. Existing standalone
  run scripts publish only to host loopback for manual testing.
- Support Windows PowerShell and Linux shell workflows. Build scripts resolve
  the Docker context from their own directory; preserve this behavior.
- Do not choose a web framework or add infrastructure for documentation-only
  work. When implementation requires that decision, record it in the docs.

## Naming and copy

- Generate animal lesson illustrations in the style of Niko Pirosmani. Follow
  `lessons/README.md` for composition, output format and private prompt storage.

- When introducing names, identifiers, filenames, or user-facing text proposed
  in a prompt, flag likely spelling, grammar, style, or clarity problems and
  suggest a clearer alternative.
- Preserve existing names, external/API-defined identifiers, and names the user
  explicitly requires. Do not rename them without approval.
- Obvious mistakes in newly created internal names may be corrected directly
  when doing so cannot affect compatibility or user intent.
- Commit messages for documentation-only changes must explicitly identify the
  documentation update, for example `Document the planned UI changes`.

## Validation

Match checks to the changed behavior. There is no committed automated test
suite or runnable lesson app yet.

- For documentation changes, verify relative links, commands, and consistency
  with the source. No Docker rebuild is needed for documentation alone.
- For synthesis API changes, test input validation, response status/content
  type, valid WAV output, synthesis failures, and timeouts. A simulated
  synthesizer can test HTTP behavior but cannot validate the real voice.
- For Docker or voice changes, build the image (its build step checks for a
  nonempty Natia WAV), check `/health`, synthesize `talker/sample.json`, and
  listen to the result when possible.
- For scripts, check syntax in the relevant shell and verify affected paths
  and options. Avoid replacing a running container merely to validate docs.
- When adding the lesson app, add tests for answer checking, replayed or
  out-of-order submissions, final scoring, and audio cache invalidation.

Run existing service scripts from the repository root as documented in
`README.md`. Report which checks ran and any unavailable runtime or Docker
engine; do not claim real synthesis passed based on a mock or health response.

## Documentation maintenance

Update documentation in the same change as behavior: root README for project
status/setup, `talker/README.md` for the speech service, `web/README.md` for the
lesson app, and `docs/architecture.md` for cross-service contracts or storage.
Keep commands executable and label illustrative API examples as proposals
until implemented. Do not replace existing detailed operational instructions
with a duplicate summary.
