# Development resources

Keep authoring resources and supporting development files here, separate from
runtime application code and private lesson definitions. This directory is
excluded from the root Docker build context and is not served to browsers.
Do not store secrets or generated runtime caches here.

[`image-prompts.json`](image-prompts.json) stores private illustration prompts,
keyed by image filename, for assets such as `dog.jpg`. Generated choice images
belong in `web/static/choices/`; prompts remain here. Follow the
[image authoring instructions](../lessons/README.md#image-assets) for style,
composition, dimensions, and encoding.
