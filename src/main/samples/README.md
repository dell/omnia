# Omnia Samples

Reference files for Omnia deployment. Setup installs the default only when the
active catalog does not exist. The catalog management commands can list and
activate a bundled variant; playbooks consume the copied runtime file, not the
sample in the source tree.

Every bundled catalog pins
`ghcr.io/openchami/image-thrillhouse:v0.0.26`, matching the x86_64 and AArch64
runtime images selected by Image Build Manager. Update the runtime variables
and every catalog pin together when adopting a later Thrillhouse release.

## Catalog Files

### Main Catalog

| File | Description |
|------|-------------|
| `catalog_rhel.json` | Default RHEL 10.0 catalog — mixed Slurm + service_k8s (x86_64 mgmt/service_k8s, aarch64 compute) without VAST |
| `cadence_catalog_rhel.json` | Catalog watched by the BuildStream cadence pipeline for periodic package syncs (ER-BSM-002) |

### Modular Catalogs (catalogs/ directory)

Organized first by catalog family, then by OS version where applicable:

```
catalogs/
├── hybrid/                                      # RHEL 10.2 control + RHEL 10.0 worker roles
│   ├── slurm_hybrid_10_2_10_0_<arch>.json
│   ├── slurm_hybrid_10_2_10_0_<arch>_no_vast.json
│   └── slurm_service_k8s_hybrid_10_2_10_0_<layout>[_no_vast].json
└── rhel/
    ├── 10.0/                                    # Single-version RHEL 10.0 variants
    │   ├── slurm_<architecture>[_no_vast].json
    │   ├── service_k8s_x86_64.json
    │   └── slurm_service_k8s_<layout>[_no_vast].json
    └── 10.2/                                    # Single-version RHEL 10.2 variants
        ├── slurm_<architecture>[_no_vast].json
        ├── service_k8s_x86_64.json
        └── slurm_service_k8s_<layout>[_no_vast].json
```

### Catalog Selection Guide

| Use Case | With VAST | Without VAST |
|----------|-----------|--------------|
| Homogeneous x86_64 cluster (Slurm + service_k8s) | `slurm_service_k8s_x86_64.json` | `slurm_service_k8s_x86_64_no_vast.json` |
| Homogeneous x86_64 cluster (Slurm only) | `slurm_x86_64.json` | `slurm_x86_64_no_vast.json` |
| Homogeneous x86_64 cluster (service_k8s only) | `service_k8s_x86_64.json` | — |
| Homogeneous aarch64 cluster (Slurm only) | `slurm_aarch64.json` | `slurm_aarch64_no_vast.json` |
| Heterogeneous cluster (x86_64 mgmt + aarch64 compute) | `slurm_x86_64_aarch64.json` | `slurm_x86_64_aarch64_no_vast.json` |
| Heterogeneous cluster with service_k8s | `slurm_service_k8s_combined.json` | `slurm_service_k8s_combined_no_vast.json` |

For a small x86_64 Slurm-only test, start with
`rhel/<version>/slurm_x86_64_no_vast.json` for the target RHEL version. It
avoids service_k8s, aarch64, and VAST content. Use a `hybrid/` selector only
when control and worker roles intentionally use different RHEL versions.

### Functional Layers by Catalog Type

**Slurm-only catalogs** include:
- `os` - Base OS packages
- `slurm_control_node` - Slurm controller (slurmctld, slurmdbd)
- `slurm_node` - Slurm compute node (slurmd)
- `login_node` - Login node
- `login_compiler_node` - Login node with compilers

**service_k8s-only catalogs** include:
- `os` - Base OS packages
- `service_kube_control_plane` - service_k8s control plane
- `service_kube_node` - service_k8s worker node

**Combined catalogs** include all of the above.

**Note**: All functional layers include `ldms_group` for LDMS lightweight distributed metric service.

### Driver Groups

All Slurm catalogs include these driver groups where applicable:
- `infiniband_stack_driver_groupv1` - RDMA/InfiniBand (DOCA OFED)
- `vast_stack_driver_groupv1` - VAST Data NFS client (only in with-VAST catalogs; excluded from `_no_vast` variants)
- `nvidia_stack_driver_groupv1` - NVIDIA GPU drivers, CUDA, HPC SDK (on slurm_node and login_compiler_node)

## Usage

```bash
# From src/main, list the bundled selectors:
./omnia.sh --list-catalogs

# Select interactively or provide an exact selector:
sudo ./omnia.sh --select-catalog
sudo ./omnia.sh --select-catalog rhel/10.2/slurm_service_k8s_x86_64.json

# The selected file is copied to CATALOG_FILE_PATH. Image Build Manager uses it
# when functional_groups_source is "catalog".
```

The list and selection commands read each JSON file and display its catalog name,
description, RHEL version, workloads, architectures, VAST client inclusion,
and functional-layer count. This makes catalog selection independent of the
file name alone. Selectors are relative to `catalogs/`, so entries retain their
family and optional version prefix (for example,
`rhel/10.2/slurm_x86_64_no_vast.json` or
`hybrid/slurm_hybrid_10_2_10_0_x86_64.json`). Bash completion discovers these
nested selectors from the same tree.

## Catalog JSON Structure

The catalog file follows this hierarchy:

```
catalog
├── identifier          # e.g., "omnia-services-rhel-10-0"
├── functionallayer[]   # Functional groups (by OS + arch)
│   ├── name            # e.g., "os_rhel_10_0_x86_64" or "slurm_node_rhel_10_0_x86_64"
│   └── components[]    # References to groups
├── groups              # Named groups of packages
│   └── {group_name}
│       └── components[]  # References to packages
└── packages            # Individual packages
    └── {package_key}
        ├── name          # Installable name (e.g., "kubeadm-1.35.1")
        ├── packagetype   # rpm, image, tarball, pip_module, etc.
        └── sources[]     # Architecture-specific download locations
            └── architecture  # x86_64 or aarch64
```

See `src/image_build_manager/docs/design/catalog-migration-design.md` for
full design details on catalog-based package resolution.
