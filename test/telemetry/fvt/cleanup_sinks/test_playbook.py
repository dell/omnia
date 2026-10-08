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
Telemetry Cleanup Sinks --- Playbook Execution.

Covers the ``cleanup_sinks`` Ansible tag which selectively cleans sink
infrastructure (Kafka, VictoriaMetrics, VictoriaLogs) with dependency
checking.

Uses ``cleanup_extra_vars()`` from ``test_config.yml`` to resolve
the ``Delete_sinks_volume`` flag.

Test cases:
    TEL_FVT_CLEANUP_SINKS_E001: Cleanup sinks (--tags cleanup_sinks)
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import (
    cleanup_extra_vars,
    cleanup_selection_fields,
)


@pytest.mark.deploy
@pytest.mark.sink
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup_sinks(host):
    """TEL_FVT_CLEANUP_SINKS_E001: Run ``telemetry.yml --tags cleanup_sinks``.

    Runs selective sink cleanup.  The ``Delete_sinks_volume`` flag is
    resolved from ``test_config.yml``.  Dependency checking is performed
    by the Ansible role -- if any dependent source is still running, the
    playbook blocks cleanup and returns a non-zero exit code.
    """
    tc = TC["deploy_cleanup_sinks"]
    tl = TestLogger(tc["title"], tc["id"])

    extra_vars = cleanup_extra_vars()
    fields = cleanup_selection_fields()
    field_summary = ", ".join(f"{k}={v}" for k, v in fields)
    tl.check(f"Running telemetry playbook --tags cleanup_sinks ({field_summary})")

    result = run_playbook(tag="cleanup_sinks", extra_vars=extra_vars or None)

    if result["success"]:
        tl.passed(
            LOG_MSGS["playbook_success"].format(
                duration=f"{result['duration']:.1f}s",
            ),
            f"rc={result['rc']}",
        )
    else:
        tl.failed(
            LOG_MSGS["playbook_failed"].format(
                rc=result["rc"],
                duration=f"{result['duration']:.1f}s",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["playbook_failed"].format(
        playbook="telemetry.yml",
        tag="cleanup_sinks",
        rc=result["rc"],
    )
