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

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    TestLogger,
    check_additional_cloud_init_bss_idempotency,
    check_additional_cloud_init_pipeline_idempotency,
    check_additional_cloud_init_smd_idempotency,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.additional_cloud_init,
    pytest.mark.non_disruptive,
    pytest.mark.idempotency,
]


@pytest.mark.order(40314)
def test_additional_cloud_init_smd_idempotency(host):
    """Verify SMD group creation is idempotent across re-reads."""
    tc = TC["additional_cloud_init_smd_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_smd_idempotency)


@pytest.mark.order(40315)
def test_additional_cloud_init_bss_idempotency(host):
    """Verify BSS registration is idempotent across re-reads."""
    tc = TC["additional_cloud_init_bss_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_bss_idempotency)


@pytest.mark.order(40316)
def test_additional_cloud_init_pipeline_idempotency(host):
    """Verify full additional cloud-init pipeline state is consistent."""
    tc = TC["additional_cloud_init_pipeline_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(
        test_log, tc, host, check_additional_cloud_init_pipeline_idempotency,
    )
