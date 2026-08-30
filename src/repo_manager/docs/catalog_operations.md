# Catalog Operations Guide

## Overview

Repo Manager provides four catalog operations:

| Operation | Purpose |
|-----------|---------|
| `catalog_generate` | Create a catalog from a text input file |
| `catalog_add` | Add new packages or update existing packages |
| `catalog_delete` | Remove package references and unreferenced packages |
| `catalog_validate` | Validate structure, references and business rules |

The configured catalog is the exact `.json` file from `CATALOG_FILE_PATH`.
Repo Manager's top-level environment validation requires this variable for
catalog operations.

---

## Quick Start

Run from `src/repo_manager/playbooks`:

```bash
# Create a catalog
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=/path/to/packages.txt"

# Add or update packages
ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=/path/to/additions.txt"

# Delete packages
ansible-playbook repo_manager.yml --tags catalog_delete \
  -e "input_file=/path/to/removals.txt"

# Validate the configured catalog
ansible-playbook repo_manager.yml --tags catalog_validate
```

Catalog writes are separate from Pulp synchronization. Run `precheck` and
`download` after changing a catalog.

---

## Generate and Add Input Format

The text input uses an INI-like structure:

```ini
[defaults]
arch=x86_64, os=rhel, os_version=10.0

[baseos_group_10.0 | type=base_os, description=base OS packages, os=rhel, os_version=10.0]
systemd, rpm, systemd, baseos
wget, rpm, wget, appstream

[slurm_custom_group | description=Slurm packages]
clustershell, rpm, clustershell, epel
papi, tarball, papi, https://example.com/papi-7.2.0.tar.gz
curl, image, docker.io/curlimages/curl, docker.io, 8.17.0

# Override one package source
doca_ofed, rpm_repo, doca-ofed, doca, arch=aarch64
```

### Group Header

```text
[group_key | key=value, key=value]
```

| Metadata | Description |
|----------|-------------|
| `type` | Group type; defaults to `group` |
| `description` | Human-readable description |
| `os` | OS name, normally `rhel` |
| `os_version` | OS version, for example `10.0` |

### Package Lines

| Type | Format | Example |
|------|--------|---------|
| `rpm` | `key, rpm, name, reponame` | `wget, rpm, wget, appstream` |
| `rpm_repo` | `key, rpm_repo, name, reponame` | `doca_ofed, rpm_repo, doca-ofed, doca` |
| `tarball` | `key, tarball, name, url` | `papi, tarball, papi, https://...` |
| `image` | `key, image, image_path, registry, tag` | `curl, image, docker.io/curlimages/curl, docker.io, 8.17.0` |

Trailing overrides supported on package lines:

- `arch=x86_64` or `arch=aarch64`
- `os=rhel`
- `os_version=10.0`

`rpm_repo` downloads the named package and its dependencies through DNF. The
mapped repository must retain content and therefore cannot use streamed policy.

---

## Delete Input Format

List package keys under their group:

```ini
[baseos_group_10.0]
wget

[slurm_custom_group]
papi
```

Deletion behavior:

- Remove the package key from the specified group.
- Remove a package object when no group references it.
- Remove an empty group when appropriate.
- Warn and continue for a missing group or package key.

---

## Operation Reference

### Generate

```bash
ansible-playbook repo_manager.yml --tags catalog_generate \
  -e "input_file=/path/to/packages.txt" \
  -e "output_file=/path/to/catalog.json" \
  -e "catalog_name=my_catalog"
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_file` | Yes | -- | Text definition file |
| `output_file` | No | Configured catalog | Output JSON file |
| `catalog_name` | No | `default` | Catalog name and initial identifier |
| `force` | No | `false` | Allow replacement of an existing output |
| `validate_after` | No | `true` | Validate generated JSON |
| `default_arch` | No | `x86_64` | Default source architecture |
| `default_os` | No | `rhel` | Default source OS |
| `default_os_version` | No | `10.0` | Default source OS version |

Generate fails when the output exists unless `force=true`.

### Add

```bash
ansible-playbook repo_manager.yml --tags catalog_add \
  -e "input_file=/path/to/additions.txt" \
  -e "catalog_input=/path/to/source.json" \
  -e "output_file=/path/to/updated.json"
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_file` | Yes | -- | Add/update definitions |
| `catalog_input` | No | Configured catalog | Source catalog |
| `output_file` | No | Configured catalog | Output catalog |
| `validate_after` | No | `true` | Validate updated JSON |

Add uses upsert semantics, creates missing groups and avoids duplicate component
references.

### Delete

```bash
ansible-playbook repo_manager.yml --tags catalog_delete \
  -e "input_file=/path/to/removals.txt" \
  -e "catalog_input=/path/to/source.json" \
  -e "output_file=/path/to/updated.json"
```

The variables have the same source/output meaning as `catalog_add`.

### Validate

```bash
ansible-playbook repo_manager.yml --tags catalog_validate \
  -e "catalog_input=/path/to/catalog.json"
```

| Validation layer | Checks |
|------------------|--------|
| JSON schema | Required fields, types and patterns |
| Referential integrity | Functional layers -> groups -> packages |
| Business rules | Supported types and type-specific fields |
| Duplicate checks | Repeated component references |
| Warnings | Unreferenced groups or packages |

Validation does not modify the catalog.

---

## Catalog JSON Shape

```json
{
  "catalog": {
    "name": "example",
    "version": "1.0",
    "identifier": "example",
    "description": "Example RHEL catalog",
    "functionallayer": [
      {
        "name": "baseos_rhel_10_0_x86_64",
        "components": ["baseos_group_10.0"]
      }
    ],
    "groups": {
      "baseos_group_10.0": {
        "name": "baseos_group_10.0",
        "type": "base_os",
        "description": "Base OS packages",
        "components": ["systemd"],
        "os": "rhel",
        "os_version": "10.0"
      }
    },
    "packages": {
      "systemd": {
        "name": "systemd",
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

## Logging

Catalog operations write:

```text
<REPO_MANAGER_DATA_PATH>/log/catalog/catalog_manager.log
```

## Safe Workflow

1. Write the text input.
2. Generate or update a new output path when reviewing a major change.
3. Run `catalog_validate`.
4. Set `CATALOG_FILE_PATH` to the approved `.json` file.
5. Run Repo Manager `precheck`.
6. Run `download` and then `status`.

See [Content Configuration Guide](content-configuration-guide.md) for how catalog
sources map to repositories and registries.
