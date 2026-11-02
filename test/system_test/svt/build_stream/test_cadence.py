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

"""SVT_BUILD_STREAM_002 - cadence.

FVT step: fvt_build_stream execute verify --suite cadence. The cadence test
builds its own image first; its outcome is recorded as build_stream run state
for the automatic cleanup."""

import pytest

from library.functions import check_svt_case
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.cadence
@pytest.mark.order(TC["build_stream_cadence"]["order"])
def test_build_stream_cadence():
    """Build the cadence image and run one cadence cycle and pipeline."""
    check_svt_case("build_stream", "cadence")
