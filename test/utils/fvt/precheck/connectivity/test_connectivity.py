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
Precheck — Connectivity Tests.

Verifies target host connectivity, environment variables, hostname, and admin IP.
"""

import pytest

from library.functions import (
    TestLogger,
    check_target_connectivity,
    check_env_var,
    get_hostname,
    check_admin_ip_assigned,
    load_test_config,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(1)
def test_target_connectivity(host):
    """Verify target host is reachable via SSH."""
    tc = TC["target_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_target_connectivity(host)

    if result["success"]:
        tl.passed(LOG["connectivity_ok"])
    else:
        tl.failed(LOG["connectivity_failed"].format(error=result["error"]))

    assert result["success"], ASSERT["connectivity_failed"].format(
        error=result["error"],
        user=load_test_config().get("oim_ssh_user", "root"),
        host=load_test_config().get("oim_server_ip", "localhost"),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_env_vars_present(host):
    """Verify OMNIA environment variables are set on target."""
    tc = TC["env_vars_present"]
    tl = TestLogger(tc["title"], tc["id"])

    required_vars = [
        "OMNIA_DATA_PATH",
        "OMNIA_PROJECT_NAME",
        "SYSTEM_ADMIN_NIC_IPV4",
        "SYSTEM_HOSTNAME",
    ]

    missing = []
    values = {}

    for var in required_vars:
        result = check_env_var(host, var)
        if result["success"]:
            values[var] = result["value"]
        else:
            missing.append(var)

    if not missing:
        details = "\n".join([f"  {k}={v}" for k, v in values.items()])
        tl.passed(f"All environment variables present:\n{details}")
    else:
        tl.failed(LOG["env_var_missing"].format(var=", ".join(missing)))

    assert not missing, ASSERT["env_var_missing"].format(var=", ".join(missing))


@pytest.mark.sanity
@pytest.mark.order(3)
def test_hostname_domain(host):
    """Verify hostname and domain match expected values."""
    tc = TC["hostname_domain"]
    tl = TestLogger(tc["title"], tc["id"])

    result = get_hostname(host)

    if not result["success"]:
        tl.failed(result["error"])
        assert False, result["error"]

    # Get expected values from environment
    hostname_result = check_env_var(host, "SYSTEM_HOSTNAME")
    domain_result = check_env_var(host, "SYSTEM_DOMAIN_NAME")

    expected_hostname = hostname_result.get("value", "")
    expected_domain = domain_result.get("value", "")

    hostname_match = (
        not expected_hostname or
        result["hostname"] == expected_hostname
    )
    domain_match = (
        not expected_domain or
        result["domain"] == expected_domain
    )

    if hostname_match and domain_match:
        tl.passed(
            f"Hostname: {result['hostname']}, Domain: {result['domain']}"
        )
    else:
        errors = []
        if not hostname_match:
            errors.append(f"hostname: expected '{expected_hostname}', got '{result['hostname']}'")
        if not domain_match:
            errors.append(f"domain: expected '{expected_domain}', got '{result['domain']}'")
        tl.failed("; ".join(errors))

    assert hostname_match, ASSERT["hostname_mismatch"].format(
        expected=expected_hostname,
        actual=result["hostname"],
    )
    assert domain_match, ASSERT["domain_mismatch"].format(
        expected=expected_domain,
        actual=result["domain"],
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_admin_ip_assigned(host):
    """Verify admin IP is assigned to a network interface."""
    tc = TC["admin_ip_assigned"]
    tl = TestLogger(tc["title"], tc["id"])

    # Get admin IP from environment
    ip_result = check_env_var(host, "SYSTEM_ADMIN_NIC_IPV4")

    if not ip_result["success"]:
        tl.skipped("SYSTEM_ADMIN_NIC_IPV4 not set, skipping")
        pytest.skip("SYSTEM_ADMIN_NIC_IPV4 not set")

    admin_ip = ip_result["value"]
    result = check_admin_ip_assigned(host, admin_ip)

    if result["success"]:
        tl.passed(LOG["admin_ip_assigned"].format(ip=admin_ip, iface=result["interface"]))
    else:
        tl.failed(LOG["admin_ip_not_assigned"].format(ip=admin_ip))

    assert result["success"], ASSERT["admin_ip_not_assigned"].format(ip=admin_ip)


@pytest.mark.sanity
@pytest.mark.order(5)
def test_omnia_setup(host):
    """Verify omnia.sh setup has been completed on target."""
    tc = TC["omnia_setup"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check for omnia.env file
    cmd = "test -f /etc/omnia/omnia.env && echo exists"
    result = host.run(cmd)

    if result.rc == 0 and "exists" in result.stdout:
        tl.passed("omnia.sh setup completed (/etc/omnia/omnia.env exists)")
    else:
        tl.failed("omnia.sh setup not completed (/etc/omnia/omnia.env missing)")

    assert result.rc == 0 and "exists" in result.stdout, (
        "omnia.sh setup not completed. Run: omnia.sh --setup-venv"
    )
