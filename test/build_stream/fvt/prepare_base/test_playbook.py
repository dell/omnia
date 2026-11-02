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
Prepare Base — Deployment.

Prepares the BuildStream prerequisites with ``./omnia.sh --prepare-base``
from ``src/main``, which validates, collects credentials for and prepares
these domains in order (fail-fast)::

    repo_manager -> image_build_manager -> orchestrator

A read-only precheck runs first. When an entry test fails (the precheck or
the deployment), every later prepare_base test is skipped with the reason
(test/build_stream/conftest.py). The readiness suite verifies the result.
"""

import pytest

from library.functions import (
    TestLogger,
    check_prepare_base_prerequisites,
    failure_summary,
    run_omnia_sh,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import OMNIA_SH_PREPARE_BASE_ARGS, PREPARE_BASE_DOMAINS
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(10000)
def test_precheck_prepare_base(host):
    """Check omnia.env, the venv, omnia.sh and base domain credentials (read-only)."""
    tc = TC["precheck_prepare_base"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_prepare_base_prerequisites(host)

    if result["success"]:
        tl.passed_fields(LOG["prepare_base_precheck_ok"], result["fields"])
    else:
        tl.failed_fields(
            LOG["prepare_base_precheck_failed"].format(count=len(result["failures"])),
            result["fields"],
        )

    assert result["success"], ASSERT["prepare_base_precheck_failed"].format(
        failures=failure_summary(result),
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(10001)
def test_deploy_prepare_base(host):
    """Deploy ./omnia.sh --prepare-base and require a zero exit code."""
    del host
    tc = TC["deploy_prepare_base"]
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
            [*fields, ("Error", result.get("error") or "See omnia.sh output above")],
        )

    assert result["success"], ASSERT["prepare_base_failed"].format(
        rc=result["rc"], duration=result["duration"], error=result.get("error"),
    )
