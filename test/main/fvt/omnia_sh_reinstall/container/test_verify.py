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
omnia.sh --reinstall / Container — Verification Tests.

Verifies that omnia.sh reinstall (overwrite) completed successfully by
checking the container, service, SSH, and metadata state.  These are the
same checks applied after a fresh install, confirming the overwrite path
leaves the system in a healthy state.

Test cases:
    TC_RV_001  Verify omnia_core container is running after reinstall
    TC_RV_002  Verify omnia_core.container file exists after reinstall
    TC_RV_003  Verify omnia_core service is running after reinstall
    TC_RV_004  Verify oim_metadata.yml exists after reinstall
    TC_RV_005  Verify SSH key pair exists after reinstall
    TC_RV_006  Verify SSH config entry after reinstall
    TC_RV_007  Verify authorized_keys entry after reinstall
    TC_RV_008  Verify omnia_core container image after reinstall
    TC_RV_009  Verify /omnia/ directory inside container after reinstall
    TC_RV_010  Verify log directories after reinstall
    TC_RV_011  Verify omnia.sh --version after reinstall

Usage:
    run_validation omnia_sh_reinstall verify
    run_validation omnia_sh_reinstall verify --suite container
"""

import pytest

from main.library import (
    TestLogger,
    TEST_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
    check_container_running,
    check_file_exists,
    check_service_running,
    check_metadata_file,
    check_ssh_key_pair_exists,
    check_ssh_config_entry,
    check_authorized_key,
    check_container_image_exists,
    check_omnia_dir_in_container,
    check_log_dirs_exist,
    check_omnia_version,
    check_ssh_to_container,
)


# =============================================================================
# REINSTALL CONTAINER VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(1)
def test_container_running_after_reinstall(host):
    """TC_RV_001: Verify omnia_core container is running after reinstall."""
    log = TestLogger("[TC_RV_001] " + TEST_NAMES["container_running"])

    result = check_container_running(host)

    if result["success"]:
        d = result["details"]
        details = (
            f"Container: {d['container']}\n"
            f"Status: {d['status']}\n"
            f"Image: {d['image']}\n"
            f"Ports: {d['ports']}"
        )
        log.passed(LOG_MSGS["container_running"], details)
    else:
        log.failed(LOG_MSGS["container_not_running"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_container_file_after_reinstall(host):
    """TC_RV_002: Verify omnia_core.container file exists after reinstall."""
    log = TestLogger("[TC_RV_002] " + TEST_NAMES["container_file"])
    path = TEST_VARS["container_file"]

    result = check_file_exists(host, path)

    if result["success"]:
        log.passed(LOG_MSGS["file_exists"], f"Path: {path}\n{result['details']}")
    else:
        log.failed(LOG_MSGS["file_not_found"], f"Path: {path}\n{result['error']}")

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(3)
def test_service_running_after_reinstall(host):
    """TC_RV_003: Verify omnia_core service is running after reinstall."""
    log = TestLogger("[TC_RV_003] " + TEST_NAMES["service_running"])
    service = TEST_VARS["service_name"]

    result = check_service_running(host, service)

    if result["success"]:
        log.passed(LOG_MSGS["service_active"], f"Service: {service}\n{result['details']}")
    else:
        log.failed(
            LOG_MSGS["service_inactive"].format(status=result["status"]),
            f"Service: {service}\n{result['details']}"
        )

    assert result["success"], ASSERT_MSGS["service_not_active"].format(status=result["status"])


@pytest.mark.sanity
@pytest.mark.order(4)
def test_metadata_file_after_reinstall(host):
    """TC_RV_004: Verify oim_metadata.yml exists inside container after reinstall."""
    log = TestLogger("[TC_RV_004] " + TEST_NAMES["metadata_file"])
    path = TEST_VARS["metadata_file"]

    result = check_metadata_file(host)

    if result["success"]:
        log.passed(LOG_MSGS["file_exists"], f"Path: {path}\n{result['details']}")
    else:
        log.failed(LOG_MSGS["file_not_found"], f"Path: {path}\n{result['error']}")

    assert result["success"], result["error"]


# =============================================================================
# REINSTALL SECURITY VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(5)
def test_ssh_key_pair_after_reinstall(host):
    """TC_RV_005: Verify SSH key pair exists after reinstall."""
    log = TestLogger("[TC_RV_005] " + TEST_NAMES["ssh_key_pair"])

    result = check_ssh_key_pair_exists(host)

    if result["success"]:
        log.passed(LOG_MSGS["ssh_key_pair_exists"], result["details"])
    else:
        log.failed(LOG_MSGS["ssh_key_pair_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(6)
def test_ssh_config_after_reinstall(host):
    """TC_RV_006: Verify SSH config entry after reinstall."""
    log = TestLogger("[TC_RV_006] " + TEST_NAMES["ssh_config_entry"])

    result = check_ssh_config_entry(host)

    if result["success"]:
        log.passed(LOG_MSGS["ssh_config_found"], result["details"])
    else:
        log.failed(LOG_MSGS["ssh_config_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(7)
def test_authorized_key_after_reinstall(host):
    """TC_RV_007: Verify oim_rsa.pub in authorized_keys after reinstall."""
    log = TestLogger("[TC_RV_007] " + TEST_NAMES["authorized_key"])

    result = check_authorized_key(host)

    if result["success"]:
        log.passed(LOG_MSGS["authorized_key_found"], result["details"])
    else:
        log.failed(LOG_MSGS["authorized_key_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.security
@pytest.mark.order(8)
def test_ssh_to_container_after_reinstall(host):
    """TC_RV_008: Verify passwordless SSH to container after reinstall."""
    log = TestLogger("[TC_RV_008] " + TEST_NAMES["ssh_to_container"])

    result = check_ssh_to_container(host)

    if result["success"]:
        d = result["details"]
        details = (
            f"Connected as: {d['user']}\n"
            f"Working directory: {d['workdir']}\n"
            f"Connection: {d['connection']}"
        )
        log.passed(LOG_MSGS["ssh_success"], details)
    else:
        log.failed(LOG_MSGS["ssh_failed"], result["error"])

    assert result["success"], ASSERT_MSGS["ssh_failed"].format(error=result["error"])


# =============================================================================
# REINSTALL CONTAINER HEALTH TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(9)
def test_container_image_after_reinstall(host):
    """TC_RV_009: Verify container image exists after reinstall."""
    log = TestLogger("[TC_RV_009] " + TEST_NAMES["container_image"])

    result = check_container_image_exists(host)

    if result["success"]:
        log.passed(LOG_MSGS["container_image_found"], result["details"])
    else:
        log.failed(LOG_MSGS["container_image_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(10)
def test_omnia_dir_after_reinstall(host):
    """TC_RV_010: Verify /omnia/ directory inside container after reinstall."""
    log = TestLogger("[TC_RV_010] " + TEST_NAMES["omnia_dir"])

    result = check_omnia_dir_in_container(host)

    if result["success"]:
        log.passed(LOG_MSGS["omnia_dir_found"], result["details"])
    else:
        log.failed(LOG_MSGS["omnia_dir_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(11)
def test_log_dirs_after_reinstall(host):
    """TC_RV_011: Verify log directories exist after reinstall."""
    log = TestLogger("[TC_RV_011] " + TEST_NAMES["log_dirs"])

    result = check_log_dirs_exist(host)

    if result["success"]:
        log.passed(LOG_MSGS["log_dirs_found"], result["details"])
    else:
        log.failed(LOG_MSGS["log_dirs_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(12)
def test_version_after_reinstall(host):
    """TC_RV_012: Verify omnia.sh --version returns valid output after reinstall."""
    log = TestLogger("[TC_RV_012] " + TEST_NAMES["omnia_version"])

    result = check_omnia_version(host)

    if result["success"]:
        log.passed(LOG_MSGS["version_output"], result["details"])
    else:
        log.failed(LOG_MSGS["version_failed"], result["error"])

    assert result["success"], result["error"]
