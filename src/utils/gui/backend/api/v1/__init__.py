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
"""API v1 module."""

from .dependencies import (
    get_settings_dependency,
    get_adapter_policy_service,
    get_catalog_editor_service,
    get_wizard_generator_service,
    get_local_repo_generator_service,
    get_os_package_service,
    get_software_config_service,
)

__all__ = [
    "get_settings_dependency",
    "get_adapter_policy_service",
    "get_catalog_editor_service",
    "get_wizard_generator_service",
    "get_local_repo_generator_service",
    "get_os_package_service",
    "get_software_config_service",
]
