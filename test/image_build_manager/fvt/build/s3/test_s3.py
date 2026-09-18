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
from library.vars.common_vars import S3_BOOT_IMAGES_BUCKET, SHARED_PATH
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


_ARTIFACT_DISPLAY = {
    "vmlinuz": (0, "Kernel"),
    "initramfs": (1, "Initrd"),
    "rootfs": (2, "Rootfs"),
}


def _success_fields(result: dict, arch: str) -> list:
    """Return ordered fields for every verified S3 artifact."""
    fields = [
        ("Architecture", arch),
        ("Build-status image type", result["image_build_type"]),
        ("S3 bucket", S3_BOOT_IMAGES_BUCKET),
        ("Functional groups verified", len(result["results"])),
    ]
    if result.get("image_build_type_mismatch"):
        fields.append((
            "Current configured image type",
            (
                f"{result['configured_image_build_type']} "
                "(different from the recorded build)"
            ),
        ))
    for group_result in result["results"]:
        functional_group = group_result["functional_group"]
        fields.append(("Functional group", functional_group))
        artifacts = sorted(
            group_result["found_images"],
            key=lambda artifact: _ARTIFACT_DISPLAY[artifact["type"]][0],
        )
        for artifact in artifacts:
            label = _ARTIFACT_DISPLAY[artifact["type"]][1]
            filename = artifact["path"].rsplit("/", 1)[-1]
            fields.append((
                f"  {label}",
                f"{filename} ({artifact['size']})",
            ))
    return fields


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
        tl.passed_fields(
            LOG["s3_images_ok"].format(count=len(result["results"])),
            _success_fields(result, arch),
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
        tl.passed_fields(
            LOG["s3_images_ok"].format(count=len(result["results"])),
            _success_fields(result, arch),
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
