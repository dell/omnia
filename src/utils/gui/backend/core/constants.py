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
"""Shared constants for Config Editor module."""

# Bundle classification constants
# Single source of truth for bundle categorization across services
FUNCTIONAL_BUNDLES = frozenset({"service_k8s", "slurm_custom", "additional_packages"})
INFRA_BUNDLES = frozenset({"csi_driver_powerscale"})
OS_BUNDLES = frozenset({
    "default_packages", "admin_debug_packages",
    "openldap", "openmpi", "ucx", "ldms", "nfs",
})
ALL_KNOWN_BUNDLES = FUNCTIONAL_BUNDLES | INFRA_BUNDLES | OS_BUNDLES
