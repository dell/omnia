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
Omnia Main Execution — Verify.

Verification tests that check results AFTER the deploy step ran
``omnia.sh --setup-venv``, ``--init``, and ``--run --tags``.

These tests are read-only — they inspect files, directories, and env
variables but do NOT execute any omnia.sh commands.

TC_EX_006: Verify venv created with ansible
TC_EX_007: Verify system env files installed
TC_EX_008: Verify domain log directories created
TC_EX_009: Verify domain input files staged
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    check_venv_created,
    check_ansible_available,
    check_env_file_installed,
    check_profile_drop_in,
    check_domain_log_dirs,
    check_domain_input_staged,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(10)
def test_verify_venv_exists(host):
    """TC_EX_006: Verify full setup created venv with ansible."""
    tl = TestLogger(
        TEST_NAMES["exec_setup_full"], "TC_EX_006"
    )

    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    result = check_venv_created(host)

    if result["success"]:
        tl.passed(LOG["venv_ok"].format(path=venv_path))
    else:
        tl.failed(LOG["venv_missing"].format(path=venv_path))

    assert result["success"], ASSERT["venv_missing"]

    # Also verify ansible is available
    ansible_result = check_ansible_available(host)
    assert ansible_result["success"], ASSERT["ansible_missing"]


@pytest.mark.sanity
@pytest.mark.order(11)
def test_verify_env_installed(host):
    """TC_EX_007: Verify full setup installed system env files."""
    tl = TestLogger(
        TEST_NAMES["exec_setup_full"], "TC_EX_007"
    )

    env_result = check_env_file_installed(host)
    profile_result = check_profile_drop_in(host)

    both_ok = env_result["success"] and profile_result["success"]

    if both_ok:
        tl.passed(LOG["env_file_ok"].format(
            path="/etc/omnia/omnia.env"
        ))
    else:
        details = []
        if not env_result["success"]:
            details.append(env_result["error"])
        if not profile_result["success"]:
            details.append(profile_result["error"])
        tl.failed("; ".join(details))

    assert env_result["success"], ASSERT["env_file_missing"]
    assert profile_result["success"], ASSERT["profile_missing"]


@pytest.mark.sanity
@pytest.mark.order(12)
def test_verify_domain_log_dirs(host):
    """TC_EX_008: Verify domain init created log directories."""
    tl = TestLogger(
        TEST_NAMES["exec_init_domain"], "TC_EX_008"
    )

    result = check_domain_log_dirs(
        host, domains=["image_build_manager"]
    )

    if result["success"]:
        tl.passed(LOG["log_dirs_ok"].format(
            count=len(result.get("found", []))
        ))
    else:
        tl.failed(LOG["log_dirs_missing"].format(
            count=len(result.get("missing", []))
        ))

    assert result["success"], ASSERT["log_dirs_missing"].format(
        missing=", ".join(result.get("missing", [])),
    )


@pytest.mark.sanity
@pytest.mark.order(13)
def test_verify_domain_input_staged(host):
    """TC_EX_009: Verify domain init staged input files."""
    tl = TestLogger(
        TEST_NAMES["exec_init_domain"], "TC_EX_009"
    )

    result = check_domain_input_staged(
        host, domain="image_build_manager"
    )

    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain="image_build_manager",
            count=result.get("file_count", 0),
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(
            domain="image_build_manager",
        ))

    assert result["success"], ASSERT["input_not_staged"].format(
        domain="image_build_manager",
    )
