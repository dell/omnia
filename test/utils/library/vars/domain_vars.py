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
Utils — Domain-specific validation variables.

Defines FVT tags, pytest markers, suite directories, and cleanup
exclusions used by ``ValidationRunner`` for this domain.
"""

from typing import Dict, List

# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "utils"

# =====================================================================
# FVT tags — each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: List[str] = [
    "precheck",
    "setup",
    "collect",
    "install_os",
    "backup_oim_logs",
    "slurm_config_util",
    "cleanup_logs",
    "cleanup_install_os",
    "cleanup",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "negative",
    "deploy",
    "x86_64",
    "aarch64",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": ["connectivity"],
    "setup": ["setup"],
    "collect": ["log_collector"],
    "install_os": ["install_os", "iso"],
    "backup_oim_logs": ["backup_oim_logs"],
    "slurm_config_util": ["slurm_config_util"],
    "cleanup_logs": ["cleanup_logs"],
    "cleanup_install_os": ["cleanup_install_os"],
    "cleanup": ["cleanup"],
}

# Ordered, non-destructive lifecycle used by an untagged ``exec`` or ``test``.
ALL_EXEC_TAGS: List[str] = ["precheck", "setup", "collect", "install_os"]
ALL_EXEC_MARKER: str = ""
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = ["negative", "destructive"]

# These scenarios validate existing state and own no deployment trigger.
VERIFY_ONLY_TAGS: List[str] = []

# Tags that require an explicit --suite argument.
REQUIRED_SUITE_TAGS: List[str] = []

# Suites that own a deployment lifecycle per tag.
SUITE_EXEC_OWNERS: Dict[str, List[str]] = {}

# Suites that only verify (no playbook deploy step of their own).
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "cleanup_logs",
    "cleanup_install_os",
    "backup_oim_logs",
    "slurm_config_util",
]
