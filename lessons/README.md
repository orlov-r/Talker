# Lesson content placeholder

This directory is reserved for server-side lesson JSON. No lessons or final
schema exist yet. The future web app will load and validate this content;
these files must not be served directly to the browser because they include
correct answers.

Define a schema with stable lesson, question, and choice IDs; lesson revision
and title; speech text and rate; choices; and a correct choice ID. Generate
audio during lesson preparation and keep WAV files in the persistent audio
cache rather than in this directory.

See [the architecture](../docs/architecture.md) for lesson versioning,
cache keys, and the browser-facing question contract. Add schema and authoring
instructions here when the first lesson is implemented.
