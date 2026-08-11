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
Image Build Prepare — Infrastructure Verification.

Validates that --tags prepare created all required infrastructure:
  S3 storage backend (MinIO container)
  Registry container running
  Systemd services active (minio, registry)
  Firewall ports open (9000, 9001, 5000)
  s3cmd installed and configured
  Registry reachable (HTTP catalog)
"""

import pytest

from library.functions import (
    TestLogger,
    check_s3_containers,
    check_container_running,
    check_services_active,
    check_firewall_ports_open,
    check_s3cmd_configured,
    check_registry_reachable,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import REGISTRY_CONTAINER
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_storage_backend_after_prepare(host):
    """Verify S3 backend after prepare."""
    tc = TC["storage_backend"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_containers(host)

    if result.get("skipped"):
        tl.skipped(LOG["storage_backend_skip_minio_check"])
        pytest.skip(LOG["storage_backend_skip_minio_check"])

    if result["success"]:
        tl.passed(LOG["storage_backend_minio"], result["details"])
    else:
        status = result.get("results", [{}])[0].get("status", "")
        tl.failed(LOG["container_not_running"].format(
            container="minio-server"
        ))
        assert False, ASSERT["container_not_running"].format(
            container="minio-server", status=status,
        )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_registry_after_prepare(host):
    """Verify registry container after prepare."""
    tc = TC["registry_container_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_container_running(host, REGISTRY_CONTAINER)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(
                container=REGISTRY_CONTAINER
            ),
            result["status"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(
                container=REGISTRY_CONTAINER
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container=REGISTRY_CONTAINER, status=result["status"],
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_services_active(host):
    """Verify systemd services are active."""
    tc = TC["services_active"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_services_active(host)

    if result["success"]:
        tl.passed(LOG["services_active_ok"], result["details"])
    else:
        inactive = [r for r in result["results"] if not r["active"]]
        tl.failed(
            LOG["services_inactive"].format(count=len(inactive)),
            result["details"],
        )

    assert result["success"], (
        f"Services not active:\n{result['details']}"
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_firewall_ports_open(host):
    """Verify firewall ports are open."""
    tc = TC["firewall_ports_open"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_firewall_ports_open(host)

    if result["success"]:
        tl.passed(LOG["firewall_ports_open_ok"], result["details"])
    else:
        tl.failed(
            LOG["firewall_ports_missing"].format(
                count=len(result["missing_ports"])
            ),
            result["details"],
        )

    assert result["success"], (
        f"Firewall ports missing:\n{result['details']}"
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_s3cmd_configured(host):
    """Verify s3cmd installed and configured."""
    tc = TC["s3cmd_configured"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3cmd_configured(host)

    if result["success"]:
        tl.passed(LOG["s3cmd_configured_ok"], result["details"])
    else:
        tl.failed(LOG["s3cmd_not_configured"], result["details"])

    assert result["success"], (
        f"s3cmd not configured:\n{result['details']}"
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_registry_reachable(host):
    """Verify registry is reachable."""
    tc = TC["registry_reachable"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_reachable(host)

    if result["success"]:
        tl.passed(LOG["registry_reachable_ok"], result["details"])
    else:
        tl.failed(LOG["registry_not_reachable"], result["details"])

    assert result["success"], result["details"]
