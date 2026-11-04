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
Precheck — Deployment.

Runs ``build_stream.yml --tags precheck``.
Checks only: OIM identity and admin IP, prerequisite containers
(pulp, minio-server, registry), repo_manager/image_build_manager credential
files and the data path NFS export. Changes nothing on the OIM.
"""

import pytest

from library.functions import TestLogger, report_tag_playbook, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import TAG_PLAYBOOK_TIMEOUTS

_TAG = "precheck"


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(20000)
def test_deploy_precheck(host):
    """Run build_stream.yml --tags precheck and require a zero exit code."""
    del host
    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag=_TAG, timeout=TAG_PLAYBOOK_TIMEOUTS[_TAG])

    failure = report_tag_playbook(tl, _TAG, result)
    assert result["success"], failure
