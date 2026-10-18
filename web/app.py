"""One-process anonymous listening app. Answers never live in session cookies."""
import os
import secrets
import threading
import time
from flask import Flask, abort, jsonify, render_template, request, session, Response
from werkzeug.exceptions import HTTPException
from web.audio import AudioCache, cache_key, synthesize
from web.content import LESSON, LEVELS, questions


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
                      MAX_CONTENT_LENGTH=4096, ATTEMPT_TTL=3600, MAX_ATTEMPTS=256,
                      SYNTHESIS_URL=os.environ.get("SYNTHESIS_URL", "http://127.0.0.1:8071"),
                      SYNTHESIS_VERSION=os.environ.get("SYNTHESIS_VERSION", "local-v1"))
    if config:
        app.config.update(config)
    attempts, lock, cache = {}, threading.RLock(), AudioCache()
    app.extensions["attempts"] = attempts

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
        response.headers["Content-Security-Policy"] = "default-src 'self'; media-src 'self' blob:; frame-ancestors 'none'"
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
        message = defaults.get(exc.code, "Не удалось выполнить запрос.") if exc.description == type(exc).description else exc.description
        return jsonify(error=message), exc.code

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, "Ожидается объект JSON.")
        return data

    def owned(aid):
        now = time.monotonic()
        for key in list(attempts):
            if attempts[key]["expires"] <= now:
                del attempts[key]
        attempt = attempts.get(aid)
        if not attempt or attempt["owner"] != session["owner"]:
            abort(404, "Урок недоступен или время истекло. Начните новый урок.")
        return attempt

    def envelope(aid, a):
        if a["index"] == len(a["questions"]):
            return {"attemptId": aid, "complete": True, "score": a["score"], "total": len(a["questions"])}
        q = a["questions"][a["index"]]
        key = cache_key(q["speechText"], q["rate"], app.config["SYNTHESIS_VERSION"])
        return {"attemptId": aid, "complete": False, "position": a["index"] + 1,
                "total": len(a["questions"]), "question": {"id": q["id"], "choices": q["choices"],
                "choiceLayout": q["choiceLayout"], "audioUrl": f"/audio/{key}.wav?attempt={aid}"}, "feedback": a["feedback"]}

    @app.get("/")
    def index():
        return render_template("index.html", csrf=session["csrf"], levels=LEVELS, lesson=LESSON)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/lessons")
    def lessons():
        return jsonify(levels=LEVELS, lessons=[{"id": LESSON["id"], "title": LESSON["title"], "levels": list(LEVELS)}])

    @app.post("/api/attempts")
    def start():
        data = body()
        if not isinstance(data.get("level"), str) or data["level"] not in LEVELS or data.get("lessonId") != LESSON["id"]:
            abort(400, "Выберите доступный уровень и урок.")
        with lock:
            now = time.monotonic()
            for key in list(attempts):
                if attempts[key]["expires"] <= now or attempts[key]["owner"] == session["owner"]:
                    del attempts[key]
            if len(attempts) >= app.config["MAX_ATTEMPTS"]:
                abort(503, "Слишком много активных уроков. Попробуйте позже.")
            aid = secrets.token_urlsafe(24)
            attempts[aid] = {"owner": session["owner"], "expires": now + app.config["ATTEMPT_TTL"],
                             "questions": questions(data["level"]), "index": 0, "score": 0, "feedback": None,
                             "audioReady": set()}
            return jsonify(envelope(aid, attempts[aid])), 201

    @app.get("/api/attempts/<aid>")
    def current(aid):
        with lock:
            return jsonify(envelope(aid, owned(aid)))

    @app.post("/api/attempts/<aid>/answers")
    def answer(aid):
        data = body()
        with lock:
            a = owned(aid)
            if a["index"] >= len(a["questions"]):
                abort(409, "Урок завершён.")
            q = a["questions"][a["index"]]
            if data.get("questionId") != q["id"] or data.get("choiceId") not in [c["id"] for c in q["choices"]]:
                abort(409, "Недопустимый вопрос или вариант ответа.")
            if q["id"] not in a["audioReady"]:
                abort(409, "Прослушайте аудио перед ответом.")
            if a["feedback"] is None:
                correct = data["choiceId"] == q["correctChoiceId"]
                a["score"] += int(correct)
                a["feedback"] = {"isCorrect": correct, "correctAnswerText": q["correctAnswerText"],
                                 "selectedChoiceId": data["choiceId"]}
            return jsonify(a["feedback"])

    @app.post("/api/attempts/<aid>/next")
    def next_question(aid):
        data = body()
        with lock:
            a = owned(aid)
            if a["index"] >= len(a["questions"]) or data.get("questionId") != a["questions"][a["index"]]["id"] or a["feedback"] is None:
                abort(409, "Ответьте на текущий вопрос, прежде чем продолжить.")
            a["index"] += 1
            a["feedback"] = None
            return jsonify(envelope(aid, a))

    @app.get("/api/attempts/<aid>/result")
    def result(aid):
        with lock:
            a = owned(aid)
            if a["index"] != len(a["questions"]):
                abort(409, "Урок ещё не завершён.")
            return jsonify(envelope(aid, a))

    @app.get("/audio/<key>.wav")
    def audio(key):
        aid = request.args.get("attempt", "")
        with lock:
            a = owned(aid)
            if a["index"] == len(a["questions"]):
                abort(404)
            q = a["questions"][a["index"]]
            if key != cache_key(q["speechText"], q["rate"], app.config["SYNTHESIS_VERSION"]):
                abort(404)
        try:
            producer = app.config.get("SYNTHESIZER", synthesize)
            data = cache.get(key, lambda: producer(q["speechText"], q["rate"], app.config["SYNTHESIS_URL"]))
        except Exception:
            app.logger.exception("Speech synthesis failed")
            abort(502, "Аудио недоступно. Проверьте сервис озвучки и повторите воспроизведение.")
        with lock:
            owned(aid)["audioReady"].add(q["id"])
        return Response(data, mimetype="audio/wav")

    return app


app = create_app()
