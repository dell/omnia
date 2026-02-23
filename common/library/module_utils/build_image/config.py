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
Configuration constants for build image modules.
"""

# ----------------------------
# Role-specific keys for additional_packages.json
# Used by base_image_package_collector.py, image_package_collector.py and additional_images_collector.py
# ----------------------------
ROLE_SPECIFIC_KEYS = [
    "slurm_control_node",
    "slurm_node",
    "login_node",
    "login_compiler_node",
    "service_kube_control_plane_first",
    "service_kube_control_plane",
    "service_kube_node"
]

# ----------------------------
# Image role keys for container image collection
# Used by additional_images_collector.py for crictl pull operations
# ----------------------------
IMAGE_ROLE_KEYS = [
    "service_kube_control_plane",
    "service_kube_control_plane_first",
    "service_kube_node"
]
