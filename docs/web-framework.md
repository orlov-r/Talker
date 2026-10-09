# Web framework choice

Flask with Jinja templates and plain JavaScript is the chosen stack for the
initial lesson app, agreed on 2026-10-10. The minimal app is implemented;
dependencies are recorded in `web/requirements.txt`.

## Chosen stack: Flask, Jinja, and plain JavaScript

The basic app needs three screens, anonymous temporary quizzes, server-side
question generation/scoring, and HTTP calls to the existing Python speech
service. Use one Python app to serve HTML, quiz endpoints, images, and audio.
Use small amounts of JavaScript for playback, answer submission, feedback, and
explicit next-question clicks. No separate frontend build pipeline is required.

[Flask](https://flask.palletsprojects.com/en/stable/) is a lightweight Python web
framework with [Jinja templates](https://flask.palletsprojects.com/en/stable/tutorial/templates/).
It fits this small page-oriented app and keeps generators in the same language
as the speech service.

The app implements quiz validation, temporary state, synchronization, and CSRF
protection. Flask's
[default session stores values in a browser cookie](https://flask.palletsprojects.com/en/stable/quickstart/#sessions);
use it only for an opaque session identifier, never hidden answers or scores.
Waitress runs production as one process with four threads; the
[development server is not for production](https://flask.palletsprojects.com/en/stable/deploying/).

## Alternatives

| Framework | Relevant strengths | Fit for this scope |
|---|---|---|
| Flask | Routing, templates, small Python application structure | Chosen for three screens and a modest quiz API |
| [FastAPI](https://fastapi.tiangolo.com/features/) | Typed validation and automatic OpenAPI documentation | Good alternative if the API becomes the main product; less central to this page-oriented scope |
| [Django](https://www.djangoproject.com/start/) | Integrated data models, authentication, and admin interface | Useful for managed content and accounts; these are outside basic scope |

These are suitability judgments based on scope, not performance benchmarks.
Serialized RHVoice synthesis and audio reuse matter more to quiz latency than
choosing among these frameworks. Future extensions do not justify a database,
account system, or separate frontend now.

Actual dependencies, entry point, setup, and validation commands are in
[`web/README.md`](../web/README.md).
