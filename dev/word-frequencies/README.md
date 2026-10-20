# Georgian–Russian vocabulary by frequency

Six curated lesson-authoring lists, with 40 entries each (240 total):

| File | Category |
|---|---|
| [animals.txt](animals.txt) | Animals, including birds, fish and insects |
| [fruits-and-vegetables.txt](fruits-and-vegetables.txt) | Fruits and vegetables, including legumes |
| [food-products.txt](food-products.txt) | Other food products, including drinks |
| [city.txt](city.txt) | City places, buildings, transport and streets |
| [documents-state-government-law.txt](documents-state-government-law.txt) | Documents, state, government and law |
| [weather-and-nature.txt](weather-and-nature.txt) | Weather, seasons, landscapes and natural features; no specific animal or plant names |

Each `.txt` file is UTF-8 without a BOM, with LF line endings and a final newline.
Each line contains exactly `Georgian<TAB>Russian`, without headers, ranks or
counts. Georgian entries use dictionary forms (normally nominative singular;
`არჩევნები`, meaning elections, uses the usual plural). Russian translations
were authored for these lists. Brief alternate meanings are included where
useful for common usage. Each list supplies a lesson with four question pools
of ten consecutive entries, preserving this order. The first pool is marked
level 1 for Easy; Medium and Hard include all forty words. The application
loads private JSON in `lessons/`, rather than these authoring lists.

## Frequency source and ordering

Ordering uses the exact-word-form counts in Giorgi Jvaridze's scraped Georgian
frequency dataset, mirrored in David Bumbeishvili's
[GeoWordsDatabase / DifferentDatasets / Scraped](https://github.com/bumbeishvili/GeoWordsDatabase/tree/master/DifferentDatasets/Scraped).
The source description identifies Georgian Wikipedia, online libraries and
forum.ge as inputs. The repository publishes an
[MIT license](https://github.com/bumbeishvili/GeoWordsDatabase/blob/master/License).

Retrieved on 2026-10-20 from this
[ZIP download](https://raw.githubusercontent.com/bumbeishvili/GeoWordsDatabase/master/DifferentDatasets/Scraped/allwords-unique-sorted.txt.zip).
The archive member is `allwords-unique-sorted.txt`; its uncompressed bytes have
SHA-256 `38e6aa619f4938204983df17a425d20e390bc7bb8aaced2f015ce23226d1d0e0`.
The archive was used temporarily and is not stored in this repository.

For each selected Georgian entry, look up its exact spelling in the source,
read the integer count, and sort by descending count. Ties use ascending
Georgian Unicode order. All 240 entries have positive source counts.

These are curated thematic selections sorted by measured frequency, not an
exhaustive extraction of the 40 most frequent members of each category.
Counts are not lemmatized: inflected and plural forms are not added together.
The corpus mixes written and forum language and is historical, so the order
does not establish current spoken frequency. Counts also combine senses of
the same spelling: for example, `ბალი` includes uses meaning a score/point,
and `ველი` includes technical uses meaning a field. Category translations
do not imply that every counted occurrence has that meaning.
