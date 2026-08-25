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

TC_OC_003: Verify omnia-cli status runs successfully
TC_OC_004: Verify omnia-cli check runs successfully
TC_OC_005: Verify omnia-cli status --project flag works
TC_OC_006: Verify omnia-cli repo-manager runs
TC_OC_007: Verify omnia-cli image-build runs
TC_OC_008: Verify omnia-cli discovery runs
TC_OC_009: Verify omnia-cli help repo-manager shows domain help
TC_OC_010: Verify omnia-cli help discovery shows domain help
TC_OC_014: Verify omnia-cli orchestrator runs
TC_OC_015: Verify omnia-cli telemetry runs
TC_OC_016: Verify omnia-cli build-stream runs
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cli_cmd,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(2)
def test_cli_status_runs(host):
    """TC_OC_003: Verify omnia-cli status runs successfully."""
    tl = TestLogger(
        TEST_NAMES["cli_status_runs"], "TC_OC_003"
    )
    result = run_omnia_cli_cmd(host, "omnia_cli_status")

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
@pytest.mark.order(3)
def test_cli_check_runs(host):
    """TC_OC_004: Verify omnia-cli check runs successfully."""
    tl = TestLogger(
        TEST_NAMES["cli_check_runs"], "TC_OC_004"
    )
    result = run_omnia_cli_cmd(host, "omnia_cli_check")

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
@pytest.mark.order(4)
def test_cli_status_project_flag(host):
    """TC_OC_005: Verify omnia-cli status --project flag works."""
    tl = TestLogger(
        TEST_NAMES["cli_status_project_flag"], "TC_OC_005"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_status_project",
        project="project_default",
    )

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
@pytest.mark.order(5)
def test_cli_repo_manager(host):
    """TC_OC_006: Verify omnia-cli repo-manager runs."""
    tl = TestLogger(
        TEST_NAMES["cli_repo_manager"], "TC_OC_006"
    )
    # repo-manager may return non-zero if not yet run —
    # we only check it does not crash (exits cleanly)
    result = run_omnia_cli_cmd(
        host, "omnia_cli_repo_manager"
    )

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
@pytest.mark.order(6)
def test_cli_image_build(host):
    """TC_OC_007: Verify omnia-cli image-build runs."""
    tl = TestLogger(
        TEST_NAMES["cli_image_build"], "TC_OC_007"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_image_build"
    )

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
@pytest.mark.order(7)
def test_cli_discovery_status(host):
    """TC_OC_008: Verify omnia-cli discovery runs."""
    tl = TestLogger(
        TEST_NAMES["cli_domain_status"], "TC_OC_008"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_domain", domain="discovery"
    )

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
@pytest.mark.order(8)
def test_cli_help_repo_manager(host):
    """TC_OC_009: Verify omnia-cli help repo-manager shows domain help."""
    tl = TestLogger(
        TEST_NAMES["cli_help_domain"], "TC_OC_009"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_help_domain",
        domain="repo-manager",
    )
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
@pytest.mark.order(9)
def test_cli_help_discovery(host):
    """TC_OC_010: Verify omnia-cli help discovery shows domain help."""
    tl = TestLogger(
        TEST_NAMES["cli_help_domain"], "TC_OC_010"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_help_domain",
        domain="discovery",
    )
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
@pytest.mark.order(10)
def test_cli_orchestrator(host):
    """TC_OC_014: Verify omnia-cli orchestrator runs."""
    tl = TestLogger(
        TEST_NAMES["cli_orchestrator"], "TC_OC_014"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_orchestrator"
    )

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
@pytest.mark.order(11)
def test_cli_telemetry(host):
    """TC_OC_015: Verify omnia-cli telemetry runs."""
    tl = TestLogger(
        TEST_NAMES["cli_telemetry"], "TC_OC_015"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_telemetry"
    )

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
@pytest.mark.order(12)
def test_cli_build_stream(host):
    """TC_OC_016: Verify omnia-cli build-stream runs."""
    tl = TestLogger(
        TEST_NAMES["cli_build_stream"], "TC_OC_016"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_build_stream"
    )

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
