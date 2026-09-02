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
Image Build Build — S3 Image Verification.

Verify x86_64 images pushed to S3 after build
Verify aarch64 images pushed to S3 after build
"""

import pytest

from library.functions import TestLogger, check_s3_bucket_images
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SHARED_PATH
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


def _format_missing_list(result):
    """Format exact missing-path diagnostics for the assertion panel."""
    error = result.get("error") or result.get("details") or "Unknown S3 error"
    return "\n".join(
        f"\u2551   - {line}" for line in str(error).splitlines()
    )


def _failure_message(result):
    """Return an accurate failure summary for group and prerequisite errors."""
    failed_count = sum(
        1 for item in result.get("results", []) if not item["success"]
    )
    if failed_count:
        return LOG["s3_images_missing"].format(count=failed_count)
    return "S3 image verification could not be completed"


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(1)
def test_s3_images_x86_64(host):
    """Verify x86_64 images pushed to S3 after build."""
    tc = TC["s3_images_x86_64"]
    arch = "x86_64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"]))
        )
    else:
        tl.failed(
            _failure_message(result),
            result.get("error"),
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list=_format_missing_list(result),
        log_path=f"{SHARED_PATH}/log/",
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(2)
def test_s3_images_aarch64(host):
    """Verify aarch64 images pushed to S3 after build."""
    tc = TC["s3_images_aarch64"]
    arch = "aarch64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"]))
        )
    else:
        tl.failed(
            _failure_message(result),
            result.get("error"),
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list=_format_missing_list(result),
        log_path=f"{SHARED_PATH}/log/",
    )
