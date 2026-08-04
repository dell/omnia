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
Image Builder — Container Verification Tests.

TC_IB_001: Verify S3 storage backend (MinIO or PowerScale)
TC_IB_002: Verify registry container is running
"""

import pytest

from library.functions import (
    TestLogger,
    check_container_running,
    check_s3_containers,
)
from library.vars.common_vars import REGISTRY_CONTAINER
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(1)
def test_s3_storage_backend(host):
    """TC_IB_001: Verify S3 storage backend is operational."""
    tl = TestLogger(TEST_NAMES["storage_backend"], "TC_IB_001")
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


@pytest.mark.x86_64
@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(2)
def test_registry_container(host):
    """TC_IB_002: Verify registry container is running."""
    tl = TestLogger(TEST_NAMES["registry_container_running"], "TC_IB_002")
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
