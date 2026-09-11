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
Orchestrator Validate — etcd Detailed Verification.

TC_K8_037: Verify etcd cluster endpoint health via etcdctl
TC_K8_038: Verify etcd member list matches control plane count
TC_K8_039: Verify etcd leader identification and RAFT consistency
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_etcd_health_detailed,
    check_k8s_etcd_member_list,
    check_k8s_etcd_leader_consistency,
)
from library.messages import (
    K8S_TEST_LOG_MSGS as LOG,
    K8S_TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.k8s_vars import TEST_CASES as TC


def _skip_if_k8s_disabled(host):
    """Skip test if Kubernetes is not enabled in catalog."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_k8s_etcd_health_detailed(host):
    """TC_K8_037: Verify etcd cluster endpoint health via etcdctl."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_etcd_health_detailed"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Running etcdctl endpoint health on each etcd pod")
    result = check_k8s_etcd_health_detailed(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["etcd_health_detailed_ok"], result["details"])
    else:
        tl.failed(LOG["etcd_health_detailed_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["etcd_health_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_k8s_etcd_member_list(host):
    """TC_K8_038: Verify etcd member list matches control plane count."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_etcd_member_list"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking etcd member list against expected CP count")
    result = check_k8s_etcd_member_list(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["etcd_member_list_ok"].format(count=result.get("member_count", 0)),
            result["details"],
        )
    else:
        tl.failed(LOG["etcd_member_list_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["etcd_member_list_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_k8s_etcd_leader_consistency(host):
    """TC_K8_039: Verify etcd leader identification and RAFT consistency."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_etcd_leader_consistency"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking etcd leader and RAFT term consistency")
    result = check_k8s_etcd_leader_consistency(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["etcd_leader_ok"], result["details"])
    else:
        tl.failed(LOG["etcd_leader_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["etcd_leader_failed"]
