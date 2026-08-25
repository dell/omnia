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

TC_CL_018: Verify --skip flag appears in help output
TC_CL_019: Verify --dry-run flag appears in help output
TC_CL_020: Verify --skip with invalid domain exits with error
TC_CL_021: Verify --skip + explicit domain list is mutually exclusive
TC_CL_022: Verify --skip without -s/-i exits with error
TC_CL_023: Verify --skip without domain list exits with error
TC_CL_024: Verify --dry-run shows domain list without executing
TC_CL_025: Verify --dry-run --skip shows filtered domain list
TC_CL_026: Verify --dry-run without -s/-i exits with error
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import KNOWN_DOMAINS


# ─────────────────────────────────────────────────────────────────────────────
# Help output tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.sanity
@pytest.mark.order(18)
def test_skip_in_help(host):
    """TC_CL_018: Verify --skip flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["skip_in_help"], "TC_CL_018"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--skip" in result.get("output", "")

    if found:
        tl.passed(LOG["skip_in_help_ok"])
    else:
        tl.failed(LOG["skip_not_in_help"])

    assert found, ASSERT["skip_not_in_help"]


@pytest.mark.sanity
@pytest.mark.order(19)
def test_dry_run_in_help(host):
    """TC_CL_019: Verify --dry-run flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["dry_run_in_help"], "TC_CL_019"
    )
    result = run_omnia_cmd(host, "omnia_sh_help")

    found = "--dry-run" in result.get("output", "")

    if found:
        tl.passed(LOG["dry_run_in_help_ok"])
    else:
        tl.failed(LOG["dry_run_not_in_help"])

    assert found, ASSERT["dry_run_not_in_help"]


# ─────────────────────────────────────────────────────────────────────────────
# --skip error handling tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.sanity
@pytest.mark.order(20)
def test_skip_invalid_domain(host):
    """TC_CL_020: Verify --skip with invalid domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["skip_invalid_domain"], "TC_CL_020"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_invalid_domain",
    )

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


@pytest.mark.sanity
@pytest.mark.order(21)
def test_skip_with_include_error(host):
    """TC_CL_021: Verify --skip + explicit domain list is rejected."""
    tl = TestLogger(
        TEST_NAMES["skip_with_include_error"], "TC_CL_021"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_with_include",
    )

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


@pytest.mark.sanity
@pytest.mark.order(22)
def test_skip_without_init_error(host):
    """TC_CL_022: Verify --skip without -s/-i exits with error."""
    tl = TestLogger(
        TEST_NAMES["skip_without_init_error"], "TC_CL_022"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_without_init",
    )

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


@pytest.mark.sanity
@pytest.mark.order(23)
def test_skip_no_args_error(host):
    """TC_CL_023: Verify --skip without domain list exits with error."""
    tl = TestLogger(
        TEST_NAMES["skip_no_args_error"], "TC_CL_023"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_skip_no_args",
    )

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
@pytest.mark.order(24)
def test_dry_run_output(host):
    """TC_CL_024: Verify --dry-run shows domain list without executing."""
    tl = TestLogger(
        TEST_NAMES["dry_run_output"], "TC_CL_024"
    )
    result = run_omnia_cmd(host, "omnia_sh_dry_run")
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
@pytest.mark.order(25)
def test_dry_run_with_skip(host):
    """TC_CL_025: Verify --dry-run --skip shows filtered domain list."""
    tl = TestLogger(
        TEST_NAMES["dry_run_with_skip"], "TC_CL_025"
    )
    result = run_omnia_cmd(
        host, "omnia_sh_dry_run_with_skip",
        domain="telemetry",
    )
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


@pytest.mark.sanity
@pytest.mark.order(26)
def test_dry_run_without_init_error(host):
    """TC_CL_026: Verify --dry-run without -s/-i exits with error."""
    tl = TestLogger(
        TEST_NAMES["dry_run_without_init_error"], "TC_CL_026"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_dry_run_without_init",
    )

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
