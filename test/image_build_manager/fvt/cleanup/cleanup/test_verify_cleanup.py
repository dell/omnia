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
  TC_CL_002: Containers removed (minio-server, registry)
  TC_CL_003: Systemd services stopped (minio.service, registry.service)
  TC_CL_004: Firewall ports closed (9000, 9001, 5000)
  TC_CL_005: S3 buckets and artifacts removed
  TC_CL_006: s3cmd configuration removed
  TC_CL_007: build_status.yml removed
  TC_CL_008: Registry cleaned (no images)
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
from library.messages import TEST_NAMES, TEST_LOG_MSGS as LOG


@pytest.mark.sanity
@pytest.mark.order(1)
def test_containers_removed(host):
    """TC_CL_002: Verify containers removed after cleanup."""
    tl = TestLogger(TEST_NAMES["containers_removed"], "TC_CL_002")
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
    """TC_CL_003: Verify systemd services stopped after cleanup."""
    tl = TestLogger(TEST_NAMES["services_removed"], "TC_CL_003")
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
    """TC_CL_004: Verify firewall ports closed after cleanup."""
    tl = TestLogger(TEST_NAMES["firewall_ports_closed"], "TC_CL_004")
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
    """TC_CL_005: Verify S3 buckets removed after cleanup."""
    tl = TestLogger(TEST_NAMES["s3_artifacts_removed"], "TC_CL_005")
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
    """TC_CL_006: Verify s3cmd configuration removed."""
    tl = TestLogger(TEST_NAMES["s3cfg_removed"], "TC_CL_006")
    result = check_s3cfg_removed(host)

    if result["success"]:
        tl.passed(LOG["s3cfg_removed_ok"], result["details"])
    else:
        tl.failed(LOG["s3cfg_still_exists"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(6)
def test_build_output_removed(host):
    """TC_CL_007: Verify build_status.yml removed."""
    tl = TestLogger(TEST_NAMES["build_output_removed"], "TC_CL_007")
    result = check_build_output_removed(host)

    if result["success"]:
        tl.passed(LOG["build_output_removed_ok"], result["details"])
    else:
        tl.failed(LOG["build_output_still_exists"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_cleaned(host):
    """TC_CL_008: Verify registry has no images."""
    tl = TestLogger(TEST_NAMES["registry_cleaned"], "TC_CL_008")
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
