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
Orchestrator Validate — Kubernetes Service Status.

TC_K8_001: Verify K8s is enabled in catalog
TC_K8_005: Verify kubelet service is running on all nodes
TC_K8_006: Verify container runtime (CRI-O) is running on all nodes
TC_K8_008: Verify Kubernetes API server is responding
TC_K8_009: Verify Kubernetes directories exist on nodes
TC_K8_010: Verify Kubernetes configuration files exist
TC_K8_011: Verify Kubernetes PKI certificates exist
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_kubelet_running,
    check_containerd_running,
    check_k8s_apiserver_responding,
    check_k8s_directories_exist,
    check_k8s_config_files_exist,
    check_k8s_pki_certs_exist,
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
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_k8s_enabled(host):
    """TC_K8_001: Verify Kubernetes is enabled in catalog."""
    tc = TC["k8s_enabled"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking catalog for Kubernetes functional groups")
    result = check_k8s_enabled(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["k8s_enabled_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_enabled_failed"], result["details"])

    assert result["success"], ASSERT["k8s_enabled_required"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_kubelet_running(host):
    """TC_K8_005: Verify kubelet service is running on all nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["kubelet_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking kubelet service status on all nodes")
    result = check_kubelet_running(host)

    if result["success"]:
        tl.passed(LOG["kubelet_check_ok"], result["details"])
    else:
        tl.failed(LOG["kubelet_check_failed"], result["error"])

    assert result["success"], ASSERT["kubelet_not_running"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_containerd_running(host):
    """TC_K8_006: Verify container runtime (CRI-O) is running on all nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["containerd_running"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking container runtime (CRI-O) status on all nodes")
    result = check_containerd_running(host)

    if result["success"]:
        tl.passed(LOG["containerd_check_ok"], result["details"])
    else:
        tl.failed(LOG["containerd_check_failed"], result["error"])

    assert result["success"], ASSERT["containerd_not_running"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(4)
def test_k8s_apiserver_responding(host):
    """TC_K8_008: Verify Kubernetes API server is responding."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_apiserver_responding"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes API server responsiveness")
    result = check_k8s_apiserver_responding(host)

    if result["success"]:
        tl.passed(LOG["apiserver_ok"], result["details"])
    else:
        tl.failed(LOG["apiserver_failed"], result["error"])

    assert result["success"], ASSERT["apiserver_not_responding"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(5)
def test_k8s_directories_exist(host):
    """TC_K8_009: Verify Kubernetes directories exist on nodes."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_directories_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes directories")
    result = check_k8s_directories_exist(host)

    if result["success"]:
        tl.passed(LOG["k8s_dirs_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_dirs_failed"], result["error"])

    assert result["success"], ASSERT["k8s_dirs_missing"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(6)
def test_k8s_config_files_exist(host):
    """TC_K8_010: Verify Kubernetes configuration files exist."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_config_files_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes configuration files")
    result = check_k8s_config_files_exist(host)

    if result["success"]:
        tl.passed(LOG["k8s_config_files_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_config_files_failed"], result["error"])

    assert result["success"], ASSERT["k8s_config_files_missing"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(7)
def test_k8s_pki_certs_exist(host):
    """TC_K8_011: Verify Kubernetes PKI certificates exist."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_pki_certs_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Kubernetes PKI certificates")
    result = check_k8s_pki_certs_exist(host)

    if result["success"]:
        tl.passed(LOG["k8s_pki_ok"], result["details"])
    else:
        tl.failed(LOG["k8s_pki_failed"], result["error"])

    assert result["success"], ASSERT["k8s_pki_missing"]
