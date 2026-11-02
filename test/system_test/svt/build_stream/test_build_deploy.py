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

"""SVT_BUILD_STREAM_001 - build and deploy.

FVT steps (fvt_build_stream): prepare_base test, precheck test, prepare test,
execute exec, the gitlab_server / gitlab_runner / gitlab_project verify suites,
then execute verify --marker automatic_execution (build_automatic and
deploy_automatic in one process, so the deploy uses the image the build made)."""

import pytest

from library.functions import check_svt_case
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.build_deploy
@pytest.mark.order(TC["build_stream_build_deploy"]["order"])
def test_build_stream_build_deploy():
    """Bring up the base domains, BuildStream and GitLab, then build and deploy."""
    check_svt_case("build_stream", "build_deploy")
