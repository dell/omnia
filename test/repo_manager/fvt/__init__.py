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
Functional Verification Tests (FVT) for repo_manager.

Scenarios:
    validate       — Validate input configuration
    deploy         — Deploy Pulp server
    download       — Download and sync packages/repositories
    cleanup        — Cleanup Pulp server and data
    repo_manager   — Full end-to-end verification (validate + deploy + download + status)
"""
