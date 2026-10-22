"""Bounded process-local audio cache; serialize misses and publish complete bytes."""

import hashlib
import io
import json
import threading
import urllib.request
import wave
from collections import OrderedDict


def cache_key(text, rate, version, voice="rhvoice"):
    return hashlib.sha256(
        json.dumps(
            [text, voice, rate, version], ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def synthesize(text, rate, url, content_type="audio/wav"):
    request = urllib.request.Request(
        url.rstrip("/") + "/synthesize",
        json.dumps({"text": text, "rate": rate}).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=65) as response:
        if response.headers.get_content_type() != content_type:
            raise ValueError("Speech service returned an unexpected content type")
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Audio too large")
    if content_type == "audio/mpeg":
        # Recognize an ID3 tag or an MPEG frame header, without decoding MP3.
        if len(data) < 4 or not (
            data.startswith(b"ID3")
            or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)
        ):
            raise ValueError("Invalid MP3 header")
    else:
        with wave.open(io.BytesIO(data)) as wav:
            if wav.getnframes() == 0:
                raise ValueError("Empty WAV")
    return data


def synthesize_edge(text, rate, url):
    return synthesize(text, rate, url, "audio/mpeg")


class AudioCache:
    def __init__(self, limit=128):
        self.entries = OrderedDict()
        self.lock = threading.Lock()
        self.limit = limit

    def get(self, key, produce):
        with self.lock:
            if key not in self.entries:
                self.entries[key] = produce()
                while len(self.entries) > self.limit:
                    self.entries.popitem(last=False)
            self.entries.move_to_end(key)
            return self.entries[key]
