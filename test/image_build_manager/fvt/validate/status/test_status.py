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
  Verify image_build_config.yml exists on target
  Verify credentials file is present on target
"""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_credentials_present,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG


@pytest.mark.sanity
@pytest.mark.order(1)
def test_input_config_exists(host):
    """Verify image_build_config.yml exists on target."""
    tc = TC["input_config_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_input_config_exists(host)

    if result["success"]:
        tl.passed(LOG["input_config_ok"], result["details"])
    else:
        tl.failed(LOG["input_config_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_credentials_present(host):
    """Verify credentials file present on target."""
    tc = TC["credentials_present_vl"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_credentials_present(host)

    if result["success"]:
        tl.passed(LOG["credentials_present_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_missing"], result["details"])

    assert result["success"], result["details"]
