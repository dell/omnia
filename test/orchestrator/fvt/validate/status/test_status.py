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
Orchestrator Validate — Input Verification Tests.

TC_VL_001: Verify orchestrator_config.yml exists on target
TC_VL_002: Verify omnia_config.yml exists on target
TC_VL_003: Verify network_spec.yml exists on target
TC_VL_004: Verify credentials file present on target
TC_VL_005: Verify repo_status.yml exists on target
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_omnia_config_exists,
    check_network_spec_exists,
    check_credentials_present,
    check_repo_status_exists,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_input_config_exists(host):
    """TC_VL_001: Verify orchestrator_config.yml exists on target."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_VL_001")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG["input_config_ok"], result["details"])
    else:
        tl.failed(LOG["input_config_missing"], result["details"])

    assert result["success"], ASSERT["input_config_missing"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_omnia_config_exists(host):
    """TC_VL_002: Verify omnia_config.yml exists on target."""
    tl = TestLogger(TEST_NAMES["omnia_config_exists"], "TC_VL_002")
    result = check_omnia_config_exists(host)

    if result["success"]:
        tl.passed(LOG["omnia_config_ok"], result["details"])
    else:
        tl.failed(LOG["omnia_config_missing"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(3)
def test_network_spec_exists(host):
    """TC_VL_003: Verify network_spec.yml exists on target."""
    tl = TestLogger(TEST_NAMES["network_spec_exists"], "TC_VL_003")
    result = check_network_spec_exists(host)

    if result["success"]:
        tl.passed(LOG["network_spec_ok"], result["details"])
    else:
        tl.failed(LOG["network_spec_missing"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(4)
def test_credentials_present(host):
    """TC_VL_004: Verify credentials file present on target."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_VL_004")
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed(LOG["credentials_present_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_missing"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(5)
def test_repo_status_exists(host):
    """TC_VL_005: Verify repo_status.yml exists on target."""
    tl = TestLogger(TEST_NAMES["repo_status_exists"], "TC_VL_005")
    result = check_repo_status_exists(host)

    if result["success"]:
        tl.passed(LOG["repo_status_ok"], result["details"])
    else:
        tl.failed(LOG["repo_status_missing"], result["details"])

    assert result["success"], ASSERT["repo_status_missing"]
