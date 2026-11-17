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
Cleanup — Deployment.

Runs ``build_stream.yml --tags cleanup -e postgres_backup=<flag>
-e cleanup_credentials=<flag>`` with the cleanup block of test_config.yml.
Removes GitLab, then the BuildStream API, Postgres (its data too when
postgres_backup is false), NFS state and the credentials (kept when
cleanup_credentials is false). Destructive: explicit only, never part of
a lifecycle.
"""

import pytest

from library.functions import (
    TestLogger,
    cleanup_settings,
    load_test_config,
    report_tag_playbook,
    run_playbook,
)
from library.functions.config_func import to_ansible_extra_vars
from library.vars import TEST_CASES as TC
from library.vars.common_vars import TAG_PLAYBOOK_TIMEOUTS

_TAG = "cleanup"


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(90000)
def test_deploy_cleanup(host):
    """Run build_stream.yml --tags cleanup and require a zero exit code."""
    del host
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    extra_vars = to_ansible_extra_vars(cleanup_settings(load_test_config()))
    rendered = " ".join(f"-e {key}={value}" for key, value in extra_vars.items())
    result = run_playbook(tag=_TAG, timeout=TAG_PLAYBOOK_TIMEOUTS[_TAG], extra_vars=extra_vars)

    failure = report_tag_playbook(tl, _TAG, result, arguments=rendered)
    assert result["success"], failure
