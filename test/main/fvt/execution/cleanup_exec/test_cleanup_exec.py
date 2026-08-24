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
Omnia Main Execution — Cleanup Tests.

Tests actual execution of ``omnia.sh --cleanup`` and ``--cleanup --all``,
verifying that cleanup removes the right artifacts and preserves data.

TC_EX_012: Execute --cleanup with 'no' — verify cancel
TC_EX_013: Execute --cleanup with 'yes' — verify success
TC_EX_014: Verify cleanup removed venv, env files, omnia-cli
TC_EX_015: Verify cleanup preserved runtime data (/opt/omnia/)
TC_EX_016: Re-deploy omnia.sh --setup-venv after cleanup (idempotency)
TC_EX_017: Execute --cleanup --all with 'yes' — full reset
TC_EX_018: Verify --cleanup --all removed data directory
TC_EX_019: Re-deploy omnia.sh --setup-venv after full cleanup
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import run_omnia_cmd
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import (
    SYSTEM_ENV_FILE,
    PROFILE_DROP_IN,
)


# =========================================================================
# TC_EX_012: Cancel cleanup
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(20)
def test_cleanup_cancel(host):
    """TC_EX_012: Execute --cleanup with 'no' — verify cancel."""
    tl = TestLogger(
        TEST_NAMES["exec_cleanup_cancel"], "TC_EX_012"
    )

    result = run_omnia_cmd(host, "omnia_sh_cleanup_no")

    # Should succeed (rc=0) and output should contain "cancelled"
    cancelled = (
        result["success"]
        and "cancelled" in result.get("output", "").lower()
    )

    if cancelled:
        tl.passed(LOG["exec_cleanup_cancelled_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            f"Expected cleanup to cancel with 'no' input "
            f"(rc={result['rc']})"
        )

    assert cancelled, ASSERT["exec_cleanup_cancel_failed"].format(
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_013: Execute cleanup
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(21)
def test_cleanup_exec(host):
    """TC_EX_013: Execute --cleanup with 'yes'."""
    tl = TestLogger(
        TEST_NAMES["exec_cleanup"], "TC_EX_013"
    )

    result = run_omnia_cmd(host, "omnia_sh_cleanup_yes")

    if result["success"]:
        tl.passed(LOG["exec_cleanup_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            LOG["exec_cleanup_failed"].format(
                rc=result["rc"]
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_cleanup_failed"].format(
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_014: Verify cleanup removed artifacts
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(22)
def test_cleanup_verify_removed(host):
    """TC_EX_014: Verify cleanup removed venv, env files, omnia-cli."""
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    tl = TestLogger(
        TEST_NAMES["exec_cleanup_verify_removed"], "TC_EX_014"
    )

    # These paths should NOT exist after cleanup
    check_paths = [
        venv_path,
        SYSTEM_ENV_FILE,
        PROFILE_DROP_IN,
        "/usr/local/bin/omnia-cli",
        "/etc/bash_completion.d/omnia-cli",
    ]

    remaining = []
    for path in check_paths:
        result = host.run(f"test -e {path} && echo exists")
        if "exists" in result.stdout:
            remaining.append(path)

    if not remaining:
        tl.passed(LOG["exec_cleanup_verify_ok"])
    else:
        tl.failed(LOG["exec_cleanup_verify_failed"].format(
            remaining=", ".join(remaining)
        ))

    assert not remaining, ASSERT["exec_cleanup_verify_failed"].format(
        remaining=", ".join(remaining),
    )


# =========================================================================
# TC_EX_015: Verify cleanup preserved runtime data
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(23)
def test_cleanup_verify_data_preserved(host):
    """TC_EX_015: Verify cleanup preserved runtime data."""
    config = load_test_config()
    data_path = config.get("omnia_data_path", "/opt/omnia")

    tl = TestLogger(
        TEST_NAMES["exec_cleanup_verify_data"], "TC_EX_015"
    )

    # Data directory should still exist after regular cleanup (not --all)
    result = host.run(f"test -d {data_path} && echo exists")
    preserved = "exists" in result.stdout

    if preserved:
        tl.passed(LOG["exec_cleanup_verify_data_ok"].format(
            data_path=data_path
        ))
    else:
        tl.failed(
            f"Runtime data at {data_path} was removed by cleanup"
        )

    assert preserved, ASSERT["exec_cleanup_data_lost"].format(
        data_path=data_path,
    )


# =========================================================================
# TC_EX_016: Re-setup after cleanup (idempotency)
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(24)
def test_re_setup_after_cleanup(host):
    """TC_EX_016: Re-deploy --setup-venv --deps-only after cleanup."""
    tl = TestLogger(
        TEST_NAMES["exec_re_setup"], "TC_EX_016"
    )

    result = run_omnia_cmd(host, "omnia_sh_setup_venv")

    if result["success"]:
        tl.passed(LOG["exec_re_setup_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            LOG["exec_re_setup_failed"].format(
                rc=result["rc"]
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_re_setup_failed"].format(
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_017: Full cleanup (--all)
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(25)
def test_cleanup_all_exec(host):
    """TC_EX_017: Execute --cleanup --all with 'yes' — full reset."""
    tl = TestLogger(
        TEST_NAMES["exec_cleanup"], "TC_EX_017"
    )

    result = run_omnia_cmd(host, "omnia_sh_cleanup_all_yes")

    if result["success"]:
        tl.passed(LOG["exec_cleanup_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            LOG["exec_cleanup_failed"].format(
                rc=result["rc"]
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_cleanup_failed"].format(
        rc=result["rc"],
    )


# =========================================================================
# TC_EX_018: Verify --all removed data directory
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(26)
def test_cleanup_all_verify_removed(host):
    """TC_EX_018: Verify --cleanup --all removed data directory."""
    config = load_test_config()
    data_path = config.get("omnia_data_path", "/opt/omnia")
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    tl = TestLogger(
        TEST_NAMES["exec_cleanup_verify_removed"], "TC_EX_018"
    )

    # After --all, these should all be gone
    check_paths = [
        data_path,
        venv_path,
        SYSTEM_ENV_FILE,
        PROFILE_DROP_IN,
        "/usr/local/bin/omnia-cli",
        "/etc/bash_completion.d/omnia-cli",
    ]

    remaining = []
    for path in check_paths:
        result = host.run(f"test -e {path} && echo exists")
        if "exists" in result.stdout:
            remaining.append(path)

    if not remaining:
        tl.passed(LOG["exec_cleanup_verify_ok"])
    else:
        tl.failed(LOG["exec_cleanup_verify_failed"].format(
            remaining=", ".join(remaining)
        ))

    assert not remaining, ASSERT["exec_cleanup_verify_failed"].format(
        remaining=", ".join(remaining),
    )


# =========================================================================
# TC_EX_019: Re-setup after full cleanup
# =========================================================================

@pytest.mark.sanity
@pytest.mark.order(27)
def test_re_setup_after_full_cleanup(host):
    """TC_EX_019: Re-deploy --setup-venv --deps-only after --all."""
    tl = TestLogger(
        TEST_NAMES["exec_re_setup"], "TC_EX_019"
    )

    result = run_omnia_cmd(host, "omnia_sh_setup_venv")

    if result["success"]:
        tl.passed(LOG["exec_re_setup_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            LOG["exec_re_setup_failed"].format(
                rc=result["rc"]
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_re_setup_failed"].format(
        rc=result["rc"],
    )
