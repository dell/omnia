# Omnia Samples

Reference files for Omnia deployment. These are **not** used at runtime — they
serve as documentation and starting-point examples.

## Files

| File | Domain | Description |
|------|--------|-------------|
| `catalog_rhel.json` | image_build_manager | Compact RHEL 10.0 catalog example. |
| `catalog_rhel_10_0_x86_64.json` | repo_manager, image_build_manager | RHEL 10.0 x86_64 catalog. |
| `catalog_rhel_10_0_aarch64.json` | repo_manager, image_build_manager | RHEL 10.0 aarch64 catalog. |
| `catalog_rhel_10_0_x86_aarch64.json` | repo_manager, image_build_manager | RHEL 10.0 dual-architecture catalog. |
| `catalog_rhel_10_2_x86_aarch64.json` | repo_manager, image_build_manager | RHEL 10.2 dual-architecture catalog. |

## Usage

```bash
# Copy sample catalog to the convention path for testing:
sudo mkdir -p /opt/omnia/catalog
sudo cp samples/catalog_rhel_10_2_x86_aarch64.json /opt/omnia/catalog/

# Select the catalog and use catalog-backed functional groups:
export CATALOG_FILE_PATH=/opt/omnia/catalog/catalog_rhel_10_2_x86_aarch64.json
# Set functional_groups_source: "catalog" in image_build_config.yml.
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
