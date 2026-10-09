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

"""Additional cloud-init idempotency verification.

Covers 2.2 baseline gaps TC-I01 .. TC-I03:
- SMD group creation is stable across re-reads
- BSS registration is stable across re-reads
- Full pipeline (SMD + BSS) state is consistent

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    check_additional_cloud_init_bss_idempotency,
    check_additional_cloud_init_pipeline_idempotency,
    check_additional_cloud_init_smd_idempotency,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.additional_cloud_init,
    pytest.mark.non_disruptive,
    pytest.mark.idempotency,
]


@pytest.mark.order(339)
def test_additional_cloud_init_smd_idempotency(host):
    """Verify SMD group creation is idempotent across re-reads."""
    verify_pxeboot(
        host,
        "additional_cloud_init_smd_idempotency",
        check_additional_cloud_init_smd_idempotency,
    )


@pytest.mark.order(340)
def test_additional_cloud_init_bss_idempotency(host):
    """Verify BSS registration is idempotent across re-reads."""
    verify_pxeboot(
        host,
        "additional_cloud_init_bss_idempotency",
        check_additional_cloud_init_bss_idempotency,
    )


@pytest.mark.order(341)
def test_additional_cloud_init_pipeline_idempotency(host):
    """Verify full additional cloud-init pipeline state is consistent."""
    verify_pxeboot(
        host,
        "additional_cloud_init_pipeline_idempotency",
        check_additional_cloud_init_pipeline_idempotency,
    )
