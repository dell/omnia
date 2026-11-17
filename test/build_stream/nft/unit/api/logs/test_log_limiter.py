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

"""TC-UT-007 / TC-UT-008: log query rate and concurrency limiters (ER-BSM-003 HLD 6.2)."""

import threading
import time
from contextlib import ExitStack

import pytest

from api.logs.limiter import (
    ConcurrencyLimiter,
    ConcurrencyLimitExceededError,
    RateLimitExceededError,
    SlidingWindowRateLimiter,
)

pytestmark = pytest.mark.unit


class _Clock:  # pylint: disable=too-few-public-methods
    """Manually advanced monotonic clock."""

    def __init__(self) -> None:
        """Start at t=1000."""
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current time."""
        return self.now


class TestSlidingWindowRateLimiter:
    """TC-UT-007."""

    def test_requests_within_limit_pass(self):
        """GIVEN 59 requests in the window WHEN request 60 arrives THEN it is allowed."""
        limiter = SlidingWindowRateLimiter(60, clock=_Clock())
        for _ in range(60):
            limiter.check("client-A")

    def test_request_over_limit_rejected_with_retry_after(self):
        """GIVEN 60 requests in the window WHEN request 61 arrives THEN it is rejected."""
        clock = _Clock()
        limiter = SlidingWindowRateLimiter(60, clock=clock)
        for _ in range(60):
            limiter.check("client-A")
        clock.now += 15
        with pytest.raises(RateLimitExceededError) as exc:
            limiter.check("client-A")
        assert exc.value.retry_after == 45

    def test_window_slides(self):
        """Requests older than the window stop counting."""
        clock = _Clock()
        limiter = SlidingWindowRateLimiter(2, clock=clock)
        limiter.check("c")
        limiter.check("c")
        clock.now += 60
        limiter.check("c")

    def test_limits_are_per_client(self):
        """One client's budget does not affect another's."""
        limiter = SlidingWindowRateLimiter(1, clock=_Clock())
        limiter.check("client-A")
        limiter.check("client-B")
        with pytest.raises(RateLimitExceededError):
            limiter.check("client-A")

    def test_stale_keys_pruned_when_table_full(self):
        """Idle keys are evicted so the key table stays bounded."""
        clock = _Clock()
        limiter = SlidingWindowRateLimiter(5, clock=clock, max_keys=2)
        limiter.check("a")
        limiter.check("b")
        clock.now += 120
        limiter.check("c")
        assert set(limiter._events) == {"c"}  # pylint: disable=protected-access


class TestConcurrencyLimiter:
    """TC-UT-008."""

    def test_requests_within_limit_pass(self):
        """GIVEN 4 in-flight requests WHEN request 5 arrives THEN it is allowed."""
        limiter = ConcurrencyLimiter(5)
        with ExitStack() as stack:
            for _ in range(5):
                stack.enter_context(limiter.slot())

    def test_request_over_limit_rejected(self):
        """GIVEN 5 in-flight requests WHEN request 6 arrives THEN it is rejected."""
        limiter = ConcurrencyLimiter(5)
        with ExitStack() as stack:
            for _ in range(5):
                stack.enter_context(limiter.slot())
            with pytest.raises(ConcurrencyLimitExceededError):
                with limiter.slot():
                    pass

    def test_slot_released_after_exception(self):
        """A failing request releases its slot."""
        limiter = ConcurrencyLimiter(1)
        with pytest.raises(RuntimeError):
            with limiter.slot():
                raise RuntimeError("boom")
        with limiter.slot():
            pass

    def test_thread_safety(self):
        """Concurrent threads never exceed the slot count."""
        limiter = ConcurrencyLimiter(3)
        barrier = threading.Barrier(6)
        admitted = []
        rejected = []
        release = threading.Event()

        def worker():
            barrier.wait()
            try:
                with limiter.slot():
                    admitted.append(1)
                    release.wait(2)
            except ConcurrencyLimitExceededError:
                rejected.append(1)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + 5
        while len(admitted) + len(rejected) < 6 and time.monotonic() < deadline:
            time.sleep(0.01)
        release.set()
        for thread in threads:
            thread.join()
        assert len(admitted) == 3
        assert len(rejected) == 3
