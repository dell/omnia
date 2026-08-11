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
Prepare scenario — ansible-playbook image_build_manager.yml --tags prepare.

Deploys MinIO and registry containers, configures systemd services,
opens firewall ports, sets up s3cmd, and creates S3 buckets.

Suites:
    container/  — Containers, services, firewall, s3cmd, registry
    s3/         — S3 bucket verification
"""
