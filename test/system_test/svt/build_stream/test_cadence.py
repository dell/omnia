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

"""Stage cadence: a new build, one cadence cycle and the cadence pipeline.

./run_validation.sh svt_build_stream cadence. The FVT cadence suite builds a
new image first, then runs the cadence; its image is handed to the automatic
cleanup through the build_stream run state."""

import pytest

from library.functions import run_svt_test
from library.vars import TEST_CASES as TC


@pytest.mark.build_stream
@pytest.mark.cadence
@pytest.mark.order(TC["build_stream_cadence_verify"]["order"])
def test_build_stream_cadence_verify():
    """Build a new image, run one cadence cycle and the cadence pipeline."""
    run_svt_test("build_stream", "cadence_verify")
