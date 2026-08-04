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
Repo Manager Validate — Input Validation Verification.

Validates that --tags validate checked the input configuration:
  TC_VL_002: Verify repo_manager_config.yml exists on target
  TC_VL_003: Verify credentials file is present
  TC_VL_004: Verify endpoint config exists
  TC_VL_005: Verify software_config.json exists
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_credentials_present,
    check_endpoint_config_exists,
    check_software_config_exists,
)
from library.messages import TEST_NAMES, LOG_MSGS


@pytest.mark.sanity
@pytest.mark.order(1)
def test_input_config_exists(host):
    """TC_VL_002: Verify repo_manager_config.yml exists on target."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_VL_002")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG_MSGS["input_config_ok"], result["details"])
    else:
        tl.failed(LOG_MSGS["input_config_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_credentials_present(host):
    """TC_VL_003: Verify credentials file present."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_VL_003")
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed(LOG_MSGS["credentials_present_ok"], result["details"])
    else:
        tl.failed(LOG_MSGS["credentials_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(3)
def test_endpoint_config_exists(host):
    """TC_VL_004: Verify endpoint config exists."""
    tl = TestLogger(TEST_NAMES["endpoint_config_exists"], "TC_VL_004")
    result = check_endpoint_config_exists(host)

    if result["success"]:
        tl.passed(LOG_MSGS["endpoint_config_ok"], result["details"])
    else:
        tl.failed(LOG_MSGS["endpoint_config_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(4)
def test_software_config_exists(host):
    """TC_VL_005: Verify software_config.json exists."""
    tl = TestLogger(TEST_NAMES["software_config_exists"], "TC_VL_005")
    result = check_software_config_exists(host)

    if result["success"]:
        tl.passed(LOG_MSGS["software_config_ok"], result["details"])
    else:
        tl.failed(LOG_MSGS["software_config_missing"], result["details"])

    assert result["success"], result["details"]
