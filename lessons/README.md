# Server-side lesson content

Three private definitions are loaded by the server’s fixed catalog:

| File | Lesson | Sources |
|---|---|---|
| `basics.json` | Приветствие | One pool of 12 everyday expressions; keeps the existing `basics` ID |
| `numbers.json` | Числа | Two generators: 1–10 and 1–20 |
| `animals.json` | Животные | Two separate pools of 10 animal names |

Never serve this directory to browsers. Source counts describe pools, not the
number of answers in a session: levels continue to use 7/10/15 answers.

The first animal pool contains dog, cat, horse, cow, pig, sheep, goat, chicken,
bird and fish. The second contains rabbit/hare, mouse, duck, goose, bear, wolf,
fox, deer, lion and elephant. This is a practical beginner selection ordered by
familiarity, not a statistically verified frequency ranking. `კურდღელი` covers
rabbit/hare; the choice label explicitly includes both Russian words.

For politeness, `ბოდიში` is presented as an apology (sorry), and `უკაცრავად`
as getting attention (excuse me). Their usage overlaps; these are learning cues,
not exclusive translations. See the [Georgian teacher’s explanation](https://www.online-georgian.com/en/post/i-am-sorry-in-georgian)
and [phrasebook examples](https://en.wikivoyage.org/wiki/Georgian_phrasebook).

## Implemented schema

A lesson defines `id`, `title`, `description`, `revision`, and `sources`. A source is a question
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
Greetings have 12 possible correct answers (Hard starts a new cycle); numbers
and animals each have 20.

The correct option plus three sampled wrong choices are shuffled once and saved
in the attempt. Its `speechText` is spoken. After answering, feedback shows
`text (translation)`, and hovering, focusing or tapping each displayed answer
shows its Georgian text between Back and Next. This area reserves space before
answering, too. These texts are sent only after
answering, including during state recovery. Replay preserves the snapshot.

`number()` chooses N uniformly from 1–20 and a random offset R from 0–3 among
offsets for which N−R through N−R+3 stays within 1–20. These four consecutive
numbers become choices, with N marked correct. `number_to_text()` converts
integers 1–20 to Georgian words; translations are digits. `number-1-10` uses the
same algorithm bounded to 1–10, including all distractors.

## Image assets

Generate animal illustrations **in the style of Niko Pirosmani**: naive Georgian
folk oil painting, flat forms, expressive eyes, restrained earthy colors, visible
paint texture, and a simple dark background. Show one recognizable full animal,
centered with margin, without text, borders or watermarks. Apply this style to
future animal images too.

Save every choice image as **512×512 pixels, JPG, quality 75**. Use the
corresponding English word as the basename, e.g. `dog.jpg`; omit style qualifiers.
Store generation prompts separately in [image-prompts.json](image-prompts.json),
keyed by image filename. This private file is not served to browsers.

All animal illustrations use the built-in image generation tool. The existing
`dog.jpg` is reused; the other 19 assets were generated for this catalog.

Validation and snapshots: [`web/content.py`](../web/content.py).
Runtime audio is never written here. See [web setup](../web/README.md) and
[architecture](../docs/architecture.md).
