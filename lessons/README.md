# Lesson content placeholder

This directory is reserved for server-side lesson JSON and trusted question
generator scripts. No lessons, generators, or final schema exist yet. The web
app will load and validate this content. Never serve these files directly to
browsers because they contain correct answers or their generation logic.

## Proposed authoring model

A lesson has a stable ID, title, skill level (Easy, Medium, Hard), revision, and
an ordered list of question sources. A source is static JSON or a registered
server-side generator, such as a script selecting a random number from 100 to
999 and constructing five number choices.

Each resolved question has a stable ID within its attempt and these fields:

| Field | Meaning |
|---|---|
| `speechText` | Text sent to RHVoice to read aloud |
| `rate` | Optional synthesis rate, integer 50–200, default 100 |
| `correctAnswerText` | Feedback text; defaults to `speechText` |
| `choices` | Exactly five distinct choices with stable IDs, displaying text or pictures with accessible labels |
| `correctChoiceId` | Correct choice ID; may be inferred from a unique text label matching `speechText` |

Proposed default matching trims surrounding whitespace and otherwise uses exact
text equality. Missing or ambiguous matches require an explicit
`correctChoiceId`. Picture answers require an explicit ID. Validate the ID
against the five choices; do not guess numeric or linguistic conversions.

For number questions, speech and feedback can spell the number in Georgian while
choices display digits. Supply the answer fields explicitly when they differ
from the defaults. Field names distinguish feedback text from the choice ID.

Generators return the same resolved structure as static questions. Invoke only
registered, trusted server code, never browser-provided scripts or arbitrary
paths from JSON. Validate output and retain it for the active attempt; replay
and submission retries must use the same question and choices.

The browser receives display assets through the web app, not source content.
Keep generated WAVs in temporary audio storage for the basic version, outside
this directory and Git. A persistent audio cache may be added later.

See [the architecture](../docs/architecture.md) for feedback timing, attempt
snapshots, cache keys, and the proposed browser-facing question contract. Add
the final schema and executable authoring examples when lessons are implemented.
