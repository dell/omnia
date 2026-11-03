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

"""Stage prepare_build_stream: the base domains, BuildStream and GitLab.

./run_validation.sh svt_build_stream prepare_build_stream. Each test runs one
FVT step of test/build_stream: the playbook (exec), then its verification
(verify), for prepare_base, precheck, prepare and execute. At the end
BuildStream runs and the GitLab server, runner and project are up."""

import pytest

from library.functions import run_svt_test
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_prepare_base_exec"]["order"])
def test_build_stream_prepare_base_exec():
    """Run ./omnia.sh --prepare-base (repo_manager, image_build_manager, orchestrator)."""
    run_svt_test("build_stream", "prepare_base_exec")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_prepare_base_verify"]["order"])
def test_build_stream_prepare_base_verify():
    """Verify the base domains prepared by --prepare-base."""
    run_svt_test("build_stream", "prepare_base_verify")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_precheck_exec"]["order"])
def test_build_stream_precheck_exec():
    """Run build_stream.yml --tags precheck."""
    run_svt_test("build_stream", "precheck_exec")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_precheck_verify"]["order"])
def test_build_stream_precheck_verify():
    """Verify the precheck: OIM, containers, credentials, NFS."""
    run_svt_test("build_stream", "precheck_verify")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_prepare_exec"]["order"])
def test_build_stream_prepare_exec():
    """Run build_stream.yml --tags prepare (Postgres, API container, watcher)."""
    run_svt_test("build_stream", "prepare_exec")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_prepare_verify"]["order"])
def test_build_stream_prepare_verify():
    """Verify the BuildStream installation."""
    run_svt_test("build_stream", "prepare_verify")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_execute_exec"]["order"])
def test_build_stream_execute_exec():
    """Run build_stream.yml --tags execute (GitLab server, runner, project)."""
    run_svt_test("build_stream", "execute_exec")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_gitlab_server_verify"]["order"])
def test_build_stream_gitlab_server_verify():
    """Verify the GitLab server."""
    run_svt_test("build_stream", "gitlab_server_verify")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_gitlab_runner_verify"]["order"])
def test_build_stream_gitlab_runner_verify():
    """Verify the GitLab runner."""
    run_svt_test("build_stream", "gitlab_runner_verify")


@pytest.mark.build_stream
@pytest.mark.prepare_build_stream
@pytest.mark.order(TC["build_stream_gitlab_project_verify"]["order"])
def test_build_stream_gitlab_project_verify():
    """Verify the omnia-catalog GitLab project."""
    run_svt_test("build_stream", "gitlab_project_verify")
