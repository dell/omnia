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

"""Minimal conftest for build_stream NFT unit tests."""

import sys
import os

# Add build_stream source to path for imports
# Use absolute path for local development
_BUILD_STREAM_SRC = "/root/Documents/omnia/src/build_stream"
if _BUILD_STREAM_SRC not in sys.path:
    sys.path.insert(0, _BUILD_STREAM_SRC)

# Set DATABASE_URL early for test environment
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
