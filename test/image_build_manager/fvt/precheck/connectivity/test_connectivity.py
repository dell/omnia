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
Image Build Precheck — Connectivity and Environment Verification.

Validates target host environment matches omnia.env configuration:
  Target host SSH connectivity
  All required omnia.env variables present (OMNIA_DATA_PATH,
    OMNIA_PROJECT_NAME, SYSTEM_ADMIN_NIC_IPV4, SYSTEM_HOSTNAME,
    SYSTEM_DOMAIN_NAME)
  Hostname and domain match configured values
  Admin IP assigned to a local interface
  omnia.sh setup completed (/etc/omnia/omnia.env exists)
"""

import pytest

from library.functions import (
    TestLogger,
    check_target_connectivity,
    check_env_vars_present,
    check_hostname_domain,
    check_admin_ip,
    check_omnia_setup,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_target_connectivity(host):
    """Verify target host is reachable via SSH."""
    tc = TC["target_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_target_connectivity(host)

    if result["success"]:
        tl.passed(LOG["connectivity_ok"], result["details"])
    else:
        tl.failed(LOG["connectivity_failed"], result.get("error", ""))

    assert result["success"], ASSERT["connectivity_failed"].format(
        error=result.get("error", "SSH check failed"),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_env_vars_present(host):
    """Verify all required omnia.env variables present on target."""
    tc = TC["env_vars_present"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_env_vars_present(host)

    if result["success"]:
        tl.passed(LOG["env_vars_ok"], result["details"])
    else:
        missing = [
            r for r in result["results"] if not r["found"]
        ]
        tl.failed(
            LOG["env_vars_missing"].format(count=len(missing)),
            result["details"],
        )

    assert result["success"], ASSERT["env_vars_missing"].format(
        error=result.get("error", "Env vars missing"),
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_hostname_domain(host):
    """Verify hostname and domain match omnia.env configuration."""
    tc = TC["hostname_domain"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_hostname_domain(host)

    if result["success"]:
        tl.passed(LOG["hostname_domain_ok"], result["details"])
    else:
        tl.failed(
            LOG["hostname_domain_mismatch"],
            result["details"],
        )

    assert result["success"], ASSERT["hostname_domain_mismatch"].format(
        error=result.get("error", "Hostname/domain mismatch"),
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_admin_ip_assigned(host):
    """Verify SYSTEM_ADMIN_NIC_IPV4 is assigned to a local interface."""
    tc = TC["admin_ip_assigned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_admin_ip(host)

    if result["success"]:
        tl.passed(LOG["admin_ip_ok"], result["details"])
    else:
        tl.failed(
            LOG["admin_ip_not_assigned"],
            result["details"],
        )

    assert result["success"], ASSERT["admin_ip_not_assigned"].format(
        error=result.get("error", "Admin IP not assigned"),
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_omnia_setup(host):
    """Verify omnia.sh setup completed on target."""
    tc = TC["omnia_setup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_omnia_setup(host)

    if result["success"]:
        tl.passed(LOG["omnia_setup_ok"], result["details"])
    else:
        tl.failed(
            LOG["omnia_setup_incomplete"],
            result["details"],
        )

    assert result["success"], ASSERT["omnia_setup_incomplete"].format(
        error=result.get("error", "omnia.sh setup incomplete"),
    )
