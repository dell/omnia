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

MAIN_FVT_SETUP_V001: Verify omnia.env installed at /etc/omnia/omnia.env
MAIN_FVT_SETUP_V002: Verify /etc/profile.d/omnia-env.sh exists
MAIN_FVT_SETUP_V003: Verify environment variables are set after install
MAIN_FVT_SETUP_V004: Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    check_env_file_installed,
    check_profile_drop_in,
    check_env_vars_loaded,
    check_env_source_validation,
)
from library.messages import (
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
    """MAIN_FVT_SETUP_V001: Verify omnia.env installed at /etc/omnia/omnia.env."""
    tc = TC["env_file_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_env_file_installed(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["env_file_ok"].format(path=SYSTEM_ENV_FILE), {
            "Path": SYSTEM_ENV_FILE,
            "Status": "present and readable",
        })
    else:
        tl.failed_fields(LOG["env_file_missing"].format(path=SYSTEM_ENV_FILE), {
            "Path": SYSTEM_ENV_FILE,
            "Status": result.get("error", "missing or unreadable"),
        })

    assert result["success"], ASSERT["env_file_missing"].format(
        path=SYSTEM_ENV_FILE,
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_profile_drop_in(host):
    """MAIN_FVT_SETUP_V002: Verify /etc/profile.d/omnia-env.sh exists."""
    tc = TC["profile_drop_in"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_profile_drop_in(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["profile_ok"].format(path=PROFILE_DROP_IN), {
            "Path": PROFILE_DROP_IN,
            "Status": "present and readable",
        })
    else:
        tl.failed_fields(LOG["profile_missing"].format(path=PROFILE_DROP_IN), {
            "Path": PROFILE_DROP_IN,
            "Status": result.get("error", "missing or unreadable"),
        })

    assert result["success"], ASSERT["profile_missing"].format(
        path=PROFILE_DROP_IN,
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_env_vars_loaded(host):
    """MAIN_FVT_SETUP_V003: Verify environment variables are set after install."""
    tc = TC["env_vars_loaded"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_env_vars_loaded(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["env_vars_ok"].format(
            count=result["details"].split()[0]
        ), {
            "Environment file": SYSTEM_ENV_FILE,
            "Variables": result["details"],
            "Values displayed": "no (sensitive values protected)",
        })
    else:
        missing = result.get("missing", [])
        tl.failed_fields(LOG["env_vars_missing"].format(count=len(missing)), {
            "Environment file": SYSTEM_ENV_FILE,
            "Missing variables": ", ".join(missing) or "unknown",
        })

    assert result["success"], ASSERT["env_vars_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {v}" for v in result.get("missing", [])
        ),
    )


@pytest.mark.regression
@pytest.mark.order(4)
def test_env_source_validation(host):
    """MAIN_FVT_SETUP_V004: Verify env source validation rejects empty SYSTEM_ADMIN_NIC_IPV4."""
    tc = TC["env_source_validation"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_env_source_validation(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["env_source_validation_ok"], {
            "Validation function": "validate_env_source",
            "Invalid input": "SYSTEM_ADMIN_NIC_IPV4 is empty",
            "Return code": result.get("rc", "unknown"),
        })
    else:
        tl.failed_fields(LOG["env_source_validation_failed"].format(
            rc=result.get("rc", "?")
        ), {
            "Validation function": "validate_env_source",
            "Expected": "non-zero return code",
            "Actual return code": result.get("rc", "unknown"),
        })

    assert result["success"], (
        ASSERT["env_source_validation_failed"]
    )
