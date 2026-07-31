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
"""API v1 routes module."""

from .catalog_routes import router as catalog_router
from .wizard_routes import router as wizard_router
from .adapter_policy_routes import router as adapter_policy_router
from .catalog_editor_routes import router as catalog_editor_router
from .local_repo_routes import router as local_repo_router

__all__ = [
    "catalog_router",
    "wizard_router",
    "adapter_policy_router",
    "catalog_editor_router",
    "local_repo_router"
]
