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
Orchestrator Prepare — OpenCHAMI Verification Tests.

TC_PR_001: Verify all OpenCHAMI containers are running
TC_PR_002: Verify OpenCHAMI systemd services are active
TC_PR_003: Verify OpenCHAMI API is reachable
"""

import pytest

from library.functions import (
    TestLogger,
    check_openchami_containers,
    check_services_active,
    check_openchami_api_reachable,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_openchami_containers_running(host):
    """TC_PR_001: Verify all OpenCHAMI containers are running."""
    tl = TestLogger(
        TEST_NAMES["openchami_container_running"].format(
            container="all"
        ),
        "TC_PR_001",
    )
    result = check_openchami_containers(host)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(container="all OpenCHAMI"),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(container="OpenCHAMI"),
            result["details"],
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container="OpenCHAMI", status=result.get("error", "unknown"),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_openchami_services_active(host):
    """TC_PR_002: Verify OpenCHAMI systemd services are active."""
    tl = TestLogger(TEST_NAMES["openchami_services_active"], "TC_PR_002")
    result = check_services_active(host)

    if result["success"]:
        tl.passed(LOG["services_active_ok"], result["details"])
    else:
        tl.failed(
            LOG["services_inactive"].format(count=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(3)
def test_openchami_api_reachable(host):
    """TC_PR_003: Verify OpenCHAMI API is reachable."""
    tl = TestLogger(TEST_NAMES["openchami_api_reachable"], "TC_PR_003")
    result = check_openchami_api_reachable(host)

    if result["success"]:
        tl.passed(LOG["api_reachable_ok"], result["details"])
    else:
        tl.failed(LOG["api_not_reachable"], result["details"])

    assert result["success"], result["error"]
