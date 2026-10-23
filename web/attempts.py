"""Bounded, process-local attempt storage and transaction synchronization."""

import secrets
import threading
import time
from contextlib import contextmanager


class AttemptUnavailable(Exception):
    """An attempt expired, is missing, or belongs to another owner."""


class AttemptCapacity(Exception):
    """The process cannot hold another attempt."""


class AttemptStore:
    """Access and mutate attempts only inside transaction(), including reads.

    The lock spans quiz transitions and response projection. Release it during
    synthesis, then recheck ownership/expiry before recording audio readiness.
    """

    def __init__(self):
        self.attempts = {}
        self._lock = threading.RLock()

    @contextmanager
    def transaction(self):
        with self._lock:
            yield

    def _expire(self, now):
        for aid in list(self.attempts):
            if self.attempts[aid]["expires"] <= now:
                del self.attempts[aid]

    def owned(self, aid, owner):
        self._expire(time.monotonic())
        attempt = self.attempts.get(aid)
        if not attempt or attempt["owner"] != owner:
            raise AttemptUnavailable(
                "Урок недоступен или время истекло. Начните новый урок."
            )
        return attempt

    def create(self, owner, voice, snapshots, *, ttl, capacity):
        """Replace the owner's attempt only after snapshots are prepared."""
        now = time.monotonic()
        self._expire(now)
        for aid in list(self.attempts):
            if self.attempts[aid]["owner"] == owner:
                del self.attempts[aid]
        if len(self.attempts) >= capacity:
            raise AttemptCapacity("Слишком много активных уроков. Попробуйте позже.")
        aid = secrets.token_urlsafe(24)
        attempt = {
            "owner": owner,
            "voice": voice,
            "expires": now + ttl,
            "questions": snapshots,
            "index": 0,
            "score": 0,
            "feedback": None,
            "audioReady": set(),
        }
        self.attempts[aid] = attempt
        return aid, attempt
