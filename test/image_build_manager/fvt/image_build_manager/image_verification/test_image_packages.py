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
Image Builder — Image Package Verification Tests.

TC_IB_011: Verify packages in x86_64 S3 images
TC_IB_012: Verify packages in aarch64 S3 images
"""

import pytest

from library.functions import TestLogger, verify_image_packages
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


def _format_pkg_details(result):
    """Build detail lines for package verification results."""
    lines = []
    for fg in result.get("results", []):
        name = fg["functional_group"]
        if fg.get("note"):
            lines.append(f"  {name}: {fg['note']}")
            continue
        expected = fg.get("expected_count", 0)
        found = fg.get("found_count", 0)
        missing = fg.get("missing_count", 0)
        if fg["success"]:
            lines.append(
                f"\u2713 {name}: {found}/{expected} packages verified"
            )
        else:
            lines.append(
                f"\u2717 {name}: {found}/{expected} "
                f"({missing} missing)"
            )
        for pkg in fg.get("package_details", []):
            if pkg["status"] == "installed":
                ver = pkg.get("found", pkg["expected"])
                lines.append(f"    \u2713 {ver}")
            else:
                lines.append(f"    \u2717 MISSING: {pkg['expected']}")
    return "\n".join(lines)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(11)
def test_image_packages_x86_64(host):
    """TC_IB_011: Verify packages in x86_64 S3 images."""
    arch = "x86_64"
    tl = TestLogger(TEST_NAMES["image_packages"].format(arch=arch), "TC_IB_011")
    result = verify_image_packages(host, arch=arch)

    if result.get("prerequisite_failed"):
        tl.failed(LOG["squashfs_tools_not_installed"], result["error"])
        pytest.fail(result["error"])

    if not result["results"]:
        tl.skipped(result.get("details", "No groups configured"))
        pytest.skip(result.get("details", "No groups"))

    details = _format_pkg_details(result)
    if result["success"]:
        tl.passed(LOG["image_packages_ok"].format(arch=arch), details)
    else:
        tl.failed(
            LOG["image_packages_failed"].format(
                count=result["failed_groups"]
            ),
            details,
        )

    assert result["success"], (
        f"{result['failed_groups']} image(s) have missing packages.\n"
        f"{details}"
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(12)
def test_image_packages_aarch64(host):
    """TC_IB_012: Verify packages in aarch64 S3 images."""
    arch = "aarch64"
    tl = TestLogger(TEST_NAMES["image_packages"].format(arch=arch), "TC_IB_012")
    result = verify_image_packages(host, arch=arch)

    if result.get("prerequisite_failed"):
        tl.failed(LOG["squashfs_tools_not_installed"], result["error"])
        pytest.fail(result["error"])

    if not result["results"]:
        tl.skipped(result.get("details", "No groups configured"))
        pytest.skip(result.get("details", "No groups"))

    details = _format_pkg_details(result)
    if result["success"]:
        tl.passed(LOG["image_packages_ok"].format(arch=arch), details)
    else:
        tl.failed(
            LOG["image_packages_failed"].format(
                count=result["failed_groups"]
            ),
            details,
        )

    assert result["success"], (
        f"{result['failed_groups']} image(s) have missing packages.\n"
        f"{details}"
    )
