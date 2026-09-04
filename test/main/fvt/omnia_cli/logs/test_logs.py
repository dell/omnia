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
Omnia CLI — Logs Command Verification.

TC_OC_012: Verify omnia-cli logs --help runs successfully
TC_OC_013: Verify omnia-cli logs searches only /var/log/omnia (not /opt/omnia/log)
TC_OC_014: Verify omnia-cli logs --limit flag works
TC_OC_015: Verify omnia-cli logs --limit rejects invalid values
TC_OC_016: Verify omnia-cli logs -l short form works
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cli_cmd,
    _resolve_clone_path,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(11)
def test_cli_logs_help(host):
    """TC_OC_012: Verify omnia-cli logs --help runs."""
    tl = TestLogger(
        TEST_NAMES["cli_logs_help"], "TC_OC_012"
    )
    result = run_omnia_cli_cmd(host, "omnia_cli_logs_help")

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_logs_help_ok"])
    else:
        tl.failed(LOG["cli_logs_help_failed"])

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.functional
@pytest.mark.order(12)
def test_cli_logs_no_opt_omnia_log(host):
    """TC_OC_013: Verify omnia-cli logs does not search /opt/omnia/log.

    The omnia-cli logs function should only search /var/log/omnia/ for
    ansible logs, not /opt/omnia/log (which was previously a bug).
    """
    tl = TestLogger(
        "Verify omnia-cli does not search /opt/omnia/log",
        "TC_OC_013",
    )

    # Read the omnia-cli script and verify the log path is correct
    clone_path = _resolve_clone_path()
    cli_path = f"{clone_path}/src/main/omnia-cli"

    result = host.run(f"grep -c 'base.*log' {cli_path}")
    # Should NOT find "${base}/log" in ansible_log_dirs
    grep_result = host.run(
        f"grep 'ansible_log_dirs' {cli_path}"
    )
    output = grep_result.stdout.strip()

    # The fix removed ${base}/log — should only contain ANSIBLE_LOG_DEFAULT
    has_base_log = "${base}/log" in output

    if not has_base_log:
        tl.passed(
            "omnia-cli logs only searches /var/log/omnia "
            "(no ${base}/log)"
        )
    else:
        tl.failed(
            "omnia-cli still references ${base}/log in "
            "ansible_log_dirs"
        )

    assert not has_base_log, (
        "omnia-cli should not search ${base}/log "
        "(was /opt/omnia/log). "
        "Only ANSIBLE_LOG_DEFAULT (/var/log/omnia) should be used."
    )


@pytest.mark.functional
@pytest.mark.order(13)
def test_cli_logs_limit(host):
    """TC_OC_014: Verify omnia-cli logs --limit flag works."""
    tl = TestLogger(
        TEST_NAMES["cli_logs_limit"], "TC_OC_014"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_logs_limit",
        domain="repo-manager",
        limit=10,
    )

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_logs_limit_ok"].format(limit=10))
    else:
        tl.failed(
            f"omnia-cli logs --limit 10 failed (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )


@pytest.mark.functional
@pytest.mark.order(14)
def test_cli_logs_limit_invalid(host):
    """TC_OC_015: Verify omnia-cli logs --limit rejects invalid values."""
    tl = TestLogger(
        TEST_NAMES["cli_logs_limit_invalid"], "TC_OC_015"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_logs_limit_invalid",
        domain="repo-manager",
        limit="abc",
    )

    # Should exit with error (rc != 0)
    rejected = result["rc"] != 0

    if rejected:
        tl.passed(LOG["cli_logs_limit_invalid_ok"].format(
            limit="abc", rc=result["rc"]
        ))
    else:
        tl.failed(
            f"omnia-cli logs --limit abc should have been rejected"
        )

    assert rejected, (
        "omnia-cli logs --limit should reject non-integer values"
    )


@pytest.mark.functional
@pytest.mark.order(15)
def test_cli_logs_limit_short(host):
    """TC_OC_016: Verify omnia-cli logs -l short form works."""
    tl = TestLogger(
        TEST_NAMES["cli_logs_limit_short"], "TC_OC_016"
    )
    result = run_omnia_cli_cmd(
        host, "omnia_cli_logs_limit_short",
        domain="repo-manager",
        limit=5,
    )

    ran_ok = result["rc"] in (0, 1)

    if ran_ok:
        tl.passed(LOG["cli_logs_limit_short_ok"].format(limit=5))
    else:
        tl.failed(
            f"omnia-cli logs -l 5 failed (rc={result['rc']})"
        )

    assert ran_ok, ASSERT["cli_status_failed"].format(
        rc=result["rc"],
    )
