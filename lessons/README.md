# Server-side lesson content

`basics.json` defines the single lesson, «Приветствия и числа», revision 1.
Its two ordered sources are a static greeting and the trusted `number`
generator registered in `generators.py`. Never serve this directory to browsers.

The app alternates sources to produce the selected level's 7, 10, or 15
questions. Each generator occurrence is resolved once and retained for its
attempt; replay does not change the number. The generator supplies numbers from 1 to 20, picks one as correct, speaks its
Georgian name, and displays digits as choices. The app samples three wrong choices
and shuffles them with the correct choice once per occurrence. Generated values may recur across questions.

## Implemented schema

A lesson defines `id`, `title`, `revision`, and ordered `sources`. A source is a
question object or `{ "generator": "number" }`. Generators are trusted registry
entries, never arbitrary paths or browser-provided code. The app loads the one
lesson at startup.

| Question field | Requirement |
|---|---|
| `speechText` | Nonempty string, at most 3000 characters |
| `choices` | At least four distinct `{id, label}` choices; optional `image` path under `/static/choices/` |
| `choiceLayout` | `"short"` for four squares in a row; `"long"` (default) for a 2×2 grid |
| `correctChoiceId` | Choice ID, or inferred from a unique label matching speech |
| `correctAnswerText` | Nonempty feedback text; defaults to speech text |

Matching trims whitespace and otherwise uses exact equality. Explicit correct
IDs are required when speech differs from the choice label (number names versus
digits). Duplicate IDs or labels are rejected. The app adds attempt-local IDs
and level-derived rates. For image choices, place assets in `web/static/choices/`; `label` provides alt
text. Source rate overrides remain a future extension.

Validation/integration belongs in [`web/content.py`](../web/content.py); source
content and generators remain here. Runtime audio is never written here.
See [web setup](../web/README.md) and [architecture](../docs/architecture.md).
