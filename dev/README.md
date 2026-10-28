# Development resources

Keep authoring resources and supporting development files here, separate from
runtime application code and private lesson definitions. This directory is
excluded from the root Docker build context and is not served to browsers.
Do not store secrets or generated runtime caches here.

[`word-frequencies/`](word-frequencies/README.md) contains six Georgian–Russian
vocabulary lists for lesson authoring, with 40 entries per category ordered by
recorded word-form frequency. Its README documents the source and ranking limits.

[`image-prompts.json`](image-prompts.json) stores private illustration prompts,
keyed by image filename, for assets such as `dog.jpg`. Generated choice images
belong in `web/static/choices/`; prompts remain here. Follow the
[image authoring instructions](../lessons/README.md#image-assets) for composition,
dimensions, and encoding.

[`image-sheets/city.json`](image-sheets/city.json) and
[`image-sheets/fruits-and-vegetables.json`](image-sheets/fruits-and-vegetables.json)
record sheet prompts and row/column mappings for those vocabulary topics.
Original sheets are kept beside their manifests;
individual cropped JPGs are served from `web/static/choices/`.
