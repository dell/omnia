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
Orchestrator Validate — Kubernetes Storage & CSI.

TC_K8_044: Verify NFS client provisioner pod is running
TC_K8_045: Verify snapshot-controller pods are running
TC_K8_046: Verify Isilon CSI driver pods are running
TC_K8_047: Verify default storage class is set correctly
TC_K8_048: Verify Persistent Volumes are Bound with correct storage class
TC_K8_049: Verify NFS StorageClass is dynamic and properly configured
TC_K8_050: Verify telemetry PVCs are Bound with correct PV and size
TC_K8_051: Deploy and verify basic BusyBox pod
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_k8s_nfs_provisioner_pod,
    check_k8s_snapshot_controller_pods,
    check_k8s_isilon_csi_pods,
    check_k8s_default_storage_class,
    check_k8s_persistent_volumes,
    check_k8s_nfs_storage_class,
    check_k8s_telemetry_pvcs,
    check_k8s_busybox_pod,
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
def test_k8s_nfs_provisioner_pod(host):
    """TC_K8_044: Verify NFS client provisioner pod is running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_nfs_provisioner_pod"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking NFS client provisioner pod")
    result = check_k8s_nfs_provisioner_pod(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["nfs_provisioner_ok"], result["details"])
    else:
        tl.failed(LOG["nfs_provisioner_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["nfs_provisioner_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_k8s_snapshot_controller_pods(host):
    """TC_K8_045: Verify snapshot-controller pods are running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_snapshot_controller_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking snapshot-controller pods (PowerScale CSI dependent)")
    result = check_k8s_snapshot_controller_pods(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["snapshot_controller_ok"], result["details"])
    else:
        tl.failed(LOG["snapshot_controller_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT.get("snapshot_controller_failed", "Snapshot controller pods not running")


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_k8s_isilon_csi_pods(host):
    """TC_K8_046: Verify Isilon CSI driver pods are running."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_isilon_csi_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Isilon CSI driver pods (PowerScale CSI dependent)")
    result = check_k8s_isilon_csi_pods(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["isilon_csi_ok"], result["details"])
    else:
        tl.failed(LOG["isilon_csi_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT.get("isilon_csi_failed", "Isilon CSI driver pods not running")


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(4)
def test_k8s_default_storage_class(host):
    """TC_K8_047: Verify default storage class is set correctly."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_default_storage_class"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking default StorageClass")
    result = check_k8s_default_storage_class(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["default_sc_ok"].format(sc=result.get("expected_sc", "")),
            result["details"],
        )
    else:
        tl.failed(LOG["default_sc_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["default_sc_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(5)
def test_k8s_persistent_volumes(host):
    """TC_K8_048: Verify Persistent Volumes are Bound with correct storage class."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_persistent_volumes"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking Persistent Volume status")
    result = check_k8s_persistent_volumes(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["persistent_volumes_ok"], result["details"])
    else:
        tl.failed(LOG["persistent_volumes_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["persistent_volumes_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(6)
def test_k8s_nfs_storage_class(host):
    """TC_K8_049: Verify NFS StorageClass is dynamic and properly configured."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_nfs_storage_class"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Validating NFS StorageClass configuration")
    result = check_k8s_nfs_storage_class(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["nfs_sc_ok"], result["details"])
    else:
        tl.failed(LOG["nfs_sc_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["nfs_sc_failed"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(7)
def test_k8s_telemetry_pvcs(host):
    """TC_K8_050: Verify telemetry PVCs are Bound with correct PV and size."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_telemetry_pvcs"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking telemetry PVCs in telemetry namespace")
    result = check_k8s_telemetry_pvcs(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["telemetry_pvcs_ok"], result["details"])
    else:
        tl.failed(LOG["telemetry_pvcs_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["telemetry_pvcs_failed"]


@pytest.mark.kubernetes
@pytest.mark.functional
@pytest.mark.order(8)
def test_k8s_busybox_pod(host):
    """TC_K8_051: Deploy and verify basic BusyBox pod."""
    _skip_if_k8s_disabled(host)

    tc = TC["k8s_busybox_pod"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Deploying BusyBox test pod")
    result = check_k8s_busybox_pod(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["busybox_pod_ok"], result["details"])
    else:
        tl.failed(LOG["busybox_pod_failed"].format(error=result["error"]), result["error"])

    assert result["success"], ASSERT["busybox_pod_failed"]
