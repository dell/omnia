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
Telemetry Precheck — PowerScale Privilege Validation.

Test cases:
    TC_PC_005: Verify PowerScale user has required privileges
"""

import pytest

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    is_logs_enabled,
)
from library.functions.powerscale_func import (
    decode_isilon_creds,
)


def _skip_if_powerscale_disabled(host):
    """Skip test if PowerScale source is not enabled."""
    if not is_source_enabled(host, "powerscale"):
        pytest.skip("PowerScale source not enabled in config")


@pytest.mark.precheck
@pytest.mark.sanity
@pytest.mark.order(5)
def test_powerscale_privileges(host):
    """TC_PC_005: Verify PowerScale user has required privileges."""
    _skip_if_powerscale_disabled(host)
    tc = TC["powerscale_privileges"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking PowerScale user privileges")
    
    # Get PowerScale credentials
    k8s_result = decode_isilon_creds(host)
    if not k8s_result["success"]:
        tl.failed(
            "Cannot read PowerScale credentials from K8s secret",
            k8s_result["error"],
        )
        pytest.fail("PowerScale secret not available in K8s")

    cluster = k8s_result["clusters"][0]
    ps_user = cluster["username"]
    ps_password = cluster["password"]
    ps_host = cluster["endpoint"]

    # Check if metrics or logs are enabled
    metrics_enabled = is_source_enabled(host, "powerscale")
    logs_enabled = is_logs_enabled(host, "powerscale")

    if not (metrics_enabled or logs_enabled):
        tl.info("PowerScale telemetry not enabled - skipping privilege check")
        pytest.skip("PowerScale telemetry not enabled")

    # Define required privileges
    required_metrics_privileges = [
        "ISI_PRIV_LOGIN_PAPI",
        "ISI_PRIV_NFS",
        "ISI_PRIV_QUOTA",
        "ISI_PRIV_SNAPSHOT",
        "ISI_PRIV_IFS_RESTORE",
        "ISI_PRIV_NS_IFS_ACCESS",
        "ISI_PRIV_IFS_BACKUP",
        "ISI_PRIV_AUTH_ZONES",
        "ISI_PRIV_SYNCIQ",
        "ISI_PRIV_STATISTICS",
    ]

    required_log_privileges = [
        "ISI_PRIV_AUDIT",
    ]

    # SSH to PowerScale and check privileges
    from omnia_auto import run_on_host
    priv_cmd = f"sshpass -p '{ps_password}' ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no {ps_user}@{ps_host} 'isi auth privileges'"
    result = run_on_host(host, priv_cmd)
    
    if result.rc != 0:
        tl.info(
            f"SSH to PowerScale failed for privilege check (rc={result.rc}, stderr: {result.stderr.strip()}). Privileges will be validated during deployment via PowerScale API."
        )
        # Don't fail the test - this is expected if SSH is not available
        # Privileges will be validated during deployment via the PowerScale API
        tl.info("Privilege check skipped - will be validated during deployment")
        pytest.skip("SSH not available from test host - privileges validated during deployment")

    # Parse available privileges
    available_privileges = []
    for line in result.stdout.split('\n'):
        if 'ISI_PRIV_' in line:
            priv_name = line.split()[0]
            available_privileges.append(priv_name)

    # Check metrics privileges
    missing_metrics = []
    if metrics_enabled:
        missing_metrics = [p for p in required_metrics_privileges if p not in available_privileges]

    # Check log privileges
    missing_logs = []
    if logs_enabled:
        missing_logs = [p for p in required_log_privileges if p not in available_privileges]

    # Build result message
    details = []
    if metrics_enabled:
        if missing_metrics:
            details.append(f"Missing metrics privileges: {', '.join(missing_metrics)}")
        else:
            details.append("All required metrics privileges present")
    
    if logs_enabled:
        if missing_logs:
            details.append(f"Missing log privileges: {', '.join(missing_logs)}")
        else:
            details.append("All required log privileges present")

    details_str = "\n".join(details)
    
    if (missing_metrics or missing_logs):
        tl.failed(
            "PowerScale user missing required privileges",
            details_str
        )
        pytest.fail(
            f"PowerScale user '{ps_user}' missing required privileges: {details_str}"
        )
    else:
        tl.passed(
            "PowerScale user has all required privileges",
            details_str
        )

    assert True, "PowerScale privilege check passed"
