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
Build Stream — Cleanup scenario.

Deploy: ansible-playbook build_stream.yml --tags cleanup

Verifies all build_stream resources are removed after cleanup.

Tests:
    TC_CL_001:          Deploy playbook --tags cleanup
Suites:
    cleanup/            — TC_CL_002-004: Post-cleanup verification
"""
