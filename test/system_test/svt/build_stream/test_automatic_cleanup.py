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

"""Stage automatic_cleanup: the automatic cleanup of the cadence image.

./run_validation.sh svt_build_stream automatic_cleanup. The FVT auto_cleanup
suite marks the cadence image FAILED, runs one cleanup_cron pass and verifies
S3, the registry and the NFS artifacts."""

import pytest

from library.functions import run_svt_test
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.automatic_cleanup
@pytest.mark.order(TC["build_stream_automatic_cleanup_verify"]["order"])
def test_build_stream_automatic_cleanup_verify():
    """Run one automatic cleanup pass on the cadence image and verify it is gone."""
    run_svt_test("build_stream", "automatic_cleanup_verify")
