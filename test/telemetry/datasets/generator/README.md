# Telemetry Dataset Generator

Creates customer-readable test datasets from the current
`src/telemetry/input` examples. The source files remain authoritative;
profiles contain only intentional differences.

## Quick start

```bash
cd test/telemetry/datasets/generator/

# See available profiles, then inspect one
./generate_dataset.py profiles
./generate_dataset.py profiles idrac_only

# Preview without publishing
./generate_dataset.py create my_dataset --profile defaults --dry-run

# Publish the dataset
./generate_dataset.py create my_dataset --profile defaults
```

Then set `dataset: "my_dataset"` in `test_config.yml`. A dataset is a local
sync source; also enable `sync_telemetry_input` when the files must be copied
to the execution target. Selecting a name alone does not modify the target.

## Profiles

| Profile | Description |
|---------|-------------|
| `defaults` | All sources and sinks enabled (production-like baseline) |
| `idrac_only` | Only iDRAC source enabled (minimal deployment) |
| `sinks_only` | No sources, only sinks (sink infrastructure testing) |
| `minimal` | Everything disabled (validation-only, fastest dry run) |

The `defaults` profile is the recommended starting point. It uses the
canonical `src/telemetry/input/` files with no patches, matching a real
production deployment configuration.

## Source-first architecture

The generator loads the three canonical source YAML files, applies any
profile patches or CLI overrides, then renders the result through a shared
Jinja2 template. Source comments and structure are preserved using
ruamel.yaml round-trip loading.

### Authoritative contracts

| Contract | Authoritative source |
|----------|----------------------|
| Telemetry configuration | `src/telemetry/input/telemetry_config.yml` |
| Storage resource config | `src/telemetry/input/telemetry_storage_config.yml` |
| Packages and install mode | `src/telemetry/input/telemetry_packages.yml` |

## Common commands

### Inspect profiles

```bash
./generate_dataset.py profiles
./generate_dataset.py profiles idrac_only
```

### Preview, publish, replace, and check

```bash
# Build in staging; publish nothing
./generate_dataset.py create my_dataset --profile defaults --dry-run

# Publish a new dataset
./generate_dataset.py create my_dataset --profile defaults

# Replace an existing dataset after staging succeeds
./generate_dataset.py create my_dataset --profile defaults --force

# Regenerate the same recipe and report any drift
./generate_dataset.py create my_dataset --profile defaults --check
```

### Override an existing field

`--set` parses values as YAML, preserving booleans and integers. Use a
dotted path with a document prefix:

```bash
./generate_dataset.py create idrac_disabled \
  --profile defaults \
  --set telemetry_config:telemetry_sources.idrac.metrics_enabled=false
```

### Legacy variable overrides

The `--var` compatibility aliases remain for common flat values:

```bash
./generate_dataset.py create custom \
  --profile defaults \
  --var idrac_metrics_enabled=false \
  --var ldms_metrics_enabled=false
```

The supported aliases are `idrac_metrics_enabled`, `ldms_metrics_enabled`,
`powerscale_metrics_enabled`, `ufm_metrics_enabled`, `vast_metrics_enabled`,
`ome_metrics_enabled`, `sfm_metrics_enabled`, and `install_mode`.
Prefer `--set` for new automation.

### Source snapshot without a profile

```bash
./generate_dataset.py create source_snapshot --from-src
```

`--from-src` uses the same rendering, manifest, and publication path as
profiles; it simply applies no profile patch.

## Custom profiles

Profile files live under `profiles/`. A profile normally carries only
recursive patches:

```yaml
---
description: "Example profile"
patches:
  telemetry_config:
    telemetry_sources:
      idrac:
        metrics_enabled: false
```

Mappings merge recursively; lists and scalar values replace their source
values.

## Generated output

```text
datasets/<name>/
  input/
    telemetry_config.yml
    telemetry_storage_config.yml
    telemetry_packages.yml
  dataset_manifest.yml
  README.md
```

`dataset_manifest.yml` records the canonical profile, source hashes,
effective patches and replacements, YAML artifact hashes,
replacement-marker count, and external runtime inputs. It has no
timestamp, so the same inputs produce stable output.

## Credentials

Generated datasets never contain credentials. Appliance credentials
(OME, SFM, UFM, VAST) are stored in `test_creds.yml` which is
auto-encrypted with Ansible Vault on first run. Never place secrets
in a dataset.

## Dependencies

- Python 3.12+
- PyYAML
- ruamel.yaml
- Jinja2

They are declared in `test/telemetry/requirements.txt`. Install them
from that directory:

```bash
cd ../..
./setup_env.sh
```
