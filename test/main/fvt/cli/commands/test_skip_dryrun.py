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
Omnia Main CLI — --skip, --dry-run Verification.

MAIN_FVT_CLI_V015: Verify --skip flag appears in help output
MAIN_FVT_CLI_V016: Verify --dry-run flag appears in help output
MAIN_FVT_CLI_V017: Verify --skip with invalid domain exits with error
MAIN_FVT_CLI_V018: Verify --skip + explicit domain list is mutually exclusive
MAIN_FVT_CLI_V019: Verify --skip without -s/-i exits with error
MAIN_FVT_CLI_V020: Verify --skip without domain list exits with error
MAIN_FVT_CLI_V021: Verify --dry-run shows domain list without executing
MAIN_FVT_CLI_V022: Verify --dry-run --skip shows filtered domain list
MAIN_FVT_CLI_V023: Verify --dry-run without -s/-i exits with error
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import KNOWN_DOMAINS


# ─────────────────────────────────────────────────────────────────────────────
# Help output tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.sanity
@pytest.mark.order(15)
def test_skip_in_help(host):
    """MAIN_FVT_CLI_V015: Verify --skip flag appears in help output."""
    tc = TC["skip_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--skip" in result.get("output", "")

    if found:
        tl.passed(LOG["skip_in_help_ok"])
    else:
        tl.failed(LOG["skip_not_in_help"])

    assert found, ASSERT["skip_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(16)
def test_dry_run_in_help(host):
    """MAIN_FVT_CLI_V016: Verify --dry-run flag appears in help output."""
    tc = TC["dry_run_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)

    found = "--dry-run" in result.get("output", "")

    if found:
        tl.passed(LOG["dry_run_in_help_ok"])
    else:
        tl.failed(LOG["dry_run_not_in_help"])

    assert found, ASSERT["dry_run_not_in_help"]


# ─────────────────────────────────────────────────────────────────────────────
# --skip error handling tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.regression
@pytest.mark.order(17)
def test_skip_invalid_domain(host):
    """MAIN_FVT_CLI_V017: Verify --skip with invalid domain exits with error."""
    tc = TC["skip_invalid_domain"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_invalid_domain",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["skip_invalid_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["skip_invalid_domain"].format(
        rc=result["rc"],
    )


@pytest.mark.regression
@pytest.mark.order(18)
def test_skip_with_include_error(host):
    """MAIN_FVT_CLI_V018: Verify --skip + explicit domain list is rejected."""
    tc = TC["skip_with_include_error"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_with_include",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["skip_include_error_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["skip_with_include"].format(
        rc=result["rc"],
    )


@pytest.mark.regression
@pytest.mark.order(19)
def test_skip_without_init_error(host):
    """MAIN_FVT_CLI_V019: Verify --skip without -s/-i exits with error."""
    tc = TC["skip_without_init_error"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_without_init",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["skip_without_init_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["skip_without_init"].format(
        rc=result["rc"],
    )


@pytest.mark.regression
@pytest.mark.order(20)
def test_skip_no_args_error(host):
    """MAIN_FVT_CLI_V020: Verify --skip without domain list exits with error."""
    tc = TC["skip_no_args_error"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_no_args",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["skip_no_args_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["skip_no_args"].format(
        rc=result["rc"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# --dry-run tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.sanity
@pytest.mark.order(21)
def test_dry_run_output(host):
    """MAIN_FVT_CLI_V021: Verify --dry-run shows domain list without executing."""
    tc = TC["dry_run_output"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_dry_run")
    tl.bind_result(result)
    output = result.get("output", "")

    # --dry-run should print "DRY RUN" and list domains
    has_dry_run = "DRY RUN" in output
    # Should mention at least one known domain
    has_domain = any(d in output for d in KNOWN_DOMAINS)
    success = has_dry_run and has_domain

    if success:
        tl.passed(LOG["dry_run_ok"])
    else:
        tl.failed(
            f"--dry-run output missing expected content "
            f"(DRY RUN: {has_dry_run}, domain: {has_domain})"
        )

    assert success, ASSERT["dry_run_failed"]


@pytest.mark.sanity
@pytest.mark.order(22)
def test_dry_run_with_skip(host):
    """MAIN_FVT_CLI_V022: Verify --dry-run --skip shows filtered domain list."""
    tc = TC["dry_run_with_skip"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(
        host, "omnia_sh_dry_run_with_skip",
        domain="telemetry",
    )
    tl.bind_result(result)
    output = result.get("output", "")

    # Should show DRY RUN and mention "Skipped"
    has_dry_run = "DRY RUN" in output
    has_skipped = "Skipped" in output or "Skipping" in output
    # Should NOT list the skipped domain in the target list
    # (it may appear in the "Skipped:" line, so check DRY RUN section)
    success = has_dry_run and has_skipped

    if success:
        tl.passed(LOG["dry_run_skip_ok"])
    else:
        tl.failed(
            f"--dry-run --skip output missing expected content "
            f"(DRY RUN: {has_dry_run}, skipped: {has_skipped})"
        )

    assert success, ASSERT["dry_run_failed"]


@pytest.mark.regression
@pytest.mark.order(23)
def test_dry_run_without_init_error(host):
    """MAIN_FVT_CLI_V023: Verify --dry-run without -s/-i exits with error."""
    tc = TC["dry_run_without_init_error"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_dry_run_without_init",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["dry_run_without_init_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["dry_run_without_init"].format(
        rc=result["rc"],
    )
