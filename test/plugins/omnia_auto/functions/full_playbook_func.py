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

"""
Shared FVT scenario that runs the complete playbook of a domain (no ``--tags``).

Every domain has one ``fvt/test_playbook.py`` (directly under ``fvt/``, like the playbook
``src/<domain>/<domain>.yml`` it runs without tags); its only test calls
:func:`run_full_playbook_test` with the domain's own ``run_playbook`` wrapper, so the playbook
name, working directory and defaults stay the domain's.  It runs with
``./run_validation.sh fvt_<domain> exec`` (no tag).
"""

from typing import Any, Callable, Dict

from .formatting_func import TestLogger
from ..messages.runner_msgs import FULL_PLAYBOOK_ASSERT_MSGS, FULL_PLAYBOOK_LOG_MSGS


def run_full_playbook_test(
    run_playbook_fn: Callable[..., Dict[str, Any]],
    playbook: str,
    title: str,
    tc_id: str,
) -> None:
    """Run the complete ``playbook`` without ``--tags`` and assert that it succeeded.

    Args:
        run_playbook_fn: The domain's ``run_playbook`` wrapper (called without arguments).
        playbook: Playbook file name, for the messages.
        title: Test case title.
        tc_id: Test case ID.
    """
    log = TestLogger(title, tc_id)
    log.check(FULL_PLAYBOOK_LOG_MSGS["starting"].format(playbook=playbook))
    result = run_playbook_fn()
    duration = f"{result['duration']:.1f}s"
    if result["success"]:
        log.passed(
            FULL_PLAYBOOK_LOG_MSGS["passed"].format(playbook=playbook, duration=duration),
            f"rc={result['rc']}",
        )
    else:
        log.failed(
            FULL_PLAYBOOK_LOG_MSGS["failed"].format(
                playbook=playbook, rc=result["rc"], duration=duration,
            ),
            result.get("error", ""),
        )
    assert result["success"], FULL_PLAYBOOK_ASSERT_MSGS["failed"].format(
        playbook=playbook, rc=result["rc"], duration=duration,
    )
