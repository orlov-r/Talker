"""Quiz contract checks using simulated audio, not real voice synthesis."""

import io
import json
import re
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from lessons.generators import (
    number, number_to_text, fractional_number_to_text, integer_question,
    fractional_question, SEMI_ROUND_OFFSETS, ALL_NUMBER_OFFSETS,
)
from web.app import create_app
from web import quiz
from web.audio import AudioCache, cache_key, synthesize_edge
from web.content import (
    LESSONS,
    available_levels,
    eligible_sources,
    load_lesson,
    questions,
    validate,
)


def wav_bytes(*args):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 160)
    return output.getvalue()


class QuizTests(unittest.TestCase):
    def test_concurrent_answers_score_once_and_next_advances_once(self):
        state = self.start()
        self.client.get(state["question"]["audioUrl"])
        store = self.app.extensions["attempt_store"]
        aid = state["attemptId"]
        with self.client.session_transaction() as session:
            owner = session["owner"]
        q = store.attempts[aid]["questions"][0]

        def answer_once(_):
            with store.transaction():
                return quiz.answer(store.owned(aid, owner), q["id"], q["correctChoiceId"])

        with ThreadPoolExecutor(max_workers=4) as pool:
            feedback = list(pool.map(answer_once, range(16)))
        self.assertTrue(all(item == feedback[0] for item in feedback))
        self.assertEqual(store.attempts[aid]["score"], 1)

        def advance_once(_):
            with store.transaction():
                try:
                    quiz.advance(store.owned(aid, owner), q["id"])
                    return True
                except quiz.QuizConflict:
                    return False

        with ThreadPoolExecutor(max_workers=4) as pool:
            advanced = list(pool.map(advance_once, range(16)))
        self.assertEqual(sum(advanced), 1)
        self.assertEqual(store.attempts[aid]["index"], 1)

    def test_expiry_during_synthesis_rechecks_attempt(self):
        state = self.start()
        aid = state["attemptId"]

        def expire_during_synthesis(*args):
            self.app.extensions["attempts"][aid]["expires"] = 0
            return wav_bytes()

        self.app.config["SYNTHESIZER"] = expire_during_synthesis
        self.assertEqual(self.client.get(state["question"]["audioUrl"]).status_code, 404)
        self.assertNotIn(aid, self.app.extensions["attempts"])

    def setUp(self):
        self.calls = []

        def synth(text, rate, url):
            self.calls.append((text, rate))
            return wav_bytes()

        self.app = create_app(
            {"TESTING": True, "SECRET_KEY": "test", "SYNTHESIZER": synth}
        )
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.token = session["csrf"]

    def post(self, path, data):
        return self.client.post(path, json=data, headers={"X-CSRF-Token": self.token})

    def start(self, level="easy", lesson="animals"):
        response = self.post(
            "/api/attempts", {"lessonId": lesson, "level": level, "voice": "rhvoice"}
        )
        self.assertEqual(response.status_code, 201)
        return response.json

    def answer(self, state, choice=None):
        question = state["question"]
        return self.post(
            f"/api/attempts/{state['attemptId']}/answers",
            {
                "questionId": question["id"],
                "choiceId": choice or question["choices"][0]["id"],
            },
        )

    def advance(self, state):
        return self.post(
            f"/api/attempts/{state['attemptId']}/next",
            {"questionId": state["question"]["id"]},
        )

    def start_voice(self, voice):
        response = self.post(
            "/api/attempts", {"lessonId": "animals", "level": "easy", "voice": voice}
        )
        self.assertEqual(response.status_code, 201)
        return response.json

    def test_precache_reuses_audio_without_revealing_or_advancing(self):
        for voice in ("rhvoice", "edge-eka", "edge-giorgi"):
            producer = Mock(return_value=b"ID3audio")
            self.app.config["EDGE_SYNTHESIZER"] = producer
            state = self.start_voice(voice)
            aid = state["attemptId"]
            attempt = self.app.extensions["attempts"][aid]
            url = f"/api/attempts/{aid}/precache"
            data = {"questionId": state["question"]["id"]}
            response = self.post(url, data)
            self.assertEqual(response.status_code, 204)
            self.assertEqual(response.data, b"")
            self.assertEqual(attempt["index"], 0)
            self.assertEqual(attempt["score"], 0)
            self.assertEqual(attempt["audioReady"], set())
            self.assertEqual(self.answer(state).status_code, 409)
            self.client.get(state["question"]["audioUrl"])
            self.answer(state)
            next_state = self.advance(state).json
            calls = (len(self.calls), producer.call_count)
            self.assertEqual(
                self.client.get(next_state["question"]["audioUrl"]).status_code, 200
            )
            self.assertEqual((len(self.calls), producer.call_count), calls)
            self.assertEqual(self.post(url, data).status_code, 409)

    def test_precache_authorization_expiry_and_last_question(self):
        state = self.start()
        aid = state["attemptId"]
        url = f"/api/attempts/{aid}/precache"
        data = {"questionId": state["question"]["id"]}
        self.assertEqual(self.client.post(url, json=data).status_code, 403)
        other = self.app.test_client()
        other.get("/")
        with other.session_transaction() as session:
            token = session["csrf"]
        self.assertEqual(
            other.post(url, json=data, headers={"X-CSRF-Token": token}).status_code, 404
        )
        self.assertEqual(self.post(url, {}).status_code, 409)
        attempt = self.app.extensions["attempts"][aid]
        attempt["index"] = len(attempt["questions"]) - 1
        data = {"questionId": attempt["questions"][-1]["id"]}
        self.assertEqual(self.post(url, data).status_code, 204)
        self.assertEqual(self.calls, [])
        attempt["index"] += 1
        self.assertEqual(self.post(url, data).status_code, 409)
        attempt["expires"] = 0
        self.assertEqual(self.post(url, data).status_code, 404)

    def test_precache_failure_retries_and_version_invalidates(self):
        state = self.start()
        aid = state["attemptId"]
        url = f"/api/attempts/{aid}/precache"
        data = {"questionId": state["question"]["id"]}
        producer = Mock(side_effect=TimeoutError())
        self.app.config["SYNTHESIZER"] = producer
        with self.assertLogs(self.app.logger, level="ERROR"):
            self.assertEqual(self.post(url, data).status_code, 502)
        attempt = self.app.extensions["attempts"][aid]
        self.assertEqual(attempt["audioReady"], set())
        self.assertEqual(attempt["index"], 0)
        producer.side_effect = None
        producer.return_value = wav_bytes()
        self.assertEqual(self.post(url, data).status_code, 204)
        self.assertEqual(self.post(url, data).status_code, 204)
        self.assertEqual(producer.call_count, 2)
        self.app.config["SYNTHESIS_VERSION"] = "updated"
        self.assertEqual(self.post(url, data).status_code, 204)
        self.assertEqual(producer.call_count, 3)

    def test_voice_selection_and_validation(self):
        page = self.client.get("/").text
        for voice in ("edge-eka", "edge-giorgi", "rhvoice"):
            self.assertIn(f'value="{voice}"', page)
        self.assertRegex(page, r'name="voice" value="edge-eka" checked')
        response = self.post("/api/attempts", {"lessonId": "animals", "level": "easy"})
        self.assertEqual(response.status_code, 201)
        state = response.json
        self.assertEqual(
            self.app.extensions["attempts"][state["attemptId"]]["voice"], "edge-eka"
        )
        for voice in ("unknown", None, [], {}):
            response = self.post(
                "/api/attempts",
                {"lessonId": "animals", "level": "easy", "voice": voice},
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                self.client.get(f"/api/attempts/{state['attemptId']}").status_code, 200
            )

    def test_edge_voices_mp3_cache_and_ownership(self):
        mp3 = b"ID3" + b"\0" * 20
        producer = Mock(return_value=mp3)
        self.app.config["EDGE_SYNTHESIZER"] = producer
        for voice, setting in (
            ("edge-eka", "EDGE_EKA_URL"),
            ("edge-giorgi", "EDGE_GIORGI_URL"),
        ):
            state = self.start_voice(voice)
            url = state["question"]["audioUrl"]
            self.assertEqual(self.client.get(url).data, mp3)
            self.assertEqual(self.client.get(url).mimetype, "audio/mpeg")
            self.assertEqual(producer.call_args.args[1:], (80, self.app.config[setting]))
            self.assertEqual(self.app.test_client().get(url).status_code, 404)
            self.assertEqual(
                self.client.get(url.replace("/audio/", "/audio/wrong")).status_code, 404
            )
            self.assertEqual(self.answer(state).status_code, 200)
            # Version changes invalidate even a previously authorized audio URL.
            self.app.config["SYNTHESIS_VERSION"] += "-new"
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(producer.call_count, 2)
        self.assertEqual(self.calls, [])
        self.assertNotEqual(
            cache_key("a", 80, "v1", "edge-eka"),
            cache_key("a", 80, "v1", "edge-giorgi"),
        )
        self.assertNotEqual(cache_key("a", 80, "v1", "edge-eka"), cache_key("a", 80, "v1"))

    def test_edge_error_fallback_and_recovery(self):
        producer = Mock(side_effect=[TimeoutError(), ValueError("bad MP3"), b"ID3audio"])
        self.app.config["EDGE_SYNTHESIZER"] = producer
        state = self.start_voice("edge-eka")
        url = state["question"]["audioUrl"]
        with self.assertLogs(self.app.logger, level="WARNING"):
            for _ in range(2):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "audio/wav")
                self.assertEqual(response.data, wav_bytes())
        self.assertEqual(len(self.calls), 1)
        response = self.client.get(url)
        self.assertEqual(response.mimetype, "audio/mpeg")
        self.assertEqual(self.client.get(url).data, b"ID3audio")
        self.assertEqual(producer.call_count, 3)
        self.assertEqual(self.answer(state).status_code, 200)
        self.assertEqual(self.advance(state).json["position"], 2)
        self.assertEqual(
            self.app.extensions["attempts"][state["attemptId"]]["voice"], "edge-eka"
        )

    def test_both_engines_fail_then_retry(self):
        self.app.config["EDGE_SYNTHESIZER"] = Mock(side_effect=OSError("offline"))
        self.app.config["SYNTHESIZER"] = Mock(side_effect=OSError("offline"))
        state = self.start_voice("edge-giorgi")
        with self.assertLogs(self.app.logger, level="WARNING"):
            self.assertEqual(
                self.client.get(state["question"]["audioUrl"]).status_code, 502
            )
        self.assertEqual(self.answer(state).status_code, 409)
        self.assertEqual(self.advance(state).status_code, 409)
        self.app.config["SYNTHESIZER"] = wav_bytes
        with self.assertLogs(self.app.logger, level="WARNING"):
            self.assertEqual(
                self.client.get(state["question"]["audioUrl"]).mimetype, "audio/wav"
            )
        self.assertEqual(self.answer(state).status_code, 200)

    def test_edge_http_validation_and_bounds(self):
        response = Mock()
        response.headers.get_content_type.return_value = "audio/mpeg"
        response.read.return_value = b"ID3audio"
        with patch("web.audio.urllib.request.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = response
            self.assertEqual(
                synthesize_edge("გამარჯობა", 80, "http://edge:8080"), b"ID3audio"
            )
            req = open_url.call_args.args[0]
            self.assertEqual(req.full_url, "http://edge:8080/synthesize")
            self.assertEqual(json.loads(req.data), {"text": "გამარჯობა", "rate": 80})
            self.assertEqual(open_url.call_args.kwargs["timeout"], 65)
            response.read.return_value = b"\xff\xfb\x90\x00"
            self.assertEqual(
                synthesize_edge("a", 100, "http://edge"), response.read.return_value
            )
            for invalid in (b"", b"html error", b"ID3" + b"a" * (4 * 1024 * 1024)):
                response.read.return_value = invalid
                with self.assertRaises(ValueError):
                    synthesize_edge("a", 100, "http://edge")
            response.headers.get_content_type.return_value = "text/html"
            with self.assertRaises(ValueError):
                synthesize_edge("a", 100, "http://edge")
            open_url.side_effect = TimeoutError()
            with self.assertRaises(TimeoutError):
                synthesize_edge("a", 100, "http://edge")

    def test_levels_and_complete_score(self):
        for level, count, rate in [
            ("easy", 7, 80),
            ("medium", 10, 100),
            ("hard", 15, 120),
        ]:
            for lesson in LESSONS:
                state = self.start(level, lesson)
                aid = state["attemptId"]
                self.assertEqual(state["total"], count)
                self.assertEqual(
                    self.client.get(f"/api/attempts/{aid}/result").status_code, 409
                )
                for i in range(count):
                    serialized = json.dumps(state)
                    self.assertNotIn("speechText", serialized)
                    self.assertNotIn("description", serialized)
                    self.assertNotIn("correctChoiceId", serialized)
                    self.assertEqual(len(state["question"]["choices"]), 4)
                    self.assertEqual(
                        self.client.get(state["question"]["audioUrl"]).mimetype,
                        "audio/wav",
                    )
                    q = self.app.extensions["attempts"][aid]["questions"][i]
                    self.assertEqual(q["rate"], rate)
                    first = self.answer(state, q["correctChoiceId"])
                    self.assertTrue(first.json["isCorrect"])
                    other = next(
                        c["id"] for c in q["choices"] if c["id"] != q["correctChoiceId"]
                    )
                    self.assertEqual(self.answer(state, other).json, first.json)
                    previous = state
                    state = self.advance(state).json
                    self.assertEqual(self.advance(previous).status_code, 409)
                self.assertEqual(state["score"], count)
                self.assertTrue(state["complete"])
                self.assertEqual(
                    self.client.get(f"/api/attempts/{aid}/result").json["score"], count
                )

    def test_wrong_answer_and_order(self):
        state = self.start()
        self.assertEqual(self.answer(state).status_code, 409)
        self.assertEqual(self.advance(state).status_code, 409)
        self.client.get(state["question"]["audioUrl"])
        self.assertEqual(self.answer(state, "unknown").status_code, 409)
        self.assertEqual(
            self.post(
                f"/api/attempts/{state['attemptId']}/answers",
                {"questionId": "q2", "choiceId": "hello"},
            ).status_code,
            409,
        )
        q = self.app.extensions["attempts"][state["attemptId"]]["questions"][0]
        wrong = next(
            c["id"]
            for c in state["question"]["choices"]
            if c["id"] != q["correctChoiceId"]
        )
        response = self.answer(state, wrong)
        self.assertEqual(response.json["selectedChoiceId"], wrong)
        self.assertEqual(
            self.client.get(f"/api/attempts/{state['attemptId']}").json["feedback"],
            response.json,
        )
        self.assertFalse(response.json["isCorrect"])
        self.assertEqual(
            self.app.extensions["attempts"][state["attemptId"]]["score"], 0
        )

    def test_lesson_selection_isolated_and_private(self):
        catalog = self.client.get("/api/lessons").json["lessons"]
        self.assertEqual([l["id"] for l in catalog], list(LESSONS))
        self.assertTrue(all(set(l) == {"id", "title", "levels"} for l in catalog))
        self.assertEqual(
            {l["id"]: l["levels"] for l in catalog},
            {lid: ["easy", "medium", "hard"] for lid in LESSONS},
        )
        self.assertEqual(
            self.client.get("/lessons/questions/animals1.json").status_code, 404
        )
        for lid in LESSONS:
            state = self.start("hard", lid)
            snapshots = self.app.extensions["attempts"][state["attemptId"]]["questions"]
            if lid == "numbers":
                self.assertTrue(
                    all(
                        q["speechText"] in [number_to_text(n) for n in range(1, 21)]
                        for q in snapshots
                    )
                )
                self.assertTrue(all(q["choiceLayout"] == "short" for q in snapshots))
            elif lid.startswith(("numbers-to-", "fractions-to-")):
                self.assertTrue(all(len(q["choices"]) == 4 for q in snapshots))
                self.assertTrue(all(q["choiceLayout"] == "short" for q in snapshots))
            else:
                pools = [
                    {c["text"] for c in s["choices"]} for s in LESSONS[lid]["sources"]
                ]
                self.assertTrue(
                    all(
                        any({c["text"] for c in q["choices"]} <= pool for pool in pools)
                        for q in snapshots
                    )
                )
            self.assertEqual(
                self.client.get(
                    "/lessons/" + ("basics" if lid == "basics" else lid) + ".json"
                ).status_code,
                404,
            )
        self.assertEqual(
            self.post("/api/attempts", {"lessonId": [], "level": "easy"}).status_code,
            400,
        )

    def test_choice_texts_are_private_until_answer_and_survive_recovery(self):
        state = self.start()
        q = self.app.extensions["attempts"][state["attemptId"]]["questions"][0]
        for public in state["question"]["choices"]:
            self.assertEqual(set(public) - {"id", "label", "image"}, set())
            private = next(c for c in q["choices"] if c["id"] == public["id"])
            self.assertEqual(public["label"], private["translation"])
        self.assertIsNone(state["feedback"])
        self.client.get(state["question"]["audioUrl"])
        self.assertEqual(self.calls, [(q["speechText"], q["rate"])])
        answered = self.answer(state, q["correctChoiceId"]).json
        self.assertEqual(
            answered["choiceTexts"], {c["id"]: c["text"] for c in q["choices"]}
        )
        self.assertEqual(answered["correctAnswerText"], q["correctAnswerText"])
        self.assertEqual(
            self.client.get(f"/api/attempts/{state['attemptId']}").json["feedback"],
            answered,
        )
        with self.client.get("/static/choices/dog.jpg") as response:
            self.assertEqual(response.mimetype, "image/jpeg")

    def test_ownership_expiry_and_private_content(self):
        state = self.start()
        other = self.app.test_client()
        other.get("/")
        with other.session_transaction() as session:
            token = session["csrf"]
        base = f"/api/attempts/{state['attemptId']}"
        for path in [base, base + "/result", state["question"]["audioUrl"]]:
            self.assertEqual(other.get(path).status_code, 404)
        for path in [base + "/answers", base + "/next"]:
            self.assertEqual(
                other.post(path, json={}, headers={"X-CSRF-Token": token}).status_code,
                404,
            )
        self.assertEqual(self.client.get("/lessons/basics.json").status_code, 404)
        self.app.extensions["attempts"][state["attemptId"]]["expires"] = 0
        self.assertEqual(self.client.get(base).status_code, 404)

    def test_validation_csrf_bounds(self):
        self.assertEqual(self.client.post("/api/attempts", json={}).status_code, 403)
        for data in [
            [],
            {},
            {"lessonId": "basics", "level": []},
            {"lessonId": "other", "level": "easy"},
        ]:
            self.assertEqual(self.post("/api/attempts", data).status_code, 400)
        self.assertEqual(
            self.post("/api/attempts", {"padding": "x" * 5000}).status_code, 413
        )

    def test_stable_generation_audio_cache_and_version(self):
        state = self.start()
        self.client.get(state["question"]["audioUrl"])
        self.client.get(state["question"]["audioUrl"])
        self.assertEqual(len(self.calls), 1)
        self.answer(state)
        dynamic = self.advance(state).json
        before = self.client.get(f"/api/attempts/{state['attemptId']}").json
        self.client.get(dynamic["question"]["audioUrl"])
        self.client.get(dynamic["question"]["audioUrl"])
        self.assertEqual(
            before, self.client.get(f"/api/attempts/{state['attemptId']}").json
        )
        self.assertEqual(len(self.calls), 2)
        self.app.config["SYNTHESIS_VERSION"] = "changed-build"
        current = self.client.get(f"/api/attempts/{state['attemptId']}").json
        self.assertNotEqual(
            current["question"]["audioUrl"], dynamic["question"]["audioUrl"]
        )
        self.assertEqual(
            self.client.get(dynamic["question"]["audioUrl"]).status_code, 404
        )
        self.client.get(current["question"]["audioUrl"])
        self.assertEqual(len(self.calls), 3)

    def test_audio_failure_retry_does_not_score_or_advance(self):
        state = self.start()

        def fail(*args):
            raise TimeoutError("simulated timeout")

        self.app.config["SYNTHESIZER"] = fail
        with self.assertLogs(self.app.logger, level="ERROR"):
            self.assertEqual(
                self.client.get(state["question"]["audioUrl"]).status_code, 502
            )
        self.assertEqual(self.answer(state).status_code, 409)
        self.assertEqual(self.advance(state).status_code, 409)
        self.app.config["SYNTHESIZER"] = wav_bytes
        self.assertEqual(
            self.client.get(state["question"]["audioUrl"]).status_code, 200
        )
        self.assertEqual(self.answer(state).status_code, 200)

    def test_capacity(self):
        self.app.config["MAX_ATTEMPTS"] = 0
        self.assertEqual(
            self.post(
                "/api/attempts", {"lessonId": "animals", "level": "easy"}
            ).status_code,
            503,
        )

    def test_equal_georgian_choices_are_all_accepted(self):
        # Four separate buttons may represent the same Georgian answer.
        source = {
            "choices": [{"text": "ერთი", "translation": str(i)} for i in range(4)]
        }
        with patch.dict(LESSONS, {"duplicate": {"sources": [source]}}):
            for index in range(4):
                state = self.start(lesson="duplicate")
                self.client.get(state["question"]["audioUrl"])
                choice = state["question"]["choices"][index]["id"]
                self.assertTrue(self.answer(state, choice).json["isCorrect"])
                self.assertTrue(self.answer(state, choice).json["isCorrect"])
                self.assertEqual(
                    self.app.extensions["attempts"][state["attemptId"]]["score"], 1
                )

    def test_invalid_lesson_does_not_replace_active_attempt(self):
        state = self.start()
        invalid = [
            None,
            {},
            {"sources": []},
            {"sources": [None]},
            {"sources": [{"choices": [None] * 4}]},
            {"sources": [{"generator": "broken"}]},
        ]
        for lesson in invalid:
            with self.subTest(lesson=lesson), patch.dict(LESSONS, {"bad": lesson}):
                with self.assertLogs(self.app.logger, level="ERROR"):
                    response = self.post(
                        "/api/attempts", {"lessonId": "bad", "level": "easy"}
                    )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    self.client.get(f"/api/attempts/{state['attemptId']}").json, state
                )

    def test_missing_images_use_translation(self):
        source = {
            "choices": [
                {"text": str(i), "translation": str(i), "image": "missing.jpg"}
                for i in range(4)
            ]
        }
        with patch.dict(LESSONS, {"missing": {"sources": [source]}}):
            state = self.start(lesson="missing")
        self.assertTrue(all("image" not in c for c in state["question"]["choices"]))
        self.assertEqual(
            {c["label"] for c in state["question"]["choices"]}, {"0", "1", "2", "3"}
        )

    def test_page_and_assets(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('<html lang="ru">', html)
        self.assertIn("Вопросов: 15", html)
        for lesson in LESSONS.values():
            self.assertIn(lesson["title"], html)
            self.assertIn(f'value="{lesson["id"]}"', html)
        for path in re.findall(r'(?:src|href)="(/static/[^\"]+)"', html):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.mimetype,
                    "text/javascript" if path.endswith(".js") else "text/css",
                )


class ContentAndCacheTests(unittest.TestCase):
    def test_generator_failures_retry_once_then_static_fallback(self):
        static = {
            "level": 2,
            "choices": [{"text": str(i), "translation": str(i)} for i in range(4)],
        }
        for bad in [
            RuntimeError("broken"), None, [], {}, {"choices": []},
            {"choices": [None]}, {"choices": [{"text": "one"}]},
        ]:
            for recover in [True, False]:
                with self.subTest(bad=bad, recover=recover):
                    generator = Mock(side_effect=[bad, number() if recover else bad])
                    lesson = {
                        "sources": [{"generator": "test", "level": 1}, static]
                    }
                    with patch.dict(
                        "web.content.GENERATORS", {"test": generator}
                    ), patch.dict(
                        "web.content.LEVELS", {"easy": {"questionCount": 1, "rate": 80}}
                    ):
                        q = questions("easy", lesson)[0]
                    self.assertEqual(generator.call_count, 2)
                    self.assertEqual(len(q["choices"]), 4)
                    if not recover:
                        self.assertIn(q["correctText"], {"0", "1", "2", "3"})

    def test_generator_failure_without_static_is_bounded(self):
        generator = Mock(side_effect=RuntimeError("broken"))
        with patch.dict("web.content.GENERATORS", {"test": generator}):
            with self.assertRaises(ValueError):
                questions("easy", {"sources": [{"generator": "test"}]})
        self.assertEqual(generator.call_count, 2)

    def test_short_generated_questions_are_padded_without_mutating_output(self):
        for count in [1, 2, 3]:
            output = {
                "choices": [
                    {"text": str(i), "translation": str(i), "isCorrect": i == 0}
                    for i in range(count)
                ]
            }
            generator = Mock(return_value=output)
            with patch.dict("web.content.GENERATORS", {"test": generator}), patch.dict(
                "web.content.LEVELS", {"easy": {"questionCount": 1, "rate": 80}}
            ):
                q = questions("easy", {"sources": [{"generator": "test"}]})[0]
            self.assertEqual(generator.call_count, 1)
            self.assertEqual(len(q["choices"]), 4)
            self.assertEqual(len({c["id"] for c in q["choices"]}), 4)
            self.assertEqual(q["correctText"], "0")
            self.assertEqual(len(output["choices"]), count)
            self.assertTrue(all("id" not in c for c in output["choices"]))

    def test_generator_can_reuse_correct_choice_dictionary(self):
        choice = {"text": "ერთი", "translation": "1", "isCorrect": True}
        with patch.dict(
            "web.content.GENERATORS", {"test": lambda: {"choices": [choice] * 4}}
        ):
            qs = questions("easy", {"sources": [{"generator": "test"}]})
        for q in qs:
            self.assertEqual(len({c["id"] for c in q["choices"]}), 4)
            self.assertEqual(q["correctText"], "ერთი")
        self.assertNotIn("id", choice)

    def test_references_and_lesson_specific_levels(self):
        root = Path(__file__).resolve().parents[1] / "lessons"
        self.assertEqual(
            json.loads((root / "animals.json").read_text(encoding="utf-8"))["sources"],
            [
                {"question": "animals1", "level": 1},
                {"question": "animals2"},
                {"question": "animals3"},
                {"question": "animals4"},
            ],
        )
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "questions").mkdir()
            source = {
                "choices": [
                    {"id": str(i), "text": str(i), "translation": str(i)}
                    for i in range(4)
                ]
            }
            question_path = directory / "questions/shared.json"
            question_path.write_text(json.dumps(source), encoding="utf-8")
            path = directory / "lesson.json"

            def load(sources):
                path.write_text(json.dumps({"sources": sources}), encoding="utf-8")
                return load_lesson(path)

            first = load([{"question": "shared", "level": 1}])
            second = load([{"question": "shared"}])
            self.assertEqual(available_levels(first), ["easy", "medium", "hard"])
            self.assertEqual(available_levels(second), ["easy", "medium", "hard"])
            self.assertEqual(len(questions("easy", first)), 7)
            self.assertEqual(len(questions("easy", second)), 7)
            mixed = load([{"question": "shared", "level": 1}, {"question": "shared"}])
            self.assertEqual(len(eligible_sources("easy", mixed)), 1)
            self.assertNotIn("level", second["sources"][0])
            self.assertEqual(
                json.loads(question_path.read_text(encoding="utf-8")), source
            )
            for ref in ["../shared", "/shared", "shared.json", 1]:
                with self.subTest(ref=ref), self.assertRaises(ValueError):
                    load([{"question": ref}])
            with self.assertRaises(FileNotFoundError):
                load([{"question": "missing"}])
            for source_ref in [
                {},
                {"question": "shared", "generator": "number"},
                {"generator": "unknown"},
                {"choices": []},
            ]:
                with self.subTest(source=source_ref), self.assertRaises(ValueError):
                    load([source_ref])
            for level in [0, -1, True, "1", 1.5, None]:
                with self.subTest(level=level), self.assertRaises(ValueError):
                    load([{"question": "shared", "level": level}])

    def test_easy_filters_sources_and_higher_difficulties_include_all(self):
        first, *advanced = LESSONS["animals"]["sources"]
        easy_ids = {c["text"] for c in first["choices"]}
        advanced_ids = {c["text"] for source in advanced for c in source["choices"]}
        for q in questions("easy", LESSONS["animals"]):
            self.assertLessEqual({c["text"] for c in q["choices"]}, easy_ids)
        for level in ["medium", "hard"]:
            # Exhaust all pools so the assertion does not depend on random draws.
            with patch.dict(
                "web.content.LEVELS", {level: {"rate": 100, "questionCount": 40}}
            ):
                qs = questions(level, LESSONS["animals"])
            correct = {q["correctText"] for q in qs}
            self.assertTrue(correct & easy_ids)
            self.assertTrue(correct & advanced_ids)
        fixed = number()
        with patch.dict("web.content.GENERATORS", {"fixed": lambda: fixed}):
            lesson = {"sources": [dict(first, level=1), {"generator": "fixed"}]}
            with patch("web.content.GENERATORS", {}):
                self.assertEqual(len(questions("easy", lesson)), 7)
            lesson = {"sources": [{"generator": "fixed", "level": 1}]}
            self.assertEqual(len(questions("easy", lesson)), 7)

    def test_implicit_levels_depend_on_explicit_level_one_in_lesson(self):
        unmarked = {"generator": "number"}
        advanced = {"generator": "number-1-10", "level": 2}
        beginner = {"generator": "number-1-10", "level": 1}
        for sources, expected in [
            ([unmarked], [unmarked]),
            ([advanced, unmarked], [unmarked]),
            ([unmarked, beginner], [beginner]),
            ([advanced, beginner, unmarked], [beginner]),
        ]:
            with self.subTest(sources=sources):
                lesson = {"sources": sources}
                self.assertEqual(eligible_sources("easy", lesson), expected)
                for level in ["medium", "hard"]:
                    self.assertEqual(eligible_sources(level, lesson), sources)
                self.assertNotIn("level", unmarked)

    def test_catalog_and_animal_assets(self):
        self.assertEqual(
            list(LESSONS),
            [
                "basics",
                "numbers",
                "numbers-to-100",
                "numbers-to-1000",
                "fractions-to-9-99",
                "fractions-to-99-99",
                "animals",
                "city",
                "documents-state-government-law",
                "food-products",
                "fruits-and-vegetables",
                "weather-and-nature",
            ],
        )
        self.assertEqual(
            [len(l["sources"]) for l in LESSONS.values()], [1] + [2] * 5 + [4] * 6
        )
        self.assertEqual(len(LESSONS["basics"]["sources"][0]["choices"]), 11)
        for source in LESSONS["animals"]["sources"]:
            self.assertEqual(len(source["choices"]), 10)
            for choice in validate(source)["choices"]:
                self.assertTrue(
                    (
                        Path(__file__).parent / "static/choices" / choice["image"]
                    ).is_file()
                )

    def test_frequency_lessons_preserve_order_and_easy_vocabulary(self):
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / "dev/word-frequencies").glob("*.txt")):
            with self.subTest(topic=path.stem):
                expected = [
                    line.split("\t")
                    for line in path.read_text(encoding="utf-8").splitlines()
                ]
                lesson = LESSONS[path.stem]
                self.assertEqual(len(lesson["sources"]), 4)
                self.assertTrue(all(len(s["choices"]) == 10 for s in lesson["sources"]))
                actual = [
                    [c["text"], c["translation"]]
                    for s in lesson["sources"]
                    for c in s["choices"]
                ]
                self.assertEqual(actual, expected)
                self.assertEqual(
                    eligible_sources("easy", lesson), lesson["sources"][:1]
                )
                self.assertEqual(lesson["sources"][0]["level"], 1)
                easy_words = {text for text, _ in expected[:10]}
                for q in questions("easy", lesson):
                    self.assertIn(q["correctText"], easy_words)
                    self.assertLessEqual({c["text"] for c in q["choices"]}, easy_words)

    def test_extended_number_names(self):
        expected = {
            0: "ნული", 21: "ოცდაერთი", 40: "ორმოცი", 59: "ორმოცდაცხრამეტი",
            60: "სამოცი", 80: "ოთხმოცი", 99: "ოთხმოცდაცხრამეტი",
            100: "ასი", 101: "ას ერთი", 200: "ორასი", 247: "ორას ორმოცდაშვიდი",
            300: "სამასი", 400: "ოთხასი", 500: "ხუთასი", 600: "ექვსასი",
            700: "შვიდასი", 800: "რვაასი", 900: "ცხრაასი",
            999: "ცხრაას ოთხმოცდაცხრამეტი", 1000: "ათასი",
        }
        for value, text in expected.items():
            self.assertEqual(number_to_text(value), text)
        self.assertEqual(len({number_to_text(n) for n in range(1001)}), 1001)
        self.assertEqual(fractional_number_to_text(3, 5), "სამი ხუთი")
        self.assertEqual(fractional_number_to_text(0, 0), "ნული ნული")
        self.assertEqual(fractional_number_to_text(99, 99),
                         "ოთხმოცდაცხრამეტი ოთხმოცდაცხრამეტი")
        for parts in [(-1, 0), (0, 100), (100, 0), (True, 5), (3, 1.5), ("3", 5)]:
            with self.assertRaises(ValueError):
                fractional_number_to_text(*parts)

    def test_integer_mutations_and_bounds(self):
        for maximum in (100, 1000):
            for semi in (False, True):
                minimum, step = (20, 5) if semi else (0, 1)
                offsets = SEMI_ROUND_OFFSETS if semi else ALL_NUMBER_OFFSETS
                for correct in range(minimum, maximum + 1, step):
                    with patch("lessons.generators.random.randrange", return_value=correct) as draw:
                        q = validate(integer_question(maximum, semi), generated=True)
                    draw.assert_called_once_with(minimum, maximum + 1, step)
                    self.assertEqual({int(c["translation"]) for c in q["choices"]},
                                     {correct + d for d in offsets
                                      if minimum <= correct + d <= maximum})
                    self.assertGreaterEqual(len(q["choices"]), 4)
                    self.assertEqual([c["translation"] for c in q["choices"] if c["isCorrect"]],
                                     [str(correct)])

    def test_fraction_mutations_and_bounds(self):
        for maximum in (9, 99):
            for semi in (False, True):
                offsets = SEMI_ROUND_OFFSETS if semi else ALL_NUMBER_OFFSETS
                for whole in (0, 4, maximum):
                    for hundredths in range(0, 100, 5 if semi else 1):
                        with patch("lessons.generators.random.randrange",
                                   side_effect=[whole, hundredths]) as draw:
                            q = validate(fractional_question(maximum, semi), generated=True)
                        self.assertEqual(draw.call_args_list,
                                         [((maximum + 1,),), ((0, 100, 5 if semi else 1),)])
                        expected = {f"{whole + dw}.{hundredths + dh:02d}"
                                    for dw in offsets for dh in offsets
                                    if 0 <= whole + dw <= maximum and 0 <= hundredths + dh <= 99}
                        self.assertEqual({c["translation"] for c in q["choices"]}, expected)
                        self.assertGreaterEqual(len(expected), 4)
                        self.assertEqual(len(q["choices"]), len(expected))
                        self.assertEqual([c["translation"] for c in q["choices"] if c["isCorrect"]],
                                         [f"{whole}.{hundredths:02d}"])

    def test_new_number_lesson_levels(self):
        for lid in ("numbers-to-100", "numbers-to-1000", "fractions-to-9-99", "fractions-to-99-99"):
            lesson = LESSONS[lid]
            self.assertEqual([s["level"] for s in lesson["sources"]], [1, 2])
            self.assertEqual(eligible_sources("easy", lesson), lesson["sources"][:1])
            self.assertEqual(eligible_sources("medium", lesson), lesson["sources"])
            for q in questions("easy", lesson):
                correct = next(c["translation"] for c in q["choices"] if c["id"] == q["correctChoiceId"])
                self.assertEqual(int(correct.split(".")[-1]) % 5, 0)

    def test_short_number_range(self):
        for correct in range(1, 11):
            for offset in range(max(0, correct - 7), min(3, correct - 1) + 1):
                with patch(
                    "lessons.generators.random.randint", side_effect=[correct, offset]
                ):
                    q = validate(number(10), generated=True)
                self.assertTrue(
                    all(1 <= int(c["translation"]) <= 10 for c in q["choices"])
                )
                self.assertEqual(
                    next(c["translation"] for c in q["choices"] if c["isCorrect"]),
                    str(correct),
                )

    def test_number_intervals_and_correct_markers(self):
        for correct in range(1, 21):
            for offset in range(max(0, correct - 17), min(3, correct - 1) + 1):
                with patch(
                    "lessons.generators.random.randint", side_effect=[correct, offset]
                ):
                    q = validate(number(), generated=True)
                self.assertEqual(
                    [int(c["translation"]) for c in q["choices"]],
                    list(range(correct - offset, correct - offset + 4)),
                )
                self.assertTrue(1 <= int(q["choices"][0]["translation"]) <= 17)
                marked = [c for c in q["choices"] if c["isCorrect"]]
                self.assertEqual([c["translation"] for c in marked], [str(correct)])
                self.assertEqual(marked[0]["text"], number_to_text(correct))
        self.assertEqual(number_to_text(1), "ერთი")
        self.assertEqual(number_to_text(20), "ოცი")
        for value in [-1, 1001, True, 1.5, "1"]:
            with self.assertRaises(ValueError):
                number_to_text(value)
        for marks in [[False] * 4, [True] * 4]:
            q = number()
            for c, mark in zip(q["choices"], marks):
                c["isCorrect"] = mark
            with self.assertRaises(ValueError):
                validate(q, generated=True)

    def test_random_questions_without_repeated_correct_answers(self):
        sequences = set()
        for level in ["easy", "medium", "hard"]:
            for _ in range(30):
                for lesson in LESSONS.values():
                    qs = questions(level, lesson)
                    texts = [
                        next(
                            c["text"]
                            for c in q["choices"]
                            if c["id"] == q["correctChoiceId"]
                        )
                        for q in qs
                    ]
                    cycle = len({
                        c["text"]
                        for source in eligible_sources(level, lesson)
                        if "choices" in source
                        for c in source["choices"]
                    }) or (10 if level == "easy" else 20)
                    for start in range(0, len(texts), cycle):
                        self.assertEqual(
                            len(texts[start : start + cycle]),
                            len(set(texts[start : start + cycle])),
                        )
                    sequences.add(tuple(texts))
        self.assertGreater(len(sequences), 1)

    def test_speech_override_and_static_choice_selection(self):
        source = {
            "level": 1,
            "choices": [
                {"id": str(i), "text": f"word{i}", "translation": str(i)}
                for i in range(7)
            ],
        }
        source["choices"][0]["speechText"] = "spoken differently"
        with patch("web.content.LESSON", {"sources": [source]}):
            qs = questions("easy")
        first = next(q for q in qs if q["correctText"] == "word0")
        self.assertEqual(first["speechText"], "spoken differently")
        self.assertEqual(first["correctAnswerText"], "word0 (0)")

    def test_static_answers_repeat_only_after_exhaustion(self):
        source = {
            "choices": [
                {"id": str(i), "text": f"word{i}", "translation": str(i)}
                for i in range(4)
            ]
        }
        with patch("web.content.LESSON", {"sources": [source]}):
            qs = questions("hard")
        self.assertEqual(len(qs), 15)
        for start in range(0, 15, 4):
            texts = [q["speechText"] for q in qs[start : start + 4]]
            self.assertEqual(len(texts), len(set(texts)))

    def test_exhausted_generator_still_completes_lesson(self):
        fixed = number()
        with patch(
            "web.content.LESSON", {"sources": [{"generator": "fixed", "level": 1}]}
        ), patch.dict("web.content.GENERATORS", {"fixed": lambda: fixed}):
            qs = questions("easy")
        self.assertEqual(len(qs), 7)
        self.assertEqual(len({q["speechText"] for q in qs}), 1)

    def test_unused_static_answers_survive_exhausted_generator(self):
        source = {
            "level": 1,
            "choices": [
                {"id": str(i), "text": f"word{i}", "translation": str(i)}
                for i in range(7)
            ],
        }
        fixed = {
            "choices": [
                dict(c, isCorrect=i == 0) for i, c in enumerate(source["choices"])
            ]
        }
        # Always propose the generator; after retries the unused static pool
        # must still win over a repeated correct answer.
        with patch(
            "web.content.LESSON",
            {"sources": [source, {"generator": "fixed", "level": 1}]},
        ), patch.dict("web.content.GENERATORS", {"fixed": lambda: fixed}), patch(
            "web.content.random.choice", side_effect=lambda items: items[-1]
        ):
            qs = questions("easy")
        self.assertEqual(len({q["speechText"] for q in qs}), 7)

    def test_defaults_and_bad_definitions(self):
        q = {
            "choices": [
                {"id": str(i), "text": name, "translation": str(i)}
                for i, name in enumerate(["one", "two", "three", "four", "five"])
            ]
        }
        resolved = validate(q)
        self.assertEqual(resolved["choices"][0]["speechText"], "one")
        self.assertNotIn("correctChoiceId", resolved)
        for changed in [
            dict(q, choices=q["choices"][:3]),
            dict(q, choices=[dict(c, translation="") for c in q["choices"]]),
        ]:
            with self.assertRaises(ValueError):
                validate(changed)

    def test_choice_sampling_and_layout(self):
        for _ in range(20):
            for q in questions("medium"):
                self.assertEqual(len(q["choices"]), 4)
                self.assertEqual(len({c["id"] for c in q["choices"]}), 4)
                self.assertIn(q["correctChoiceId"], [c["id"] for c in q["choices"]])
                correct = next(
                    c for c in q["choices"] if c["id"] == q["correctChoiceId"]
                )
                self.assertEqual(q["speechText"], correct["speechText"])
                self.assertEqual(
                    q["correctAnswerText"],
                    f"{correct['text']} ({correct['translation']})",
                )
        q = {
            "choices": [
                {"id": str(i), "text": str(i), "translation": str(i)} for i in range(4)
            ]
        }
        self.assertEqual(validate(q)["choiceLayout"], "long")
        with self.assertRaises(ValueError):
            validate(dict(q, choiceLayout="wide"))
        q["choices"][0]["image"] = "zero.jpg"
        self.assertEqual(validate(q)["choices"][0]["image"], "zero.jpg")
        q["choices"][0]["image"] = "https://example.com/zero.jpg"
        with self.assertRaises(ValueError):
            validate(q)

    def test_cache_bounds_concurrent_misses_and_keys(self):
        cache, calls = AudioCache(limit=2), []

        def produce():
            calls.append(1)
            return b"audio"

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(
                list(pool.map(lambda _: cache.get("one", produce), range(8))),
                [b"audio"] * 8,
            )
        self.assertEqual(len(calls), 1)
        cache.get("two", produce)
        cache.get("three", produce)
        self.assertEqual(len(cache.entries), 2)
        self.assertNotIn("one", cache.entries)
        self.assertNotEqual(cache_key("a", 80, "v1"), cache_key("a", 100, "v1"))
        self.assertNotEqual(cache_key("a", 80, "v1"), cache_key("a", 80, "v2"))


if __name__ == "__main__":
    unittest.main()
