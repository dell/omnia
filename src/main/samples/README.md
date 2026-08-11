# Omnia Samples

Reference files for Omnia deployment. These are **not** used at runtime — they
serve as documentation and starting-point examples.

## Files

| File | Domain | Description |
|------|--------|-------------|
| `catalog_rhel.json` | image_build_manager | Sample RHEL catalog JSON produced by repo_manager. Shows functional layers, groups, and packages structure. |

## Usage

```bash
# Copy sample catalog to the convention path for testing:
sudo mkdir -p /opt/omnia/catalog
sudo cp samples/catalog_rhel.json /opt/omnia/catalog/

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
