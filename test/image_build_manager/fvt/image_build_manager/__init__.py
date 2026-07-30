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
Image Build Manager — Full end-to-end scenario.

Deploy: ansible-playbook image_build_manager.yml (no tags — default
prepare + build flow).

Verifies the complete state: containers, S3 images, registry images,
build status, and image package contents.

Tests:
    TC_IB_000:          Deploy playbook (no tags)
Suites:
    container/          — TC_IB_001-002: MinIO and registry containers
    s3/                 — TC_IB_003-005: S3 buckets and images per arch
    registry/           — TC_IB_006-010: Registry images, build status, groups
    image_verification/ — TC_IB_011-012: Package verification inside images
"""
