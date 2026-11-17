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
Image Build Cleanup — Deploy.

Deploy image_build_manager --tags cleanup
(-e cleanup_credentials=false when test_config.yml sets cleanup_credentials: false)
"""

import pytest

from library.functions import (
    TestLogger,
    cleanup_credentials_enabled,
    load_test_config,
    run_playbook,
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
def test_deploy_cleanup(host):
    """Deploy image_build_manager --tags cleanup."""
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    extra_vars = None if cleanup_credentials_enabled() else {"cleanup_credentials": "false"}
    result = run_playbook(playbook=PLAYBOOK_ENTRY_POINT, tag="cleanup", extra_vars=extra_vars)

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

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="image_build_manager.yml", tag="cleanup",
        rc=result["rc"], duration=result["duration"],
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=config.get("project_name", "project_default"),
        ),
    )
