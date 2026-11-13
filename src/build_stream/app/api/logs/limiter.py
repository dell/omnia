# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-AUTH-001.6
# ****

"""In-process rate and concurrency limits for the log query API (ER-BSM-003 HLD 6.2).

BSM runs a single uvicorn process, so in-memory counters are authoritative.
Counters reset when the service restarts.
"""

import math
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Callable, Deque, Dict, Iterator


class RateLimitExceededError(Exception):
    """The client exceeded its request budget for the current window."""

    def __init__(self, retry_after: int) -> None:
        """Store the number of seconds after which a retry may succeed."""
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class ConcurrencyLimitExceededError(Exception):
    """All concurrent log query slots are in use."""

    def __init__(self, retry_after: int = 1) -> None:
        """Store the suggested retry delay in seconds."""
        super().__init__("Log query capacity exhausted")
        self.retry_after = retry_after


class SlidingWindowRateLimiter:  # pylint: disable=too-few-public-methods
    """Allow at most ``limit`` requests per key within ``window_seconds``."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 1024,
    ) -> None:
        """Create the limiter; ``clock`` is injectable for tests."""
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record one request for ``key``.

        Raises:
            RateLimitExceededError: The key already used its budget in this window.
        """
        now = self._clock()
        with self._lock:
            events = self._events.get(key)
            if events is None:
                if len(self._events) >= self._max_keys:
                    self._prune(now)
                events = self._events.setdefault(key, deque())
            while events and now - events[0] >= self._window:
                events.popleft()
            if len(events) >= self._limit:
                retry_after = max(1, math.ceil(self._window - (now - events[0])))
                raise RateLimitExceededError(retry_after)
            events.append(now)

    def _prune(self, now: float) -> None:
        """Drop keys with no requests inside the current window."""
        stale = [k for k, ev in self._events.items() if not ev or now - ev[-1] >= self._window]
        for key in stale:
            del self._events[key]


class ConcurrencyLimiter:  # pylint: disable=too-few-public-methods
    """Bound the number of log queries served at the same time."""

    def __init__(self, max_concurrent: int) -> None:
        """Create the limiter with ``max_concurrent`` slots."""
        self._semaphore = threading.BoundedSemaphore(max_concurrent)

    @contextmanager
    def slot(self) -> Iterator[None]:
        """Hold one slot for the duration of the block.

        Raises:
            ConcurrencyLimitExceededError: No slot is free.
        """
        if not self._semaphore.acquire(blocking=False):  # pylint: disable=consider-using-with
            raise ConcurrencyLimitExceededError()
        try:
            yield
        finally:
            self._semaphore.release()
