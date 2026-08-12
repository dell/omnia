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
Repo Manager Cleanup — Comprehensive Verification.

Validates that --tags cleanup_pulp removed all artifacts:
  TC_CL_002: Verify Pulp container removed
  TC_CL_003: Verify Pulp data directories removed
  TC_CL_004: Verify Pulp service removed
  TC_CL_005: Verify no containers remain (even stopped)
  TC_CL_006: Verify Pulp container image removed
  TC_CL_007: Verify Pulp quadlet/systemd file removed

References: src/repo_manager/playbooks/cleanup/cleanup_pulp.yml
            src/repo_manager/vars/cleanup_pulp_vars.yml
"""

import pytest

from library.functions import (
    TestLogger,
    check_pulp_removed,
    check_pulp_data_removed,
    check_services_removed,
    check_containers_removed,
    check_pulp_image_removed,
    check_pulp_quadlet_removed,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_pulp_removed(host):
    """TC_CL_002: Verify Pulp container removed after cleanup."""
    tc = TC["pulp_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_removed_ok"], result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_pulp_data_removed(host):
    """TC_CL_003: Verify Pulp data directories removed after cleanup."""
    tc = TC["pulp_data_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_data_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_data_removed_ok"], result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], ASSERT["cleanup_data_failed"].format(
        error=result["details"],
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_services_removed(host):
    """TC_CL_004: Verify Pulp service removed after cleanup."""
    tc = TC["services_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_services_removed(host)

    if result["success"]:
        tl.passed(LOG["services_removed_ok"], result["details"])
    else:
        tl.failed(
            LOG["services_inactive"].format(
                count=sum(1 for r in result["results"] if not r["removed"])
            ),
            result["details"],
        )

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(4)
def test_containers_removed(host):
    """TC_CL_005: Verify no containers remain after cleanup."""
    tc = TC["containers_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_containers_removed(host)

    if result["success"]:
        tl.passed(LOG["containers_removed_ok"], result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(5)
def test_pulp_image_removed(host):
    """TC_CL_006: Verify Pulp container image removed after cleanup."""
    tc = TC["pulp_image_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_image_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_image_removed_ok"], result["details"])
    else:
        tl.failed(LOG["pulp_image_still_exists"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(6)
def test_pulp_quadlet_removed(host):
    """TC_CL_007: Verify Pulp quadlet/systemd file removed after cleanup."""
    tc = TC["pulp_quadlet_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_pulp_quadlet_removed(host)

    if result["success"]:
        tl.passed(LOG["pulp_quadlet_removed_ok"], result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]
