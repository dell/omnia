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
Full Cleanup — Deploy (exec entry point).

Cleans every domain enabled in test_config.yml in the fixed order
build_stream -> orchestrator -> image_build_manager -> repo_manager.
Playbooks have no timeout. Each block's flags are passed to its playbook
(``-e`` or, for tag-gated flags such as cleanup_credentials on build_stream
and image_build_manager, ``--skip-tags``). The orchestrator cleanup always
gets skip_approval=true so it runs unattended. cleanup.fail_fast stops at
the first failed playbook.

Right before each playbook the paths that must be preserved are recorded,
so the postconditions suite (verify phase) never reports a path that did
not exist as deleted.
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_full_cleanup,
    save_run_state,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_CLEANUP


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.deploy
@pytest.mark.destructive
@pytest.mark.sanity
@pytest.mark.order(4002)
def test_full_cleanup(host):
    """Run every enabled domain cleanup playbook in the configured order."""
    tc = TC["full_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_full_cleanup(host, load_test_config(), tl.info)
    save_run_state(SCENARIO_CLEANUP, result["state"])

    if result["success"]:
        tl.passed_fields(LOG["cleanup_exec_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["cleanup_exec_failed"].format(count=len(result["failures"])),
                         result["fields"])
    assert result["success"], ASSERT["cleanup_exec_failed"].format(
        failures=", ".join(result["failures"]))
