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
Deploys GitLab CE on the GitLab host with the project, CI/CD files,
omnia.env, domain inputs and the gitlab-runner.
"""

import pytest

from library.functions import TestLogger, report_tag_playbook, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import TAG_PLAYBOOK_TIMEOUTS

_TAG = "execute"


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(40000)
def test_deploy_execute(host):
    """Run build_stream.yml --tags execute and require a zero exit code."""
    del host
    tc = TC["deploy_execute"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag=_TAG, timeout=TAG_PLAYBOOK_TIMEOUTS[_TAG])

    failure = report_tag_playbook(tl, _TAG, result)
    assert result["success"], failure
