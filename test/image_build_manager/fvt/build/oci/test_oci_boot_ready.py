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
Image Build Build — OCI Boot-Ready Contract Verification.

Validates FR-1.5 on a real Thrillhouse image in the local registry:
  A complete image is accepted and its kernel version is reported
  Images missing the initramfs, the modules, or the kernel are rejected
  Layers are preserved in order and each base layer is stored once
"""

import pytest

from library.functions import (
    TestLogger,
    check_boot_ready_complete,
    check_boot_ready_incomplete,
    check_layers_preserved,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import BOOT_FIXTURE_KINDS
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(1)
def test_oci_boot_ready_complete(host):
    """Verify a Thrillhouse OCI image is accepted by the boot-ready check."""
    tc = TC["oci_boot_ready_complete"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_boot_ready_complete(host)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["oci_boot_ready_ok"].format(versions=result["details"]))
    else:
        tl.failed(LOG["oci_boot_ready_rejected"].format(kind="complete", path=result["error"]))

    assert result["success"], ASSERT["oci_boot_ready_failed"].format(
        error=result["error"]
    )


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(2)
@pytest.mark.parametrize("kind", sorted(BOOT_FIXTURE_KINDS))
def test_oci_boot_ready_incomplete(host, kind):
    """Verify incomplete OCI images are rejected naming the missing path."""
    tc = TC["oci_boot_ready_incomplete"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_boot_ready_incomplete(host, kind)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["oci_boot_ready_rejected"].format(
                kind=kind, path=result["expected_path"]
            )
        )
    else:
        tl.failed(
            LOG["oci_boot_ready_rejected"].format(
                kind=kind, path=result.get("expected_path", "")
            )
        )

    assert result["success"], ASSERT["oci_boot_ready_failed"].format(
        error=result["error"]
    )


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(3)
def test_oci_layers_preserved(host):
    """Verify OCI layers are preserved and stored once in the registry."""
    tc = TC["oci_layers_preserved"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_layers_preserved(host)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["oci_layers_ok"].format(shared=result["shared"]))
    else:
        tl.failed(LOG["oci_layers_bad"])

    assert result["success"], ASSERT["oci_layers_failed"].format(
        error=result["error"]
    )
