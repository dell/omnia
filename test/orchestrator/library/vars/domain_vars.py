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
Orchestrator — Domain-specific validation variables.

Defines FVT tags, pytest markers, suite directories, and cleanup
exclusions used by ``ValidationRunner`` for this domain.

Includes support for both FVT (Functional Verification Tests) and
NFT (Non-Functional Tests) for comprehensive testing coverage.

To register a new domain, create a similar file in that domain's
``library/vars/`` folder and import it in ``_run.py``.
"""

from typing import Dict, List

# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "orchestrator"

# =====================================================================
# FVT tags — each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: List[str] = [
    "precheck",
    "validate",
    "prepare",
    "deploy",
    "provision",
    "execute",
    "pxeboot",
    "check",
    "cleanup",
    "rollback",
    "playbooks",
    "negative",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "deploy",
    "slurm",
    "kubernetes",
    "nft",
    "performance",
    "idempotency",
    "security",
    "negative",
    "buildstream",
    "destructive",
    "additional_cloud_init",
    "hpc_benchmarks",
    "apptainer",
    "gpu",
    "openldap",
    "storage",
    "vast",
    "powervault",
    "recovery",
    "unit",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": [],
    "validate": [],
    "prepare": ["openchami", "openldap"],
    "deploy": [],
    "provision": ["slurm", "kubernetes"],
    "execute": [],
    "pxeboot": [],
    "check": ["slurm", "kubernetes", "status"],
    "cleanup": ["status"],
    "rollback": [],
    "playbooks": [],
    "negative": [],
}

# Ordered non-destructive lifecycle used by an untagged ``test`` or ``exec``.
# The execute playbook includes provisioning and conditional PXE boot exactly as
# the public orchestrator lifecycle defines it.
ALL_EXEC_TAGS: List[str] = ["precheck", "prepare", "execute"]
ALL_EXEC_MARKER: str = "sanity"
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = ["negative", "destructive"]

# These areas validate already-produced state or source contracts. They do not
# own an Ansible lifecycle operation and must never be presented as deployable.
VERIFY_ONLY_TAGS: List[str] = [
    "check",
    "playbooks",
    "negative",
]

REQUIRED_SUITE_TAGS: List[str] = []
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {}

# Kubernetes and Slurm follow the same provision-suite convention: the
# selected suite contains the one deployment owner for that platform.
SUITE_EXEC_OWNERS: Dict[str, List[str]] = {
    "provision": ["kubernetes", "slurm"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "rollback",
    "negative",
    "pxeboot",
]
