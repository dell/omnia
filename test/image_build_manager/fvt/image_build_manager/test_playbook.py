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
Image Build Manager — Deploy (full playbook, no tags).

Deploy image_build_manager.yml without tags (prepare + build)
"""

import pytest

from library.functions import (
    TestLogger, run_playbook, load_test_config, collect_build_logs,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    BUILD_LOG_PATH,
    SHARED_PATH,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_image_build_manager(host):
    """Deploy image_build_manager.yml (default: prepare + build)."""
    tc = TC["deploy_full"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(playbook=PLAYBOOK_ENTRY_POINT)

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        # Collect build logs for diagnostics
        logs = collect_build_logs(host, max_lines=50)
        log_snippet = logs.get("log_output", "") if logs["success"] else ""
        error_detail = result.get("error", "See playbook output above")
        if log_snippet:
            error_detail += f"\n\n--- Build Log ({logs['log_path']}) ---\n{log_snippet}"
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            error_detail,
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="image_build_manager.yml", tag="(none)",
        rc=result["rc"], duration=result["duration"],
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=config.get("project_name", "project_default"),
        ),
    )
