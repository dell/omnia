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
Image Build Cleanup Images — Verification.

Validates that --tags cleanup_images removed built images:
  - S3 images are deleted (boot-images bucket contents are empty).
  - Registry images are deleted (no tagged images remain).

Note: Docker Distribution keeps repository metadata even after all
manifests are deleted, so ``regctl repo ls`` may still list repo names.
The verification checks for remaining *tags*, not repo entries.
"""

import pytest

from library.functions import (
    TestLogger,
    check_s3_images_removed,
    check_registry_cleaned,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG


@pytest.mark.sanity
@pytest.mark.order(1)
def test_s3_images_cleaned(host):
    """Verify S3 images are deleted after cleanup_images."""
    tc = TC["s3_images_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_images_removed(host)

    if result.get("skipped"):
        tl.skipped(
            LOG["cleanup_images_s3_not_initialized"],
            result["details"],
        )
        pytest.skip(result["details"])
    elif result["success"]:
        tl.passed(LOG["cleanup_images_s3_ok"], result["details"])
    else:
        tl.failed(
            LOG["cleanup_images_s3_still_exist"],
            result["details"],
        )

    assert result["success"], result.get(
        "details", "S3 image cleanup could not be verified"
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_registry_images_cleaned(host):
    """Verify registry images are deleted after cleanup_images."""
    tc = TC["registry_images_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_cleaned(host, require_available=True)

    if result.get("skipped"):
        tl.skipped(
            LOG["cleanup_images_registry_not_initialized"],
            result["details"],
        )
        pytest.skip(result["details"])
    elif result["success"]:
        tl.passed(LOG["cleanup_images_registry_ok"], result["details"])
    else:
        tl.failed(
            LOG["cleanup_images_registry_still_exist"],
            result["details"],
        )

    assert result["success"], (
        result.get("details", "Registry image cleanup could not be verified")
    )
