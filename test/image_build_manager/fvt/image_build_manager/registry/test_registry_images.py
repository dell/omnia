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
Image Builder — Registry and Build Status Verification Tests.

Verify x86_64 images in registry
Verify aarch64 images in registry
Verify build_status.yml reports success
Verify x86_64 functional groups built
Verify aarch64 functional groups built
"""

import pytest

from library.functions import (
    TestLogger,
    check_registry_images,
    check_build_status_file,
    check_functional_groups_built,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SHARED_PATH
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(6)
def test_registry_images_x86_64(host):
    """Verify x86_64 images in registry."""
    tc = TC["ib_registry_x86_64"]
    arch = "x86_64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    url = result.get("registry_url", "unknown")
    lines = [f"Registry: {url}"]
    for img in result.get("found_images", []):
        lines.append(f"\u2713 {img}")
    for img in result.get("missing_images", []):
        lines.append(f"\u2717 {img}: MISSING")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed(LOG["registry_images_ok"].format(arch=arch), details)
    else:
        tl.failed(
            LOG["registry_images_missing"].format(
                count=len(result["missing_images"])
            ),
            details,
        )

    assert result["success"], ASSERT["registry_images_missing"].format(
        registry_url=url,
        missing_list="\n".join(
            f"\u2551   - {i}" for i in result["missing_images"]
        ),
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(7)
def test_registry_images_aarch64(host):
    """Verify aarch64 images in registry."""
    tc = TC["ib_registry_aarch64"]
    arch = "aarch64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_registry_images(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    url = result.get("registry_url", "unknown")
    lines = [f"Registry: {url}"]
    for img in result.get("found_images", []):
        lines.append(f"\u2713 {img}")
    for img in result.get("missing_images", []):
        lines.append(f"\u2717 {img}: MISSING")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed(LOG["registry_images_ok"].format(arch=arch), details)
    else:
        tl.failed(
            LOG["registry_images_missing"].format(
                count=len(result["missing_images"])
            ),
            details,
        )

    assert result["success"], ASSERT["registry_images_missing"].format(
        registry_url=url,
        missing_list="\n".join(
            f"\u2551   - {i}" for i in result["missing_images"]
        ),
    )


@pytest.mark.x86_64
@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(8)
def test_build_status(host):
    """Verify build_status.yml reports success."""
    tc = TC["ib_build_status"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_status_file(host)
    path = result.get("status_path", "")

    if result.get("not_found"):
        tl.skipped(LOG["build_status_not_found"], result.get("error", ""))
        pytest.skip(LOG["build_status_not_found"])

    if result["success"]:
        tl.passed(LOG["build_status_ok"], result["details"])
    else:
        tl.failed(LOG["build_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT["build_status_failed"].format(
        error=result.get("error", ""),
        status_path=path,
        log_path=f"{SHARED_PATH}/log/",
    )


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(9)
def test_functional_groups_built_x86_64(host):
    """Verify x86_64 functional groups built."""
    tc = TC["ib_groups_x86_64"]
    arch = "x86_64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_functional_groups_built(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    lines = []
    for g in result.get("found", []):
        lines.append(f"\u2713 {g}")
    for g in result.get("missing", []):
        lines.append(f"\u2717 {g}: NOT in build output")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed(
            LOG["functional_groups_ok"].format(
                count=len(result["found"]), arch=arch,
            ),
            details,
        )
    else:
        tl.failed(
            LOG["functional_groups_missing"].format(
                count=len(result["missing"])
            ),
            details,
        )

    assert result["success"], result.get("error", "Check failed")


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(10)
def test_functional_groups_built_aarch64(host):
    """Verify aarch64 functional groups built."""
    tc = TC["ib_groups_aarch64"]
    arch = "aarch64"
    tl = TestLogger(tc["title"], tc["id"])
    result = check_functional_groups_built(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    lines = []
    for g in result.get("found", []):
        lines.append(f"\u2713 {g}")
    for g in result.get("missing", []):
        lines.append(f"\u2717 {g}: NOT in build output")
    details = "\n".join(lines)

    if result["success"]:
        tl.passed(
            LOG["functional_groups_ok"].format(
                count=len(result["found"]), arch=arch,
            ),
            details,
        )
    else:
        tl.failed(
            LOG["functional_groups_missing"].format(
                count=len(result["missing"])
            ),
            details,
        )

    assert result["success"], result.get("error", "Check failed")
