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
- `compute_images_dict` — dict of `{layer_name: {functional_group, packages}}`
- `service_k8s_version` — Kubernetes version string (catalog mode) or `""` (config mode)

## Requirements

- Network access to RPM repositories (or local Pulp mirror)
- Valid `repo_status.yml` with repository URLs
- **Config mode**: `package_groups.yml` in `input/<project>/`
- **Catalog mode**: Catalog JSON at path specified in `image_build_config.yml`

## Modules Used

| Module | Purpose |
|--------|---------|
| `omnia.image_build.parse_catalog` | Parses catalog JSON, resolves three-level hierarchy (functionallayer → groups → packages), filters by architecture and package type |

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
#   catalog_file: "/opt/omnia/catalog/catalog_rhel.json"
```
