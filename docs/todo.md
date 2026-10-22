# Future enhancements

Unchecked items are proposed work, not implemented behavior. They retain the
remaining recommendations from the project review. The directory reorganization
and correction of outdated project guidance are complete.

## Audio correctness and availability

- [x] Support Edge TTS MP3 in the lesson app, with content-type/header validation,
  engine/voice cache identity, Eka/Giorgi selection, Compose instances, and
  RHVoice fallback. MP3 frame decoding remains a browser responsibility.

- [ ] Validate actual WAV frame data before caching. Header parsing and a
  positive declared frame count currently allow truncated audio. Add regression
  tests for missing or truncated payloads and malformed upstream responses.
- [ ] Allow cache hits while an unrelated miss is synthesizing. Keep synthesis
  misses serialized, publish only validated bytes, and test concurrency and
  failure recovery without holding the cache lock throughout upstream work.
- [ ] Add bounded browser fetch and audio-preparation waits, cancellation, and
  event/object-URL cleanup. Ensure failure releases busy state and offers retry.

## Backend structure and content validation

- [ ] Extract attempt storage and quiz rules from `web/app.py` into small,
  focused modules. Keep routes responsible for HTTP concerns and preserve
  ownership, expiry, synchronization, scoring, and retry semantics.
- [ ] Validate the entire lesson catalog at startup: metadata, duplicate lesson
  IDs, and detailed source diagnostics. Basic question/source validation, generator
  retries and static fallbacks are implemented; missing images use text. Report the
  file and source location for invalid content. Keep the explicit trusted catalog.

## Source style

- [x] Expand and consolidate `web/static/style.css`, removing duplicate rules
  and obsolete selectors while preserving appearance and responsive behavior.
- [x] Normalize Python and JavaScript formatting, simplify dense expressions,
  and document lightweight formatting conventions. Preserve public identifiers.

## Repeatable validation and builds

- [ ] Commit speech HTTP tests for request bounds, validation, status/content
  type, valid WAV responses, synthesis failures, timeouts, and temporary cleanup.
  Mock synthesis tests must remain distinct from real Natia validation.
- [ ] Add targeted browser checks for playback failures, keyboard navigation,
  and lost-response recovery. Keep existing quiz contract checks.
- [ ] Run appropriate tests and syntax checks in CI.
- [ ] Record reproducible Python dependencies, RHVoice revisions, and container
  base images for deployments. Current dependency ranges, upstream `master`,
  and base-image tags can change between builds. Keep the synthesis cache
  version aligned with engine and voice changes.

Persistent storage remains conditional on requirements for saved progress or
multiple processes. Add volumes, migrations, and backup/restore documentation
when needed; this maintenance work does not introduce a database, accounts,
a new framework, or a frontend build pipeline.
