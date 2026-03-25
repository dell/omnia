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

"""User Acceptance Tests (UAT) for Build Stream API.

These tests assume the API server is already running and configured.
They focus on API contract validation and user workflows without infrastructure setup.

To run UAT tests:
    pytest tests/uat/ -v -m uat

Required environment variable:
    BUILD_STREAM_AUTH_PASSWORD - Password for OAuth registration
"""
