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
Execute — Deployment.

Runs ``build_stream.yml --tags execute``.
The tag first reads ``gitlab_mode`` from the build_stream input file:

- ``hosted``: deploys GitLab CE on the GitLab host with the project, CI/CD
  files, omnia.env, domain inputs and the gitlab-runner;
- ``external``: configures the customer-managed GitLab through its REST API
  (project, access token, trigger, CI/CD variables and files); GitLab and the
  runner are the operator's.
"""

import pytest

from library.functions import (
    TestLogger,
    check_gitlab_mode_inputs,
    gitlab_settings,
    load_test_config,
    report_check,
    report_tag_playbook,
    run_playbook,
)
from library.functions.probe_func import failure_summary
from library.vars import TEST_CASES as TC
from library.vars.common_vars import TAG_PLAYBOOK_TIMEOUTS

_TAG = "execute"


def _gitlab_mode_result(host):
    """Return the gitlab_mode check using the expected mode of test_config.yml."""
    return check_gitlab_mode_inputs(host, gitlab_settings(load_test_config())["expected_mode"])


@pytest.mark.sanity
@pytest.mark.order(39999)
def test_gitlab_mode_detected(host):
    """Read gitlab_mode from the input file and validate the inputs that mode needs."""
    tc = TC["gitlab_mode_detected"]
    tl = TestLogger(tc["title"], tc["id"])
    result = _gitlab_mode_result(host)
    report_check(tl, result)
    assert result["success"], f"gitlab_mode check failed: {failure_summary(result)}"


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(40000)
def test_deploy_execute(host):
    """Check gitlab_mode, then run build_stream.yml --tags execute (exit code 0)."""
    tc = TC["deploy_execute"]
    tl = TestLogger(tc["title"], tc["id"])
    mode = _gitlab_mode_result(host)
    assert mode["success"], f"gitlab_mode check failed: {failure_summary(mode)}"
    tl.info(f"gitlab_mode: {mode['mode']} (input file validated)")
    result = run_playbook(tag=_TAG, timeout=TAG_PLAYBOOK_TIMEOUTS[_TAG])

    failure = report_tag_playbook(tl, _TAG, result)
    assert result["success"], failure
