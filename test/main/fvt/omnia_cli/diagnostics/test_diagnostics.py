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
Omnia CLI — Diagnostics Commands Verification.

MAIN_FVT_OMNIA_CLI_V001: Verify omnia-cli status runs successfully
MAIN_FVT_OMNIA_CLI_V002: Verify omnia-cli check runs successfully
MAIN_FVT_OMNIA_CLI_V003: Verify omnia-cli status --project flag works
MAIN_FVT_OMNIA_CLI_V004: Verify omnia-cli repo-manager runs
MAIN_FVT_OMNIA_CLI_V005: Verify omnia-cli image-build runs
MAIN_FVT_OMNIA_CLI_V006: Verify omnia-cli discovery runs
MAIN_FVT_OMNIA_CLI_V007: Verify omnia-cli help repo-manager shows domain help
MAIN_FVT_OMNIA_CLI_V008: Verify omnia-cli help discovery shows domain help
MAIN_FVT_OMNIA_CLI_V009: Verify omnia-cli orchestrator runs
MAIN_FVT_OMNIA_CLI_V010: Verify omnia-cli telemetry runs
MAIN_FVT_OMNIA_CLI_V011: Verify omnia-cli build-stream runs
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cli_cmd,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_cli_status_runs(host):
    """MAIN_FVT_OMNIA_CLI_V001: Verify omnia-cli status runs successfully."""
    tc = TC["cli_status_runs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(host, "omnia_cli_status")
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["cli_status_ok"])
    else:
        tl.failed(
            f"omnia-cli status failed (rc={result['rc']})"
        )

    assert result["success"], ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_cli_check_runs(host):
    """MAIN_FVT_OMNIA_CLI_V002: Verify omnia-cli check runs successfully."""
    tc = TC["cli_check_runs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(host, "omnia_cli_check")
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["cli_check_ok"])
    else:
        tl.failed(
            f"omnia-cli check failed (rc={result['rc']})"
        )

    assert result["success"], ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_cli_status_project_flag(host):
    """MAIN_FVT_OMNIA_CLI_V003: Verify omnia-cli status --project flag works."""
    tc = TC["cli_status_project_flag"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_status_project",
        project="project_default",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["cli_project_ok"].format(
            project="project_default"
        ))
    else:
        tl.failed(
            "omnia-cli status --project failed"
            f" (rc={result['rc']})"
        )

    assert result["success"], ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_cli_repo_manager(host):
    """MAIN_FVT_OMNIA_CLI_V004: Verify omnia-cli repo-manager runs."""
    tc = TC["cli_repo_manager"]
    tl = TestLogger(tc["title"], tc["id"])
    # repo-manager may return non-zero if not yet run —
    # we only check it does not crash (exits cleanly)
    result = run_omnia_cli_cmd(
        host, "omnia_cli_repo_manager"
    )
    tl.bind_result(result)

    # Accept rc 0 or 1 (1 = domain not yet run, which is valid)
    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_domain_ok"].format(
            domain="repo-manager", rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli repo-manager crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_cli_image_build(host):
    """MAIN_FVT_OMNIA_CLI_V005: Verify omnia-cli image-build runs."""
    tc = TC["cli_image_build"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_image_build"
    )
    tl.bind_result(result)

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_domain_ok"].format(
            domain="image-build", rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli image-build crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_cli_discovery_status(host):
    """MAIN_FVT_OMNIA_CLI_V006: Verify omnia-cli discovery runs."""
    tc = TC["cli_discovery_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_domain", domain="discovery"
    )
    tl.bind_result(result)

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_domain_ok"].format(
            domain="discovery", rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli discovery crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_cli_help_repo_manager(host):
    """MAIN_FVT_OMNIA_CLI_V007: Verify omnia-cli help repo-manager shows domain help."""
    tc = TC["cli_help_repo_manager"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_help_domain",
        domain="repo-manager",
    )
    tl.bind_result(result)
    output = result["output"]

    has_usage = "USAGE:" in output or "usage:" in output.lower()

    if has_usage:
        tl.passed(LOG["cli_domain_help_ok"].format(
            domain="repo-manager"
        ))
    else:
        tl.failed(
            "omnia-cli help repo-manager missing USAGE section"
        )

    assert has_usage, ASSERT["cli_help_missing"].format(
        sections="USAGE",
    )


@pytest.mark.sanity
@pytest.mark.order(8)
def test_cli_help_discovery(host):
    """MAIN_FVT_OMNIA_CLI_V008: Verify omnia-cli help discovery shows domain help."""
    tc = TC["cli_help_discovery"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_help_domain",
        domain="discovery",
    )
    tl.bind_result(result)
    output = result["output"]

    has_usage = "USAGE:" in output or "usage:" in output.lower()

    if has_usage:
        tl.passed(LOG["cli_domain_help_ok"].format(
            domain="discovery"
        ))
    else:
        tl.failed(
            "omnia-cli help discovery missing USAGE section"
        )

    assert has_usage, ASSERT["cli_help_missing"].format(
        sections="USAGE",
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_cli_orchestrator(host):
    """MAIN_FVT_OMNIA_CLI_V009: Verify omnia-cli orchestrator runs."""
    tc = TC["cli_orchestrator"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_orchestrator"
    )
    tl.bind_result(result)

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_orchestrator_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli orchestrator crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(10)
def test_cli_telemetry(host):
    """MAIN_FVT_OMNIA_CLI_V010: Verify omnia-cli telemetry runs."""
    tc = TC["cli_telemetry"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_telemetry"
    )
    tl.bind_result(result)

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_telemetry_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli telemetry crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(11)
def test_cli_build_stream(host):
    """MAIN_FVT_OMNIA_CLI_V011: Verify omnia-cli build-stream runs."""
    tc = TC["cli_build_stream"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cli_cmd(
        host, "omnia_cli_build_stream"
    )
    tl.bind_result(result)

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_build_stream_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli build-stream crashed"
            f" (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )
