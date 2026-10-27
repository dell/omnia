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

# pylint: disable=too-few-public-methods

"""Unit tests for the automatic cleanup scheduler and its hot reload."""

import asyncio

import pytest
import yaml

from orchestrator.cleanup.retention_config import (
    RetentionConfig,
    load_retention_config,
)
from orchestrator.cleanup.scheduler import AutoCleanupScheduler

pytestmark = pytest.mark.unit

HOUR = 3600


class FakeClock:
    """Manually advanced monotonic clock."""

    def __init__(self, now: float = 10_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


class SequenceLoader:
    """Config loader returning queued configs, then repeating the last."""

    def __init__(self, *configs):
        self.configs = list(configs)
        self.fallbacks = []

    def __call__(self, fallback):
        self.fallbacks.append(fallback)
        if len(self.configs) > 1:
            return self.configs.pop(0)
        return self.configs[0]


def _scheduler(loader, clock, runner=None, startup_delay=300):
    calls = []

    def _runner(config):
        calls.append(config)
        return 0

    scheduler = AutoCleanupScheduler(
        cleanup_runner=runner or _runner,
        config_loader=loader,
        startup_delay_seconds=startup_delay,
        reload_interval_seconds=60,
        clock=clock,
    )
    return scheduler, calls


def _start(scheduler):
    """Run start() and cancel the background loop immediately."""
    async def _go():
        await scheduler.start()
        await scheduler.stop()
    asyncio.run(_go())


def test_first_cycle_runs_after_startup_delay():
    """No cycle at startup; the first one is due after the startup delay."""
    clock = FakeClock()
    scheduler, _ = _scheduler(SequenceLoader(RetentionConfig()), clock)
    _start(scheduler)

    assert not scheduler.is_cycle_due()
    clock.now += 299
    assert not scheduler.is_cycle_due()
    clock.now += 1
    assert scheduler.is_cycle_due()


def test_cycle_passes_reloaded_config_and_resets_interval():
    """The runner receives the current config; the next cycle waits a full interval."""
    clock = FakeClock()
    config = RetentionConfig(retention_age_days=45, evaluation_interval_hours=2)
    scheduler, calls = _scheduler(SequenceLoader(config), clock, startup_delay=0)
    _start(scheduler)

    assert scheduler.is_cycle_due()
    assert asyncio.run(scheduler.run_cycle()) == 0
    assert calls == [config]
    assert not scheduler.is_cycle_due()
    clock.now += 2 * HOUR
    assert scheduler.is_cycle_due()


def test_disabled_cleanup_never_runs():
    """auto_cleanup_enabled=false suppresses cycles even when overdue."""
    clock = FakeClock()
    scheduler, _ = _scheduler(
        SequenceLoader(RetentionConfig(auto_cleanup_enabled=False)),
        clock,
        startup_delay=0,
    )
    _start(scheduler)
    clock.now += 100 * HOUR

    assert not scheduler.is_cycle_due()


def test_reload_applies_new_interval_without_restart():
    """A shortened evaluation interval takes effect on the next reload."""
    clock = FakeClock()
    loader = SequenceLoader(
        RetentionConfig(evaluation_interval_hours=24),
        RetentionConfig(evaluation_interval_hours=1),
    )
    scheduler, _ = _scheduler(loader, clock, startup_delay=0)
    _start(scheduler)
    asyncio.run(scheduler.run_cycle())
    clock.now += HOUR

    assert not scheduler.is_cycle_due()  # still on the 24 h interval
    assert scheduler.reload_config().evaluation_interval_hours == 1
    assert scheduler.is_cycle_due()


def test_reload_passes_last_good_config_as_fallback():
    """Each reload hands the config in effect to the loader as fallback."""
    first = RetentionConfig(retention_age_days=200)
    loader = SequenceLoader(first, RetentionConfig())
    scheduler, _ = _scheduler(loader, FakeClock())
    _start(scheduler)
    scheduler.reload_config()

    assert loader.fallbacks == [None, first]


def test_runner_exception_does_not_stop_scheduler():
    """A failing cycle is logged and the scheduler keeps running."""
    def _boom(_config):
        raise RuntimeError("db down")

    clock = FakeClock()
    scheduler, _ = _scheduler(
        SequenceLoader(RetentionConfig()), clock, runner=_boom, startup_delay=0
    )
    _start(scheduler)

    assert asyncio.run(scheduler.run_cycle()) is None
    assert not scheduler.is_cycle_due()


def test_loop_runs_due_cycle_after_reload():
    """The background loop reloads the config and runs a due cycle."""
    clock = FakeClock()
    config = RetentionConfig(evaluation_interval_hours=1)

    async def _go():
        calls = []

        def _runner(cfg):
            calls.append(cfg)
            return 0

        scheduler = AutoCleanupScheduler(
            cleanup_runner=_runner,
            config_loader=SequenceLoader(config),
            startup_delay_seconds=0,
            reload_interval_seconds=0.01,
            clock=clock,
        )
        await scheduler.start()
        for _ in range(100):
            if calls:
                break
            await asyncio.sleep(0.01)
        await scheduler.stop()
        return calls

    assert asyncio.run(_go()) == [config]


def test_hot_reload_from_file(tmp_path):
    """Editing build_stream_config.yml changes the next cycle's settings."""
    path = tmp_path / "build_stream_config.yml"
    path.write_text(yaml.safe_dump({"retention": {"retention_age_days": 90}}))
    clock = FakeClock()
    scheduler, calls = _scheduler(
        lambda fallback: load_retention_config(path, fallback=fallback),
        clock,
        startup_delay=0,
    )
    _start(scheduler)
    path.write_text(yaml.safe_dump({"retention": {"retention_age_days": 30}}))
    scheduler.reload_config()
    asyncio.run(scheduler.run_cycle())

    assert calls[0].retention_age_days == 30

    path.write_text(yaml.safe_dump({"retention": {"retention_age_days": 0}}))
    assert scheduler.reload_config().retention_age_days == 30
