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
Prepare Base — Deploy (exec entry point).

Runs ./omnia.sh --prepare-base (no timeout), which validates, collects
credentials for and prepares these domains in dependency order (fail-fast):
  repo_manager
  image_build_manager
  orchestrator
The result is verified by the readiness suite (verify phase).
"""

import pytest

from library.functions import TestLogger, run_omnia_sh
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import OMNIA_SH_PREPARE_BASE_ARGS, PREPARE_BASE_DOMAINS


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.prepare_base
@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(1002)
def test_run_prepare_base(host):
    """Run ./omnia.sh --prepare-base and require a zero exit code."""
    del host
    tc = TC["run_prepare_base"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_sh(OMNIA_SH_PREPARE_BASE_ARGS)

    fields = [
        ("Command", result["command"]),
        ("Domains", " -> ".join(PREPARE_BASE_DOMAINS)),
        ("Return code", result["rc"]),
        ("Duration seconds", f"{result['duration']:.1f}"),
    ]
    if result["success"]:
        tl.passed_fields(LOG["prepare_base_ok"].format(duration=result["duration"]), fields)
    else:
        tl.failed_fields(
            LOG["prepare_base_failed"].format(rc=result["rc"], duration=result["duration"]),
            [*fields, ("Error", result.get("error") or "See output above")],
        )

    assert result["success"], ASSERT["prepare_base_failed"].format(
        rc=result["rc"], duration=result["duration"], error=result.get("error"),
    )
