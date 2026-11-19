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

"""
OCI Image Ingest — Orchestrator Acceptance Verification.

Validates the Orchestrator's acceptance of both image build types:
  TC-FVT-049: Orchestrator accepts image-thrillhouse and oci-image-ingest,
              rejects unknown types
"""

import pytest

from library.functions import (
    TestLogger,
)
from library.functions.oci_image_ingest_func import (
    check_orchestrator_build_type,
)
from library.vars import (
    TEST_CASES as TC,
    OCI_ACCEPTED_BUILD_TYPES,
)
from library.messages import TEST_LOG_MSGS as LOG


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(220)
def test_oci_orchestrator_accepts_types(host):
    """Verify Orchestrator accepts both image-thrillhouse and oci-image-ingest."""
    tc = TC["oci_orchestrator_accepts_types"]
    tl = TestLogger(tc["title"], tc["id"])

    # Test accepted types
    for build_type in OCI_ACCEPTED_BUILD_TYPES:
        result = check_orchestrator_build_type(host, build_type)
        assert result["accepted"], (
            f"Orchestrator should accept build type '{build_type}'"
        )

    # Test rejected type
    result = check_orchestrator_build_type(host, "custom-builder")
    assert not result["accepted"], (
        "Orchestrator should reject build type 'custom-builder'"
    )

    tl.passed(LOG["oci_orchestrator_accepted"].format(
        build_type=", ".join(OCI_ACCEPTED_BUILD_TYPES)
    ))
