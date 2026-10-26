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
Full Cleanup — Per-Domain Postcondition Verification.

Verifies each domain cleaned by the cleanup exec test against the flags its
playbook received (recorded with the preserve baseline):
  build_stream          BSM API, Postgres (postgres_backup), playbook-watcher,
                        runtime directories, credentials
  orchestrator          OpenCHAMI and OpenLDAP containers/units, credentials
  image_build_manager   MinIO, registry, ports, build status, credentials
  repo_manager          Pulp container and quadlet, data, logs, credentials
Verification runs after every enabled cleanup, so a later domain's cleanup
deleting data an earlier one preserved is reported. A domain that was
disabled or not run (fail_fast) is skipped, as is a run without exec state.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    load_run_state,
    verify_domain_cleanup,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import SCENARIO_CLEANUP


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(4101)
def test_build_stream_cleanup(host):
    """Verify the build_stream cleanup postconditions match its flags."""
    tc = TC["build_stream_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    name = "cleanup_build_stream"
    state = load_run_state(SCENARIO_CLEANUP)
    if not state["success"]:
        message = LOG["state_missing"].format(error=state["error"], scenario=SCENARIO_CLEANUP)
        tl.skipped(message)
        pytest.skip(message)
    result = verify_domain_cleanup(host, name, state["data"]["domains"].get(name, {}))
    if result["skipped"]:
        message = LOG["cleanup_verify_skip"].format(name=name, status=result["status"])
        tl.skipped(message)
        pytest.skip(message)

    if result["success"]:
        tl.passed_fields(LOG["cleanup_verify_ok"].format(name=name), result["fields"])
    else:
        tl.failed_fields(LOG["cleanup_verify_failed"].format(
            name=name, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["cleanup_verify_failed"].format(
        name=name, failures=failure_summary(result))


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(4102)
def test_orchestrator_cleanup(host):
    """Verify the orchestrator cleanup postconditions match its flags."""
    tc = TC["orchestrator_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    name = "cleanup_orchestrator"
    state = load_run_state(SCENARIO_CLEANUP)
    if not state["success"]:
        message = LOG["state_missing"].format(error=state["error"], scenario=SCENARIO_CLEANUP)
        tl.skipped(message)
        pytest.skip(message)
    result = verify_domain_cleanup(host, name, state["data"]["domains"].get(name, {}))
    if result["skipped"]:
        message = LOG["cleanup_verify_skip"].format(name=name, status=result["status"])
        tl.skipped(message)
        pytest.skip(message)

    if result["success"]:
        tl.passed_fields(LOG["cleanup_verify_ok"].format(name=name), result["fields"])
    else:
        tl.failed_fields(LOG["cleanup_verify_failed"].format(
            name=name, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["cleanup_verify_failed"].format(
        name=name, failures=failure_summary(result))


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(4103)
def test_image_build_manager_cleanup(host):
    """Verify the image_build_manager cleanup postconditions match its flags."""
    tc = TC["image_build_manager_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    name = "cleanup_image_build_manager"
    state = load_run_state(SCENARIO_CLEANUP)
    if not state["success"]:
        message = LOG["state_missing"].format(error=state["error"], scenario=SCENARIO_CLEANUP)
        tl.skipped(message)
        pytest.skip(message)
    result = verify_domain_cleanup(host, name, state["data"]["domains"].get(name, {}))
    if result["skipped"]:
        message = LOG["cleanup_verify_skip"].format(name=name, status=result["status"])
        tl.skipped(message)
        pytest.skip(message)

    if result["success"]:
        tl.passed_fields(LOG["cleanup_verify_ok"].format(name=name), result["fields"])
    else:
        tl.failed_fields(LOG["cleanup_verify_failed"].format(
            name=name, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["cleanup_verify_failed"].format(
        name=name, failures=failure_summary(result))


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.cleanup
@pytest.mark.sanity
@pytest.mark.order(4104)
def test_repo_manager_cleanup(host):
    """Verify the repo_manager cleanup postconditions match its flags."""
    tc = TC["repo_manager_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    name = "cleanup_repo_manager"
    state = load_run_state(SCENARIO_CLEANUP)
    if not state["success"]:
        message = LOG["state_missing"].format(error=state["error"], scenario=SCENARIO_CLEANUP)
        tl.skipped(message)
        pytest.skip(message)
    result = verify_domain_cleanup(host, name, state["data"]["domains"].get(name, {}))
    if result["skipped"]:
        message = LOG["cleanup_verify_skip"].format(name=name, status=result["status"])
        tl.skipped(message)
        pytest.skip(message)

    if result["success"]:
        tl.passed_fields(LOG["cleanup_verify_ok"].format(name=name), result["fields"])
    else:
        tl.failed_fields(LOG["cleanup_verify_failed"].format(
            name=name, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["cleanup_verify_failed"].format(
        name=name, failures=failure_summary(result))
