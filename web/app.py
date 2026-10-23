"""One-process anonymous listening app. Answers never live in session cookies."""

import os
import secrets
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from web import quiz
from web.attempts import AttemptCapacity, AttemptStore, AttemptUnavailable
from web.audio import AudioCache, cache_key, synthesize, synthesize_edge
from web.content import LESSONS, LEVELS, available_levels


VOICES = {
    "edge-eka": "Эка · Edge TTS",
    "edge-giorgi": "Гиорги · Edge TTS",
    "rhvoice": "Натия · RHVoice",
}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=4096,
        ATTEMPT_TTL=3600,
        MAX_ATTEMPTS=256,
        SYNTHESIS_URL=os.environ.get("SYNTHESIS_URL", "http://127.0.0.1:8071"),
        SYNTHESIS_VERSION=os.environ.get("SYNTHESIS_VERSION", "local-v1"),
        EDGE_EKA_URL=os.environ.get("EDGE_EKA_URL", "http://127.0.0.1:8072"),
        EDGE_GIORGI_URL=os.environ.get("EDGE_GIORGI_URL", "http://127.0.0.1:8073"),
    )
    if config:
        app.config.update(config)
    store = AttemptStore()
    cache = AudioCache()
    app.extensions["attempts"] = store.attempts
    app.extensions["attempt_store"] = store

    @app.before_request
    def protect():
        session.setdefault("owner", secrets.token_urlsafe(24))
        session.setdefault("csrf", secrets.token_urlsafe(24))
        if request.method == "POST":
            token = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(token, session["csrf"]):
                abort(403, "Обновите страницу и попробуйте ещё раз.")

    @app.after_request
    def headers(response):
        # Windows registry MIME mappings can classify .js/.css as text/plain.
        if request.endpoint == "static" and response.status_code == 200:
            filename = request.view_args.get("filename", "")
            if filename.endswith(".js"):
                response.mimetype = "text/javascript"
            elif filename.endswith(".css"):
                response.mimetype = "text/css"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; media-src 'self' blob:; frame-ancestors 'none'"
        )
        return response

    @app.errorhandler(HTTPException)
    def error(exc):
        defaults = {
            400: "Некорректный запрос.",
            404: "Страница или аудиозапись не найдена.",
            405: "Этот метод запроса не поддерживается.",
            413: "Слишком большой запрос.",
            500: "Ошибка сервера. Попробуйте ещё раз позже.",
        }
        message = (
            defaults.get(exc.code, "Не удалось выполнить запрос.")
            if exc.description == type(exc).description
            else exc.description
        )
        return jsonify(error=message), exc.code

    @app.errorhandler(AttemptUnavailable)
    @app.errorhandler(AttemptCapacity)
    @app.errorhandler(quiz.QuizConflict)
    @app.errorhandler(quiz.InvalidSelection)
    def domain_error(exc):
        status = {
            AttemptUnavailable: 404,
            AttemptCapacity: 503,
            quiz.QuizConflict: 409,
            quiz.InvalidSelection: 400,
        }[type(exc)]
        return jsonify(error=str(exc)), status

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, "Ожидается объект JSON.")
        return data

    def envelope(aid, a):
        if a["index"] == len(a["questions"]):
            return {
                "attemptId": aid,
                "complete": True,
                "score": a["score"],
                "total": len(a["questions"]),
            }
        q = a["questions"][a["index"]]
        key = cache_key(
            q["speechText"], q["rate"], app.config["SYNTHESIS_VERSION"], a["voice"]
        )
        suffix = ".wav" if a["voice"] == "rhvoice" else ""
        choices = []
        for choice in q["choices"]:
            public_choice = {"id": choice["id"], "label": choice["translation"]}
            if "image" in choice and (
                Path(app.static_folder) / "choices" / choice["image"]
            ).is_file():
                public_choice["image"] = "/static/choices/" + choice["image"]
            choices.append(public_choice)
        return {
            "attemptId": aid,
            "complete": False,
            "position": a["index"] + 1,
            "total": len(a["questions"]),
            "question": {
                "id": q["id"],
                "choices": choices,
                "choiceLayout": q["choiceLayout"],
                "audioUrl": f"/audio/{key}{suffix}?attempt={aid}",
            },
            "feedback": a["feedback"],
        }

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            csrf=session["csrf"],
            levels=LEVELS,
            lessons=LESSONS.values(),
            voices=VOICES,
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/lessons")
    def lessons():
        return jsonify(
            levels=LEVELS,
            voices=VOICES,
            lessons=[
                {
                    "id": lesson["id"],
                    "title": lesson["title"],
                    "levels": available_levels(lesson),
                }
                for lesson in LESSONS.values()
            ],
        )

    @app.post("/api/attempts")
    def start():
        data = body()
        voice = data.get("voice", "edge-eka")
        quiz.validate_selection(data.get("level"), data.get("lessonId"), voice, VOICES)
        with store.transaction():
            try:
                snapshots = quiz.prepare_questions(data["level"], data["lessonId"])
            except ValueError:
                app.logger.exception("Lesson preparation failed")
                abort(400, "Не удалось подготовить вопросы урока. Попробуйте ещё раз.")
            aid, attempt = store.create(
                session["owner"],
                voice,
                snapshots,
                ttl=app.config["ATTEMPT_TTL"],
                capacity=app.config["MAX_ATTEMPTS"],
            )
            return jsonify(envelope(aid, attempt)), 201

    @app.get("/api/attempts/<aid>")
    def current(aid):
        with store.transaction():
            return jsonify(envelope(aid, store.owned(aid, session["owner"])))

    @app.post("/api/attempts/<aid>/answers")
    def answer(aid):
        data = body()
        with store.transaction():
            a = store.owned(aid, session["owner"])
            return jsonify(quiz.answer(a, data.get("questionId"), data.get("choiceId")))

    @app.post("/api/attempts/<aid>/next")
    def next_question(aid):
        data = body()
        with store.transaction():
            a = store.owned(aid, session["owner"])
            quiz.advance(a, data.get("questionId"))
            return jsonify(envelope(aid, a))

    @app.get("/api/attempts/<aid>/result")
    def result(aid):
        with store.transaction():
            a = store.owned(aid, session["owner"])
            quiz.require_complete(a)
            return jsonify(envelope(aid, a))

    @app.get("/audio/<key>.wav")
    @app.get("/audio/<key>")
    def audio(key):
        aid = request.args.get("attempt", "")
        with store.transaction():
            a = store.owned(aid, session["owner"])
            if a["index"] == len(a["questions"]):
                abort(404)
            q = a["questions"][a["index"]]
            if key != cache_key(
                q["speechText"], q["rate"], app.config["SYNTHESIS_VERSION"], a["voice"]
            ):
                abort(404)
            voice = a["voice"]

        def rhvoice_audio():
            producer = app.config.get("SYNTHESIZER", synthesize)
            fallback_key = cache_key(
                q["speechText"], q["rate"], app.config["SYNTHESIS_VERSION"]
            )
            return cache.get(
                fallback_key,
                lambda: producer(
                    q["speechText"], q["rate"], app.config["SYNTHESIS_URL"]
                ),
            )

        try:
            mimetype = "audio/wav"
            if voice == "rhvoice":
                data = rhvoice_audio()
            else:
                try:
                    producer = app.config.get("EDGE_SYNTHESIZER", synthesize_edge)
                    url = app.config[
                        "EDGE_EKA_URL" if voice == "edge-eka" else "EDGE_GIORGI_URL"
                    ]
                    data = cache.get(
                        key, lambda: producer(q["speechText"], q["rate"], url)
                    )
                    mimetype = "audio/mpeg"
                except Exception:
                    app.logger.warning(
                        "Edge TTS failed; falling back to RHVoice", exc_info=True
                    )
                    data = rhvoice_audio()
        except Exception:
            app.logger.exception("Speech synthesis failed")
            abort(
                502,
                "Аудио недоступно. Проверьте сервис озвучки и повторите воспроизведение.",
            )
        with store.transaction():
            store.owned(aid, session["owner"])["audioReady"].add(q["id"])
        return Response(data, mimetype=mimetype)

    return app


app = create_app()
