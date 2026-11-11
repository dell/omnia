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
Repo Manager Cleanup Repos — Deploy (cleanup_repos tag).

Clean only an explicitly named disposable RPM repository.
Set ``REPO_MANAGER_TEST_CLEANUP_REPO`` to a disposable, fully-qualified
Repo Manager RPM repository identity before selecting this scenario.
"""

import os
import re

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


TARGET_ENVIRONMENT_VARIABLE = "REPO_MANAGER_TEST_CLEANUP_REPO"
TARGET_PATTERN = re.compile(
    r"^(x86_64|aarch64)_rhel_(\d+\.\d+)_([A-Za-z0-9_.-]+)$"
)


def _cleanup_target():
    """Return the explicitly authorized disposable cleanup target."""
    target = os.environ.get(TARGET_ENVIRONMENT_VARIABLE, "").strip()
    assert target, (
        f"{TARGET_ENVIRONMENT_VARIABLE} must name a disposable exact RPM "
        "repository before running cleanup_repos FVT"
    )
    match = TARGET_PATTERN.fullmatch(target)
    assert match and target.lower() != "all", (
        "Selective cleanup FVT requires an exact "
        "<arch>_rhel_<version>_<repo> identity"
    )
    return target, match.group(2)


@pytest.mark.deploy
@pytest.mark.destructive
@pytest.mark.order(0)
def test_deploy_cleanup_repos(host):
    """Deploy exact repository cleanup."""
    tc = TC["exact_repository_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    target, _version = _cleanup_target()
    result = run_playbook(
        tag="cleanup_repos",
        extra_vars={"cleanup_repos": target, "force": "true"},
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="repo_manager.yml", tag="cleanup_repos",
        rc=result["rc"], duration=result["duration"],
    )
