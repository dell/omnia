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

"""Unit coverage for cadence lifecycle integration in the watcher service."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


WATCHER_PATH = (
    Path(__file__).parents[5]
    / "src"
    / "build_stream"
    / "app"
    / "playbook-watcher"
    / "playbook_watcher_service.py"
)
SPEC = importlib.util.spec_from_file_location(
    "cadence_test_playbook_watcher_service",
    WATCHER_PATH,
)
WATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCHER)


@pytest.mark.unit
def test_disabled_cadence_still_starts_reloadable_timer():
    """TC-UT-010-008: Disabled cadence does not terminate its timer thread."""
    config = {
        "enabled": False,
        "interval_days": 7,
    }

    with patch(
        "cadence_manager.load_cadence_config",
        return_value=config,
    ), patch("cadence_manager.CadenceTimerThread") as timer_class:
        timer = WATCHER._start_cadence_timer()  # pylint: disable=protected-access

    assert timer is timer_class.return_value
    timer.start.assert_called_once_with()
