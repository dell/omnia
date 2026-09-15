# Omnia Samples

Reference files for Omnia deployment. These are **not** used at runtime — they
serve as documentation and starting-point examples.

## Catalog Files

### Main Catalog

| File | Description |
|------|-------------|
| `catalog_rhel.json` | Default RHEL 10.0 catalog — mixed Slurm + service_k8s (x86_64 mgmt/service_k8s, aarch64 compute) without VAST |

### Modular Catalogs (catalogs/ directory)

Organized by OS version and workload type for flexible deployment scenarios:

```
catalogs/
├── 10.0/
│   ├── slurm_x86_64.json                       # All Slurm layers on x86_64 (with VAST)
│   ├── slurm_x86_64_no_vast.json                # All Slurm layers on x86_64 (no VAST)
│   ├── slurm_aarch64.json                       # All Slurm layers on aarch64 (with VAST)
│   ├── slurm_aarch64_no_vast.json                # All Slurm layers on aarch64 (no VAST)
│   ├── slurm_x86_64_aarch64.json                # Mixed: x86_64 control/login, aarch64 node/login-compiler (with VAST)
│   ├── slurm_x86_64_aarch64_no_vast.json         # Mixed: x86_64 control/login, aarch64 node/login-compiler (no VAST)
│   ├── service_k8s_x86_64.json                  # service_k8s only on x86_64
│   ├── slurm_service_k8s_x86_64.json            # All Slurm + service_k8s on x86_64 (with VAST)
│   ├── slurm_service_k8s_x86_64_no_vast.json     # All Slurm + service_k8s on x86_64 (no VAST)
│   ├── slurm_service_k8s_combined.json           # Mixed Slurm + service_k8s (with VAST)
│   └── slurm_service_k8s_combined_no_vast.json    # Mixed Slurm + service_k8s (no VAST)
│
└── 10.2/
    ├── slurm_x86_64.json                        # All Slurm layers on x86_64 (with VAST)
    ├── slurm_x86_64_no_vast.json                 # All Slurm layers on x86_64 (no VAST)
    ├── slurm_aarch64.json                        # All Slurm layers on aarch64 (with VAST)
    ├── slurm_aarch64_no_vast.json                 # All Slurm layers on aarch64 (no VAST)
    ├── slurm_x86_64_aarch64.json                 # Mixed: x86_64 control/login, aarch64 node/login-compiler (with VAST)
    ├── slurm_x86_64_aarch64_no_vast.json          # Mixed: x86_64 control/login, aarch64 node/login-compiler (no VAST)
    ├── service_k8s_x86_64.json                   # service_k8s only on x86_64
    ├── slurm_service_k8s_x86_64.json             # All Slurm + service_k8s on x86_64 (with VAST)
    ├── slurm_service_k8s_x86_64_no_vast.json      # All Slurm + service_k8s on x86_64 (no VAST)
    ├── slurm_service_k8s_combined.json            # Mixed Slurm + service_k8s (with VAST)
    └── slurm_service_k8s_combined_no_vast.json     # Mixed Slurm + service_k8s (no VAST)
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
`slurm_x86_64_no_vast.json` from the directory matching the target RHEL
version. It avoids service_k8s, aarch64, and VAST content. Use a different row
from the table only when the deployment requires those capabilities.

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
# Copy sample catalog to the convention path for testing:
sudo mkdir -p /opt/omnia/catalog
sudo cp samples/catalog_rhel.json /opt/omnia/catalog/

# Or use a specific modular catalog:
sudo cp samples/catalogs/10.2/slurm_service_k8s_x86_64.json /opt/omnia/catalog/catalog_rhel.json

# Then configure image_build_config.yml:
#   catalog_file: "/opt/omnia/catalog/catalog_rhel.json"
#   functional_groups_source: "catalog"
```

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
