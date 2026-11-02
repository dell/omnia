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
Domain Cleanup — Execution.

Cleans the other domains in the order orchestrator -> image_build_manager ->
repo_manager (the reverse of --prepare-base), each with the flags of its block
under ``domain_cleanup`` in test_config.yml (``cleanup_credentials: false`` keeps
the credential store, via ``--skip-tags`` where the playbook gates it by tag).
The orchestrator cleanup always gets skip_approval=true so it runs unattended.
A fourth block, ``cleanup_main`` (``./omnia.sh --cleanup``), removes the venv and
system env files, i.e. the setup, so it is DISABLED by default.

Right before each block, the paths that must survive are recorded so the
postconditions suite never reports a path that did not exist as deleted.
Destructive: explicit only, never part of a lifecycle; run build_stream cleanup
first. ``domain_cleanup.fail_fast`` stops at the first failed block.
"""

import pytest

from library.functions import (
    TestLogger,
    clear_run_state,
    failure_summary,
    load_test_config,
    precheck_domain_cleanup,
    run_domain_cleanups,
    save_run_state,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_DOMAIN_CLEANUP


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(95000)
def test_precheck_domain_cleanup(host):
    """Check the enabled cleanup blocks and their playbooks (read-only)."""
    tc = TC["precheck_domain_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    clear_run_state(SCENARIO_DOMAIN_CLEANUP)
    result = precheck_domain_cleanup(host, load_test_config())
    if result["success"]:
        tl.passed_fields(LOG["domain_cleanup_precheck_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["domain_cleanup_precheck_failed"].format(
            count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["domain_cleanup_precheck_failed"].format(
        failures=failure_summary(result))


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(95001)
def test_deploy_domain_cleanup(host):
    """Run every enabled domain cleanup in the configured order."""
    tc = TC["deploy_domain_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_domain_cleanups(host, load_test_config(), tl.info)
    save_run_state(SCENARIO_DOMAIN_CLEANUP, result["state"])
    if result["success"]:
        tl.passed_fields(LOG["domain_cleanup_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["domain_cleanup_failed"].format(
            count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["domain_cleanup_failed"].format(
        failures=", ".join(result["failures"]))
