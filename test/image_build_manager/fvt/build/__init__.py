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
Build scenario — ansible-playbook image_build_manager.yml --tags build.

Builds x86_64 and aarch64 OS images, pushes to S3 and registry,
writes build_status.yml.

Suites:
    s3/         — TC_BD_002-003: S3 image verification per architecture
    registry/   — TC_BD_004-006: Registry images, build status, functional groups
"""
