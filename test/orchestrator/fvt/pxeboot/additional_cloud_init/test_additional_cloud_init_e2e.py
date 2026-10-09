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

"""Additional cloud-init end-to-end node verification.

Covers 2.2 baseline gaps TC-F16 .. TC-F21:
- TC-F16: End-to-end common only
- TC-F17: End-to-end per-FG only
- TC-F18: End-to-end common + per-FG combined
- TC-F19: End-to-end multiple functional groups
- TC-F20: End-to-end mixed directives (write_files + runcmd)
- TC-F21: Integration with additional packages

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    check_additional_cloud_init_e2e_combined,
    check_additional_cloud_init_e2e_common_only,
    check_additional_cloud_init_e2e_mixed_directives,
    check_additional_cloud_init_e2e_multiple_fgs,
    check_additional_cloud_init_e2e_packages,
    check_additional_cloud_init_e2e_per_fg_only,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.additional_cloud_init,
    pytest.mark.non_disruptive,
]


# -- End-to-end node verification (TC-F16 .. TC-F20) --------------------


@pytest.mark.order(342)
def test_additional_cloud_init_e2e_common_only(host):
    """Verify end-to-end cloud-init with common section only."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_common_only",
        check_additional_cloud_init_e2e_common_only,
    )


@pytest.mark.order(343)
def test_additional_cloud_init_e2e_per_fg_only(host):
    """Verify end-to-end cloud-init with per-FG section only."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_per_fg_only",
        check_additional_cloud_init_e2e_per_fg_only,
    )


@pytest.mark.order(344)
def test_additional_cloud_init_e2e_combined(host):
    """Verify end-to-end cloud-init with common + per-FG combined."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_combined",
        check_additional_cloud_init_e2e_combined,
    )


@pytest.mark.order(345)
def test_additional_cloud_init_e2e_multiple_fgs(host):
    """Verify end-to-end cloud-init with multiple functional groups."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_multiple_fgs",
        check_additional_cloud_init_e2e_multiple_fgs,
    )


@pytest.mark.order(346)
def test_additional_cloud_init_e2e_mixed_directives(host):
    """Verify end-to-end cloud-init with mixed write_files and runcmd."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_mixed_directives",
        check_additional_cloud_init_e2e_mixed_directives,
    )


# -- Package integration (TC-F21) ---------------------------------------


@pytest.mark.order(347)
def test_additional_cloud_init_e2e_packages(host):
    """Verify additional cloud-init integration with additional packages."""
    verify_pxeboot(
        host,
        "additional_cloud_init_e2e_packages",
        check_additional_cloud_init_e2e_packages,
    )
