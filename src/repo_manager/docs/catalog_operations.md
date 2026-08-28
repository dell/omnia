# Catalog Operations Guide

This document describes how to use the catalog management system in repo_manager.

## Overview

The catalog management system provides operations to:
- **Generate**: Create a new catalog from an input text file
- **Add**: Add or update packages in an existing catalog (upsert semantics)
- **Delete**: Remove packages from a catalog
- **Validate**: Validate a catalog against the schema and business rules

## Quick Start

```bash
cd /path/to/repo_manager/playbooks

# Generate a new catalog
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=input/packages.txt"

# Add packages to existing catalog
ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=input/additions.txt"

# Delete packages from catalog
ansible-playbook repo_manager.yml --tags catalog_delete \
  -e "input_file=input/removals.txt"

# Validate a catalog
ansible-playbook repo_manager.yml --tags catalog_validate
```

## Input File Format

### For Generate and Add Operations

The input file uses an INI-like format with optional defaults header:

```ini
# Optional defaults section (applies to all packages unless overridden)
[defaults]
arch=x86_64, os=rhel, os_version=10.0

# Group headers with optional metadata
# Format: [group_key | key=value, key=value, ...]
# Supported metadata: type, description, os, os_version
# 'type' defaults to "group" if omitted

[baseos_group_10.0 | type=base_os, description=base os packages, os=rhel, os_version=10.0]
systemd, rpm, systemd, baseos
wget, rpm, wget, appstream
glibc_langpack_en, rpm, glibc-langpack-en, baseos

[slurm_custom_group | description=slurm custom packages]
clustershell, rpm, clustershell, epel
papi, tarball, papi, https://github.com/icl-utk-edu/papi/releases/download/papi-7-2-0-t/papi-7.2.0.tar.gz
curl, image, docker.io/curlimages/curl, docker.io, 8.17.0

# Override arch for a specific package
doca_ofed, rpm_repo, doca-ofed, doca, arch=aarch64
```

### Package Line Formats

| Type | Format | Example |
|------|--------|---------|
| `rpm` | `key, rpm, name, reponame` | `wget, rpm, wget, appstream` |
| `rpm_repo` | `key, rpm_repo, name, reponame` | `doca_ofed, rpm_repo, doca-ofed, doca` |
| `tarball` | `key, tarball, name, url` | `papi, tarball, papi, https://...` |
| `image` | `key, image, image_path, registry, tag` | `curl, image, docker.io/curl, docker.io, 8.17.0` |

### Trailing Overrides

Any package line can have trailing key=value overrides:
- `arch=aarch64` - Override architecture
- `os=rhel` - Override OS
- `os_version=9.4` - Override OS version

### For Delete Operations

The delete input file is simpler - just group headers and package keys:

```ini
[baseos_group_10.0]
wget
glibc_langpack_en

[slurm_custom_group]
papi
```

## Operations Reference

### catalog_generate

Creates a new catalog from an input file.

```bash
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=input/packages.txt"
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_file` | Yes | - | Path to input text file |
| `catalog_file` | No | `catalogs/catalog.json` | Output catalog path |
| `catalog_name` | No | `default` | Name for the catalog |
| `force` | No | `false` | Overwrite existing file |
| `validate_after` | No | `true` | Run validation after generate |

**Behavior:**
- Fails if output file exists (unless `force=true`)
- Creates parent directories automatically

### catalog_add

Adds or updates packages in an existing catalog.

```bash
ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=input/additions.txt"
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_file` | Yes | - | Path to input text file |
| `catalog_file` | No | `catalogs/catalog.json` | Source catalog path |
| `output_file` | No | Same as `catalog_file` | Output path (preserves source if different) |
| `validate_after` | No | `true` | Run validation after add |

**Behavior:**
- **Upsert semantics**: Updates existing packages, adds new ones
- Auto-creates groups that don't exist
- No duplicates in `components[]` arrays

### catalog_delete

Removes packages from a catalog.

```bash
ansible-playbook repo_manager.yml --tags catalog_delete \
  -e "input_file=input/removals.txt"
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_file` | Yes | - | Path to delete input file |
| `catalog_file` | No | `catalogs/catalog.json` | Source catalog path |
| `output_file` | No | Same as `catalog_file` | Output path |
| `validate_after` | No | `true` | Run validation after delete |

**Behavior:**
- Removes packages from specified groups
- Deletes packages entirely when unreferenced by any group
- Removes empty groups automatically
- Skips (with warning) missing groups/packages

### catalog_validate

Validates a catalog against schema and business rules.

```bash
ansible-playbook repo_manager.yml --tags catalog_validate
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `catalog_file` | No | `catalogs/catalog.json` | Catalog to validate |
| `schema_file` | No | `schemas/catalog_schema.json` | JSON schema file |

**Validation Layers:**

1. **Structural (JSON Schema)**: Required fields, types, patterns
2. **Referential Integrity**: FunctionalLayer → Groups → Packages
3. **Business Rules**:
   - No duplicate components in arrays
   - Valid package types
   - Type-specific required fields (reponame for rpm, url for tarball, etc.)
   - base_os groups must have os and os_version
4. **Warnings**:
   - Orphan packages (unreferenced by any group)
   - Orphan groups (unreferenced by any functional layer)

## Catalog JSON Structure

```json
{
  "catalog": {
    "name": "default",
    "version": "1.0",
    "identifier": "default",
    "description": "",
    "functionallayer": [
      {
        "name": "layer_name",
        "components": ["group_key_1", "group_key_2"]
      }
    ],
    "groups": {
      "group_key": {
        "name": "group_key",
        "type": "group",
        "description": "Group description",
        "components": ["pkg_key_1", "pkg_key_2"]
      }
    },
    "packages": {
      "pkg_key": {
        "name": "package_name",
        "packagetype": "rpm",
        "sources": [
          {
            "architecture": "x86_64",
            "reponame": "baseos",
            "name": "rhel",
            "version": ["10.0"]
          }
        ]
      }
    }
  }
}
```

## Default Values

| Variable | Default | Description |
|----------|---------|-------------|
| `default_arch` | `x86_64` | Default architecture |
| `default_os` | `rhel` | Default OS |
| `default_os_version` | `10.0` | Default OS version |
| `catalog_file` | `catalogs/catalog.json` | Default catalog path |
| `schema_file` | `schemas/catalog_schema.json` | Default schema path |

## Logging

All operations write logs to `$OMNIA_DATA_PATH/repo_manager/log/catalog/`.

## Examples

### Complete Workflow

```bash
# 1. Create input file
cat > input/my_catalog.txt <<'EOF'
[defaults]
arch=x86_64, os=rhel, os_version=10.0

[baseos_group_10.0 | type=base_os, description=base os packages, os=rhel, os_version=10.0]
systemd, rpm, systemd, baseos
wget, rpm, wget, appstream

[slurm_group | description=slurm packages]
clustershell, rpm, clustershell, epel
EOF

# 2. Generate catalog
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=input/my_catalog.txt"

# 3. Add more packages
cat > input/add_packages.txt <<'EOF'
[slurm_group]
geopm, tarball, geopm, https://github.com/geopm/geopm/releases/geopm-3.1.0.tar.gz
EOF

ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=input/add_packages.txt"

# 4. Validate
ansible-playbook repo_manager.yml --tags catalog_validate

# 5. Delete a package
cat > input/remove.txt <<'EOF'
[baseos_group_10.0]
wget
EOF

ansible-playbook repo_manager.yml --tags catalog_delete \
  -e "input_file=input/remove.txt"
```

### Using Custom Paths

```bash
# Custom output path
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=input/packages.txt" \
  -e "catalog_file=catalogs/custom.json" \
  -e "catalog_name=my_custom_catalog"

# Preserve source catalog
ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=input/additions.txt" \
  -e "catalog_file=catalogs/v1.json" \
  -e "output_file=catalogs/v2.json"
```
