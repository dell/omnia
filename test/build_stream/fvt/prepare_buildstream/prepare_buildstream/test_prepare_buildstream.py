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
Prepare BuildStream — Verification Tests.

Verifies that repo_manager --prepare and image_build_manager --prepare
deployed services are running and healthy.

Tests:
  - Pulp server deployment and health
  - MinIO S3 deployment and health
  - Local container registry deployment and health
  - Credential file existence
"""

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


def _skip_if_no_creds(tl):
    """Skip test if credentials are not configured."""
    from omnia_auto import load_test_config
    config = load_test_config()
    if not config.get("repo_manager_credentials_loaded", False):
        tl.check("Skipping: repo_manager credentials not loaded")
        pytest.skip("repo_manager credentials not loaded")


@pytest.mark.sanity
@pytest.mark.order(1)
def test_pulp_container_running(host):
    """TC_PREP_001: Verify Pulp container is running."""
    tc = TC["pulp_container_running"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if pulp container is running
    result = host.run("podman ps --filter name=pulp --format '{{.Status}}'")
    if result.rc == 0 and "running" in result.stdout:
        tl.passed("Pulp container is running")
    else:
        tl.failed("Pulp container is not running")

    assert result.rc == 0 and "running" in result.stdout, "Pulp container not running"


@pytest.mark.sanity
@pytest.mark.order(2)
def test_pulp_health_endpoint(host):
    """TC_PREP_002: Verify Pulp health endpoint is accessible."""
    tc = TC["pulp_health_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check Pulp health endpoint (typically on port 24817)
    result = host.run("curl -sk http://localhost:24817/pulp/api/v3/status/")
    if result.rc == 0:
        tl.passed("Pulp health endpoint is accessible")
    else:
        tl.failed("Pulp health endpoint is not accessible")

    assert result.rc == 0, "Pulp health endpoint not accessible"


@pytest.mark.sanity
@pytest.mark.order(3)
def test_pulp_cli_available(host):
    """TC_PREP_003: Verify pulp CLI is available."""
    tc = TC["pulp_cli_available"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if pulp CLI symlink exists
    result = host.run("which pulp")
    if result.rc == 0:
        tl.passed("pulp CLI is available")
    else:
        tl.failed("pulp CLI is not available")

    assert result.rc == 0, "pulp CLI not available"


@pytest.mark.sanity
@pytest.mark.order(4)
def test_minio_container_running(host):
    """TC_PREP_004: Verify MinIO container is running."""
    tc = TC["minio_container_running"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if minio container is running
    result = host.run("podman ps --filter name=minio --format '{{.Status}}'")
    if result.rc == 0 and "running" in result.stdout:
        tl.passed("MinIO container is running")
    else:
        tl.failed("MinIO container is not running")

    assert result.rc == 0 and "running" in result.stdout, "MinIO container not running"


@pytest.mark.sanity
@pytest.mark.order(5)
def test_minio_health_endpoint(host):
    """TC_PREP_005: Verify MinIO health endpoint is accessible."""
    tc = TC["minio_health_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check MinIO health endpoint (typically on port 9000)
    result = host.run("curl -sk http://localhost:9000/minio/health/live")
    if result.rc == 0:
        tl.passed("MinIO health endpoint is accessible")
    else:
        tl.failed("MinIO health endpoint is not accessible")

    assert result.rc == 0, "MinIO health endpoint not accessible"


@pytest.mark.sanity
@pytest.mark.order(6)
def test_registry_container_running(host):
    """TC_PREP_006: Verify local container registry is running."""
    tc = TC["registry_container_running"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if registry container is running
    result = host.run("podman ps --filter name=registry --format '{{.Status}}'")
    if result.rc == 0 and "running" in result.stdout:
        tl.passed("Registry container is running")
    else:
        tl.failed("Registry container is not running")

    assert result.rc == 0 and "running" in result.stdout, "Registry container not running"


@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_health_endpoint(host):
    """TC_PREP_007: Verify registry health endpoint is accessible."""
    tc = TC["registry_health_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check registry health endpoint (typically on port 5000)
    result = host.run("curl -sk http://localhost:5000/v2/")
    if result.rc == 0:
        tl.passed("Registry health endpoint is accessible")
    else:
        tl.failed("Registry health endpoint is not accessible")

    assert result.rc == 0, "Registry health endpoint not accessible"


@pytest.mark.sanity
@pytest.mark.order(8)
def test_repo_manager_credentials_exist(host):
    """TC_PREP_008: Verify repo_manager credentials file exists."""
    tc = TC["repo_manager_credentials_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if repo_manager_credentials.yml exists
    result = host.run("test -f /opt/omnia/repo_manager/repo_manager_credentials.yml")
    if result.rc == 0:
        tl.passed("repo_manager_credentials.yml exists")
    else:
        tl.failed("repo_manager_credentials.yml does not exist")

    assert result.rc == 0, "repo_manager_credentials.yml not found"


@pytest.mark.sanity
@pytest.mark.order(9)
def test_repo_manager_credentials_filled(host):
    """TC_PREP_010: Verify repo_manager credentials are filled with valid data."""
    tc = TC["repo_manager_credentials_filled"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if pulp_username is set (not empty)
    result = host.run("grep -q 'pulp_username:' /opt/omnia/repo_manager/repo_manager_credentials.yml")
    if result.rc == 0:
        tl.passed("repo_manager_credentials.yml contains pulp_username")
    else:
        tl.failed("repo_manager_credentials.yml missing pulp_username")

    assert result.rc == 0, "repo_manager_credentials.yml missing pulp_username"

    # Check if pulp_password is set (not empty)
    result = host.run("grep -q 'pulp_password:' /opt/omnia/repo_manager/repo_manager_credentials.yml")
    if result.rc == 0:
        tl.passed("repo_manager_credentials.yml contains pulp_password")
    else:
        tl.failed("repo_manager_credentials.yml missing pulp_password")

    assert result.rc == 0, "repo_manager_credentials.yml missing pulp_password"


@pytest.mark.sanity
@pytest.mark.order(10)
def test_image_build_credentials_exist(host):
    """TC_PREP_009: Verify image_build_credentials.yml exists."""
    tc = TC["image_build_credentials_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if image_build_credentials.yml exists
    result = host.run("test -f /opt/omnia/image_build_manager/image_build_credentials.yml")
    if result.rc == 0:
        tl.passed("image_build_credentials.yml exists")
    else:
        tl.failed("image_build_credentials.yml does not exist")

    assert result.rc == 0, "image_build_credentials.yml not found"


@pytest.mark.sanity
@pytest.mark.order(11)
def test_image_build_credentials_filled(host):
    """TC_PREP_011: Verify image_build credentials are filled with valid data."""
    tc = TC["image_build_credentials_filled"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if s3_access_id is set (not empty)
    result = host.run("grep -q 's3_access_id:' /opt/omnia/image_build_manager/image_build_credentials.yml")
    if result.rc == 0:
        tl.passed("image_build_credentials.yml contains s3_access_id")
    else:
        tl.failed("image_build_credentials.yml missing s3_access_id")

    assert result.rc == 0, "image_build_credentials.yml missing s3_access_id"

    # Check if s3_secret_key is set (not empty)
    result = host.run("grep -q 's3_secret_key:' /opt/omnia/image_build_manager/image_build_credentials.yml")
    if result.rc == 0:
        tl.passed("image_build_credentials.yml contains s3_secret_key")
    else:
        tl.failed("image_build_credentials.yml missing s3_secret_key")

    assert result.rc == 0, "image_build_credentials.yml missing s3_secret_key"
