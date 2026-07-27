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
omnia.sh --uninstall / Cleanup — Verification Tests.

Verifies that omnia.sh --uninstall completed successfully by checking
that all resources are properly cleaned up.

Test cases:
    TC_UT_002  Verify omnia_core container is removed
    TC_UT_003  Verify omnia_core.container file is removed
    TC_UT_004  Verify omnia_core.service is inactive
    TC_UT_005  Verify fstab entry is removed (NFS external)
    TC_UT_006  Verify NFS mount is removed (NFS external)
    TC_UT_007  Verify SSH key pair removed
    TC_UT_008  Verify SSH config entry removed
    TC_UT_009  Verify known_hosts entry cleaned

Usage:
    run_validation omnia_sh_uninstall verify
    run_validation omnia_sh_uninstall verify --suite cleanup
"""

import pytest

from main.library import (
    TestLogger,
    OMNIA_SH_VARS,
    TEST_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    SKIP_MSGS,
    run_on_oim,
    check_container_not_running,
    check_service_not_exists,
    check_fstab_entry_removed,
    check_mount_removed,
    check_ssh_key_pair_removed,
    check_ssh_config_entry_removed,
    check_known_hosts_cleaned,
)
from main.library.vars.common_vars import CMDS


# =============================================================================
# CLEANUP VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(1)
def test_container_removed(host):
    """TC_UT_002: Verify omnia_core container is removed after uninstall."""
    log = TestLogger("[TC_UT_002] " + TEST_NAMES["cleanup_container_removed"])

    result = check_container_not_running(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_container_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_container_still_running"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_container_file_removed(host):
    """TC_UT_003: Verify omnia_core.container file is removed."""
    log = TestLogger("[TC_UT_003] " + TEST_NAMES["cleanup_service_removed"])

    result = check_service_not_exists(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_service_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_service_exists"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(3)
def test_service_removed(host):
    """TC_UT_004: Verify omnia_core.service is inactive after uninstall."""
    log = TestLogger("[TC_UT_004] Verify omnia_core.service is inactive")
    service = TEST_VARS["service_name"]

    cmd = run_on_oim(host, CMDS["systemctl_is_active"].format(service=service))
    status = cmd.stdout.strip()

    if status in ("inactive", "unknown", ""):
        log.passed("Service is inactive", f"Service: {service}\nStatus: {status}")
    else:
        log.failed(
            f"Service still active: {status}",
            f"Service: {service}\nStatus: {status}"
        )

    assert status in ("inactive", "unknown", ""), (
        f"Service {service} is still {status} after uninstall"
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_fstab_entry_removed(host):
    """TC_UT_005: Verify fstab entry is removed (NFS external only)."""
    log = TestLogger("[TC_UT_005] " + TEST_NAMES["cleanup_fstab_removed"])

    if OMNIA_SH_VARS["share_option"] != "NFS" or OMNIA_SH_VARS["nfs_type"] != "external":
        log.skipped(SKIP_MSGS["not_nfs_external"])
        pytest.skip(SKIP_MSGS["not_nfs_external"])

    result = check_fstab_entry_removed(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_fstab_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_fstab_exists"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(5)
def test_mount_removed(host):
    """TC_UT_006: Verify NFS mount is removed (NFS external only)."""
    log = TestLogger("[TC_UT_006] " + TEST_NAMES["cleanup_mount_removed"])

    if OMNIA_SH_VARS["share_option"] != "NFS" or OMNIA_SH_VARS["nfs_type"] != "external":
        log.skipped(SKIP_MSGS["not_nfs_external"])
        pytest.skip(SKIP_MSGS["not_nfs_external"])

    result = check_mount_removed(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_mount_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_mount_exists"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(6)
def test_ssh_key_pair_removed(host):
    """TC_UT_007: Verify SSH key pair (oim_rsa) removed after uninstall."""
    log = TestLogger("[TC_UT_007] " + TEST_NAMES["cleanup_ssh_keys_removed"])

    result = check_ssh_key_pair_removed(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_ssh_keys_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_ssh_keys_exist"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(7)
def test_ssh_config_entry_removed(host):
    """TC_UT_008: Verify SSH config entry removed after uninstall."""
    log = TestLogger("[TC_UT_008] " + TEST_NAMES["cleanup_ssh_config_removed"])

    result = check_ssh_config_entry_removed(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_ssh_config_removed"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_ssh_config_exists"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(8)
def test_known_hosts_cleaned(host):
    """TC_UT_009: Verify known_hosts [localhost]:2222 entry cleaned."""
    log = TestLogger("[TC_UT_009] " + TEST_NAMES["cleanup_known_hosts_cleaned"])

    result = check_known_hosts_cleaned(host)

    if result["success"]:
        log.passed(LOG_MSGS["cleanup_known_hosts_cleaned"], result["details"])
    else:
        log.failed(LOG_MSGS["cleanup_known_hosts_exists"], result["error"])

    assert result["success"], result["error"]
