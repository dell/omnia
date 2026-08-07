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
Omnia Main Setup — Venv Verification.

TC_SU_005: Verify Python venv created at OMNIA_VENV_PATH
TC_SU_006: Verify ansible is available in venv
TC_SU_009: Verify pip packages installed in venv
TC_SU_010: Verify Galaxy collections installed in venv
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    check_venv_created,
    check_ansible_available,
    check_pip_packages,
    check_galaxy_collections,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(4)
def test_venv_created(host):
    """TC_SU_005: Verify Python venv created at OMNIA_VENV_PATH."""
    tl = TestLogger(
        TEST_NAMES["venv_created"], "TC_SU_005"
    )
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    result = check_venv_created(host)

    if result["success"]:
        tl.passed(LOG["venv_ok"].format(path=venv_path))
    else:
        tl.failed(LOG["venv_missing"].format(path=venv_path))

    assert result["success"], ASSERT["venv_missing"].format(
        path=venv_path,
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_ansible_available(host):
    """TC_SU_006: Verify ansible is available in venv."""
    tl = TestLogger(
        TEST_NAMES["ansible_available"], "TC_SU_006"
    )
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    result = check_ansible_available(host)

    if result["success"]:
        tl.passed(LOG["ansible_ok"].format(
            version=result["details"]
        ))
    else:
        tl.failed(LOG["ansible_missing"])

    assert result["success"], ASSERT["ansible_missing"].format(
        path=venv_path,
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_pip_packages_installed(host):
    """TC_SU_009: Verify pip packages installed in venv."""
    tl = TestLogger(
        TEST_NAMES["pip_packages_installed"], "TC_SU_009"
    )
    result = check_pip_packages(host)

    if result["success"]:
        tl.passed(LOG["pip_ok"].format(
            packages=result["details"]
        ))
    else:
        tl.failed(LOG["pip_missing"].format(
            count=len(result.get("missing", []))
        ))

    assert result["success"], ASSERT["pip_packages_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {p}" for p in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_galaxy_collections_installed(host):
    """TC_SU_010: Verify Galaxy collections installed in venv."""
    tl = TestLogger(
        TEST_NAMES["galaxy_collections_installed"], "TC_SU_010"
    )
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    result = check_galaxy_collections(host)

    if result["success"]:
        tl.passed(LOG["galaxy_ok"].format(
            count=result["details"]
        ))
    else:
        tl.failed(LOG["galaxy_missing"])

    assert result["success"], ASSERT["galaxy_missing"].format(
        path=venv_path,
    )
