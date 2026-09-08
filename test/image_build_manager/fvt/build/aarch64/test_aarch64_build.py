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
Image Build Build — AArch64-specific Verification.

Verifies passwordless SSH, node architecture and kernel, work directories,
Podman and the builder image, and the regctl installation on the optional
AArch64 build node.
"""

import pytest

from library.functions import (
    TestLogger,
    check_aarch64_architecture,
    check_aarch64_builder_image,
    check_aarch64_regctl_installed,
    check_aarch64_ssh_connectivity,
    check_aarch64_work_dirs,
)
from library.messages import (
    TEST_ASSERT_MSGS as ASSERT,
    TEST_LOG_MSGS as LOG,
)
from library.vars import TEST_CASES as TC


def _skip_optional_aarch64(result, test_logger):
    """Skip an AArch64 check when no optional build node is configured."""
    if result.get("skipped"):
        message = LOG["aarch64_not_configured"]
        test_logger.skipped(message)
        pytest.skip(message)


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(10)
def test_aarch64_ssh_connectivity(host):
    """Verify passwordless SSH from the OIM to the AArch64 node."""
    tc = TC["aarch64_ssh_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_aarch64_ssh_connectivity(host)
    _skip_optional_aarch64(result, tl)

    if result["success"]:
        tl.passed_fields(
            LOG["aarch64_ssh_ok"].format(host=result["host"]),
            {
                "Source OIM": result["source"],
                "Destination": result["destination"],
                "Authentication": result["authentication"],
            },
        )
    else:
        tl.failed(
            LOG["aarch64_ssh_failed"].format(host=result["host"]),
            result["error"],
        )

    assert result["success"], ASSERT["aarch64_ssh_failed"].format(
        host=result["host"], error=result["error"],
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(11)
def test_aarch64_architecture(host):
    """Verify the node architecture and report its kernel information."""
    tc = TC["aarch64_architecture"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_aarch64_architecture(host)
    _skip_optional_aarch64(result, tl)

    if result["success"]:
        tl.passed_fields(
            LOG["aarch64_architecture_ok"].format(host=result["host"]),
            {
                "AArch64 node": result["host"],
                "Architecture": result["architecture"],
                "Kernel": result["kernel"],
            },
        )
    else:
        tl.failed(
            LOG["aarch64_architecture_failed"].format(
                host=result["host"],
            ),
            result["error"],
        )

    assert result["success"], ASSERT["aarch64_architecture_failed"].format(
        host=result["host"], error=result["error"],
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(12)
def test_aarch64_work_dirs(host):
    """Verify and list the work directories on the AArch64 node."""
    tc = TC["aarch64_work_dirs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_aarch64_work_dirs(host)
    _skip_optional_aarch64(result, tl)

    if result["success"]:
        fields = [("AArch64 node", result["host"])]
        fields.extend(
            (f"Directory {index}", directory)
            for index, directory in enumerate(result["directories"], 1)
        )
        tl.passed_fields(
            LOG["aarch64_work_dirs_ok"].format(
                count=len(result["directories"]), host=result["host"],
            ),
            fields,
        )
    else:
        tl.failed(
            LOG["aarch64_work_dirs_failed"].format(
                count=len(result["missing"]), host=result["host"],
            ),
            result["error"],
        )

    assert result["success"], ASSERT["aarch64_work_dirs_failed"].format(
        host=result["host"], error=result["error"],
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(13)
def test_aarch64_builder_image(host):
    """Verify Podman and list builder images on the AArch64 node."""
    tc = TC["aarch64_builder_image"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_aarch64_builder_image(host)
    _skip_optional_aarch64(result, tl)

    if result["success"]:
        fields = [
            ("AArch64 node", result["host"]),
            ("Podman", result["podman_version"]),
        ]
        fields.extend(
            ("Builder image", image) for image in result["images"]
        )
        tl.passed_fields(
            LOG["aarch64_builder_image_ok"].format(host=result["host"]),
            fields,
        )
    else:
        tl.failed(
            LOG["aarch64_builder_image_failed"].format(
                host=result["host"],
            ),
            result["error"],
        )

    assert result["success"], ASSERT["aarch64_builder_image_failed"].format(
        host=result["host"], error=result["error"],
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(14)
def test_aarch64_regctl_installed(host):
    """Verify regctl and report its version and source revision."""
    tc = TC["aarch64_regctl_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_aarch64_regctl_installed(host)
    _skip_optional_aarch64(result, tl)

    if result["success"]:
        tl.passed_fields(
            LOG["aarch64_regctl_ok"].format(host=result["host"]),
            {
                "AArch64 node": result["host"],
                "Version": result["version"],
                "Revision": result["revision"],
            },
        )
    else:
        tl.failed(
            LOG["aarch64_regctl_failed"].format(host=result["host"]),
            result["error"],
        )

    assert result["success"], ASSERT["aarch64_regctl_failed"].format(
        host=result["host"], error=result["error"],
    )
