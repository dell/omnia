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

"""Artifact postconditions produced by full Orchestrator cleanup."""

import pytest
from library.functions import check_cleanup_artifacts

from fvt.result import verify_cleanup

pytestmark = [pytest.mark.sanity, pytest.mark.destructive]


@pytest.mark.order(5)
def test_artifacts_removed_and_inputs_preserved(host):
    """Verify generated state is removed without deleting required inputs."""
    verify_cleanup(
        host, "cleanup_artifacts", "Artifact cleanup", check_cleanup_artifacts
    )
