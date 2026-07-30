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
Image Build Build — Registry & Status Verification.

TC_BD_004: Verify x86_64 images in registry after build
TC_BD_005: Verify build_status.yml after build
TC_BD_006: Verify functional groups built
"""

import pytest

from library.functions import (
    TestLogger,
    check_registry_images,
    check_build_status_file,
    check_functional_groups_built,
)
from library.vars.common_vars import SHARED_PATH
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(3)
def test_registry_images_x86_64(host):
    """TC_BD_004: Verify x86_64 images in registry after build."""
    arch = "x86_64"
    tl = TestLogger(TEST_NAMES["registry_images"].format(arch=arch), "TC_BD_004")
    result = check_registry_images(host, arch=arch)
    url = result.get("registry_url", "unknown")

    if result["success"]:
        tl.passed(LOG["registry_images_ok"].format(arch=arch))
    else:
        tl.failed(
            LOG["registry_images_missing"].format(
                count=len(result["missing_images"])
            )
        )

    assert result["success"], ASSERT["registry_images_missing"].format(
        registry_url=url,
        missing_list="\n".join(
            f"\u2551   - {i}" for i in result["missing_images"]
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_build_status(host):
    """TC_BD_005: Verify build_status.yml after build."""
    tl = TestLogger(TEST_NAMES["build_status_file"], "TC_BD_005")
    result = check_build_status_file(host)

    if result["success"]:
        tl.passed(LOG["build_status_ok"], result["details"])
    else:
        tl.failed(LOG["build_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT["build_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
        log_path=f"{SHARED_PATH}/log/",
    )


@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(5)
def test_functional_groups_x86_64(host):
    """TC_BD_006: Verify functional groups built after build tag."""
    arch = "x86_64"
    tl = TestLogger(
        TEST_NAMES["functional_groups_built"].format(arch=arch), "TC_BD_006"
    )
    result = check_functional_groups_built(host, arch=arch)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["functional_groups_ok"].format(
                count=len(result["found"]), arch=arch,
            )
        )
    else:
        tl.failed(
            LOG["functional_groups_missing"].format(
                count=len(result["missing"])
            )
        )

    assert result["success"], result.get("error", "Check failed")
