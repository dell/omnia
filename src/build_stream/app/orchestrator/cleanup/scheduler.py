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

"""Background scheduler for automatic image cleanup (ER-BSM-002 Story 4).

Runs inside the BuildStream API process next to the result poller. The
``retention`` settings are re-read from ``build_stream_config.yml`` every
``reload_interval_seconds`` (default 60), so enabling/disabling cleanup or
changing the retention age or the evaluation interval takes effect without
restarting the container. A cycle runs once ``evaluation_interval_hours``
have elapsed since the previous cycle.
"""

import asyncio
import time
from typing import Callable, Optional

from api.logging_utils import log_secure_info
from orchestrator.cleanup.retention_config import (
    RetentionConfig,
    load_retention_config,
)

# Delay before the first cycle so a restarting container settles first.
DEFAULT_STARTUP_DELAY_SECONDS = 300
DEFAULT_RELOAD_INTERVAL_SECONDS = 60

CleanupRunner = Callable[[RetentionConfig], int]
ConfigLoader = Callable[[Optional[RetentionConfig]], RetentionConfig]


def _default_cleanup_runner(config: RetentionConfig) -> int:
    """Run one cleanup pass through the ``cleanup_cron`` entry-point."""
    import cleanup_cron  # pylint: disable=import-outside-toplevel
    return cleanup_cron.main(retention_config=config)


def _default_config_loader(fallback: Optional[RetentionConfig]) -> RetentionConfig:
    return load_retention_config(fallback=fallback)


class AutoCleanupScheduler:  # pylint: disable=too-many-instance-attributes
    """Periodically run automatic cleanup with hot-reloaded settings."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        cleanup_runner: Optional[CleanupRunner] = None,
        config_loader: Optional[ConfigLoader] = None,
        startup_delay_seconds: float = DEFAULT_STARTUP_DELAY_SECONDS,
        reload_interval_seconds: float = DEFAULT_RELOAD_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cleanup_runner = cleanup_runner or _default_cleanup_runner
        self._config_loader = config_loader or _default_config_loader
        self._startup_delay_seconds = startup_delay_seconds
        self._reload_interval_seconds = reload_interval_seconds
        self._clock = clock
        self._config: Optional[RetentionConfig] = None
        self._last_run: Optional[float] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def config(self) -> Optional[RetentionConfig]:
        """Configuration applied by the most recent reload."""
        return self._config

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._task is not None:
            log_secure_info("warning", "Auto-cleanup scheduler is already running")
            return
        self.reload_config()
        # Treat startup as if a cycle just ran minus the startup delay, so the
        # first cycle happens after the delay and then every interval.
        self._last_run = (
            self._clock() - self._interval_seconds() + self._startup_delay_seconds
        )
        self._task = asyncio.create_task(self._run_loop())
        log_secure_info(
            "info",
            f"Auto-cleanup scheduler started: {self._config.as_dict()}, "
            f"first cycle in {int(self._startup_delay_seconds)}s",
        )

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        log_secure_info("info", "Auto-cleanup scheduler stopped")

    def reload_config(self) -> RetentionConfig:
        """Re-read the retention settings and log what changed.

        Returns:
            The configuration now in effect.
        """
        previous = self._config
        current = self._config_loader(previous)
        if previous is not None and current != previous:
            old_values, new_values = previous.as_dict(), current.as_dict()
            for key, value in new_values.items():
                if old_values[key] != value:
                    log_secure_info(
                        "info",
                        f"Retention config reloaded: {key} "
                        f"{old_values[key]} -> {value}",
                    )
        self._config = current
        return current

    def _interval_seconds(self) -> float:
        return self._config.evaluation_interval_hours * 3600

    def is_cycle_due(self) -> bool:
        """Return whether a cleanup cycle should run now."""
        if not self._config.auto_cleanup_enabled:
            return False
        return self._clock() - self._last_run >= self._interval_seconds()

    async def run_cycle(self) -> Optional[int]:
        """Run one cleanup cycle off the event loop.

        Returns:
            The cleanup exit code, or ``None`` if the cycle raised.
        """
        self._last_run = self._clock()
        config = self._config
        log_secure_info(
            "info", f"Auto-cleanup cycle started: {config.as_dict()}"
        )
        try:
            exit_code = await asyncio.to_thread(self._cleanup_runner, config)
        except Exception as exc:  # pylint: disable=broad-except
            log_secure_info(
                "error", f"Auto-cleanup cycle failed: {exc}", exc_info=True
            )
            return None
        log_secure_info(
            "info" if exit_code == 0 else "warning",
            f"Auto-cleanup cycle finished: exit_code={exit_code}, "
            f"next cycle in {config.evaluation_interval_hours}h",
        )
        return exit_code

    async def _run_loop(self) -> None:
        """Reload settings periodically and run cleanup when due."""
        while True:
            await asyncio.sleep(self._reload_interval_seconds)
            try:
                self.reload_config()
                if self.is_cycle_due():
                    await self.run_cycle()
            except Exception as exc:  # pylint: disable=broad-except
                log_secure_info(
                    "error", f"Auto-cleanup scheduler error: {exc}", exc_info=True
                )
