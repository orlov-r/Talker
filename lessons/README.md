# Server-side lesson content

Private lesson definitions are loaded by the server's fixed catalog. Examples:

| File | Lesson | Example content |
|---|---|---|
| `basics.json` | Приветствие | Everyday expressions; keeps the existing `basics` ID |
| `numbers.json` | Числа | Generated number questions |
| `animals.json` | Животные | Illustrated animal vocabulary |

Never serve this directory to browsers. Source counts describe pools, not the
number of answers in a session: levels continue to use 7/10/15 answers.

Six thematic lessons use all 40 entries from each list in
[`dev/word-frequencies/`](../dev/word-frequencies/README.md), including animals,
city, and food products.
Each lesson references four pools of ten consecutive entries in the supplied
order. Only the first pool is explicitly marked `"level": 1`, so Easy uses the
first ten words; Medium and Hard use all forty. These curated selections use
recorded word-form frequency, with the ranking limits documented at the source.
Animals use pictures; the other topics use Russian text choices.
`კურდღელი` covers
rabbit/hare; the choice label explicitly includes both Russian words.

For politeness, `ბოდიში` is presented as an apology (sorry), and `უკაცრავად`
as getting attention (excuse me). Their usage overlaps; these are learning cues,
not exclusive translations. See the [Georgian teacher’s explanation](https://www.online-georgian.com/en/post/i-am-sorry-in-georgian)
and [phrasebook examples](https://en.wikivoyage.org/wiki/Georgian_phrasebook).

## Directory structure

Lesson JSON files live directly in `lessons/` and reference private question
files in [`questions/`](questions/README.md). For example, `animals1` resolves
to `questions/animals1.json`. `generators.py` provides trusted server-side
generators; generator references stay directly in the lesson.

Development resources live in [`dev/`](../dev/README.md), outside runtime lesson
content. Keep READMEs focused on schema and a few examples; the JSON files are
the authoritative content. The selection list is maintained separately below.

## Selection catalog

[`catalog.json`](catalog.json) is the ordered selection list. Each entry is a
lesson or a group; nested groups and duplicate lesson IDs are rejected:

```json
[
  { "id": "basics" },
  {
    "title": "Числа",
    "lessons": [
      { "id": "numbers", "title": "До 20", "description": "Начальный диапазон" },
      { "id": "numbers-to-100" }
    ]
  },
  [
    { "id": "fractions-to-9-99" },
    { "id": "fractions-to-99-99" }
  ]
]
```

Lesson entries use the lesson's `id`, independent of its JSON filename.
Optional `title` overrides the lesson title; optional `description` defaults to
an empty string, without inheriting the private lesson description. A group can
be a nonempty array of lesson entries or an object with a nonempty `lessons` list
and optional `title` (empty by default). Groups have no other fields. A nonempty
group title appears first in the horizontal row, before its lesson buttons;
untitled groups have no heading. Group rows add no surrounding padding.
Only listed lessons can be started. The server finds definitions in the JSON
files directly in this directory and validates references at startup; IDs must be
unique. Keep this catalog private alongside the lessons; the app exposes only
resolved display metadata, never sources or answers. Restart the app after edits
(rebuild the web image when using Compose).

## Implemented schema

A lesson defines `id`, `title`, `description`, `revision`, and `sources`.
A source is `{ "question": "animals1", "level": 1 }` or
`{ "generator": "number" }`. Question references use a basename without `.json`,
matching `[a-z][a-z0-9-]*`; paths and nested references are not supported.
Question JSON contains the question object described below. Generators are
trusted registry entries, never browser-provided code or arbitrary paths.

Each source reference may specify a positive integer `level`. Unmarked sources
default to level 1 when the lesson has no explicit `level: 1` source; otherwise
they default to level 2. The level belongs to the lesson reference, so different lessons may
assign different levels to the same question. Easy selects only level 1;
Medium and Hard include every level. This also applies to generator references.
Each frequency lesson explicitly marks its first pool level 1. Numbers marks
the 1–10 generator level 1; greetings includes its unmarked pool on Easy.
Lessons remain visible at every
difficulty. Explicit levels are preserved; if every source explicitly has a
higher level, the start API rejects Easy with HTTP 400.

A question has `choiceLayout` (`"short"`: four squares in a row; `"long"`, the
default: 2×2 grid) and at least four `choices` for static pools:

Question files may also include a short `description` for content authors.
Use this field instead of comments: standard JSON does not support comments.
It describes the vocabulary pool, stays server-side, and does not change
selection, speech, or scoring.

| Choice field | Requirement |
|---|---|
| `text` | Georgian text, nonempty, at most 3000 characters |
| `speechText` | Optional nonempty speech override, at most 3000 characters; defaults to `text` |
| `translation` | Russian translation (digits for numbers), nonempty, at most 3000 characters |
| `image` | Optional image filename in `web/static/choices/`, e.g. `dog.jpg` |
| `isCorrect` | Generators mark the correct Georgian text with `true`; static choices omit it |

Choices need no IDs. Duplicate texts and translations are allowed; all choices
whose trimmed Georgian text matches the correct text are accepted. Multiple
generator markers must agree on that text. Images use
lowercase English words as filenames with a `.jpg` extension (hyphens may join
multiword names). Do not add style qualifiers such as `pirosmani`.
Buttons show an image when present, otherwise the translation. The translation
also supplies accessible image text. Missing images are nonfatal: the Russian
translation is shown instead, including if image loading fails in the browser.

## Selection and playback

The app randomly selects an eligible source for each of the difficulty's 7, 10 or 15 questions.
For static questions it randomly chooses a correct option whose Georgian text
has not already been correct in this attempt. Generated questions supply their
correct option; duplicate correct texts cause a retry. Exhausted static pools
are excluded. After all static answers are exhausted, uniqueness resets and a
new cycle begins. Generators get up to 100 proposals per question. If these
cannot supply an unused correct answer, unused static vocabulary is preferred;
if none remains, uniqueness resets and the last valid generated question is used.
A generator that raises an exception or returns invalid data is called again
once. After a second failure, a random static question from the same lesson is
used, ignoring difficulty and previously used answers. Without a static fallback,
lesson start returns an error and preserves the active attempt. Nonempty valid
generated questions with fewer than four choices are padded with duplicates.
Static content and eligible sources are validated before the attempt starts.
The uniqueness retry limit bounds generator work and permits a very small chance
of repeating a generated answer before its full output space is exhausted.
For example, a lesson with fewer unique answers than the requested question
count starts a new cycle after those answers are exhausted.

The correct option plus three sampled other choices are shuffled once and saved
in the attempt. Its `speechText` is spoken. After answering, feedback shows
`text (translation)`, and hovering, focusing or tapping each displayed answer
shows its Georgian text between Back and Next. This area reserves space before
answering, too. These texts are sent only after
answering, including during state recovery. Replay preserves the snapshot.

`number()` chooses N uniformly from 1–20 and a random offset R from 0–3 among
offsets for which N−R through N−R+3 stays within 1–20. These four consecutive
numbers become choices, with N marked correct. `number_to_text()` converts
integers 0–1000 to Georgian words; translations are digits. `number-1-10` uses the
same algorithm bounded to 1–10, including all distractors.

### Extended number and fraction generators

The additional number lessons cover 0–100 and 0–1000. Each has two generator
sources: semi-round numbers (multiples of five starting at 20) at level 1,
and every integer including zero at level 2. For example,
`number-20-100-semi-round` and `number-0-100` are the sources for Numbers to 100.
The original 1–10/1–20 lesson remains available.

Fraction lessons cover 0.00–9.99 and 0.00–99.99. Semi-round sources at level 1
allow every whole part and hundredths ending in 0 or 5; level 2 allows every
hundredth. For example, `fraction-9-99-semi-round` generates the easier pool.
`fractional_number_to_text(whole, hundredths)` accepts two integers from 0–99
and joins their Georgian names with a space, without “dot” or “hundredths”.
Thus 3.05 is spoken as the names of 3 and 5; labels always retain two decimal
digits, including 3.00. Integer parts avoid floating-point rounding.

Semi-round choices use offsets 0, ±5, ±10, ±15 (seven candidates away from
boundaries). All-number choices use 0, ±1, ±9, ±10, ±11, ±19, ±20, ±21.
Out-of-range candidates are dropped; integer choices stay in the source range.
Fraction choices are the Cartesian product of valid mutations of each part,
using the same offset set for both parts. Whole parts stay in 0–9 or 0–99;
hundredths stay in 0–99, with no carrying or wrapping. Each pool has at least
four choices. The app retains the correct answer and samples three distractors.
Two sources per lesson do not change the 7/10/15 questions per attempt.

Georgian compound number forms follow the [Georgian number reference](https://omniglot.com/language/numbers/georgian.htm).

## Image assets

Generate animal illustrations **in the style of Niko Pirosmani**: naive Georgian
folk oil painting, flat forms, expressive eyes, restrained earthy colors, visible
paint texture, and a simple dark background. Show one recognizable full animal,
centered with margin, without text, borders or watermarks. Apply this style to
future animal images too.

Save every choice image as **512×512 pixels, JPG, quality 75**. Use the
corresponding English word as the basename, e.g. `dog.jpg`; omit style qualifiers.
Store generation prompts separately in
[`dev/image-prompts.json`](../dev/image-prompts.json), keyed by image filename.
This private development file is not served to browsers or copied into images.

Animal illustrations use the built-in image generation tool. Reuse suitable
existing assets when extending the catalog.

Validation and snapshots: [`web/content.py`](../web/content.py).
Runtime audio is never written here. See [web setup](../web/README.md) and
[architecture](../docs/architecture.md).
