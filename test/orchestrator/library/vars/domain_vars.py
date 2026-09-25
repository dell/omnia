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

"""Orchestrator validation-runner configuration."""


# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "orchestrator"

# =====================================================================
# FVT tags — each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: list[str] = [
    "precheck",
    "prepare",
    "provision",
    "pxeboot",
    "cleanup",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: list[str] = [
    "sanity",
    "functional",
    "deploy",
    "openldap",
    "connectivity",
    "cloudinit",
    "kubernetes",
    "slurm",
    "apptainer",
    "image_download",
    "negative",
    "non_disruptive",
    "disruptive",
    "reboot",
    "scheduler_state",
    "destructive",
    "nft",
    "performance",
    "idempotency",
    "security",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: dict[str, list[str]] = {
    "precheck": ["environment", "storage", "dependencies", "inputs"],
    "prepare": ["openchami", "network", "openldap"],
    "provision": ["openchami"],
    "pxeboot": [
        "connectivity",
        "cloudinit",
        "kubernetes_cluster",
        "kubernetes_etcd",
        "kubernetes_storage",
        "kubernetes_recovery",
        "slurm_cluster",
        "slurm_jobs",
        "slurm_ldap",
        "slurm_gpu",
        "slurm_openmpi",
        "slurm_ucx",
        "slurm_infiniband",
        "slurm_recovery",
        "slurm_apptainer",
    ],
    "cleanup": [
        "openchami",
        "openldap",
        "slurm",
        "kubernetes",
        "artifacts",
        "credentials",
    ],
}

# Each lifecycle owns one playbook execution followed by independent checks.
ALL_EXEC_TAGS: list[str] = ["precheck", "prepare", "provision", "pxeboot"]
ALL_EXEC_MARKER: str = "sanity"
ALL_VERIFY_EXCLUDE_MARKERS: list[str] = ["disruptive", "negative"]

VERIFY_ONLY_TAGS: list[str] = []

REQUIRED_SUITE_TAGS: list[str] = []
VERIFY_ONLY_SUITES: dict[str, list[str]] = {}

SUITE_EXEC_OWNERS: dict[str, list[str]] = {}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: list[str] = ["cleanup"]
