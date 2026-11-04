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
Omnia Main Cleanup — Verification (read-only, after test_deploy_cleanup).

MAIN_FVT_CLEANUP_V001: /etc/omnia/omnia.env and the profile drop-in removed
MAIN_FVT_CLEANUP_V002: Omnia venv removed
MAIN_FVT_CLEANUP_V003: omnia-cli and its Bash completion removed
MAIN_FVT_CLEANUP_V004: activate-omnia.sh and the dependency cache removed
MAIN_FVT_CLEANUP_V005: OMNIA_DATA_PATH removed with --all, kept without it

Runtime paths fall back to src/main/omnia.env once /etc/omnia/omnia.env is gone.
"""

import pytest

from library.functions import (
    TestLogger,
    check_cleanup_data_path,
    check_cleanup_removed,
    load_test_config,
)
from library.functions.omnia_main_func import is_running_from_omnia_venv
from library.messages import TEST_ASSERT_MSGS as ASSERT
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_SKIP_VENV_MSG = (
    "Skipped: running from omnia production venv — "
    "test_deploy_cleanup did not run"
)


def _verify_removed(host, tc_key: str, group: str) -> None:
    """Assert that omnia.sh --cleanup removed every path of ``group``."""
    tc = TC[tc_key]
    tl = TestLogger(tc["title"], tc["id"])
    if is_running_from_omnia_venv(host):
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)
    result = check_cleanup_removed(host, group)
    tl.bind_result(result)
    if result["success"]:
        tl.passed_fields(LOG["cleanup_removed_ok"].format(count=len(result["paths"])), {
            "Paths": result["details"],
            "Status": "absent",
        })
    else:
        tl.failed_fields(LOG["cleanup_removed_failed"].format(count=len(result["present"])), {
            "Paths": result["details"],
            "Still present": ", ".join(result["present"]),
        })
    assert result["success"], ASSERT["cleanup_paths_present"].format(
        present_list="\n".join(f"║   - {path}" for path in result["present"]),
    )


@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(1)
def test_cleanup_system_env_removed(host):
    """MAIN_FVT_CLEANUP_V001: /etc/omnia/omnia.env and the profile drop-in removed."""
    _verify_removed(host, "cleanup_system_env_removed", "system_env")


@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(2)
def test_cleanup_venv_removed(host):
    """MAIN_FVT_CLEANUP_V002: Omnia venv removed."""
    _verify_removed(host, "cleanup_venv_removed", "venv")


@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(3)
def test_cleanup_cli_removed(host):
    """MAIN_FVT_CLEANUP_V003: omnia-cli and its Bash completion removed."""
    _verify_removed(host, "cleanup_cli_removed", "cli")


@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(4)
def test_cleanup_data_helpers_removed(host):
    """MAIN_FVT_CLEANUP_V004: activate-omnia.sh and the dependency cache removed."""
    _verify_removed(host, "cleanup_data_helpers_removed", "data_helpers")


@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(5)
def test_cleanup_data_path(host):
    """MAIN_FVT_CLEANUP_V005: OMNIA_DATA_PATH removed with --all, kept without it."""
    tc = TC["cleanup_data_path"]
    tl = TestLogger(tc["title"], tc["id"])
    if is_running_from_omnia_venv(host):
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)
    cleanup_all = load_test_config().get("cleanup_all", False)
    if not isinstance(cleanup_all, bool):
        tl.failed(LOG["exec_cleanup_invalid_flag"].format(value=cleanup_all))
        pytest.fail(LOG["exec_cleanup_invalid_flag"].format(value=cleanup_all))
    option = "--cleanup --all" if cleanup_all else "--cleanup"
    expected = "absent" if cleanup_all else "present"
    result = check_cleanup_data_path(host, cleanup_all)
    tl.bind_result(result)
    state = "present" if result["exists"] else "absent"
    if result["success"]:
        tl.passed(LOG["cleanup_data_path_ok"].format(
            path=result["path"], state=state, option=option))
    else:
        tl.failed(LOG["cleanup_data_path_failed"].format(
            path=result["path"], state=state, expected=expected, option=option))
    assert result["success"], ASSERT["cleanup_data_path_state"].format(
        path=result["path"], state=state, expected=expected, option=option)
