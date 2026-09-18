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

Verify packages in x86_64 S3 images
Verify packages in aarch64 S3 images
"""

import pytest

from library.functions import TestLogger, verify_image_packages
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG


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
            if fg.get("error") and not fg.get("package_details"):
                lines.append(f"    ERROR: {fg['error']}")
        for pkg in fg.get("package_details", []):
            if pkg["status"] == "installed":
                ver = pkg.get("found", pkg["expected"])
                lines.append(f"    \u2713 {ver}")
            else:
                lines.append(f"    \u2717 MISSING: {pkg['expected']}")
    return "\n".join(lines)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(13)
def test_image_packages_x86_64(host):
    """Verify packages in x86_64 S3 images."""
    tc = TC["packages_x86_64"]
    arch = "x86_64"
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_image_packages(host, arch=arch)

    if result.get("prerequisite_failed"):
        tl.failed(LOG["squashfs_tools_not_installed"], result["error"])
        pytest.fail(result["error"])

    if not result["results"]:
        tl.skipped(result.get("details", "No groups configured"))
        pytest.skip(result.get("details", "No groups"))

    details = _format_pkg_details(result)
    failure_message = result.get("error") or (
        LOG["image_packages_failed"].format(
            count=result["failed_groups"]
        )
    )
    if result["success"]:
        tl.passed(LOG["image_packages_ok"].format(arch=arch), details)
    else:
        tl.failed(failure_message, details)

    assert result["success"], (
        f"{failure_message}\n{details}"
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(14)
def test_image_packages_aarch64(host):
    """Verify packages in aarch64 S3 images."""
    tc = TC["packages_aarch64"]
    arch = "aarch64"
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_image_packages(host, arch=arch)

    if result.get("prerequisite_failed"):
        tl.failed(LOG["squashfs_tools_not_installed"], result["error"])
        pytest.fail(result["error"])

    if not result["results"]:
        tl.skipped(result.get("details", "No groups configured"))
        pytest.skip(result.get("details", "No groups"))

    details = _format_pkg_details(result)
    failure_message = result.get("error") or (
        LOG["image_packages_failed"].format(
            count=result["failed_groups"]
        )
    )
    if result["success"]:
        tl.passed(LOG["image_packages_ok"].format(arch=arch), details)
    else:
        tl.failed(failure_message, details)

    assert result["success"], (
        f"{failure_message}\n{details}"
    )
