# Agent development guidance

## Scope and project state

This file applies to the whole repository. Read `README.md` and
`docs/architecture.md` before changing project boundaries. Read the relevant
subproject README before editing its files.

`talker-rhvoice/` is the implemented RHVoice/Natia service. `web/` contains the
implemented Flask lesson app and its automated tests; `lessons/` contains private
lesson JSON and trusted generators. Compose is implemented. Distinguish existing
behavior from future enhancements in `docs/todo.md`.

## Ownership and boundaries

- Keep synthesis code, the voice image, and its manual test page in `talker-rhvoice/`.
- Keep the lesson UI and API in `web/`. Do not turn `talker-rhvoice/index.html`
  into the lesson application or add scoring to the synthesis service.
- Put lesson source content in `lessons/`. Correct answers must remain on the
  server; never serve these files directly to browsers.
- Keep architecture and workflow documentation in `docs/`.
- Keep development resources, including private image prompts, in `dev/`.
  `lessons/questions/` holds reusable private question JSON; lessons reference
  questions and may set their level. Generators remain in `lessons/generators.py`.
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
- In the web app, check answers and calculate scores on the server.
  Validate attempt ownership, current question, and submitted choice; prevent
  repeated submissions from incrementing the score again.
- Current attempts and audio use bounded process memory. If SQLite or a persistent
  audio cache is added, use persistent storage. Do not commit generated
  WAV files, database files, Docker image archives, secrets, or runtime caches.
- Keep RHVoice internal in the Compose deployment. Existing standalone
  run scripts publish only to host loopback for manual testing.
- Support Windows PowerShell and Linux shell workflows. Build scripts resolve
  the Docker context from their own directory; preserve this behavior.
- Do not choose a web framework or add infrastructure for documentation-only
  work. When implementation requires that decision, record it in the docs.

## Naming and copy

- Save new lesson images as 256×256 JPGs at quality 75. Follow
  `lessons/README.md` for composition, output format and private prompt storage.
  Documentation does not prescribe an illustration style. Do not modify existing
  images without an explicit instruction.

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

Match checks to the changed behavior. Quiz tests are committed in
`web/test_app.py`; run `python -m unittest discover -s web -p test_app.py -v`
from the root. Speech HTTP tests are not yet committed. Quiz tests use simulated
audio and cannot validate the real voice.

- For documentation changes, verify relative links, commands, and consistency
  with the source. No Docker rebuild is needed for documentation alone.
- For synthesis API changes, test input validation, response status/content
  type, valid WAV output, synthesis failures, and timeouts. A simulated
  synthesizer can test HTTP behavior but cannot validate the real voice.
- For Docker or voice changes, build the image (its build step checks for a
  nonempty Natia WAV), check `/health`, synthesize `talker-rhvoice/sample.json`, and
  listen to the result when possible.
- For scripts, check syntax in the relevant shell and verify affected paths
  and options. Avoid replacing a running container merely to validate docs.
- When changing the lesson app, maintain tests for answer checking, replayed or
  out-of-order submissions, final scoring, and audio cache invalidation.

Run existing service scripts from the repository root as documented in
`README.md`. Report which checks ran and any unavailable runtime or Docker
engine; do not claim real synthesis passed based on a mock or health response.

## Documentation maintenance

Update documentation in the same change as behavior: root README for project
status/setup, `talker-rhvoice/README.md` for the speech service, `web/README.md` for the
lesson app, and `docs/architecture.md` for cross-service contracts or storage.
Keep commands executable and label illustrative API examples as proposals
until implemented. Do not replace existing detailed operational instructions
with a duplicate summary.
Use a few examples (usually three or four) in READMEs rather than maintaining
complete lists of lessons, questions, or choices. Content files are authoritative.
