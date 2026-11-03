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

"""Stage build_deploy: automatic build pipeline, then the deploy of its image.

./run_validation.sh svt_build_stream build_deploy. One FVT run of the
automatic_execution marker (build_automatic and deploy_automatic in one
process, so the deploy uses the image the build made)."""

import pytest

from library.functions import run_svt_test
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.build_deploy
@pytest.mark.order(TC["build_stream_build_deploy_verify"]["order"])
def test_build_stream_build_deploy_verify():
    """Commit a catalog (automatic build pipeline), then deploy the image it built."""
    run_svt_test("build_stream", "build_deploy_verify")
