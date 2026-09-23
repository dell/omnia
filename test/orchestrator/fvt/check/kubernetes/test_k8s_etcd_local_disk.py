# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may use this file except in compliance with the License.
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
Orchestrator Validate — etcd Local Disk Verification.

TC_K8_057: Verify etcd_on_local_disk is enabled in omnia_config.yml
TC_K8_058: Verify Dell BOSS card detection via PCI scan
TC_K8_059: Verify disk partitioning for etcd data
TC_K8_057: Verify filesystem creation on etcd partition
TC_K8_058: Verify UUID-based fstab entry and active mount for /var/lib/etcd
TC_K8_059: Verify etcd configuration to use local disk (not NFS)
TC_K8_060: Verify fallback disk detection (non-BOSS disk)
TC_K8_061: Verify first boot disk setup (etcd-disk-setup.sh)
TC_K8_062: Verify SSD disk support for etcd
TC_K8_063: Verify HDD disk support for etcd
TC_K8_064: Verify NVMe disk support for etcd
"""

import pytest

from library.functions import TestLogger
from library.functions.k8s_func import (
    check_k8s_enabled,
    check_etcd_on_local_disk_enabled,
    check_k8s_etcd_boss_card_detection,
    check_k8s_etcd_disk_partitioning,
    check_k8s_etcd_filesystem_creation,
    check_k8s_etcd_fstab_and_mount,
    check_k8s_etcd_local_disk_config,
    check_k8s_etcd_fallback_disk_detection,
    check_k8s_etcd_first_boot_setup,
    check_k8s_etcd_ssd_disk_support,
    check_k8s_etcd_hdd_disk_support,
    check_k8s_etcd_nvme_disk_support,
)
from library.vars.k8s_vars import TEST_CASES as TC


def _skip_if_k8s_disabled(host):
    """Skip test if Kubernetes is not enabled in catalog."""
    result = check_k8s_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


def _skip_if_etcd_local_disk_disabled(host):
    """Skip test if etcd_on_local_disk is not enabled in omnia_config.yml."""
    result = check_etcd_on_local_disk_enabled(host)
    if not result.get("enabled"):
        pytest.skip(f"etcd_on_local_disk is not enabled: {result['details']}")


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(1)
def test_k8s_etcd_local_disk_enabled(host):
    """TC_K8_054: Verify etcd_on_local_disk is enabled in omnia_config.yml."""
    _skip_if_k8s_disabled(host)

    tc = TC.get("k8s_etcd_local_disk_enabled", {
        "id": "TC_K8_057",
        "title": "Verify etcd_on_local_disk is enabled in omnia_config.yml"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking if etcd_on_local_disk is enabled in omnia_config.yml")
    result = check_etcd_on_local_disk_enabled(host)

    if result["enabled"]:
        tl.passed("etcd_on_local_disk is enabled", result["details"])
    else:
        tl.skipped("etcd_on_local_disk is disabled - skipping etcd local disk tests", result["details"])
        pytest.skip("etcd_on_local_disk is not enabled in omnia_config.yml")


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(2)
def test_k8s_etcd_boss_card_detection(host):
    """TC_K8_055: Verify Dell BOSS card detection via PCI scan on control plane nodes."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_boss_card_detection", {
        "id": "TC_K8_058",
        "title": "Verify Dell BOSS card detection"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying Dell BOSS card detection via PCI scan")
    result = check_k8s_etcd_boss_card_detection(host)

    if result["success"]:
        if result.get("boss_detected"):
            tl.passed("BOSS card detected on control plane nodes", result["details"])
        else:
            tl.skipped("BOSS card not detected on all nodes - fallback disk may be in use", result["details"])
            pytest.skip("BOSS card not available in test environment - verify with TC_K8_060 fallback disk detection")
    else:
        tl.failed("BOSS card detection check failed", result["error"])

    assert result["success"], result["error"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(3)
def test_k8s_etcd_disk_partitioning(host):
    """TC_K8_056: Verify disk partitioning for etcd data."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_disk_partitioning", {
        "id": "TC_K8_056",
        "title": "Verify disk partitioning for etcd"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying GPT partition exists for etcd data and root disk is excluded")
    result = check_k8s_etcd_disk_partitioning(host)

    if result["success"]:
        if result.get("partition_exists"):
            tl.passed("Etcd partition found on control plane nodes", result["details"])
        else:
            tl.failed("Etcd partition not found on control plane nodes", result["details"])
    else:
        tl.failed("Disk partitioning check failed", result["error"])

    assert result["success"] and result.get("partition_exists"), result.get("error", result.get("details"))


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(4)
def test_k8s_etcd_filesystem_creation(host):
    """TC_K8_057: Verify filesystem creation on etcd partition."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_filesystem_creation", {
        "id": "TC_K8_057",
        "title": "Verify filesystem creation on etcd partition"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying ext4 filesystem on etcd partition")
    result = check_k8s_etcd_filesystem_creation(host)

    if result["success"]:
        if result.get("filesystem_valid"):
            tl.passed("Ext4 filesystem found on etcd partition", result["details"])
        else:
            tl.failed("Ext4 filesystem not found on etcd partition", result["details"])
    else:
        tl.failed("Filesystem creation check failed", result["error"])

    assert result["success"] and result.get("filesystem_valid"), result.get("error", result.get("details"))


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(5)
def test_k8s_etcd_fstab_and_mount(host):
    """TC_K8_058: Verify UUID-based fstab entry and active mount for /var/lib/etcd."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_fstab_and_mount", {
        "id": "TC_K8_058",
        "title": "Verify fstab and mount for etcd"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying UUID-based fstab entry and active mount for /var/lib/etcd")
    result = check_k8s_etcd_fstab_and_mount(host)

    if result["success"]:
        if result.get("fstab_entry_exists") and result.get("mount_active"):
            # Also verify mount is not NFS
            local_disk_result = check_k8s_etcd_local_disk_config(host)
            if local_disk_result.get("using_local_disk"):
                tl.passed("fstab entry exists and mount is active (local disk)", result["details"])
            else:
                tl.failed("fstab entry exists and mount is active but using NFS instead of local disk", local_disk_result["details"])
        else:
            tl.failed("fstab entry or mount issue", result["details"])
    else:
        tl.failed("fstab and mount check failed", result["error"])

    assert result["success"] and result.get("fstab_entry_exists") and result.get("mount_active"), result.get("error", result.get("details"))


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(6)
def test_k8s_etcd_local_disk_config(host):
    """TC_K8_059: Verify etcd configuration to use local disk."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_local_disk_config", {
        "id": "TC_K8_059",
        "title": "Verify etcd configuration to use local disk"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying etcd uses local disk at /var/lib/etcd (not NFS)")
    result = check_k8s_etcd_local_disk_config(host)

    if result["success"]:
        if result.get("using_local_disk"):
            tl.passed("etcd is using local disk", result["details"])
        else:
            tl.failed("etcd is not using local disk", result["details"])
    else:
        tl.failed("Local disk configuration check failed", result["error"])

    assert result["success"] and result.get("using_local_disk"), result.get("error", result.get("details"))


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(7)
def test_k8s_etcd_fallback_disk_detection(host):
    """TC_K8_060: Verify fallback disk detection (non-BOSS disk)."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_fallback_disk_detection", {
        "id": "TC_K8_060",
        "title": "Verify fallback disk detection"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying fallback disk detection (non-BOSS disk)")
    result = check_k8s_etcd_fallback_disk_detection(host)

    if result["success"]:
        if result.get("fallback_disk_detected"):
            tl.passed("Fallback disk detected", result["details"])
        else:
            tl.skipped("Using primary disk (BOSS card detected)", result["details"])
            pytest.skip("Using primary disk (BOSS card detected)")
    else:
        tl.failed("Fallback disk detection check failed", result["error"])

    assert result["success"], result["error"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(8)
def test_k8s_etcd_first_boot_setup(host):
    """TC_K8_061: Verify first boot disk setup (etcd-disk-setup.sh)."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_first_boot_setup", {
        "id": "TC_K8_061",
        "title": "Verify first boot disk setup (etcd-disk-setup.sh)"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying etcd-disk-setup.sh script exists and executed successfully")
    result = check_k8s_etcd_first_boot_setup(host)

    if result["success"]:
        if result.get("script_exists") and result.get("script_executed"):
            tl.passed("etcd-disk-setup.sh script exists and was executed on control plane nodes", result["details"])
        else:
            tl.failed("etcd-disk-setup.sh script or log missing on control plane nodes", result["details"])
    else:
        tl.failed("First boot setup check failed", result["error"])

    assert result["success"] and result.get("script_exists") and result.get("script_executed"), result.get("error", result.get("details"))


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(9)
def test_k8s_etcd_ssd_disk_support(host):
    """TC_K8_062: Verify SSD disk support for etcd."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_ssd_disk_support", {
        "id": "TC_K8_062",
        "title": "Verify SSD disk support for etcd"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying SSD disk used for etcd on control plane nodes")
    result = check_k8s_etcd_ssd_disk_support(host)

    if result["success"]:
        if result.get("ssd_detected"):
            tl.passed("SSD disk used for etcd on control plane nodes", result["details"])
        else:
            tl.skipped("SSD disk not used for etcd on any control plane node", result["details"])
            pytest.skip("SSD disk not available for etcd on control plane nodes")
    else:
        tl.failed("SSD disk support check failed", result["error"])

    assert result["success"], result["error"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(10)
def test_k8s_etcd_hdd_disk_support(host):
    """TC_K8_063: Verify HDD disk support for etcd."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_hdd_disk_support", {
        "id": "TC_K8_063",
        "title": "Verify HDD disk support for etcd"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying HDD disk used for etcd on control plane nodes")
    result = check_k8s_etcd_hdd_disk_support(host)

    if result["success"]:
        if result.get("hdd_detected"):
            tl.passed("HDD disk used for etcd on control plane nodes", result["details"])
        else:
            tl.skipped("HDD disk not used for etcd on any control plane node", result["details"])
            pytest.skip("HDD disk not available for etcd on control plane nodes")
    else:
        tl.failed("HDD disk support check failed", result["error"])

    assert result["success"], result["error"]


@pytest.mark.kubernetes
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(11)
def test_k8s_etcd_nvme_disk_support(host):
    """TC_K8_064: Verify NVMe disk support for etcd."""
    _skip_if_k8s_disabled(host)
    _skip_if_etcd_local_disk_disabled(host)

    tc = TC.get("k8s_etcd_nvme_disk_support", {
        "id": "TC_K8_064",
        "title": "Verify NVMe disk support for etcd"
    })
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Verifying NVMe disk used for etcd on control plane nodes")
    result = check_k8s_etcd_nvme_disk_support(host)

    if result["success"]:
        if result.get("nvme_detected"):
            tl.passed("NVMe disk used for etcd on control plane nodes", result["details"])
        else:
            tl.skipped("NVMe disk not used for etcd on any control plane node", result["details"])
            pytest.skip("NVMe disk not available for etcd on control plane nodes")
    else:
        tl.failed("NVMe disk support check failed", result["error"])

    assert result["success"], result["error"]