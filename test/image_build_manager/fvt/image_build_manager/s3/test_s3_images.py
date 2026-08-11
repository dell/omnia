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
Image Builder — S3 Verification Tests.

Verify required S3 buckets exist
Verify x86_64 images pushed to S3
Verify aarch64 images pushed to S3
"""

import pytest

from library.functions import (
    TestLogger,
    check_s3_buckets,
    check_s3_bucket_images,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SHARED_PATH
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(3)
def test_s3_buckets_created(host):
    """Verify required S3 buckets exist."""
    tc = TC["ib_s3_buckets"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_buckets(host)

    if result["success"]:
        tl.passed(
            LOG["s3_buckets_ok"].format(count=len(result["found"])),
            result["details"],
        )
    else:
        tl.failed(
            LOG["s3_buckets_missing"].format(
                count=len(result["missing"])
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["s3_buckets_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {b}" for b in result["missing"]
        ),
    )


def _format_s3_details(result):
    """Build detail lines for S3 image results."""
    lines = []
    for fg in result.get("results", []):
        name = fg["functional_group"]
        if fg["success"]:
            lines.append(f"\u2713 {name}:")
            for img in fg.get("image_details", []):
                lines.append(
                    f"    {img['type']}: {img['filename']} "
                    f"({img['size_human']})"
                )
        else:
            missing = fg.get("missing_images", [])
            lines.append(
                f"\u2717 {name}: missing {', '.join(missing)}"
            )
    return "\n".join(lines)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(4)
def test_s3_bucket_images_x86_64(host):
    """Verify x86_64 images pushed to S3."""
    tc = TC["ib_s3_images_x86_64"]
    arch = "x86_64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    details = _format_s3_details(result)
    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"])),
            details,
        )
    else:
        failed = [r for r in result["results"] if not r["success"]]
        tl.failed(
            LOG["s3_images_missing"].format(count=len(failed)),
            details,
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list=details, log_path=f"{SHARED_PATH}/log/",
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(5)
def test_s3_bucket_images_aarch64(host):
    """Verify aarch64 images pushed to S3."""
    tc = TC["ib_s3_images_aarch64"]
    arch = "aarch64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_bucket_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    details = _format_s3_details(result)
    if result["success"]:
        tl.passed(
            LOG["s3_images_ok"].format(count=len(result["results"])),
            details,
        )
    else:
        failed = [r for r in result["results"] if not r["success"]]
        tl.failed(
            LOG["s3_images_missing"].format(count=len(failed)),
            details,
        )

    assert result["success"], ASSERT["s3_images_missing"].format(
        missing_list=details, log_path=f"{SHARED_PATH}/log/",
    )
