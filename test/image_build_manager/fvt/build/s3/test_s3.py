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

TC_BD_002: Verify x86_64 images pushed to S3 after build
TC_BD_003: Verify aarch64 images pushed to S3 after build
"""

import pytest

from library.functions import TestLogger, check_s3_bucket_images
from library.vars.common_vars import SHARED_PATH
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(1)
def test_s3_images_x86_64(host):
    """TC_BD_002: Verify x86_64 images pushed to S3 after build."""
    arch = "x86_64"
    tl = TestLogger(TEST_NAMES["s3_bucket_images"].format(arch=arch), "TC_BD_002")
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"]))
        )
    else:
        failed = [r for r in result["results"] if not r["success"]]
        tl.failed(
            LOG["s3_images_missing"].format(count=len(failed))
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list="See output above",
        log_path=f"{SHARED_PATH}/log/",
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(2)
def test_s3_images_aarch64(host):
    """TC_BD_003: Verify aarch64 images pushed to S3 after build."""
    arch = "aarch64"
    tl = TestLogger(TEST_NAMES["s3_bucket_images"].format(arch=arch), "TC_BD_003")
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"]))
        )
    else:
        failed = [r for r in result["results"] if not r["success"]]
        tl.failed(
            LOG["s3_images_missing"].format(count=len(failed))
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list="See output above",
        log_path=f"{SHARED_PATH}/log/",
    )
