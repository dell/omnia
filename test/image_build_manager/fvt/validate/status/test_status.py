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
Image Build Validate — Input Validation Verification.

Validates that --tags validate checked the input configuration:
  TC_VL_002: Verify image_build_config.yml exists on target
  TC_VL_003: Verify credentials file is present on target
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_credentials_present,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_input_config_exists(host):
    """TC_VL_002: Verify image_build_config.yml exists on target."""
    tl = TestLogger(TEST_NAMES["input_config_exists"], "TC_VL_002")
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG["input_config_ok"], result["details"])
    else:
        tl.failed(LOG["input_config_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_credentials_present(host):
    """TC_VL_003: Verify credentials file present on target."""
    tl = TestLogger(TEST_NAMES["credentials_present"], "TC_VL_003")
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed(LOG["credentials_present_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_missing"], result["details"])

    assert result["success"], result["details"]
