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
omnia.sh --install / Container — Verification Tests.

Verifies that omnia.sh --install completed successfully by checking
the container, service, and metadata state.  These tests apply after
both fresh install and reinstall operations.

Test cases:
    TC_IT_003  Verify omnia_core container is running
    TC_IT_004  Verify omnia_core.container file exists
    TC_IT_005  Verify omnia_core service is running
    TC_IT_006  Verify oim_metadata.yml file exists
    TC_IT_012  Verify omnia_core container image exists
    TC_IT_013  Verify /omnia/ directory inside container
    TC_IT_014  Verify log directories in shared path
    TC_IT_015  Verify omnia.sh --version output

For SSH connectivity tests, see security/test_ssh.py.

Usage:
    run_validation omnia_sh_install verify
    run_validation omnia_sh_install verify --suite container
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
    check_container_image_exists,
    check_omnia_dir_in_container,
    check_log_dirs_exist,
    check_omnia_version,
)


# =============================================================================
# CONTAINER VERIFICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(3)
def test_omnia_core_container_running(host):
    """TC_IT_003: Verify omnia_core container is running."""
    log = TestLogger("[TC_IT_003] " + TEST_NAMES["container_running"])

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
@pytest.mark.order(4)
def test_omnia_core_container_file_exists(host):
    """TC_IT_004: Verify omnia_core.container file is present."""
    log = TestLogger("[TC_IT_004] " + TEST_NAMES["container_file"])
    path = TEST_VARS["container_file"]

    result = check_file_exists(host, path)

    if result["success"]:
        log.passed(LOG_MSGS["file_exists"], f"Path: {path}\n{result['details']}")
    else:
        log.failed(LOG_MSGS["file_not_found"], f"Path: {path}\n{result['error']}")

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(5)
def test_omnia_core_service_running(host):
    """TC_IT_005: Verify omnia_core systemd service is running."""
    log = TestLogger("[TC_IT_005] " + TEST_NAMES["service_running"])
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
@pytest.mark.order(6)
def test_oim_metadata_file_exists(host):
    """TC_IT_006: Verify oim_metadata.yml file exists inside container."""
    log = TestLogger("[TC_IT_006] " + TEST_NAMES["metadata_file"])
    path = TEST_VARS["metadata_file"]

    result = check_metadata_file(host)

    if result["success"]:
        log.passed(LOG_MSGS["file_exists"], f"Path: {path}\n{result['details']}")
    else:
        log.failed(LOG_MSGS["file_not_found"], f"Path: {path}\n{result['error']}")

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(12)
def test_container_image_exists(host):
    """TC_IT_012: Verify omnia_core container image exists locally."""
    log = TestLogger("[TC_IT_012] " + TEST_NAMES["container_image"])

    result = check_container_image_exists(host)

    if result["success"]:
        log.passed(LOG_MSGS["container_image_found"], result["details"])
    else:
        log.failed(LOG_MSGS["container_image_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.order(13)
def test_omnia_dir_in_container(host):
    """TC_IT_013: Verify /omnia/ directory exists inside container."""
    log = TestLogger("[TC_IT_013] " + TEST_NAMES["omnia_dir"])

    result = check_omnia_dir_in_container(host)

    if result["success"]:
        log.passed(LOG_MSGS["omnia_dir_found"], result["details"])
    else:
        log.failed(LOG_MSGS["omnia_dir_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(14)
def test_log_dirs_exist(host):
    """TC_IT_014: Verify log directories exist in shared path."""
    log = TestLogger("[TC_IT_014] " + TEST_NAMES["log_dirs"])

    result = check_log_dirs_exist(host)

    if result["success"]:
        log.passed(LOG_MSGS["log_dirs_found"], result["details"])
    else:
        log.failed(LOG_MSGS["log_dirs_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(15)
def test_omnia_version(host):
    """TC_IT_015: Verify omnia.sh --version returns valid output."""
    log = TestLogger("[TC_IT_015] " + TEST_NAMES["omnia_version"])

    result = check_omnia_version(host)

    if result["success"]:
        log.passed(LOG_MSGS["version_output"], result["details"])
    else:
        log.failed(LOG_MSGS["version_failed"], result["error"])

    assert result["success"], result["error"]
