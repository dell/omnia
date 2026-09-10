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
Orchestrator Validate — Kubernetes Configuration Validation.

TC_K8_015: Verify K8s NFS configuration directory exists
TC_K8_024: Verify K8s functional groups registered in SMD
TC_K8_025: Verify K8s metadata-service configuration exists
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_nfs_config_exists,
    check_k8s_smd_groups,
    check_k8s_metadata_configured,
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
@pytest.mark.order(1)
def test_k8s_nfs_config_exists(host):
    """TC_K8_015: Verify K8s NFS configuration directory exists."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_nfs_config_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes NFS configuration directory")
    result = check_k8s_nfs_config_exists(host)

    if result["success"]:
        tl.passed(LOG["k8s_nfs_config_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_nfs_config_failed"], result["error"])

    assert result["success"], ASSERT["k8s_nfs_config_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(2)
def test_k8s_smd_groups(host):
    """TC_K8_024: Verify K8s functional groups registered in SMD."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_smd_groups_registered"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes functional groups in SMD")
    result = check_k8s_smd_groups(host)

    if result["success"]:
        tl.passed(LOG["smd_groups_ok"], result["details"])
    else:
        tl.failed(LOG["smd_groups_failed"], result["error"])

    assert result["success"], ASSERT["smd_groups_missing"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.order(3)
def test_k8s_metadata_configured(host):
    """TC_K8_025: Verify K8s metadata-service configuration exists."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_metadata_configured"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes metadata-service configuration")
    result = check_k8s_metadata_configured(host)

    if result["success"]:
        tl.passed(LOG["metadata_ok"], result["details"])
    else:
        tl.failed(LOG["metadata_failed"], result["error"])

    assert result["success"], ASSERT["k8s_metadata_failed"]
