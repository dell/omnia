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

MAIN_FVT_CLI_V001: Verify omnia.sh with no args shows help
MAIN_FVT_CLI_V002: Verify --run with invalid domain exits with error
MAIN_FVT_CLI_V003: Verify --run without domain exits with error
MAIN_FVT_CLI_V004: Verify --deps-only flag appears in help output
MAIN_FVT_CLI_V005: Verify unknown option exits with error
MAIN_FVT_CLI_V006: Verify --cleanup flag appears in help output
MAIN_FVT_CLI_V007: Verify --check-deps flag appears in help output
MAIN_FVT_CLI_V008: Verify --force-deps flag appears in help output
MAIN_FVT_CLI_V009: Verify --skip-catalog flag appears in help output
MAIN_FVT_CLI_V010: Verify --force-deps without -s/-i exits with error
MAIN_FVT_CLI_V011: Verify --check-deps runs
MAIN_FVT_CLI_V012: Verify --setup-venv --skip-catalog --deps-only accepted
MAIN_FVT_CLI_V013: Verify --skip-omnia-cli flag appears in help output
MAIN_FVT_CLI_V014: Verify --setup-venv --skip-omnia-cli --deps-only accepted
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
    check_error_contains,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Append MAIN_FVT_CLI_V006/008 import (re-uses existing LOG / ASSERT keys)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_no_args_shows_help(host):
    """MAIN_FVT_CLI_V001: Verify omnia.sh with no args shows help."""
    tc = TC["no_args_shows_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_no_args")
    tl.bind_result(result)
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


@pytest.mark.regression
@pytest.mark.order(2)
def test_run_invalid_domain(host):
    """MAIN_FVT_CLI_V002: Verify --run with invalid domain exits with error."""
    tc = TC["run_invalid_domain"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_invalid",
        domain="nonexistent_domain_xyz",
    )
    tl.bind_result(result)

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


@pytest.mark.regression
@pytest.mark.order(3)
def test_run_no_domain(host):
    """MAIN_FVT_CLI_V003: Verify --run without domain exits with error."""
    tc = TC["run_no_domain"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_no_domain",
    )
    tl.bind_result(result)

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
    """MAIN_FVT_CLI_V004: Verify --deps-only flag appears in help output."""
    tc = TC["deps_only_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--deps-only" in result.get("output", "")

    if found:
        tl.passed(LOG["help_ok"])
    else:
        tl.failed("--deps-only flag not found in help output")

    assert found, (
        "--deps-only flag must appear in omnia.sh --help output"
    )


@pytest.mark.regression
@pytest.mark.order(5)
def test_unknown_option(host):
    """MAIN_FVT_CLI_V005: Verify unknown option exits with error."""
    tc = TC["unknown_option"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_unknown_option",
    )
    tl.bind_result(result)

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
    """MAIN_FVT_CLI_V006: Verify --cleanup flag appears in help output."""
    tc = TC["cleanup_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--cleanup" in result.get("output", "")

    if found:
        tl.passed(LOG["cleanup_in_help_ok"])
    else:
        tl.failed(LOG["cleanup_not_in_help"])

    assert found, ASSERT["cleanup_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_check_deps_in_help(host):
    """MAIN_FVT_CLI_V007: Verify --check-deps flag appears in help output."""
    tc = TC["check_deps_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--check-deps" in result.get("output", "")

    if found:
        tl.passed(LOG["check_deps_in_help_ok"])
    else:
        tl.failed(LOG["check_deps_not_in_help"])

    assert found, ASSERT["check_deps_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(8)
def test_force_deps_in_help(host):
    """MAIN_FVT_CLI_V008: Verify --force-deps flag appears in help output."""
    tc = TC["force_deps_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--force-deps" in result.get("output", "")

    if found:
        tl.passed(LOG["force_deps_in_help_ok"])
    else:
        tl.failed(LOG["force_deps_not_in_help"])

    assert found, ASSERT["force_deps_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(9)
def test_skip_catalog_in_help(host):
    """MAIN_FVT_CLI_V009: Verify --skip-catalog flag appears in help output."""
    tc = TC["skip_catalog_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--skip-catalog" in result.get("output", "")

    if found:
        tl.passed(LOG["skip_catalog_in_help_ok"])
    else:
        tl.failed(LOG["skip_catalog_not_in_help"])

    assert found, ASSERT["skip_catalog_not_in_help"]


@pytest.mark.regression
@pytest.mark.order(10)
def test_force_deps_invalid(host):
    """MAIN_FVT_CLI_V010: Verify --force-deps without -s/-i exits with error."""
    tc = TC["force_deps_invalid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_force_deps_invalid",
    )
    tl.bind_result(result)

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
    """MAIN_FVT_CLI_V011: Verify --check-deps command runs."""
    tc = TC["check_deps_runs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_check_deps")
    tl.bind_result(result)

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


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(12)
def test_skip_catalog_accepted(host):
    """MAIN_FVT_CLI_V012: Verify --setup-venv --skip-catalog --deps-only is accepted.

    This test verifies the option is parsed correctly (not rejected
    as an unknown option). The setup itself may fail for environment
    reasons — that is OK; we only assert the flag is accepted.
    """
    tc = TC["skip_catalog_accepted"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(
        host, "omnia_sh_setup_skip_catalog"
    )
    tl.bind_result(result)
    output = result.get("output", "")

    # The flag is accepted if:
    #   - rc == 0 (setup succeeded), OR
    #   - output does NOT contain "unknown option" / "unrecognized"
    rejected = (
        "unknown option" in output.lower()
        or "unrecognized" in output.lower()
        or "invalid option" in output.lower()
    )
    accepted = not rejected

    if accepted:
        tl.passed(LOG["skip_catalog_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["skip_catalog_failed"].format(
            rc=result["rc"]
        ))

    assert accepted, ASSERT["skip_catalog_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(13)
def test_skip_omnia_cli_in_help(host):
    """MAIN_FVT_CLI_V013: Verify --skip-omnia-cli flag appears in help output."""
    tc = TC["skip_omnia_cli_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--skip-omnia-cli" in result.get("output", "")

    if found:
        tl.passed(LOG["skip_omnia_cli_in_help_ok"])
    else:
        tl.failed(LOG["skip_omnia_cli_not_in_help"])

    assert found, ASSERT["skip_omnia_cli_not_in_help"]


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(14)
def test_skip_omnia_cli_accepted(host):
    """MAIN_FVT_CLI_V014: Verify --setup-venv --skip-omnia-cli --deps-only is accepted.

    This test verifies the option is parsed correctly (not rejected
    as an unknown option). The setup itself may fail for environment
    reasons -- that is OK; we only assert the flag is accepted.
    """
    tc = TC["skip_omnia_cli_accepted"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(
        host, "omnia_sh_setup_skip_omnia_cli"
    )
    tl.bind_result(result)
    output = result.get("output", "")

    rejected = (
        "unknown option" in output.lower()
        or "unrecognized" in output.lower()
        or "invalid option" in output.lower()
    )
    accepted = not rejected

    if accepted:
        tl.passed(LOG["skip_omnia_cli_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["skip_omnia_cli_failed"].format(
            rc=result["rc"]
        ))

    assert accepted, ASSERT["skip_omnia_cli_failed"].format(
        rc=result["rc"],
    )
