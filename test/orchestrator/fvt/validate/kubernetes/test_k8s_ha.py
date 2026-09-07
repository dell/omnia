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
Orchestrator Validate — Kubernetes HA / Virtual IP.

TC_K8_040: Verify VIP is configured on exactly one control plane
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_virtual_ip,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.k8s_vars import TEST_CASES as TC


def _skip_if_k8s_disabled(host):
    """Skip test if Kubernetes is not enabled in catalog."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(1)
def test_k8s_virtual_ip(host):
    """TC_K8_040: Verify VIP is configured on exactly one control plane."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_virtual_ip"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking HA virtual IP configuration across control planes")
    result = check_k8s_virtual_ip(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        nodes_with_vip = result.get("nodes_with_vip", [])
        tl.passed(
            LOG["vip_ok"].format(node=nodes_with_vip[0] if nodes_with_vip else "unknown"),
            result["details"],
        )
    else:
        tl.failed(LOG["vip_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["vip_failed"]
