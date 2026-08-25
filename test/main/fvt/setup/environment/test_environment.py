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
Omnia Main Setup — Environment Verification.

TC_SU_002: Verify omnia.env installed at /etc/omnia/omnia.env
TC_SU_003: Verify /etc/profile.d/omnia-env.sh exists
TC_SU_004: Verify environment variables are set after install
TC_SU_011: Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    check_env_file_installed,
    check_profile_drop_in,
    check_env_vars_loaded,
    check_env_source_validation,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.common_vars import (
    SYSTEM_ENV_FILE,
    PROFILE_DROP_IN,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_env_file_installed(host):
    """TC_SU_002: Verify omnia.env installed at /etc/omnia/omnia.env."""
    tl = TestLogger(
        TEST_NAMES["env_file_installed"], "TC_SU_002"
    )
    result = check_env_file_installed(host)

    if result["success"]:
        tl.passed(LOG["env_file_ok"].format(
            path=SYSTEM_ENV_FILE
        ))
    else:
        tl.failed(LOG["env_file_missing"].format(
            path=SYSTEM_ENV_FILE
        ))

    assert result["success"], ASSERT["env_file_missing"].format(
        path=SYSTEM_ENV_FILE,
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_profile_drop_in(host):
    """TC_SU_003: Verify /etc/profile.d/omnia-env.sh exists."""
    tl = TestLogger(
        TEST_NAMES["profile_drop_in"], "TC_SU_003"
    )
    result = check_profile_drop_in(host)

    if result["success"]:
        tl.passed(LOG["profile_ok"].format(
            path=PROFILE_DROP_IN
        ))
    else:
        tl.failed(LOG["profile_missing"].format(
            path=PROFILE_DROP_IN
        ))

    assert result["success"], ASSERT["profile_missing"].format(
        path=PROFILE_DROP_IN,
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_env_vars_loaded(host):
    """TC_SU_004: Verify environment variables are set after install."""
    tl = TestLogger(
        TEST_NAMES["env_vars_loaded"], "TC_SU_004"
    )
    result = check_env_vars_loaded(host)

    if result["success"]:
        tl.passed(LOG["env_vars_ok"].format(
            count=result["details"].split()[0]
        ))
    else:
        missing = result.get("missing", [])
        tl.failed(LOG["env_vars_missing"].format(
            count=len(missing)
        ))

    assert result["success"], ASSERT["env_vars_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {v}" for v in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_env_source_validation(host):
    """TC_SU_011: Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4."""
    tl = TestLogger(
        TEST_NAMES["env_source_validation"], "TC_SU_011"
    )
    result = check_env_source_validation(host)

    if result["success"]:
        tl.passed(LOG["env_source_validation_ok"])
    else:
        tl.failed(LOG["env_source_validation_failed"].format(
            rc=result.get("rc", "?")
        ))

    assert result["success"], (
        ASSERT["env_source_validation_failed"]
    )
