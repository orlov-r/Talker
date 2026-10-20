# Private question definitions

This directory holds reusable question JSON, including vocabulary pools such
as `animals1.json`, `animals2.json`, and `basics1.json`.

Lessons reference a file with `{ "question": "animals1", "level": 1 }` in
`sources`. The extension is omitted. Each file contains `choiceLayout` and
`choices`; the loader validates the question and resolves it on the server.
Level is set on the lesson reference and controls Easy eligibility. Unmarked
sources default to 1 if the lesson has no explicit level 1 source, otherwise to 2.
Generators remain in `lessons/generators.py` and are referenced directly by lessons.
Keep these files and answer keys server-side; they are never browser assets.

See [the lesson schema](../README.md#implemented-schema).
