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
Image Build Manager — Non-Functional Security Tests.

Regression guards for the CWE-732 / CWE-522 hardening that restricts
credential-bearing files to root-only access (0600, root:root). A future
accidental revert to a world-readable mode will fail one of these cases.

Cases:
  IMGBM_NFT_SECURITY_001 — /etc/containers/systemd/minio.container 0600 root:root
  IMGBM_NFT_SECURITY_002 — /root/.s3cfg 0600 root:root
  IMGBM_NFT_SECURITY_003 — no *.container under /etc/containers/systemd/ is o+r
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_permissions,
)
from library.vars import TEST_CASES as TC


MINIO_QUADLET_PATH = "/etc/containers/systemd/minio.container"
S3CFG_PATH = "/root/.s3cfg"


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(10)
def test_minio_quadlet_permissions(host):
    """MinIO quadlet must be 0600 root:root (contains S3 credentials)."""
    tc = TC["minio_quadlet_permissions"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_file_permissions(
        host, MINIO_QUADLET_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(11)
def test_s3cfg_permissions(host):
    """/root/.s3cfg must be 0600 root:root (contains MinIO access key/secret)."""
    tc = TC["s3cfg_permissions"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_file_permissions(
        host, S3CFG_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]
