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
Orchestrator — Non-Functional Idempotency Tests.

Verifies that running orchestrator playbooks multiple times produces no side effects:
  - Prepare is idempotent (OpenCHAMI containers not recreated unnecessarily)
  - Validate is idempotent (config validation safe to re-run)
  - Cleanup is idempotent (safe to cleanup twice)

Test cases:
    NFT_OR_005: Prepare idempotency (OpenCHAMI containers stable)
    NFT_OR_006: Validate idempotency (config validation safe to re-run)
    NFT_OR_007: Cleanup idempotency (safe to cleanup twice)
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    check_openchami_containers,
    check_containers_removed,
    check_services_removed,
)
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(1)
def test_prepare_idempotent(host):
    """NFT_OR_005: Verify running prepare twice does not recreate containers unnecessarily.

    Runs prepare playbook twice and verifies that:
    1. Both runs complete successfully (rc=0)
    2. OpenCHAMI containers remain running after second run
    3. OpenCHAMI services remain active after second run
    """
    tl = TestLogger("NFT: Prepare idempotency", "NFT_OR_005")

    # First run
    tl.check("First prepare run")
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="prepare",
    )

    if not result1["success"]:
        tl.failed(f"First prepare failed (rc={result1['rc']})")
        pytest.fail(f"First prepare failed (rc={result1['rc']})")

    # Check containers after first run
    containers1 = check_openchami_containers(host)

    # Second run
    tl.check("Second prepare run (idempotency check)")
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="prepare",
    )

    # Check containers after second run
    containers2 = check_openchami_containers(host)

    all_ok = (
        result2["success"]
        and containers2["success"]
    )

    if all_ok:
        tl.passed(
            f"Prepare idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"OpenCHAMI containers stable.",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2['rc']}\n"
            f"Containers after run1: {containers1['details']}\n"
            f"Containers after run2: {containers2['details']}",
        )
    else:
        tl.failed(
            f"Prepare not idempotent. "
            f"rc={result2.get('rc')}, "
            f"containers={containers2['success']}",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2.get('rc')}\n"
            f"Containers after run2: {containers2.get('error', 'Unknown error')}",
        )

    assert result2["success"], (
        f"Second prepare run failed (rc={result2['rc']})"
    )
    assert containers2["success"], "OpenCHAMI containers not running after second run"


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(2)
def test_validate_idempotent(host):
    """NFT_OR_006: Verify validate can be run multiple times safely.

    Runs validate playbook twice and verifies that:
    1. Both runs complete successfully (rc=0)
    2. No errors occur on subsequent runs
    """
    tl = TestLogger("NFT: Validate idempotency", "NFT_OR_006")

    # First run
    tl.check("First validate run")
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="validate",
    )

    if not result1["success"]:
        tl.failed(f"First validate failed (rc={result1['rc']})")
        pytest.fail(f"First validate failed (rc={result1['rc']})")

    # Second run
    tl.check("Second validate run (idempotency check)")
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="validate",
    )

    if result2["success"]:
        tl.passed(
            f"Validate idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2['rc']}",
        )
    else:
        tl.failed(
            f"Validate not idempotent (rc={result2['rc']})",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2['rc']}\n"
            f"Error: {result2.get('error', 'Unknown error')}",
        )

    assert result2["success"], (
        f"Second validate run failed (rc={result2['rc']})"
    )


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(3)
def test_cleanup_idempotent(host):
    """NFT_OR_007: Verify cleanup can be run multiple times safely.

    Runs cleanup playbook twice and verifies that:
    1. Both runs complete successfully (rc=0)
    2. Containers remain removed after second run
    3. Services remain stopped after second run
    """
    tl = TestLogger("NFT: Cleanup idempotency", "NFT_OR_007")

    # First run
    tl.check("First cleanup run")
    result1 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
    )

    if not result1["success"]:
        tl.failed(f"First cleanup failed (rc={result1['rc']})")
        pytest.fail(f"First cleanup failed (rc={result1['rc']})")

    # Check state after first run
    containers1 = check_containers_removed(host)
    services1 = check_services_removed(host)

    # Second run
    tl.check("Second cleanup run (idempotency check)")
    result2 = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup",
    )

    # Check state after second run
    containers2 = check_containers_removed(host)
    services2 = check_services_removed(host)

    all_ok = (
        result2["success"]
        and containers2["success"]
        and services2["success"]
    )

    if all_ok:
        tl.passed(
            f"Cleanup idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"Containers and services remain cleaned.",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2['rc']}\n"
            f"Containers after run2: {containers2['details']}\n"
            f"Services after run2: {services2['details']}",
        )
    else:
        tl.failed(
            f"Cleanup not idempotent. "
            f"rc={result2.get('rc')}, "
            f"containers={containers2['success']}, "
            f"services={services2['success']}",
            f"First run: {result1['duration']:.1f}s, rc={result1['rc']}\n"
            f"Second run: {result2['duration']:.1f}s, rc={result2.get('rc')}\n"
            f"Containers: {containers2.get('error', 'Unknown')}\n"
            f"Services: {services2.get('error', 'Unknown')}",
        )

    assert result2["success"], (
        f"Second cleanup run failed (rc={result2['rc']})"
    )
    assert containers2["success"], "Containers not removed after second run"
    assert services2["success"], "Services not stopped after second run"