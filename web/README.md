# Lesson web app placeholder

This directory is reserved for the lesson frontend and backend. No application,
package dependencies, Dockerfile, or runnable entry point exists yet.
[Flask with Jinja templates and plain JavaScript](../docs/web-framework.md) is
the chosen stack for the initial implementation.

The basic interface has three screens:

- **Start:** Select skill level (Easy, Medium, Hard) and a lesson.
- **Question:** Play audio, offer replay and five text/picture answer buttons,
  then show correctness and correct answer text after submission. Enable
  **Next question** only after answering; advance on that click.
- **Result:** Show correct answers out of total and **OK** to return to selection.

The server loads static JSON or calls trusted generators from `lessons/`,
validates questions, owns temporary anonymous attempts, checks answers,
calculates scores, and obtains WAVs from RHVoice/Natia. Correct answers stay on
the server until feedback; source files are never served directly. Resolve each
generated question once so replay cannot change its answer.

Accounts, statistics, saved progress, and persistent attempts/results are outside
basic scope. No database is required. Temporary attempts and audio need bounds
and cleanup. Expired or restarted quizzes return to selection with an
explanation. Optional future features are not an initial priority.

See [the architecture](../docs/architecture.md) for question defaults, proposed
routes, container boundaries, and state handling, and
[the development workflow](../docs/development.md) for validation expectations.

When implementation begins, add setup, run, test, configuration, and deployment
instructions for the chosen stack here.
