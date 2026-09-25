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

"""Fresh boot and authoritative cloud-init verification."""

import pytest
from library.functions import TestLogger, check_node_cloud_init
from library.messages import PXEBOOT_TEST_ASSERT_MSGS as ASSERT
from library.messages import PXEBOOT_TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.sanity
@pytest.mark.cloudinit
@pytest.mark.order(204)
def test_node_cloud_init(host):
    """Verify PXE report freshness and direct cloud-init JSON state."""
    tc = TC["node_cloud_init"]
    test_log = TestLogger(tc["title"], tc["id"])
    result = check_node_cloud_init(host)
    fields = result["details"]["fields"]
    if result["success"]:
        test_log.passed_fields(
            LOG["check_passed"].format(component=tc["component"]), fields
        )
    else:
        test_log.failed_fields(
            LOG["check_failed"].format(component=tc["component"]),
            [*fields, ("Error", result["error"])],
        )
    assert result["success"], ASSERT["verification_failed"].format(
        component=tc["component"], error=result["error"]
    )
