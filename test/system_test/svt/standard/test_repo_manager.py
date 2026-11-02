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

"""SVT_STANDARD_002 - repo_manager.

FVT step: fvt_repo_manager test (precheck, prepare, execute, status,
user_registry)."""

import pytest

from library.functions import check_svt_case
from library.vars import TEST_CASES as TC


@pytest.mark.standard
@pytest.mark.repo_manager
@pytest.mark.order(TC["standard_repo_manager"]["order"])
def test_standard_repo_manager():
    """Run the repo_manager FVT lifecycle."""
    check_svt_case("standard", "repo_manager")
