# Omnia Samples

Reference files for Omnia deployment. These are **not** used at runtime — they
serve as documentation and starting-point examples.

## Catalog Files

### Main Catalog

| File | Description |
|------|-------------|
| `catalog_rhel.json` | Default RHEL 10.0 catalog with all Slurm + service_k8s layers on x86_64 (7 layers, 23 groups, 222 packages) |

### Modular Catalogs (catalogs/ directory)

Organized by OS version and workload type for flexible deployment scenarios:

```
catalogs/
├── 10.0/
│   ├── slurm_x86.json           # All Slurm layers on x86_64
│   ├── slurm_aarch64.json       # All Slurm layers on aarch64
│   ├── slurm_x86_aarch64.json   # Mixed: x86_64 control/login, aarch64 node/login-compiler
│   ├── service_k8s_x86_64.json             # service_k8s only on x86_64
│   ├── slurm_service_k8s_x86_64.json       # All Slurm + service_k8s on x86_64
│   └── slurm_service_k8s_combined.json  # Mixed Slurm + service_k8s (x86_64 mgmt/service_k8s, aarch64 compute)
│
└── 10.2/
    ├── slurm_x86.json                   # All Slurm layers on x86_64
    ├── slurm_aarch64.json               # All Slurm layers on aarch64
    ├── slurm_x86_aarch64.json           # Mixed: x86_64 control/login, aarch64 node/login-compiler
    ├── service_k8s_x86_64.json             # service_k8s only on x86_64
    ├── slurm_service_k8s_x86_64.json       # All Slurm + service_k8s on x86_64
    └── slurm_service_k8s_combined.json  # Mixed Slurm + service_k8s (x86_64 mgmt/service_k8s, aarch64 compute)
```

### Catalog Selection Guide

| Use Case | Recommended Catalog |
|----------|---------------------|
| Homogeneous x86_64 cluster (Slurm + service_k8s) | `slurm_service_k8s_x86_64.json` |
| Homogeneous x86_64 cluster (Slurm only) | `slurm_x86.json` |
| Homogeneous x86_64 cluster (service_k8s only) | `service_k8s_x86_64.json` |
| Homogeneous aarch64 cluster (Slurm only) | `slurm_aarch64.json` |
| Heterogeneous cluster (x86_64 mgmt + aarch64 compute) | `slurm_x86_aarch64.json` |
| Heterogeneous cluster with service_k8s | `slurm_service_k8s_combined.json` |

### Functional Layers by Catalog Type

**Slurm-only catalogs** include:
- `baseos` - Base OS packages
- `slurm_control_node` - Slurm controller (slurmctld, slurmdbd)
- `slurm_node` - Slurm compute node (slurmd)
- `login_node` - Login node
- `login_compiler_node` - Login node with compilers

**service_k8s-only catalogs** include:
- `baseos` - Base OS packages
- `service_kube_control_plane` - service_k8s control plane
- `service_kube_node` - service_k8s worker node

**Combined catalogs** include all of the above.

### Driver Groups

All Slurm catalogs include these driver groups where applicable:
- `infiniband_stack_driver_groupv1` - RDMA/InfiniBand (DOCA OFED)
- `vast_stack_driver_groupv1` - VAST Data NFS client
- `nvidia_stack_driver_groupv1` - NVIDIA GPU drivers, CUDA, HPC SDK (on slurm_node and login_compiler_node)

## Usage

```bash
# Copy sample catalog to the convention path for testing:
sudo mkdir -p /opt/omnia/catalog
sudo cp samples/catalog_rhel_10_2_x86_aarch64.json /opt/omnia/catalog/

# Or use a specific modular catalog:
sudo cp samples/catalogs/10.2/slurm_k8s_x86.json /opt/omnia/catalog/catalog_rhel.json

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
│   ├── name            # e.g., "slurm_node_rhel_10_0_x86_64"
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
