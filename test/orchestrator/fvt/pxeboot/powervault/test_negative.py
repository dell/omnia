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

"""PowerVault negative test cases for error handling and edge conditions."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    TestLogger,
    check_powervault_gpt_missing_label,
    check_powervault_duplicate_fstab_detection,
)
from library.vars import TEST_CASES as TC


@pytest.mark.negative
@pytest.mark.order(330)
def test_neg_powervault_gpt_missing_label(host):
    """Verify GPT partition check correctly detects missing GPT label.

    This negative test validates that the check properly rejects devices
    without a valid GPT partition table, ensuring proper error detection
    for incorrectly formatted PowerVault volumes.
    """
    tc = TC["powervault_gpt_missing_label"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_gpt_missing_label)


@pytest.mark.negative
@pytest.mark.order(331)
def test_neg_powervault_duplicate_fstab(host):
    """Verify duplicate fstab entry detection works correctly.

    This negative test validates that the check correctly identifies
    duplicate fstab entries, ensuring proper error detection for
    misconfigured persistent mount configurations.
    """
    tc = TC["powervault_duplicate_fstab"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_powervault_duplicate_fstab_detection)
