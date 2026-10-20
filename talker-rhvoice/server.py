import json
import subprocess
import tempfile
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error(self, status, message):
        self.reply(status, json.dumps({"error": message}).encode())

    def do_GET(self):
        if self.path == "/":
            self.reply(200, Path(__file__).with_name("index.html").read_bytes(),
                       "text/html; charset=utf-8")
        elif self.path == "/health":
            self.reply(200, b'{"status":"ok","voice":"Natia"}')
        else:
            self.error(404, "Not found")

    def do_POST(self):
        if self.path != "/synthesize":
            self.error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                self.error(413, "Request must contain 1–32768 bytes")
                return

            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Expected a JSON object")

            text = request.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("text must be a nonempty string")
            if len(text) > 3000:
                raise ValueError("text must be at most 3000 characters")

            rate = request.get("rate", 100)
            if type(rate) is not int or not 50 <= rate <= 200:
                raise ValueError("rate must be an integer from 50 to 200")
        except (ValueError, UnicodeError) as exc:
            self.error(400, str(exc))
            return

        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "speech.wav"
                subprocess.run(
                    ["RHVoice-test", "-p", "Natia",
                     "-r", str(rate), "-o", str(output)],
                    input=text.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=60,
                )
                with wave.open(str(output)) as audio:
                    if audio.getnframes() == 0:
                        raise ValueError("Empty audio")
                body = output.read_bytes()
        except subprocess.TimeoutExpired:
            self.error(504, "Synthesis timed out")
            return
        except (subprocess.CalledProcessError, OSError,
                ValueError, wave.Error):
            self.error(500, "Synthesis failed")
            return

        self.reply(200, body, "audio/wav")


# Serialize synthesis requests to keep memory use predictable.
if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
