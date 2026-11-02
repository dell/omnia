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

"""SVT_STANDARD_003 - image_build_manager.

FVT steps (fvt_image_build_manager): precheck, validate, prepare and build, each
exec followed by verify."""

import pytest

from library.functions import check_svt_case
from library.vars import TEST_CASES as TC


@pytest.mark.standard
@pytest.mark.image_build_manager
@pytest.mark.order(TC["standard_image_build_manager"]["order"])
def test_standard_image_build_manager():
    """Run the image_build_manager FVT lifecycle up to the image build."""
    check_svt_case("standard", "image_build_manager")
