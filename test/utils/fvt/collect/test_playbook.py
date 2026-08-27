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
Collect Scenario — Playbook Deployment Tests.

Tests for deploying the collect.yml playbook with various tags.
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    load_test_config,
    get_utils_input_path,
)
from library.vars import TEST_CASES as TC, PLAYBOOK_COLLECT, PLAYBOOK_WORKDIR
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(0)
def test_deploy_collect_setup(host):
    """Deploy collect.yml with setup tag."""
    tc = TC["deploy_collect_setup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_COLLECT, tag="setup")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_COLLECT,
        tag="setup",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(1)
def test_deploy_collect_prepare(host):
    """Deploy collect.yml with prepare tag."""
    tc = TC["deploy_collect_prepare"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_COLLECT, tag="prepare")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_COLLECT,
        tag="prepare",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(2)
def test_deploy_collect_bundle(host):
    """Deploy collect.yml with bundle tag."""
    tc = TC["deploy_collect_bundle"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_COLLECT, tag="bundle")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_COLLECT,
        tag="bundle",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(3)
def test_deploy_collect_full(host):
    """Deploy collect.yml with all tags (full execution)."""
    tc = TC["deploy_collect_full"]
    tl = TestLogger(tc["title"], tc["id"])

    # Run without tag to execute all plays
    result = run_playbook(playbook=PLAYBOOK_COLLECT, tag=None)

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_COLLECT,
        tag="(all)",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )
