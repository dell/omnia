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
Image Build Cleanup — Comprehensive Verification.

Validates that --tags cleanup removed all artifacts:
  Containers removed (minio-server, registry)
  Systemd services stopped (minio.service, registry.service)
  Firewall ports closed (9000, 9001, 5000)
  S3 buckets and artifacts removed
  s3cmd configuration removed
  build_status.yml removed
  Registry cleaned (no images)
"""

import pytest

from library.functions import (
    TestLogger,
    check_containers_removed,
    check_services_removed,
    check_firewall_ports_removed,
    check_s3_artifacts_removed,
    check_s3cfg_removed,
    check_build_output_removed,
    check_registry_cleaned,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG


@pytest.mark.sanity
@pytest.mark.order(1)
def test_containers_removed(host):
    """Verify containers removed after cleanup."""
    tc = TC["containers_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_containers_removed(host)

    lines = []
    for c in result["results"]:
        status = "✓ removed" if c["removed"] else "✗ STILL EXISTS"
        lines.append(f"  {c['container']}: {status}")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed("All containers removed", details)
    else:
        tl.failed("Some containers still exist", details)

    assert result["success"], (
        f"Containers not removed after cleanup:\n{details}"
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_services_removed(host):
    """Verify systemd services stopped after cleanup."""
    tc = TC["services_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_services_removed(host)

    if result["success"]:
        tl.passed(LOG["services_removed_ok"], result["details"])
    else:
        active = [r for r in result["results"] if not r["removed"]]
        tl.failed(
            LOG["services_still_active"].format(count=len(active)),
            result["details"],
        )

    assert result["success"], (
        f"Services not stopped:\n{result['details']}"
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_firewall_ports_closed(host):
    """Verify firewall ports closed after cleanup."""
    tc = TC["firewall_ports_closed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_firewall_ports_removed(host)

    if result["success"]:
        tl.passed(LOG["firewall_ports_closed_ok"], result["details"])
    else:
        tl.failed(
            LOG["firewall_ports_still_open"].format(
                count=len(result["open_ports"])
            ),
            result["details"],
        )

    assert result["success"], (
        f"Firewall ports still open:\n{result['details']}"
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_s3_artifacts_removed(host):
    """Verify S3 buckets removed after cleanup."""
    tc = TC["s3_artifacts_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_artifacts_removed(host)

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], (
        f"S3 artifacts not cleaned: {result.get('remaining_buckets')}"
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_s3cfg_removed(host):
    """Verify s3cmd configuration removed."""
    tc = TC["s3cfg_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3cfg_removed(host)

    if result["success"]:
        tl.passed(LOG["s3cfg_removed_ok"], result["details"])
    else:
        tl.failed(LOG["s3cfg_still_exists"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(6)
def test_build_output_removed(host):
    """Verify build_status.yml removed."""
    tc = TC["build_output_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_output_removed(host)

    if result["success"]:
        tl.passed(LOG["build_output_removed_ok"], result["details"])
    else:
        tl.failed(LOG["build_output_still_exists"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_cleaned(host):
    """Verify registry has no images."""
    tc = TC["registry_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_cleaned(host)

    if result["success"]:
        tl.passed(LOG["registry_cleaned_ok"], result["details"])
    else:
        tl.failed(
            LOG["registry_still_has_images"].format(
                count=len(result.get("repos", []))
            ),
            result["details"],
        )

    assert result["success"], result["details"]
