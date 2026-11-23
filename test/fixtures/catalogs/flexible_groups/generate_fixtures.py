#!/usr/bin/env python3
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
"""Generate positive and negative catalog fixtures for flexible functional groups."""

import copy
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent

BASE_PACKAGES = {
    "bash": {
        "name": "bash",
        "packagetype": "rpm",
        "sources": [
            {
                "architecture": "x86_64",
                "reponame": "baseos",
                "name": "rhel",
                "version": ["10.2", "10.0"],
            },
            {"architecture": "aarch64", "reponame": "baseos", "name": "rhel", "version": ["10.0"]},
        ],
    },
    "chrony": {
        "name": "chrony",
        "packagetype": "rpm",
        "sources": [
            {
                "architecture": "x86_64",
                "reponame": "baseos",
                "name": "rhel",
                "version": ["10.2", "10.0"],
            },
            {"architecture": "aarch64", "reponame": "baseos", "name": "rhel", "version": ["10.0"]},
        ],
    },
    "ghcr_io/openchami/image_thrillhouse": {
        "name": "ghcr.io/openchami/image-thrillhouse",
        "packagetype": "image",
        "tag": "v0.0.26",
        "sources": [
            {
                "architecture": "x86_64",
                "registry": "ghcr.io",
                "name": "rhel",
                "version": ["10.2", "10.0"],
            },
            {"architecture": "aarch64", "registry": "ghcr.io", "name": "rhel", "version": ["10.0"]},
        ],
    },
    "tcpdump": {
        "name": "tcpdump",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "baseos", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "vim": {
        "name": "vim-enhanced",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "appstream", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "munge": {
        "name": "munge",
        "packagetype": "rpm",
        "sources": [
            {
                "architecture": "x86_64",
                "reponame": "appstream",
                "name": "rhel",
                "version": ["10.2"],
            },
            {
                "architecture": "aarch64",
                "reponame": "appstream",
                "name": "rhel",
                "version": ["10.0"],
            },
        ],
    },
    "nginx": {
        "name": "nginx",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "appstream", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "postgresql": {
        "name": "postgresql-server",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "appstream", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "python3": {
        "name": "python3",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "baseos", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "redis": {
        "name": "redis",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "appstream", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "prometheus_node_exporter": {
        "name": "node_exporter",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "appstream", "name": "rhel", "version": ["10.2"]}
        ],
    },
    "nfs_utils": {
        "name": "nfs-utils",
        "packagetype": "rpm",
        "sources": [
            {"architecture": "x86_64", "reponame": "baseos", "name": "rhel", "version": ["10.0"]}
        ],
    },
    "openmpi": {
        "name": "openmpi",
        "packagetype": "rpm",
        "sources": [
            {
                "architecture": "aarch64",
                "reponame": "appstream",
                "name": "rhel",
                "version": ["10.0"],
            }
        ],
    },
}

BASE_GROUPS = {
    "baseos_group_10.2": {
        "name": "baseos_group_10.2",
        "type": "baseos",
        "os": "rhel",
        "os_version": "10.2",
        "description": "Minimal OS packages for RHEL 10.2",
        "components": ["bash", "chrony", "ghcr_io/openchami/image_thrillhouse"],
    },
    "baseos_group_10.0": {
        "name": "baseos_group_10.0",
        "type": "baseos",
        "os": "rhel",
        "os_version": "10.0",
        "description": "Minimal OS packages for RHEL 10.0",
        "components": ["bash", "chrony", "ghcr_io/openchami/image_thrillhouse"],
    },
    "admin_debug_group": {
        "name": "admin_debug_group",
        "type": "group",
        "description": "Admin diagnostic utilities",
        "components": ["tcpdump", "vim"],
    },
    "slurm_group": {
        "name": "slurm_group",
        "type": "group",
        "description": "Slurm workload manager components",
        "components": ["munge"],
    },
    "web_group": {
        "name": "web_group",
        "type": "group",
        "description": "Web service components",
        "components": ["nginx"],
    },
    "db_group": {
        "name": "db_group",
        "type": "group",
        "description": "Database server components",
        "components": ["postgresql"],
    },
    "analytics_group": {
        "name": "analytics_group",
        "type": "group",
        "description": "Data analytics runtime",
        "components": ["python3"],
    },
    "cache_group": {
        "name": "cache_group",
        "type": "group",
        "description": "In-memory cache services",
        "components": ["redis"],
    },
    "monitoring_group": {
        "name": "monitoring_group",
        "type": "group",
        "description": "Telemetry monitoring exporter",
        "components": ["prometheus_node_exporter"],
    },
    "storage_group": {
        "name": "storage_group",
        "type": "group",
        "description": "Network storage mount client",
        "components": ["nfs_utils"],
    },
    "worker_group": {
        "name": "worker_group",
        "type": "group",
        "description": "HPC parallel compute worker",
        "components": ["openmpi"],
    },
}


def _prune_unused(layers, groups, packages):
    """Keep only referenced groups and packages to prevent orphan noise."""
    needed_groups = set()
    for layer in layers:
        needed_groups.update(layer.get("components", []))

    pruned_groups = {k: v for k, v in groups.items() if k in needed_groups}

    needed_packages = set()
    for g in pruned_groups.values():
        needed_packages.update(g.get("components", []))

    pruned_packages = {k: v for k, v in packages.items() if k in needed_packages}

    # Ensure schema constraint: at least 1 group and 1 package
    if not pruned_groups:
        pruned_groups = {"baseos_group_10.2": copy.deepcopy(BASE_GROUPS["baseos_group_10.2"])}
    if not pruned_packages:
        pruned_packages = {"bash": copy.deepcopy(BASE_PACKAGES["bash"])}

    return pruned_groups, pruned_packages


def make_catalog(name, identifier, layers, groups=None, packages=None, extra=None, prune=True):
    """Create a catalog fixture with optional pruning."""
    raw_groups = groups or copy.deepcopy(BASE_GROUPS)
    raw_packages = packages or copy.deepcopy(BASE_PACKAGES)

    if prune:
        final_groups, final_packages = _prune_unused(layers, raw_groups, raw_packages)
    else:
        final_groups, final_packages = raw_groups, raw_packages

    cat = {
        "name": name,
        "version": "1.0",
        "schema_version": 2,
        "identifier": identifier,
        "description": f"Catalog fixture: {name}",
        "functionallayer": layers,
        "groups": final_groups,
        "packages": final_packages,
    }
    if extra:
        cat.update(extra)
    return {"catalog": cat}


def generate_all_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Positive: Manual valid FG catalog (exactly 10 FG groups + standard groups)
    valid_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "slurm_control_node_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "slurm_group"],
        },
        {
            "name": "slurm_node_rhel_10_0_aarch64",
            "components": ["baseos_group_10.0", "worker_group"],
        },
        # Exactly 10 flexible groups
        {"name": "fg_webserver_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "web_group"]},
        {"name": "fg_database_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "db_group"]},
        {
            "name": "fg_analytics_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "analytics_group"],
        },
        {"name": "fg_cache_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "cache_group"]},
        {"name": "fg_ingress_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "web_group"]},
        {
            "name": "fg_monitoring_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "monitoring_group"],
        },
        {
            "name": "fg_storage_agent_rhel_10_0_x86_64",
            "components": ["baseos_group_10.0", "storage_group"],
        },
        {
            "name": "fg_ml_inference_rhel_10_0_x86_64",
            "components": ["baseos_group_10.0", "analytics_group"],
        },
        {
            "name": "fg_compute_worker_rhel_10_0_aarch64",
            "components": ["baseos_group_10.0", "worker_group"],
        },
        {
            "name": "fg_mpi_worker_rhel_10_0_aarch64",
            "components": ["baseos_group_10.0", "worker_group"],
        },
    ]
    manual_valid = make_catalog(
        "Manual Valid Flexible Groups Catalog", "manual-valid-fg-catalog", valid_layers
    )
    (FIXTURES_DIR / "manual_valid_fg_catalog.json").write_text(
        json.dumps(manual_valid, indent=2) + "\n"
    )

    # 2. Positive: Reviewed generated FG catalog (ER-BSM-001 review gate evidence)
    reviewed_generated = make_catalog(
        "Reviewed Generated Flexible Groups Catalog",
        "reviewed-generated-fg-catalog",
        valid_layers,
        extra={
            "generated": True,
            "authoring": {
                "generated": True,
                "tool": "catalog-generation",
                "contract": "ER-BSM-001",
            },
            "operator_review": {
                "approved": True,
                "status": "approved",
                "reviewer": "cluster-admin@omnia.test",
                "review_date": "2026-10-06T12:00:00Z",
                "authoring_contract": ("ER-BSM-001-nersc-ai-skills-catalog-authoring"),
                "notes": (
                    "Reviewed and approved by operator. " "Passed all semantic and boundary checks."
                ),
            },
        },
    )
    (FIXTURES_DIR / "reviewed_generated_fg_catalog.json").write_text(
        json.dumps(reviewed_generated, indent=2) + "\n"
    )

    # 3. Negative: Missing mandatory fg_ prefix on flexible group
    invalid_prefix_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "webserver_flexible_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "web_group"],
        },
    ]
    invalid_prefix = make_catalog(
        "Invalid Missing fg_ Prefix Catalog", "invalid-prefix-fg-catalog", invalid_prefix_layers
    )
    (FIXTURES_DIR / "invalid_missing_prefix_catalog.json").write_text(
        json.dumps(invalid_prefix, indent=2) + "\n"
    )

    # 4. Negative: Count exceeded (>10 flexible groups)
    eleven_fg_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "slurm_control_node_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "slurm_group"],
        },
    ] + [
        {
            "name": f"fg_node_{i:02d}_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "web_group"],
        }
        for i in range(1, 12)
    ]
    invalid_count = make_catalog(
        "Invalid Count Exceeded Catalog", "invalid-count-fg-catalog", eleven_fg_layers
    )
    (FIXTURES_DIR / "invalid_count_exceeded_catalog.json").write_text(
        json.dumps(invalid_count, indent=2) + "\n"
    )

    # 5. Negative: Missing platform suffix
    invalid_suffix_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {"name": "fg_worker_no_suffix", "components": ["baseos_group_10.2", "worker_group"]},
    ]
    invalid_suffix = make_catalog(
        "Invalid Missing Suffix Catalog", "invalid-suffix-fg-catalog", invalid_suffix_layers
    )
    (FIXTURES_DIR / "invalid_suffix_missing_catalog.json").write_text(
        json.dumps(invalid_suffix, indent=2) + "\n"
    )

    # 6. Negative: Unsupported architecture
    invalid_arch_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "fg_compute_rhel_10_2_ppc64le",
            "components": ["baseos_group_10.2", "worker_group"],
        },
    ]
    invalid_arch = make_catalog(
        "Invalid Unsupported Architecture Catalog", "invalid-arch-fg-catalog", invalid_arch_layers
    )
    (FIXTURES_DIR / "invalid_architecture_catalog.json").write_text(
        json.dumps(invalid_arch, indent=2) + "\n"
    )

    # 7. Non-blocking warning: Valid syntax but unverified OS version (e.g. rocky 10.2)
    warning_os_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "fg_compute_rocky_10_2_x86_64",
            "components": ["baseos_group_10.2", "worker_group"],
        },
    ]
    warning_os = make_catalog(
        "Warning Unqualified OS Version Catalog", "warning-os-fg-catalog", warning_os_layers
    )
    (FIXTURES_DIR / "warning_os_version_catalog.json").write_text(
        json.dumps(warning_os, indent=2) + "\n"
    )

    # 8. Negative: Broken referential integrity - missing group in groups{}
    broken_group_layers = [
        {"name": "os_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "admin_debug_group"]},
        {
            "name": "fg_web_rhel_10_2_x86_64",
            "components": ["baseos_group_10.2", "nonexistent_group_ref"],
        },
    ]
    broken_group = make_catalog(
        "Broken Group Reference Catalog", "broken-group-fg-catalog", broken_group_layers
    )
    (FIXTURES_DIR / "broken_referential_group_catalog.json").write_text(
        json.dumps(broken_group, indent=2) + "\n"
    )

    # 9. Negative: Broken referential integrity - missing package in packages{}
    broken_pkgs_groups = {
        "baseos_group_10.2": copy.deepcopy(BASE_GROUPS["baseos_group_10.2"]),
        "web_group": copy.deepcopy(BASE_GROUPS["web_group"]),
    }
    broken_pkgs_groups["web_group"]["components"].append("nonexistent_package_ref")
    needed_pkgs = {"bash", "chrony", "ghcr_io/openchami/image_thrillhouse", "nginx"}
    broken_pkgs_packages = {
        k: copy.deepcopy(v) for k, v in BASE_PACKAGES.items() if k in needed_pkgs
    }
    broken_package = make_catalog(
        "Broken Package Reference Catalog",
        "broken-pkg-fg-catalog",
        [{"name": "fg_web_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "web_group"]}],
        groups=broken_pkgs_groups,
        packages=broken_pkgs_packages,
        prune=False,
    )
    (FIXTURES_DIR / "broken_referential_package_catalog.json").write_text(
        json.dumps(broken_package, indent=2) + "\n"
    )

    # 10. Negative: Broken baseos - layer has no baseos group
    broken_baseos_layers = [{"name": "fg_web_rhel_10_2_x86_64", "components": ["web_group"]}]
    broken_baseos = make_catalog(
        "Broken BaseOS Catalog", "broken-baseos-fg-catalog", broken_baseos_layers
    )
    (FIXTURES_DIR / "broken_baseos_catalog.json").write_text(
        json.dumps(broken_baseos, indent=2) + "\n"
    )

    # 11. Negative: Unreviewed generated catalog (lacks operator review)
    unreviewed_generated = make_catalog(
        "Unreviewed Generated Catalog",
        "unreviewed-generated-fg-catalog",
        valid_layers,
        extra={
            "generated": True,
            "authoring": {
                "generated": True,
                "tool": "catalog-generation",
                "contract": "ER-BSM-001",
            },
            "operator_review": {"approved": False, "status": "pending_operator_review"},
        },
    )
    (FIXTURES_DIR / "unreviewed_generated_catalog.json").write_text(
        json.dumps(unreviewed_generated, indent=2) + "\n"
    )

    # 12. Negative: Invalid package structure - image package missing tag
    broken_img_packages = copy.deepcopy(BASE_PACKAGES)
    broken_img_packages["bad_image"] = {
        "name": "registry.test/bad/image",
        "packagetype": "image",
        # missing tag
        "sources": [
            {
                "architecture": "x86_64",
                "registry": "registry.test",
                "name": "rhel",
                "version": ["10.2"],
            }
        ],
    }
    broken_img_groups = copy.deepcopy(BASE_GROUPS)
    broken_img_groups["img_group"] = {
        "name": "img_group",
        "type": "group",
        "description": "Image group with bad image",
        "components": ["bad_image"],
    }
    broken_image = make_catalog(
        "Invalid Package Image Catalog",
        "invalid-image-fg-catalog",
        [{"name": "fg_app_rhel_10_2_x86_64", "components": ["baseos_group_10.2", "img_group"]}],
        groups=broken_img_groups,
        packages=broken_img_packages,
        prune=True,
    )
    (FIXTURES_DIR / "invalid_package_image_catalog.json").write_text(
        json.dumps(broken_image, indent=2) + "\n"
    )

    print(f"Generated 12 catalog fixtures in {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
