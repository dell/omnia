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
omnia.sh --install / Security — SSH Connectivity Tests.

Verifies passwordless SSH connectivity between OIM server and
omnia_core container in both directions.

Test cases:
    TC_IT_007  Verify passwordless SSH: OIM server → omnia_core
    TC_IT_008  Verify passwordless SSH: omnia_core → OIM server
    TC_IT_009  Verify SSH key pair (oim_rsa) exists
    TC_IT_010  Verify SSH config entry for omnia_core
    TC_IT_011  Verify oim_rsa.pub in authorized_keys

Usage:
    run_validation omnia_sh_install verify
    run_validation omnia_sh_install verify --suite security
"""

import pytest

from main.library import (
    TestLogger,
    TEST_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
    check_ssh_to_container,
    check_ssh_from_container,
    check_ssh_key_pair_exists,
    check_ssh_config_entry,
    check_authorized_key,
)


# =============================================================================
# SSH SECURITY TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.security
@pytest.mark.order(7)
def test_passwordless_ssh_to_container(host):
    """TC_IT_007: Verify passwordless SSH from OIM server to omnia_core."""
    log = TestLogger("[TC_IT_007] " + TEST_NAMES["ssh_to_container"])
    alias = TEST_VARS["ssh_alias"]

    result = check_ssh_to_container(host)

    if result["success"]:
        d = result["details"]
        details = (
            f"Direction: OIM server → {alias}\n"
            f"Connected as: {d['user']}\n"
            f"Working directory: {d['workdir']}\n"
            f"Connection: {d['connection']}"
        )
        log.passed(LOG_MSGS["ssh_success"], details)
    else:
        log.failed(LOG_MSGS["ssh_failed"], f"Direction: OIM server → {alias}\n{result['error']}")

    assert result["success"], ASSERT_MSGS["ssh_failed"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(8)
def test_passwordless_ssh_from_container_to_host(host):
    """TC_IT_008: Verify passwordless SSH from omnia_core to OIM server."""
    log = TestLogger("[TC_IT_008] " + TEST_NAMES["ssh_from_container"])
    alias = TEST_VARS["ssh_alias"]
    oim_ip = TEST_VARS["oim_server_ip"]

    if not oim_ip:
        oim_ip = "localhost"

    result = check_ssh_from_container(host, oim_ip)

    if result["success"]:
        d = result["details"]
        details = (
            f"Direction: {alias} → OIM server ({oim_ip})\n"
            f"Connected as: {d['user']}\n"
            f"Target: {d['target']}\n"
            f"Connection: {d['connection']}"
        )
        log.passed(LOG_MSGS["ssh_success"], details)
    else:
        log.failed(LOG_MSGS["ssh_failed"], f"Direction: {alias} → OIM server ({oim_ip})\n{result['error']}")

    assert result["success"], ASSERT_MSGS["ssh_failed"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(9)
def test_ssh_key_pair_exists(host):
    """TC_IT_009: Verify SSH key pair (oim_rsa + oim_rsa.pub) exists."""
    log = TestLogger("[TC_IT_009] " + TEST_NAMES["ssh_key_pair"])

    result = check_ssh_key_pair_exists(host)

    if result["success"]:
        log.passed(LOG_MSGS["ssh_key_pair_exists"], result["details"])
    else:
        log.failed(LOG_MSGS["ssh_key_pair_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(10)
def test_ssh_config_entry(host):
    """TC_IT_010: Verify SSH config has Host omnia_core entry."""
    log = TestLogger("[TC_IT_010] " + TEST_NAMES["ssh_config_entry"])

    result = check_ssh_config_entry(host)

    if result["success"]:
        log.passed(LOG_MSGS["ssh_config_found"], result["details"])
    else:
        log.failed(LOG_MSGS["ssh_config_missing"], result["error"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.security
@pytest.mark.order(11)
def test_authorized_key(host):
    """TC_IT_011: Verify oim_rsa.pub is in authorized_keys."""
    log = TestLogger("[TC_IT_011] " + TEST_NAMES["authorized_key"])

    result = check_authorized_key(host)

    if result["success"]:
        log.passed(LOG_MSGS["authorized_key_found"], result["details"])
    else:
        log.failed(LOG_MSGS["authorized_key_missing"], result["error"])

    assert result["success"], result["error"]
