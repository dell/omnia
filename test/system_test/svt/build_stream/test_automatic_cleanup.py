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

"""SVT_BUILD_STREAM_003 - automatic cleanup.

FVT step: fvt_build_stream execute verify --suite auto_cleanup. It deletes the
image the cadence case built (marked FAILED first) and verifies S3, the
registry and the NFS artifacts; it skips when the cadence build failed."""

import pytest

from library.functions import check_svt_case
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.automatic_cleanup
@pytest.mark.order(TC["build_stream_automatic_cleanup"]["order"])
def test_build_stream_automatic_cleanup():
    """Run one automatic cleanup pass on the cadence image and verify it is gone."""
    check_svt_case("build_stream", "automatic_cleanup")
