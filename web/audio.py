"""Bounded process-local WAV cache; serialize misses and publish complete bytes."""
from collections import OrderedDict
import hashlib
import io
import json
import threading
import urllib.request
import wave


def cache_key(text, rate, version):
    return hashlib.sha256(json.dumps([text, "Natia", rate, version], ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def synthesize(text, rate, url):
    request = urllib.request.Request(url.rstrip("/") + "/synthesize",
                                     json.dumps({"text": text, "rate": rate}).encode(),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=65) as response:
        if response.headers.get_content_type() != "audio/wav":
            raise ValueError("Speech service returned non-WAV data")
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Audio too large")
    with wave.open(io.BytesIO(data)) as wav:
        if wav.getnframes() == 0:
            raise ValueError("Empty WAV")
    return data


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
