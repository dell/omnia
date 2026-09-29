# Master Reference File

**Version:** 1.0.0  
**Captured:** 2026-09-25  
**Consumers:** Catalog Generation, Catalog Editing, and Analysis skills read this file directly (channel-agnostic instructions and reference data — no coding-agent-only tooling assumed, per FR-5.1). The Selection Catalogue `support_status` gate every skill applies against the A.1 table below is defined in `SKILL.md` in the parent `catalog-selection-gate` package directory.

This file is a development-time deliverable, hand-derived and maintained by the Build Stream team as part of the build/release process for the AI-assisted catalog authoring skills (ER-BSM-001-nersc-ai-skills-catalog-authoring, FR-1.0). It is not generated at skill-invocation time by an operator. Each row's provenance names the exact master-catalog file(s) or repository-configuration file it was read from; a handful of A.1/A.7 rows (AMD/ROCm, BeeGFS) additionally cross-reference `src/repo_manager/plugins/module_utils/input_validation/core/config.py`'s `expected_versions` map, which carries a version pin with no corresponding catalog group — evidence that a capability is `planned`, not `supported`, without needing an online lookup. No row in this capture required an online source; regenerate by repeating the same read-and-tabulate process against the current `src/main/samples/catalogs/**/*.json` and `src/repo_manager/input/repo_manager_config.yml` whenever either changes, falling back to online sources (Red Hat Compatibility Matrix, vendor docs) only for a genuinely unresolvable row, and flagging that row as incomplete rather than fabricating it (NFR-2). Master catalogs remain the authoritative source for the concrete package set of an already-shipped configuration.

**Topology scope of this capture, and the required re-derivation trigger:** every provenance note, file count, and glob pattern in this file was captured against the specific catalog tree that existed under `src/main/samples/catalogs/` on the date above — currently a flat `<os_version>/*.json` layout with no versioned `rhel/` subtree and no `hybrid/` subtree. **If the shipped catalog tree's topology changes** (e.g. RHEL catalogs move under a versioned `catalogs/rhel/<os_version>/` path, or a `catalogs/hybrid/` tree of mixed-stack catalogs is introduced, or the total catalog count changes), **every count, provenance path, and A.1–A.8 row in this file must be re-derived against the new tree before being treated as authoritative** — do not assume an old row still applies just because its `axis`/`option`/`role` text looks unchanged; re-run the read-and-tabulate process (see `SKILL.md`'s "Regenerating" section) and re-verify every count. Every discovery command a consuming skill runs against `src/main/samples/catalogs/` (Step 4b's `grep -rl`, `bulk-edit-catalog`'s catalog-set search, etc.) is written recursively (`catalogs/**/*.json`) specifically so it keeps working across a topology change without its own wording needing an update — only this file's hand-tabulated rows need re-deriving.

**Hybrid catalog classification:** a catalog is "hybrid" when its functional layers reference groups from more than one top-level stack category (e.g. both `slurm_*`-pattern groups and `service_kube_*`-pattern groups in the same catalog) — this already exists today as the `stack: slurm + service_k8s` row in A.1 below, and any future `catalogs/hybrid/` tree is expected to hold catalogs matching that same classification rule, not a new stack category. If a shipped hybrid catalog combines stacks in a way no existing A.1 `stack` row covers, do not fabricate a verdict for it — treat it exactly like any other selection absent from the table (`SKILL.md` Step 3): flag it, and re-derive this file against the new combination before it can be treated as `supported`.

## Source Locations

| Source | Path | Description |
|--------|------|-------------|
| Sample catalogs (RHEL 10.0) | `src/main/samples/catalogs/10.0/` | 12 master catalog JSON files (e.g., `slurm_x86_64.json`, `service_k8s_x86_64.json`, `slurm_service_k8s_combined.json`) |
| Sample catalogs (RHEL 10.2) | `src/main/samples/catalogs/10.2/` | 12 master catalog JSON files (content-equivalent to 10.0 apart from version pinning) |
| Catalog schema | `src/repo_manager/schemas/catalog_schema.json` | JSON schema defining the structure and validation rules for catalog files |
| Repository configuration | `src/repo_manager/input/repo_manager_config.yml` | Repository/registry source defaults (A.5 table) and expected version pins |

**These two rows describe the topology captured on 2026-09-25 only** (a
flat two-directory layout, 24 files total). If `src/main/samples/catalogs/`
now also has a versioned `rhel/<os_version>/` subtree, a `hybrid/` subtree,
or a different total file count, this table — and every count elsewhere in
this file — is stale and must be re-derived against the tree that actually
exists before being relied on.

---

## A.1 Selection Catalogue

One row per selectable option across every decision axis.

| axis | option | support_status | notes | provenance |
|---|---|---|---|---|
| os_version | RHEL 10.0 | supported |  | src/main/samples/catalogs/10.0/ (captured 2026-09-25) |
| os_version | RHEL 10.2 | supported | Content-equivalent to 10.0 apart from version pinning (verified by diffing every 10.0/10.2 catalog pair after normalizing version substrings) | src/main/samples/catalogs/10.2/ (captured 2026-09-25) |
| architecture | x86_64 | supported |  | src/main/samples/catalogs/**/*_x86_64*.json (captured 2026-09-25) |
| architecture | aarch64 | supported | Some image-builder and helm artifacts are arch-specific | src/main/samples/catalogs/**/*_aarch64*.json (captured 2026-09-25) |
| stack | slurm | supported |  | src/main/samples/catalogs/**/slurm_*.json (captured 2026-09-25) |
| stack | service_k8s | supported | Kubernetes is not supported on aarch64 in this release (x86_64 only — no service_k8s_aarch64.json ships in any inspected catalogs/<os_version>/ directory) | src/main/samples/catalogs/**/service_k8s_*.json (captured 2026-09-25) |
| stack | slurm + service_k8s | supported | Mixed-stack catalogs are a shipped configuration; x86_64 only when Kubernetes is included | src/main/samples/catalogs/**/slurm_service_k8s_*.json (captured 2026-09-25) |
| gpu | NVIDIA | supported |  | src/main/samples/catalogs (nvidia_stack_driver_groupv1); src/orchestrator/plugins/modules/bulk_discover_node_specs.py (_detect_gpus_from_processors/_detect_gpus_from_pcie) (captured 2026-09-25) |
| gpu | AMD / ROCm | planned | Version pins exist in repository configuration; no functional group ships today and hardware detection only regex-matches NVIDIA | src/repo_manager/plugins/module_utils/input_validation/core/config.py expected_versions['amdgpu'/'rocm'] (captured 2026-09-25) |
| storage | VAST (NFS/RDMA) | supported | Slurm-scoped — see A.4 | src/main/samples/catalogs (vast_stack_driver_groupv1, Slurm layers only) (captured 2026-09-25) |
| storage | PowerScale (CSI) | supported | Kubernetes-scoped — see A.4 | src/main/samples/catalogs (powerscale_csi_group, service_k8s layers only) (captured 2026-09-25) |
| storage | PowerVault (iSCSI) | supported | Stack-neutral; runtime-discovered device, no catalog group | src/orchestrator/roles/mount_config/tasks/process_single_powervault.yml; src/orchestrator/input/storage_config.yml (captured 2026-09-25) |
| storage | Generic NFS | supported | Stack-neutral; no catalog group | src/orchestrator/roles/mount_config/tasks/cloud_init.yml (captured 2026-09-25) |
| storage | BeeGFS | planned | Version pin only; no functional group or role found in any inspected catalog | src/repo_manager/plugins/module_utils/input_validation/core/config.py expected_versions['beegfs'] (captured 2026-09-25) |
| network | InfiniBand (DOCA OFED) | supported | Additive per functional layer, not a vendor choice | src/main/samples/catalogs (infiniband_stack_driver_groupv1); src/orchestrator/roles/configure_ochami/templates/doca-ofed/doca-install.sh.j2 (captured 2026-09-25) |
| network | Ethernet-only | supported | Absence of the InfiniBand group; no dedicated group | src/main/samples/catalogs (absence of infiniband group) (captured 2026-09-25) |

---

## A.2 Node-Role Table

One row per node role, keyed by stack.

| stack | role | layer_name_pattern | mandatory | gpu_capable | provenance |
|---|---|---|---|---|---|
| (any) | os | <role>_rhel_<os_version>_<architecture> | yes | no | master catalogs: 18 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| service_k8s | service_kube_control_plane | <role>_rhel_<os_version>_<architecture> | yes | no | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_k8s | service_kube_node | <role>_rhel_<os_version>_<architecture> | yes | no | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| slurm | login_compiler_node | <role>_rhel_<os_version>_<architecture> | no | yes | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm | login_node | <role>_rhel_<os_version>_<architecture> | no | no | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm | slurm_control_node | <role>_rhel_<os_version>_<architecture> | yes | no | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm | slurm_node | <role>_rhel_<os_version>_<architecture> | yes | yes | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |

---

## A.3 Functional-Layer Composition Table

Role -> the groups its functional layer references, and the selection that governs each conditional group.

| role | group | inclusion | governed_by | provenance |
|---|---|---|---|---|
| login_compiler_node | admin_debug_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | baseos_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | common_pks | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | ldms_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | login_compiler_node_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | nvidia_stack_driver_groupv1 | conditional | gpu=NVIDIA | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | openldap_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | openmpi_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | slurm_custom_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | ucx_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_compiler_node | vast_stack_driver_groupv1 | conditional | storage=VAST | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| login_node | admin_debug_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | baseos_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | common_pks | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | ldms_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | login_node_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | openldap_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | openmpi_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | slurm_custom_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | ucx_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| login_node | vast_stack_driver_groupv1 | conditional | storage=VAST | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| os | baseos_group | always | - | master catalogs: 18 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| os | ldms_group | always | - | master catalogs: 18 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| service_kube_control_plane | admin_debug_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | baseos_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | common_pks | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | ldms_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | powerscale_csi_group | conditional | storage=PowerScale | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | service_k8s_cluster_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | service_k8s_common_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | service_k8s_telemetry_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_control_plane | service_kube_control_plane_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | admin_debug_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | baseos_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | common_pks | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | ldms_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | powerscale_csi_group | conditional | storage=PowerScale | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | service_k8s_common_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | service_k8s_telemetry_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| service_kube_node | service_kube_node_group | always | - | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| slurm_control_node | admin_debug_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | baseos_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | common_pks | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | ldms_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | openldap_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | slurm_control_node_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_control_node | slurm_custom_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | admin_debug_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | baseos_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | common_pks | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | infiniband_stack_driver_groupv1 | conditional | network=IB | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | ldms_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | nvidia_stack_driver_groupv1 | conditional | gpu=NVIDIA | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | openldap_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | openmpi_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | slurm_custom_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | slurm_node_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | ucx_group | always | - | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| slurm_node | vast_stack_driver_groupv1 | conditional | storage=VAST | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |

---

## A.4 Stack-Storage Compatibility Table

| storage_option | valid_for_slurm | valid_for_service_k8s | mechanism | default_for | provenance |
|---|---|---|---|---|---|
| VAST (NFS/RDMA) | yes | no | Mount targeted at Slurm functional-group prefixes; contributes a catalog group (vast_stack_driver_groupv1) | Slurm functional clusters | src/main/samples/catalogs/**/*.json (captured 2026-09-25) |
| PowerScale (CSI) | no | yes | Enabled per Kubernetes cluster; contributes a CSI catalog group (powerscale_csi_group) | Kubernetes functional clusters | src/main/samples/catalogs/**/*.json (captured 2026-09-25) |
| PowerVault (iSCSI) | yes | yes | Runtime-discovered device; no catalog group | (operator-configured) | src/orchestrator/roles/mount_config/tasks/process_single_powervault.yml (captured 2026-09-25) |
| Generic NFS | yes | yes | Plain mount; no catalog group | (operator-configured) | src/orchestrator/roles/mount_config/tasks/cloud_init.yml (captured 2026-09-25) |

---

## A.5 Package Source Defaults Table

Per OS version and architecture, the repositories/registries a package source may reference.

| source_name | source_kind | os_version | architecture | default_url | gpgkey | required_by | provenance |
|---|---|---|---|---|---|---|---|
| baseos | subscription_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=baseos | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| appstream | subscription_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=appstream | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| codeready-builder | subscription_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=codeready-builder | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| epel | default_repo | 10.0 | x86_64 | https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/ | https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-10 | packages referencing reponame=epel | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| kubernetes-v1-35 | default_repo | 10.0 | x86_64 | https://pkgs.k8s.io/core:/stable:/v1.35/rpm/ | https://pkgs.k8s.io/core:/stable:/v1.35/rpm/repodata/repomd.xml.key | packages referencing reponame=kubernetes-v1-35 | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| cri-o-v1-35 | default_repo | 10.0 | x86_64 | https://ftp.gwdg.de/pub/opensuse/repositories/isv:/cri-o:/stable:/v1.35/rpm/ | https://ftp.gwdg.de/pub/opensuse/repositories/isv:/cri-o:/stable:/v1.35/rpm/repodata/repomd.xml.key | packages referencing reponame=cri-o-v1-35 | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| doca | default_repo | 10.0 | x86_64 | https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/x86_64/ | https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/x86_64/repodata/repomd.xml.key | packages referencing reponame=doca | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| docker-ce | default_repo | 10.0 | x86_64 | https://download.docker.com/linux/centos/10/x86_64/stable/ | https://download.docker.com/linux/centos/gpg | packages referencing reponame=docker-ce | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| cuda | default_repo | 10.0 | x86_64 | https://developer.download.nvidia.com/compute/cuda/repos/rhel10/x86_64/ | https://developer.download.nvidia.com/compute/cuda/repos/rhel10/x86_64/repodata/repomd.xml.key | packages referencing reponame=cuda | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| nvidia-hpc-sdk | default_repo | 10.0 | x86_64 | https://developer.download.nvidia.com/hpc-sdk/rhel/x86_64 | https://developer.download.nvidia.com/hpc-sdk/rhel/RPM-GPG-KEY-NVIDIA-HPC-SDK | packages referencing reponame=nvidia-hpc-sdk | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| slurm_custom | operator_supplied_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=slurm_custom | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| ldms | operator_supplied_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=ldms | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| vast | operator_supplied_repo | 10.0 | x86_64 | (operator-supplied) | - | packages referencing reponame=vast | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| baseos | subscription_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=baseos | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| appstream | subscription_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=appstream | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| codeready-builder | subscription_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=codeready-builder | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| epel | default_repo | 10.0 | aarch64 | https://dl.fedoraproject.org/pub/epel/10/Everything/aarch64/ | https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-10 | packages referencing reponame=epel | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| doca | default_repo | 10.0 | aarch64 | https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/arm64-sbsa/ | https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/arm64-sbsa/repodata/repomd.xml.key | packages referencing reponame=doca | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| docker-ce | default_repo | 10.0 | aarch64 | https://download.docker.com/linux/centos/10/aarch64/stable/ | https://download.docker.com/linux/centos/gpg | packages referencing reponame=docker-ce | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| cuda | default_repo | 10.0 | aarch64 | https://developer.download.nvidia.com/compute/cuda/repos/rhel10/sbsa/ | https://developer.download.nvidia.com/compute/cuda/repos/rhel10/sbsa/repodata/repomd.xml.key | packages referencing reponame=cuda | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| nvidia-hpc-sdk | default_repo | 10.0 | aarch64 | https://developer.download.nvidia.com/hpc-sdk/rhel/aarch64 | https://developer.download.nvidia.com/hpc-sdk/rhel/RPM-GPG-KEY-NVIDIA-HPC-SDK | packages referencing reponame=nvidia-hpc-sdk | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| slurm_custom | operator_supplied_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=slurm_custom | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| ldms | operator_supplied_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=ldms | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |
| vast | operator_supplied_repo | 10.0 | aarch64 | (operator-supplied) | - | packages referencing reponame=vast | src/repo_manager/input/repo_manager_config.yml (captured 2026-09-25) |

---

## A.6 Pinned Version Table

| component | pinned_version | pin_location | arch_variance | provenance |
|---|---|---|---|---|
| PyMySQL==1_1_2 | 1.1.2 | packages.PyMySQL==1_1_2 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| calico_v3_32_1 | v3.32.1 | packages.calico_v3_32_1 (packagetype=manifest) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| cert_manager_v1_10_2 | v1.10.0 | packages.cert_manager_v1_10_2 (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| cffi==1_17_1 | 1.17.1 | packages.cffi==1_17_1 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| cri_o_1_35_1 | 1.35.1 | packages.cri_o_1_35_1 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| cryptography==45_0_7 | 45.0.7 | packages.cryptography==45_0_7 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| csi_powerscale_v2_17_0 | v2.17.0 | packages.csi_powerscale_v2_17_0 (packagetype=git) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| cuda_toolkit | 13.3.1 | packages.cuda_toolkit (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| datacenter_gpu_manager | 4.6.1 | packages.datacenter_gpu_manager (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| doca_ofed | 3.2.1 | packages.doca_ofed (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| external_snapshotter_v8_5_0 | v8.5.0 | packages.external_snapshotter_v8_5_0 (packagetype=git) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| helm_charts | container-storage-modules-1.10.0 | packages.helm_charts (packagetype=git) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| helm_charts_2_17_0 | csi-isilon-2.17.0 | packages.helm_charts_2_17_0 (packagetype=git) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| karavi_observability | v1.15.0 | packages.karavi_observability (packagetype=git) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| kubeadm_1_35_1 | 1.35.1 | packages.kubeadm_1_35_1 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| kubectl_1_35_1 | 1.35.1 | packages.kubectl_1_35_1 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| kubelet_1_35_1 | 1.35.1 | packages.kubelet_1_35_1 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| kubernetes==33_1_0 | 33.1.0 | packages.kubernetes==33_1_0 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| metallb_native_v0_16_1 | v0.16.1 | packages.metallb_native_v0_16_1 (packagetype=manifest) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| nfs_subdir_external_provisioner | 4.0.18 | packages.nfs_subdir_external_provisioner (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| nfs_subdir_external_provisioner_4_0_18 | 4.0.18 | packages.nfs_subdir_external_provisioner_4_0_18 (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| nvhpc | 26.5 | packages.nvhpc (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| nvidia_driver | 580.159.04 | packages.nvidia_driver (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| nvidia_driver_cuda | 580.159.04 | packages.nvidia_driver_cuda (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 20 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_aarch64_no_vast.json (captured 2026-09-25) |
| omsdk==1_2_518 | 1.2.518 | packages.omsdk==1_2_518 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| prettytable==3_14_0 | 3.14.0 | packages.prettytable==3_14_0 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 22 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_aarch64.json (captured 2026-09-25) |
| prometheus_client==0_20_0 | 0.20.0 | packages.prometheus_client==0_20_0 (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| pymysql | 1.1.2 | packages.pymysql (packagetype=pip_module) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| python3 | 3.12.9 | packages.python3 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| python3_3_12_9 | 3.12.9 | packages.python3_3_12_9 (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| strimzi_kafka_operator_helm_3_chart | 1.1.0 | packages.strimzi_kafka_operator_helm_3_chart (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| strimzi_kafka_operator_helm_3_chart_1_1_0 | 1.1.0 | packages.strimzi_kafka_operator_helm_3_chart_1_1_0 (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| vastnfs | 4.1 | packages.vastnfs (packagetype=rpm) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/slurm_aarch64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| victoria_metrics_operator | 0.59.3 | packages.victoria_metrics_operator (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |
| victoria_metrics_operator_0_59_3 | 0.59.3 | packages.victoria_metrics_operator_0_59_3 (packagetype=tarball) | see per-architecture catalog file list in provenance | master catalogs: 10 files, e.g. src/main/samples/catalogs/10.0/service_k8s_x86_64.json, src/main/samples/catalogs/10.0/slurm_service_k8s_combined.json (captured 2026-09-25) |

---

## A.7 Supported Hardware Table

| category | vendor_model | detection_path | catalog_effect | support_status | provenance |
|---|---|---|---|---|---|
| server | Dell PowerEdge | Inventory / Redfish | none directly; determines architecture | supported | src/orchestrator/plugins/modules/bulk_discover_node_specs.py (captured 2026-09-25) |
| bmc | iDRAC | Redfish endpoints | none; provisioning path only | supported | src/orchestrator/plugins/modules/bulk_discover_node_specs.py (captured 2026-09-25) |
| gpu | NVIDIA data-centre and workstation families | Processor type + vendor match (_detect_gpus_from_processors), PCIe class-code fallback (_detect_gpus_from_pcie) | implies the NVIDIA group on gpu_capable roles | supported | src/orchestrator/plugins/modules/bulk_discover_node_specs.py (captured 2026-09-25) |
| gpu | AMD | not detected — _detect_gpus_from_processors/_pcie only regex-match 'nvidia' | none; may be seen as a generic PCIe display-controller | planned | src/orchestrator/plugins/modules/bulk_discover_node_specs.py (captured 2026-09-25) |
| fabric_adapter | NVIDIA/Mellanox InfiniBand | `lspci \| grep -i mellanox` (DOCA-OFED / VAST install scripts) | implies the InfiniBand group | supported | src/orchestrator/roles/configure_ochami/templates/doca-ofed/doca-install.sh.j2; src/orchestrator/roles/configure_ochami/templates/vast/configure_vast_installation.sh.j2 (captured 2026-09-25) |
| storage_array | VAST, PowerScale, PowerVault | operator-declared, not discovered (src/orchestrator/input/storage_config.yml) | see A.4 | supported | src/orchestrator/input/storage_config.yml (captured 2026-09-25) |

---

## A.8 Constraint and Co-Requisite Table

| constraint_id | scope | rule | severity | provenance |
|---|---|---|---|---|
| CON-001 | storage, stack | Storage selection must be valid for the chosen stack (A.4) | blocking | A.4 Stack-Storage Compatibility Table (captured 2026-09-25) |
| CON-002 | gpu, node_role | A GPU group may be attached only to a gpu_capable role (A.2) | blocking | A.2 Node-Role Table (captured 2026-09-25) |
| CON-003 | stack, architecture | Kubernetes stack is supported only on x86_64 architecture (A.1) | blocking | A.1 Selection Catalogue; absence of service_k8s_aarch64.json (captured 2026-09-25) |
| CON-004 | Kubernetes pinned components | Kubernetes RPM, image, and repository version pins must agree | blocking | src/main/samples/catalogs (kubeadm_1_35_1/kubelet_1_35_1/kubectl_1_35_1, docker.io/alpine/kubectl, cri-o-1.35.1 all pinned to the same minor) (captured 2026-09-25) |
| CON-005 | package source, architecture | A package source's architecture must be one of the catalog's selected architectures | blocking | A.5 Package Source Defaults Table (captured 2026-09-25) |
| CON-006 | operator-supplied repository | An operator-supplied repository referenced by any package must have a URL before sync | blocking | src/repo_manager/input/repo_manager_config.yml user_repos (slurm_custom, ldms, vast ship with an empty url by design) (captured 2026-09-25) |
| CON-007 | functional layer, group removal | Removing a group that another selected role also references affects both roles | warning | A.3 Functional-Layer Composition Table (captured 2026-09-25) |
| CON-008 | driver group, repository configuration | Adding a driver group pulls in a repository that may not yet be configured | warning | A.5 Package Source Defaults Table; A.3 Functional-Layer Composition Table (captured 2026-09-25) |

