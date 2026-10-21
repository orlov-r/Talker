import http.client
import importlib.util
import json
import subprocess
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "edge_speech_server", Path(__file__).with_name("server.py")
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self.httpd = HTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.paths = []
        self.log_patch = patch.object(server.Handler, "log_message")
        self.log_patch.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.log_patch.stop()
        for path in self.paths:
            self.assertFalse(path.exists(), "Temporary synthesis files must be removed")

    def request(self, method="POST", path="/synthesize", body=None, headers=None):
        connection = http.client.HTTPConnection(*self.httpd.server_address, timeout=3)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def post(self, data):
        return self.request(body=json.dumps(data).encode("utf-8"))

    def synthesize(self, args, **kwargs):
        source = Path(args[args.index("--file") + 1])
        output = Path(args[args.index("--write-media") + 1])
        self.paths.append(source.parent)
        self.assertEqual(source.read_text(encoding="utf-8"), "გამარჯობა!")
        self.assertEqual(kwargs["timeout"], 60)
        self.assertTrue(kwargs["check"])
        # Simulated payload: checks HTTP transport, not MP3 decoding or real speech.
        output.write_bytes(b"ID3simulated-audio")

    def test_page_health_and_routes_do_not_synthesize(self):
        with patch.object(server.subprocess, "run") as run:
            status, content_type, body = self.request("GET", "/")
            self.assertEqual((status, content_type), (200, "text/html; charset=utf-8"))
            self.assertIn(b"Edge TTS", body)
            with patch.object(server, "VOICE", "ka-GE-GiorgiNeural"):
                status, _, body = self.request("GET", "/health")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["voice"], "ka-GE-GiorgiNeural")
            self.assertEqual(self.request("GET", "/missing")[0], 404)
            self.assertEqual(self.request(path="/missing", body=b"{}")[0], 404)
            run.assert_not_called()

    def test_invalid_requests_never_synthesize(self):
        invalid = [None, [], {}, {"text": " "}, {"text": 4}, {"text": "a" * 3001}]
        invalid += [
            {"text": "a", "rate": rate}
            for rate in [True, 49, 201, 100.0, "100", None]
        ]
        with patch.object(server.subprocess, "run") as run:
            for data in invalid:
                with self.subTest(data=str(data)[:80]):
                    self.assertEqual(self.post(data)[0], 400)
            for body in [b"{", b"\xff"]:
                self.assertEqual(self.request(body=body)[0], 400)
            for length in ["0", "-1", "32769"]:
                response = self.request(
                    body=b"", headers={"Content-Length": length}
                )
                self.assertEqual(response[0], 413)
            response = self.request(body=b"", headers={"Content-Length": "bad"})
            self.assertEqual(response[0], 400)
            run.assert_not_called()

    def test_mp3_response_default_voice_and_rate_mapping(self):
        for rate in [None, 50, 80, 100, 120, 200]:
            with self.subTest(rate=rate):
                data = {"text": "გამარჯობა!"}
                if rate is not None:
                    data["rate"] = rate
                with patch.object(
                    server.subprocess, "run", side_effect=self.synthesize
                ) as run:
                    status, content_type, body = self.post(data)
                self.assertEqual((status, content_type), (200, "audio/mpeg"))
                self.assertEqual(body, b"ID3simulated-audio")
                args = run.call_args.args[0]
                self.assertIn(f"--rate={(rate or 100) - 100:+d}%", args)
                self.assertEqual(args[args.index("--voice") + 1], server.VOICE)

    def test_failure_timeout_and_empty_output_cleanup(self):
        for error, expected in [
            (subprocess.CalledProcessError(1, "edge-tts"), 500),
            (subprocess.TimeoutExpired("edge-tts", 60), 504),
            (FileNotFoundError(), 500),
        ]:
            def fail(args, **kwargs):
                self.paths.append(Path(args[args.index("--file") + 1]).parent)
                raise error

            with self.subTest(error=type(error).__name__):
                with patch.object(server.subprocess, "run", side_effect=fail):
                    status, content_type, body = self.post({"text": "a"})
                self.assertEqual((status, content_type), (expected, "application/json"))
                self.assertIn("error", json.loads(body))

        for size in [0, server.MAX_AUDIO_BYTES + 1]:
            def bad_audio(args, **kwargs):
                output = Path(args[args.index("--write-media") + 1])
                self.paths.append(output.parent)
                output.write_bytes(b"x" * size)

            with self.subTest(size=size):
                with patch.object(server.subprocess, "run", side_effect=bad_audio):
                    self.assertEqual(self.post({"text": "a"})[0], 500)


if __name__ == "__main__":
    unittest.main()
