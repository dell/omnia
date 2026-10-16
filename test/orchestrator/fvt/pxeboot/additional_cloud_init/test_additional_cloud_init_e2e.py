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

"""End-to-end additional cloud-init node verification and package integration.

Covers:
- TC-F16 .. TC-F20: end-to-end provisioning scenarios
- TC-F21: package integration with additional cloud-init

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    TestLogger,
    check_additional_cloud_init_e2e_combined,
    check_additional_cloud_init_e2e_common_only,
    check_additional_cloud_init_e2e_mixed_directives,
    check_additional_cloud_init_e2e_multiple_fgs,
    check_additional_cloud_init_e2e_packages,
    check_additional_cloud_init_e2e_per_fg_only,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.additional_cloud_init,
    pytest.mark.non_disruptive,
]


# -- End-to-end node verification (TC-F16 .. TC-F20) --------------------


@pytest.mark.order(40316)
def test_additional_cloud_init_e2e_common_only(host):
    """Verify end-to-end cloud-init with common section only."""
    tc = TC["additional_cloud_init_e2e_common_only"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_e2e_common_only)


@pytest.mark.order(40317)
def test_additional_cloud_init_e2e_per_fg_only(host):
    """Verify end-to-end cloud-init with per-FG section only."""
    tc = TC["additional_cloud_init_e2e_per_fg_only"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_e2e_per_fg_only)


@pytest.mark.order(40318)
def test_additional_cloud_init_e2e_combined(host):
    """Verify end-to-end cloud-init with common + per-FG combined."""
    tc = TC["additional_cloud_init_e2e_combined"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_e2e_combined)


@pytest.mark.order(40319)
def test_additional_cloud_init_e2e_multiple_fgs(host):
    """Verify end-to-end cloud-init with multiple functional groups."""
    tc = TC["additional_cloud_init_e2e_multiple_fgs"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_e2e_multiple_fgs)


@pytest.mark.order(40320)
def test_additional_cloud_init_e2e_mixed_directives(host):
    """Verify end-to-end cloud-init with mixed write_files and runcmd."""
    tc = TC["additional_cloud_init_e2e_mixed_directives"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(
        test_log, tc, host, check_additional_cloud_init_e2e_mixed_directives,
    )


# -- Package integration (TC-F21) ---------------------------------------


@pytest.mark.order(40321)
def test_additional_cloud_init_e2e_packages(host):
    """Verify additional cloud-init integration with additional packages."""
    tc = TC["additional_cloud_init_e2e_packages"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_e2e_packages)
