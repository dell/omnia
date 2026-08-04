# fetch_build_packages

Resolves RPM packages required for OS image building using **dual-mode** package
resolution: config mode (from `package_groups.yml`) or catalog mode (from
`catalog_rhel.json` via the `parse_catalog` Python module).

## Modes

| Mode | Source | When |
|------|--------|------|
| **config** | `package_groups.yml` in project input dir | `functional_groups_source: "config"` |
| **catalog** | Catalog JSON via `omnia.image_build.parse_catalog` module | `functional_groups_source: "catalog"` |

Both modes produce the **same output shape**:
- `base_image_packages` — list of RPM names for base OS images
- `compute_images_dict` — dict of `{layer_name: {functional_group, packages, os_version}}`
- `cluster_os_type` — OS type (e.g. `rhel`); from `package_groups.yml` or catalog baseos group
- `cluster_os_version` — OS version (e.g. `10.0`); from `package_groups.yml` or catalog baseos group
- `service_k8s_version` — Kubernetes version string (catalog mode) or `""` (config mode)

### Config Mode Details

In config mode, functional groups are derived from the keys of the `functional_groups`
dict in `package_groups.yml`, filtered by architecture suffix (`_x86_64` / `_aarch64`).
No separate `functional_groups` list is needed in `image_build_config.yml`.

OS metadata (`os`, `os_version`) is read from top-level fields in `package_groups.yml`.

### Catalog Layer Classification

In catalog mode, layers are classified by **layer name** (not component membership):

| Layer Name Pattern | Classification | Package Handling |
|-------------------|---------------|-----------------|
| `baseos_*` (e.g. `baseos_rhel_10_0_x86_64`) | Base OS | All packages → `base_image_packages` |
| Any other (e.g. `slurm_node_rhel_10_0_x86_64`) | Compute | Only non-baseos component packages → `compute_images_dict` |

Compute layers that reference `baseos_group_*` components extract the `os_version`
from those groups but skip their packages (already in the base image).

## Requirements

- Network access to RPM repositories (or local Pulp mirror)
- Valid `repo_status.yml` with repository URLs
- **Config mode**: `package_groups.yml` in `input/<project>/` (contains OS metadata + group-to-RPM mapping)
- **Catalog mode**: Catalog JSON at path from `CATALOG_FILE_PATH` environment variable

## Modules Used

| Module | Purpose |
|--------|---------|
| `omnia.image_build.parse_catalog` | Parses catalog JSON, resolves three-level hierarchy (functionallayer → groups → packages), classifies layers by name prefix, extracts OS type and version from baseos groups, filters by architecture and package type |

## Role Variables

See `vars/main.yml` for the full list.

## Dependencies

- `image_build_setup` — environment, config loading, and repo_status parsing

## Example

```yaml
# Config mode (default)
- hosts: localhost
  roles:
    - fetch_build_packages

# Catalog mode — set in image_build_config.yml:
#   functional_groups_source: "catalog"
# Set CATALOG_FILE_PATH in omnia.env (e.g., /opt/omnia/catalog/catalog_rhel.json)
```
