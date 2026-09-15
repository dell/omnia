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

"""BuildStream NFT fixtures plus compatibility setup for retained source tests."""

import sys
import os
from pathlib import Path

import pytest

# Add build_stream source to path for imports
# Use dynamic path resolution for both local and CI environments
_CURRENT_DIR = Path(__file__).parent.resolve()
# Navigate to the build_stream source directory
# test/build_stream/nft/ -> ../../src/build_stream/
_BUILD_STREAM_SRC = _CURRENT_DIR.parent.parent.parent / "src" / "build_stream"
_BUILD_STREAM_APP = _BUILD_STREAM_SRC / "app"

if str(_BUILD_STREAM_SRC) not in sys.path:
    sys.path.insert(0, str(_BUILD_STREAM_SRC))
if str(_BUILD_STREAM_APP) not in sys.path:
    sys.path.insert(0, str(_BUILD_STREAM_APP))

# Set DATABASE_URL early for test environment
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

if os.environ.get("OMNIA_COMMAND_TYPE") == "nft":
    # The shared validation runner selects only registered NFT cases. Retained
    # source-level tests are not part of this category.
    collect_ignore = ["unit", "others"]

    @pytest.fixture(scope="session")
    def nft_state():
        """Share only test-created pipeline and job identifiers across NFT cases."""
        return {
            "cancelled_pipeline_id": 0,
            "cancelled_job_id": "",
            "active_pipeline_id": 0,
            "active_job_id": "",
            "security_job_id": "",
        }


    @pytest.fixture(scope="session", autouse=True)
    def cleanup_test_pipeline(host, request):
        """Cancel a still-running pipeline created by this NFT session."""
        session_state = request.getfixturevalue("nft_state")
        yield
        pipeline_id = int(session_state.get("active_pipeline_id", 0) or 0)
        if pipeline_id:
            from library.functions import cancel_pipeline  # pylint: disable=import-outside-toplevel

            cancel_pipeline(host, pipeline_id)
else:
    # Compatibility shim for developers running the retained source tests
    # directly with their full development dependencies installed.
    import sqlalchemy.dialects.sqlite.base as sqlite_base
    from sqlalchemy import JSON

    if not hasattr(sqlite_base, "JSONB"):
        sqlite_base.JSONB = JSON
