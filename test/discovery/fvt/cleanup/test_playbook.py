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
Discovery Cleanup -- Deploy.

DISCOVERY_FVT_CLEANUP_E001: Deploy discovery.yml --tags cleanup (full cleanup)
DISCOVERY_FVT_CLEANUP_E002: Deploy discovery.yml --tags cleanup \
    -e cleanup_credentials=false (preserve credentials)
DISCOVERY_FVT_CLEANUP_E003: Deploy discovery.yml --tags cleanup \
    -e cleanup_logs=false (preserve logs)
DISCOVERY_FVT_CLEANUP_E004: Deploy discovery.yml --tags cleanup \
    (idempotency test)
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_cleanup(_host):
    """DISCOVERY_FVT_CLEANUP_E001: Deploy discovery.yml --tags cleanup (full cleanup)."""
    tc = TC["deploy_cleanup"]
    tl = TestLogger(
        TEST_NAMES["deploy_cleanup"], tc["id"]
    )
    result = run_playbook(tag="cleanup")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="discovery.yml",
        rc=result["rc"], duration=result["duration"],
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_cleanup_preserve_credentials(_host):
    """DISCOVERY_FVT_CLEANUP_E002: Deploy discovery.yml --tags cleanup \
        -e cleanup_credentials=false (preserve credentials)."""
    tc = TC["deploy_cleanup_preserve_credentials"]
    tl = TestLogger(
        TEST_NAMES["deploy_cleanup_preserve_credentials"], tc["id"]
    )
    result = run_playbook(tag="cleanup", extra_vars="cleanup_credentials=false")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="discovery.yml",
        rc=result["rc"], duration=result["duration"],
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(2)
def test_deploy_cleanup_preserve_logs(_host):
    """DISCOVERY_FVT_CLEANUP_E003: Deploy discovery.yml --tags cleanup \
        -e cleanup_logs=false (preserve logs)."""
    tc = TC["deploy_cleanup_preserve_logs"]
    tl = TestLogger(
        TEST_NAMES["deploy_cleanup_preserve_logs"], tc["id"]
    )
    result = run_playbook(tag="cleanup", extra_vars="cleanup_logs=false")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="discovery.yml",
        rc=result["rc"], duration=result["duration"],
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(3)
def test_deploy_cleanup_idempotent(_host):
    """DISCOVERY_FVT_CLEANUP_E004: Deploy discovery.yml --tags cleanup \
        (idempotency test - run cleanup twice)."""
    tc = TC["deploy_cleanup_idempotent"]
    tl = TestLogger(
        TEST_NAMES["deploy_cleanup_idempotent"], tc["id"]
    )

    # First cleanup run
    result1 = run_playbook(tag="cleanup")

    # Second cleanup run (should be idempotent)
    result2 = run_playbook(tag="cleanup")

    if result1["success"] and result2["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result1["duration"] + result2["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result1["rc"] if not result1["success"] else result2["rc"],
                duration=result1["duration"] + result2["duration"],
            ),
            result1.get("error", "See playbook output above")
            if not result1["success"]
            else result2.get("error", "See playbook output above"),
        )

    assert result1["success"] and result2["success"], ASSERT["playbook_failed"].format(
        playbook="discovery.yml",
        rc=result1["rc"] if not result1["success"] else result2["rc"],
        duration=result1["duration"] + result2["duration"],
    )
