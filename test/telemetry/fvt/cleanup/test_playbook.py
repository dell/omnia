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

"""Telemetry cleanup playbook tests are defined in test_cleanup_preservation.py.

Both cleanup deployments and their dependent verification tests must remain in
one module so pytest-order preserves this sequence across the complete flow:

    preservation cleanup -> preservation checks -> default cleanup -> deletion checks

The preservation and default cleanup deployments remain separate test cases.
"""
