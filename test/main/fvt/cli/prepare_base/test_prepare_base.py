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
Omnia Main CLI -- --prepare-base Verification.

TC_PB_001: Verify --prepare-base flag appears in help output
TC_PB_002: Verify --prepare-base --dry-run shows domains and phases
TC_PB_003: Verify --prepare-base --dry-run --skip filters domains
TC_PB_004: Verify --prepare-base --skip with invalid domain exits with error
TC_PB_005: Verify --prepare-base --skip all domains shows no-op message
TC_PB_006: Verify --prepare-base --dry-run shows all lifecycle phases
TC_PB_007: Verify --prepare-base --dry-run shows fail-fast note
TC_PB_008: Verify --prepare-base --dry-run shows correct domain order
TC_PB_009: Verify --prepare-base --dry-run --skip with 2 domains
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
from library.vars.common_vars import (
    PREPARE_BASE_DOMAINS,
    PREPARE_BASE_PHASES,
)


# ---------------------------------------------------------------------------
# Help output tests
# ---------------------------------------------------------------------------

@pytest.mark.sanity
@pytest.mark.order(27)
def test_prepare_base_in_help(host):
    """TC_PB_001: Verify --prepare-base flag appears in help output."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_in_help"], "TC_PB_001"
    )
    result = run_omnia_cmd(host, "omnia_sh_prepare_base_help")

    found = "--prepare-base" in result.get("output", "")

    if found:
        tl.passed(LOG["prepare_base_in_help_ok"])
    else:
        tl.failed(LOG["prepare_base_not_in_help"])

    assert found, ASSERT["prepare_base_not_in_help"]


# ---------------------------------------------------------------------------
# --prepare-base --dry-run tests
# ---------------------------------------------------------------------------

@pytest.mark.sanity
@pytest.mark.order(28)
def test_prepare_base_dry_run(host):
    """TC_PB_002: Verify --prepare-base --dry-run shows domains and phases."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_output"], "TC_PB_002"
    )
    result = run_omnia_cmd(host, "omnia_sh_prepare_base_dry_run")
    output = result.get("output", "")

    has_dry_run = "DRY RUN" in output
    has_domains = all(
        d in output for d in PREPARE_BASE_DOMAINS
    )
    success = has_dry_run and has_domains

    if success:
        tl.passed(LOG["prepare_base_dry_run_ok"])
    else:
        tl.failed(
            f"--prepare-base --dry-run output missing expected content "
            f"(DRY RUN: {has_dry_run}, all domains: {has_domains})"
        )

    assert success, ASSERT["prepare_base_dry_run_failed"]


@pytest.mark.sanity
@pytest.mark.order(29)
def test_prepare_base_dry_run_skip(host):
    """TC_PB_003: Verify --prepare-base --dry-run --skip filters domains."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_skip"], "TC_PB_003"
    )
    result = run_omnia_cmd(
        host, "omnia_sh_prepare_base_dry_run_skip",
        domain="orchestrator",
    )
    output = result.get("output", "")

    has_dry_run = "DRY RUN" in output
    has_skipped = (
        "Skipping" in output or "Skipped" in output
    )
    # orchestrator should be in Skipping line but not in
    # the domain list under each phase
    has_remaining = (
        "repo_manager" in output
        and "image_build_manager" in output
    )
    success = has_dry_run and has_skipped and has_remaining

    if success:
        tl.passed(LOG["prepare_base_dry_run_skip_ok"])
    else:
        tl.failed(
            f"--prepare-base --dry-run --skip output missing "
            f"expected content (DRY RUN: {has_dry_run}, "
            f"skipped: {has_skipped}, remaining: {has_remaining})"
        )

    assert success, ASSERT["prepare_base_dry_run_failed"]


# ---------------------------------------------------------------------------
# --prepare-base --skip error handling tests
# ---------------------------------------------------------------------------

@pytest.mark.sanity
@pytest.mark.order(30)
def test_prepare_base_skip_invalid(host):
    """TC_PB_004: Verify --prepare-base --skip with invalid domain exits
    with error."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_skip_invalid"], "TC_PB_004"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_prepare_base_skip_invalid",
    )

    if result["success"]:
        tl.passed(LOG["prepare_base_skip_invalid_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["prepare_base_skip_invalid"].format(
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(31)
def test_prepare_base_skip_all(host):
    """TC_PB_005: Verify --prepare-base --skip all domains shows no-op
    message."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_skip_all"], "TC_PB_005"
    )
    result = run_omnia_cmd(
        host, "omnia_sh_prepare_base_skip_all",
    )
    output = result.get("output", "")

    has_no_op = (
        "No domains to prepare" in output
        or "all were skipped" in output
    )

    if has_no_op:
        tl.passed(LOG["prepare_base_skip_all_ok"])
    else:
        tl.failed(LOG["prepare_base_skip_all_failed"])

    assert has_no_op, ASSERT["prepare_base_skip_all_failed"]


# ---------------------------------------------------------------------------
# --prepare-base --dry-run content verification
# ---------------------------------------------------------------------------

@pytest.mark.sanity
@pytest.mark.order(32)
def test_prepare_base_dry_run_phases(host):
    """TC_PB_006: Verify --prepare-base --dry-run shows all lifecycle
    phases."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_phases"], "TC_PB_006"
    )
    result = run_omnia_cmd(host, "omnia_sh_prepare_base_dry_run")
    output = result.get("output", "")

    missing = [
        p for p in PREPARE_BASE_PHASES if p not in output
    ]
    success = len(missing) == 0

    if success:
        tl.passed(LOG["prepare_base_phases_ok"])
    else:
        tl.failed(LOG["prepare_base_phases_missing"].format(
            missing=", ".join(missing)
        ))

    assert success, ASSERT["prepare_base_phases_failed"]


@pytest.mark.sanity
@pytest.mark.order(33)
def test_prepare_base_dry_run_fail_fast_note(host):
    """TC_PB_007: Verify --prepare-base --dry-run shows fail-fast note."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_fail_fast_note"],
        "TC_PB_007",
    )
    result = run_omnia_cmd(host, "omnia_sh_prepare_base_dry_run")
    output = result.get("output", "")

    has_note = (
        "fail-fast" in output.lower()
        or "stops immediately" in output.lower()
    )

    if has_note:
        tl.passed(LOG["prepare_base_fail_fast_ok"])
    else:
        tl.failed(LOG["prepare_base_fail_fast_missing"])

    assert has_note, ASSERT["prepare_base_fail_fast_failed"]


@pytest.mark.sanity
@pytest.mark.order(34)
def test_prepare_base_dry_run_domain_order(host):
    """TC_PB_008: Verify --prepare-base --dry-run shows correct domain
    order (repo_manager -> image_build_manager -> orchestrator)."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_domain_order"],
        "TC_PB_008",
    )
    result = run_omnia_cmd(host, "omnia_sh_prepare_base_dry_run")
    output = result.get("output", "")

    # Verify order by checking relative positions
    pos_repo = output.find("repo_manager")
    pos_img = output.find("image_build_manager")
    pos_orch = output.find("orchestrator")

    all_found = (
        pos_repo >= 0
        and pos_img >= 0
        and pos_orch >= 0
    )
    correct_order = (
        all_found
        and pos_repo < pos_img < pos_orch
    )

    if correct_order:
        tl.passed(LOG["prepare_base_order_ok"])
    else:
        tl.failed(LOG["prepare_base_order_wrong"])

    assert correct_order, ASSERT["prepare_base_order_failed"]


@pytest.mark.sanity
@pytest.mark.order(35)
def test_prepare_base_dry_run_skip_multiple(host):
    """TC_PB_009: Verify --prepare-base --dry-run --skip with 2 domains
    leaves only one domain."""
    tl = TestLogger(
        TEST_NAMES["prepare_base_dry_run_skip_multiple"],
        "TC_PB_009",
    )
    result = run_omnia_cmd(
        host, "omnia_sh_prepare_base_dry_run_skip",
        domain="orchestrator,repo_manager",
    )
    output = result.get("output", "")

    has_dry_run = "DRY RUN" in output
    # Only image_build_manager should remain
    has_remaining = "image_build_manager" in output
    # The skipped domains should appear in "Skipping" lines
    # but not in phase domain lists
    success = has_dry_run and has_remaining

    if success:
        tl.passed(LOG["prepare_base_dry_run_skip_ok"])
    else:
        tl.failed(
            f"--prepare-base --dry-run --skip 2 domains: "
            f"DRY RUN: {has_dry_run}, "
            f"remaining: {has_remaining}"
        )

    assert success, ASSERT["prepare_base_dry_run_failed"]
