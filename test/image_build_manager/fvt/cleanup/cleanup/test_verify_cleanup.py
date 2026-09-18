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
  Domain credential file and vault key removed
"""

import pytest

from library.functions import (
    TestLogger,
    check_containers_removed,
    check_services_removed,
    check_firewall_ports_removed,
    check_s3_artifacts_removed,
    check_s3cfg_removed,
    check_credentials_removed,
    check_build_output_removed,
    check_registry_cleaned,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import LISTENING_PORTS, REGISTRY_PORT
from library.messages import (
    TEST_ASSERT_MSGS as ASSERT,
    TEST_LOG_MSGS as LOG,
)


def _assert_cleanup_result(result, check):
    """Assert one cleanup postcondition with a concise shared message."""
    assert result["success"], ASSERT["cleanup_postcondition_failed"].format(
        check=check,
        error=result.get("error") or result.get("details", "unknown error"),
    )


def _resource_state(item):
    """Return a readable state without hiding inspection failures."""
    if item.get("query_error"):
        return f"inspection failed ({item['query_error']})"
    return "removed" if item["removed"] else "STILL EXISTS"


@pytest.mark.sanity
@pytest.mark.order(1)
def test_containers_removed(host):
    """Verify containers removed after cleanup."""
    tc = TC["containers_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    tl.info(LOG["cleanup_verify_prerequisite"])
    result = check_containers_removed(host)
    fields = [
        ("Container", f"{item['container']}: {_resource_state(item)}")
        for item in result["results"]
    ]

    if result["success"]:
        tl.passed_fields(LOG["containers_removed_ok"], fields)
    else:
        tl.failed_fields(LOG["containers_still_exist"], fields)

    _assert_cleanup_result(result, "Container")


@pytest.mark.sanity
@pytest.mark.order(2)
def test_services_removed(host):
    """Verify systemd services stopped after cleanup."""
    tc = TC["services_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_services_removed(host)
    fields = []
    for item in result["results"]:
        if item.get("error"):
            state = f"inspection failed ({item['error']})"
        else:
            state = "inactive" if item["removed"] else "still active"
        fields.append(("Service", f"{item['service']}: {state}"))

    if result["success"]:
        tl.passed_fields(LOG["services_removed_ok"], fields)
    else:
        active = [r for r in result["results"] if not r["removed"]]
        tl.failed_fields(
            LOG["services_still_active"].format(count=len(active)),
            fields,
        )

    _assert_cleanup_result(result, "Systemd service")


@pytest.mark.sanity
@pytest.mark.order(3)
def test_firewall_ports_closed(host):
    """Verify firewall ports closed after cleanup."""
    tc = TC["firewall_ports_closed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_firewall_ports_removed(host)
    fields = []
    query_errors = result.get("query_errors", [])
    for port in LISTENING_PORTS:
        probe_failed = any(f"port {port} " in err for err in query_errors)
        if probe_failed:
            state = "inspection failed"
        else:
            state = (
                "STILL LISTENING"
                if port in result["open_ports"]
                else "closed"
            )
        fields.append(("TCP port", f"{port}: {state}"))

    if result["success"]:
        tl.passed_fields(LOG["firewall_ports_closed_ok"], fields)
    else:
        tl.failed_fields(
            LOG["firewall_ports_still_open"].format(
                count=len(result["open_ports"]),
            ),
            fields,
        )

    _assert_cleanup_result(result, "TCP listener")


@pytest.mark.sanity
@pytest.mark.order(4)
def test_s3_artifacts_removed(host):
    """Verify S3 buckets removed after cleanup."""
    tc = TC["s3_artifacts_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_artifacts_removed(host)

    fields = [
        ("S3 provider", result["provider"]),
        ("Managed storage", result["storage_path"]),
    ]
    fields.extend(
        ("Remaining bucket", bucket)
        for bucket in result["remaining_buckets"]
    )

    if result.get("skipped"):
        tl.skipped_fields(LOG["cleanup_powerscale_s3_skip"], fields)
        pytest.skip(LOG["cleanup_powerscale_s3_skip"])

    if result["success"]:
        tl.passed_fields(LOG["s3_artifacts_removed_ok"], fields)
    else:
        tl.failed_fields(LOG["s3_artifacts_still_exist"], fields)

    _assert_cleanup_result(result, "Managed MinIO storage")


@pytest.mark.sanity
@pytest.mark.order(5)
def test_s3cfg_removed(host):
    """Verify s3cmd configuration removed."""
    tc = TC["s3cfg_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3cfg_removed(host)
    fields = [
        ("S3 provider", result["provider"]),
        ("Configuration", result["path"]),
    ]

    if result.get("skipped"):
        tl.skipped_fields(LOG["cleanup_powerscale_s3cfg_skip"], fields)
        pytest.skip(LOG["cleanup_powerscale_s3cfg_skip"])

    if result["success"]:
        tl.passed_fields(LOG["s3cfg_removed_ok"], fields)
    else:
        tl.failed_fields(LOG["s3cfg_still_exists"], fields)

    _assert_cleanup_result(result, "s3cmd configuration")


@pytest.mark.sanity
@pytest.mark.order(6)
def test_build_output_removed(host):
    """Verify build_status.yml removed."""
    tc = TC["build_output_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_output_removed(host)
    fields = [("Build status", result["path"])]

    if result["success"]:
        tl.passed_fields(LOG["build_output_removed_ok"], fields)
    else:
        tl.failed_fields(LOG["build_output_still_exists"], fields)

    _assert_cleanup_result(result, "Build status")


@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_cleaned(host):
    """Verify registry has no images."""
    tc = TC["registry_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_cleaned(host)
    tagged_repos = result.get("repos_with_tags", [])
    fields = [
        ("Registry endpoint", f"http://localhost:{REGISTRY_PORT}"),
        ("Tagged repositories", len(tagged_repos)),
    ]
    fields.extend(
        (f"Repository {index}", repository)
        for index, repository in enumerate(tagged_repos, 1)
    )
    fields.extend(
        ("Query error", error)
        for error in result.get("query_errors", [])
    )

    if result["success"]:
        tl.passed_fields(LOG["registry_cleaned_ok"], fields)
    else:
        tl.failed_fields(
            LOG["registry_still_has_images"].format(
                count=len(tagged_repos),
            ),
            fields,
        )

    _assert_cleanup_result(result, "Registry")


@pytest.mark.sanity
@pytest.mark.order(8)
def test_credentials_removed(host):
    """Verify the credential file and vault key were removed."""
    tc = TC["credentials_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_credentials_removed(host)
    fields = [
        ("Credential artifact", f"{item['path']}: {_resource_state(item)}")
        for item in result["results"]
    ]

    if result["success"]:
        tl.passed_fields(LOG["credentials_removed_ok"], fields)
    else:
        remaining = [item for item in result["results"] if not item["removed"]]
        tl.failed_fields(
            LOG["credentials_still_exist"].format(count=len(remaining)),
            fields,
        )

    _assert_cleanup_result(result, "Credential artifact")
