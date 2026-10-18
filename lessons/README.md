# Server-side lesson content

`basics.json` defines «Приветствия и числа», revision 2: a vocabulary pool
(including `ძაღლი`, dog) and the trusted `number` generator in `generators.py`.
Never serve this directory to browsers.

## Implemented schema

A lesson defines `id`, `title`, `revision`, and `sources`. A source is a question
object or `{ "generator": "number" }`. Generators are trusted registry entries,
never browser-provided code or arbitrary paths.

A question has `choiceLayout` (`"short"`: four squares in a row; `"long"`, the
default: 2×2 grid) and at least four distinct `choices`:

| Choice field | Requirement |
|---|---|
| `id` | Nonempty stable identifier, unique within the source |
| `text` | Georgian text, nonempty, at most 3000 characters |
| `speechText` | Optional nonempty speech override, at most 3000 characters; defaults to `text` |
| `translation` | Russian translation (digits for numbers), nonempty, at most 3000 characters |
| `image` | Optional image filename in `web/static/choices/`, e.g. `dog.jpg` |
| `isCorrect` | Generators mark exactly one choice `true`; static choices omit it |

IDs, trimmed texts and trimmed translations must each be distinct. Images use
lowercase English words as filenames with a `.jpg` extension (hyphens may join
multiword names). Do not add style qualifiers such as `pirosmani`.
Buttons show an image when present, otherwise the translation. The translation
also supplies accessible image text.

## Selection and playback

The app randomly selects a source for each of the level's 7, 10 or 15 questions.
For static questions it randomly chooses a correct option whose Georgian text
has not already been correct in this attempt. Generated questions supply their
correct option; duplicate correct texts cause a retry. Exhausted static pools
are excluded. After all static answers are exhausted, uniqueness resets and a
new cycle begins. Generators get up to 100 proposals per question. If these
cannot supply an unused correct answer, unused static vocabulary is preferred;
if none remains, uniqueness resets and the last valid generated question is used.
This bounds generator work and permits a very small chance of repeating a
generated answer before its full output space is exhausted.
The current 26 possible answers are sufficient for all levels.

The correct option plus three sampled wrong choices are shuffled once and saved
in the attempt. Its `speechText` is spoken. After answering, feedback shows
`text (translation)`, and hovering, focusing or tapping each displayed answer
shows its Georgian text between Back and Next. This area reserves space before
answering, too. These texts are sent only after
answering, including during state recovery. Replay preserves the snapshot.

`number()` chooses N uniformly from 1–20 and a random offset R from 0–3 among
offsets for which N−R through N−R+3 stays within 1–20. These four consecutive
numbers become choices, with N marked correct. `number_to_text()` converts
integers 1–20 to Georgian words; translations are digits.

## Image assets

Save every choice image as **512×512 pixels, JPG, quality 75**. Use the
corresponding English word as the basename, e.g. `dog.jpg`; omit style qualifiers.
Store generation prompts separately in [image-prompts.json](image-prompts.json),
keyed by image filename. This private file is not served to browsers.

The dog illustration was created with the built-in image generation tool and
converted to `web/static/choices/dog.jpg`; it was not regenerated.

Validation and snapshots: [`web/content.py`](../web/content.py).
Runtime audio is never written here. See [web setup](../web/README.md) and
[architecture](../docs/architecture.md).
