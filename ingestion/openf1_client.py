from __future__ import annotations

import logging
import time
from collections import deque

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ingestion.config import (
    OPENF1_BASE_URL,
    OPENF1_RATE_LIMIT_PER_MIN,
)

logger = logging.getLogger(__name__)


class _SlidingWindowRateLimiter:
    """Guarantees no more than `max_calls` requests per `period` seconds.

    OpenF1 enforces a hard 30 requests/minute limit. Rather than pacing
    with a fixed sleep and reacting to 429s (which triggered pathological
    exponential backoff), we proactively cap ourselves just under the
    limit: before each call we check how many requests happened in the
    last 60s and, if we're at the ceiling, sleep exactly until the oldest
    one ages out of the window. This keeps runs predictable (~30 min for a
    full season) and means we essentially never get a 429."""

    def __init__(self, max_calls: int, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls: deque[float] = deque()

    def acquire(self) -> None:
        now = time.monotonic()
        # Drop timestamps outside the rolling window.
        while self._calls and now - self._calls[0] >= self.period:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            sleep_for = self.period - (now - self._calls[0]) + 0.05
            if sleep_for > 0:
                logger.debug("Rate limiter: sleeping %.1fs", sleep_for)
                time.sleep(sleep_for)
            # Re-evaluate the window after sleeping.
            now = time.monotonic()
            while self._calls and now - self._calls[0] >= self.period:
                self._calls.popleft()
        self._calls.append(time.monotonic())


class OpenF1Client:
    """Thin wrapper around the public OpenF1 API (https://openf1.org).

    No API key is required for historical (non real-time) data.
    """

    def __init__(self, base_url: str = OPENF1_BASE_URL, rate_limit_per_min: int = OPENF1_RATE_LIMIT_PER_MIN):
        self.base_url = base_url
        self._session = requests.Session()
        self._limiter = _SlidingWindowRateLimiter(max_calls=rate_limit_per_min)

    # The rate limiter keeps us under the quota, so retries here only guard
    # against genuine transient failures (network blips, 5xx). A 429 that
    # slips through still retries, but with a short, bounded backoff.
    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=15),
    )
    def _get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        self._limiter.acquire()
        response = self._session.get(f"{self.base_url}/{endpoint}", params=params or {}, timeout=30)
        if response.status_code == 404:
            # OpenF1 returns 404 {"detail": "No results found."} for a
            # legitimately empty result set — not an error, don't retry it.
            return []
        response.raise_for_status()
        return response.json()

    def meetings(self, year: int) -> list[dict]:
        return self._get("meetings", {"year": year})

    def sessions(self, meeting_key: int) -> list[dict]:
        return self._get("sessions", {"meeting_key": meeting_key})

    def drivers(self, session_key: int) -> list[dict]:
        return self._get("drivers", {"session_key": session_key})

    def laps(self, session_key: int) -> list[dict]:
        return self._get("laps", {"session_key": session_key})

    def stints(self, session_key: int) -> list[dict]:
        return self._get("stints", {"session_key": session_key})

    def pit(self, session_key: int) -> list[dict]:
        return self._get("pit", {"session_key": session_key})

    def race_control(self, session_key: int) -> list[dict]:
        return self._get("race_control", {"session_key": session_key})

    def weather(self, session_key: int) -> list[dict]:
        return self._get("weather", {"session_key": session_key})

    def session_result(self, session_key: int) -> list[dict]:
        return self._get("session_result", {"session_key": session_key})

    def starting_grid(self, session_key: int) -> list[dict]:
        """Grid of the race that follows a qualifying session, penalties applied.

        OpenF1 keys it by the QUALIFYING session (Qualifying -> Grand Prix grid,
        Sprint Qualifying -> Sprint grid)."""
        return self._get("starting_grid", {"session_key": session_key})
