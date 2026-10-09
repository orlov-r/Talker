# Lesson web app placeholder

This directory is reserved for the lesson frontend and backend. No application,
package dependencies, Dockerfile, or runnable entry point exists yet. The web
framework has not been selected.

The app will serve lesson selection, audio playback, choices, feedback,
progress, and final scores. Its server will load lesson JSON, own attempts and
answer checking, store results in SQLite, and prepare/cache WAV files through
the RHVoice/Natia service.

See [the proposed architecture](../docs/architecture.md) for routes, container
boundaries, persistence, and implementation order, and
[the development workflow](../docs/development.md) for validation expectations.
Keep correct answers and lesson source files on the server.

When implementation begins, replace this placeholder with setup, run, test,
configuration, and deployment instructions for the chosen stack.
