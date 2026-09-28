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
Discovery — Non-Functional Idempotency Tests.

Verifies that running the discovery playbook twice produces no errors:
  Precheck is idempotent (second run succeeds)
  Cleanup is idempotent (second run succeeds, output stays clean)
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_output_dir_removed,
    check_credentials_removed,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT


@pytest.mark.nft
@pytest.mark.order(1)
def test_precheck_idempotent(host):
    """Verify running precheck twice does not produce errors."""
    tc = TC["precheck_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])

    # First run
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="precheck",
    )
    if not result1["success"]:
        tl.failed(f"First precheck failed (rc={result1['rc']})")
        pytest.fail(f"First precheck failed (rc={result1['rc']})")

    # Second run
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="precheck",
    )

    if result2["success"]:
        tl.passed(
            f"Precheck idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s."
        )
    else:
        tl.failed(
            f"Precheck not idempotent. "
            f"rc={result2.get('rc')}"
        )

    assert result2["success"], (
        f"Second precheck run failed (rc={result2['rc']})"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_cleanup_idempotent(host):
    """Verify running cleanup twice leaves a clean state."""
    tc = TC["cleanup_idempotent"]
    tl = TestLogger(tc["title"], tc["id"])

    # First cleanup
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="cleanup",
    )
    if not result1["success"]:
        tl.failed(f"First cleanup failed (rc={result1['rc']})")
        pytest.fail(f"First cleanup failed (rc={result1['rc']})")

    # Second cleanup
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="cleanup",
    )

    # Post-check: output and credentials should be removed
    output_check = check_output_dir_removed(host)
    creds_check = check_credentials_removed(host)

    all_ok = (
        result2["success"]
        and output_check["success"]
        and creds_check["success"]
    )

    if all_ok:
        tl.passed(
            f"Cleanup idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"Output and credentials clean."
        )
    else:
        tl.failed(
            f"Cleanup not idempotent. "
            f"rc={result2.get('rc')}, "
            f"output_clean={output_check['success']}, "
            f"creds_clean={creds_check['success']}"
        )

    assert result2["success"], (
        f"Second cleanup run failed (rc={result2['rc']})"
    )
    assert output_check["success"], "Output directory not clean after cleanup"
    assert creds_check["success"], "Credentials not removed after cleanup"
