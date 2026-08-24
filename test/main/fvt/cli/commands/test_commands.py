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
Omnia Main CLI — Command Verification.

TC_CL_002: Verify omnia.sh with no args shows help
TC_CL_003: Verify --run with invalid domain exits with error
TC_CL_004: Verify --run without domain exits with error
TC_CL_005: Verify --deps-only flag appears in help output
TC_CL_006: Verify unknown option exits with error
TC_CL_007: Verify --cleanup flag appears in help output
TC_CL_008: Verify --check-deps flag appears in help output
TC_CL_009: Verify --force-deps flag appears in help output
TC_CL_010: Verify --skip-catalog flag appears in help output
TC_CL_011: Verify --force-deps without -s/-i exits with error
TC_CL_012: Verify --check-deps runs
TC_CL_015: Verify --setup-venv --skip-catalog --deps-only accepted
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
    check_error_contains,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Append TC_CL_007/008 import (re-uses existing LOG / ASSERT keys)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_no_args_shows_help(host):
    """TC_CL_002: Verify omnia.sh with no args shows help."""
    tl = TestLogger(
        TEST_NAMES["no_args_shows_help"], "TC_CL_002"
    )
    result = run_omnia_cmd(host, "omnia_sh_no_args")
    output = result["output"]

    has_usage = check_error_contains(output, "usage")

    if has_usage:
        tl.passed(LOG["help_ok"])
    else:
        tl.failed(LOG["help_missing_section"].format(
            section="USAGE"
        ))

    assert has_usage, ASSERT["help_missing"].format(
        sections="USAGE",
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_run_invalid_domain(host):
    """TC_CL_003: Verify --run with invalid domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["invalid_domain_error"], "TC_CL_003"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_invalid",
        domain="nonexistent_domain_xyz",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --run nonexistent_domain_xyz",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_run_no_domain(host):
    """TC_CL_004: Verify --run without domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["run_no_domain_error"], "TC_CL_004"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_no_domain",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --run",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_deps_only_in_help(host):
    """TC_CL_005: Verify --deps-only flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["deps_only_setup"], "TC_CL_005"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--deps-only" in result.get("output", "")

    if found:
        tl.passed(LOG["help_ok"])
    else:
        tl.failed("--deps-only flag not found in help output")

    assert found, (
        "--deps-only flag must appear in omnia.sh --help output"
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_unknown_option(host):
    """TC_CL_006: Verify unknown option exits with error."""
    tl = TestLogger(
        TEST_NAMES["unknown_option_error"], "TC_CL_006"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_unknown_option",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --bogus",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_cleanup_in_help(host):
    """TC_CL_007: Verify --cleanup flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["cleanup_in_help"], "TC_CL_007"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--cleanup" in result.get("output", "")

    if found:
        tl.passed(LOG["cleanup_in_help_ok"])
    else:
        tl.failed(LOG["cleanup_not_in_help"])

    assert found, ASSERT["cleanup_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_check_deps_in_help(host):
    """TC_CL_008: Verify --check-deps flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["check_deps_in_help"], "TC_CL_008"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--check-deps" in result.get("output", "")

    if found:
        tl.passed(LOG["check_deps_in_help_ok"])
    else:
        tl.failed(LOG["check_deps_not_in_help"])

    assert found, ASSERT["check_deps_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(8)
def test_force_deps_in_help(host):
    """TC_CL_009: Verify --force-deps flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["force_deps_in_help"], "TC_CL_009"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--force-deps" in result.get("output", "")

    if found:
        tl.passed(LOG["force_deps_in_help_ok"])
    else:
        tl.failed(LOG["force_deps_not_in_help"])

    assert found, ASSERT["force_deps_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(9)
def test_skip_catalog_in_help(host):
    """TC_CL_010: Verify --skip-catalog flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["skip_catalog_in_help"], "TC_CL_010"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--skip-catalog" in result.get("output", "")

    if found:
        tl.passed(LOG["skip_catalog_in_help_ok"])
    else:
        tl.failed(LOG["skip_catalog_not_in_help"])

    assert found, ASSERT["skip_catalog_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(10)
def test_force_deps_invalid(host):
    """TC_CL_011: Verify --force-deps without -s/-i exits with error."""
    tl = TestLogger(
        TEST_NAMES["force_deps_invalid"], "TC_CL_011"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_force_deps_invalid",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["force_deps_invalid"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(11)
def test_check_deps_runs(host):
    """TC_CL_012: Verify --check-deps command runs."""
    tl = TestLogger(
        TEST_NAMES["check_deps_runs"], "TC_CL_012"
    )
    result = run_omnia_cmd(host, "omnia_sh_check_deps")

    # --check-deps may exit 0 (no mismatches) or 1 (mismatches found).
    # Both are valid executions.  We check that it produces output.
    output = result.get("output", "")
    ran = "Dependency Version Audit" in output

    if ran:
        tl.passed(LOG["check_deps_ok"])
    else:
        tl.failed(LOG["check_deps_failed"].format(
            rc=result["rc"]
        ))

    assert ran, ASSERT["check_deps_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(12)
def test_skip_catalog_accepted(host):
    """TC_CL_015: Verify --setup-venv --skip-catalog --deps-only is accepted."""
    tl = TestLogger(
        TEST_NAMES["skip_catalog_accepted"], "TC_CL_015"
    )
    result = run_omnia_cmd(
        host, "omnia_sh_setup_skip_catalog"
    )

    if result["success"]:
        tl.passed(LOG["skip_catalog_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["skip_catalog_failed"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["skip_catalog_failed"].format(
        rc=result["rc"],
    )
