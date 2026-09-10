# Telemetry Dataset Generator

Creates customer-readable test datasets from the current
`src/telemetry/input` examples. The source files remain authoritative;
profiles contain only intentional differences.

## Quick start

```bash
cd test/telemetry/datasets/generator/

# See available profiles, then inspect one
./generate_dataset.py profiles
./generate_dataset.py profiles idrac_powerscale

# Preview without publishing
./generate_dataset.py create my_dataset --profile defaults --dry-run

# Publish the dataset
./generate_dataset.py create my_dataset --profile defaults
```

Then set `dataset: "my_dataset"` in `test_config.yml`. A dataset is a local
sync source; also enable `sync_telemetry_input` when the files must be copied
to the execution target. Selecting a name alone does not modify the target.

## Profiles

| Profile | Description | Use Case |
|---------|-------------|----------|
| `idrac_powerscale` | iDRAC and PowerScale enabled | Server and PowerScale storage telemetry |
| `idrac_ldms_powerscale` | iDRAC, LDMS, and PowerScale enabled | HPC compute, server, and PowerScale telemetry |
| `idrac_ldms` | iDRAC and LDMS enabled | HPC cluster baseline |
| `idrac_ome_ufm_sfm` | iDRAC, OME, and UFM enabled; SFM connects externally | Server, management, and fabric telemetry |
| `idrac_powerscale_vast` | iDRAC, PowerScale, and VAST enabled | Server and multi-storage telemetry |
| `ldms_only` | Only LDMS enabled | Compute-node metrics |
| `powerscale_only` | Only PowerScale metrics and logs enabled | PowerScale storage telemetry |
| `defaults` | Canonical source defaults | Source-aligned baseline |
| `online_mode` | Canonical source defaults with online installation | Internet-connected deployment |
| `offline_mode` | Canonical source defaults with offline installation | Air-gapped deployment |

The `defaults` profile is the recommended starting point. It uses the
canonical `src/telemetry/input/` files with no patches. Currently this enables
iDRAC, LDMS, PowerScale, and OME while leaving UFM and VAST disabled.

SFM is not a `telemetry_sources` configuration entry. In the
`idrac_ome_ufm_sfm` scenario, SFM sends metrics directly to the deployed
VictoriaMetrics remote-write endpoint using the connection details produced by
`external_victoria_connect`.

**Profile selection guide:**
- **`idrac_powerscale`** — Test server and PowerScale storage telemetry
- **`idrac_ldms_powerscale`** — Test the HPC baseline with PowerScale storage
- **`idrac_ldms`** — Test BMC and compute-node telemetry
- **`idrac_ome_ufm_sfm`** — Test iDRAC, OME, UFM, and external SFM integration
- **`idrac_powerscale_vast`** — Test iDRAC with PowerScale and VAST storage
- **`ldms_only`** — Test compute-node metrics without other sources
- **`powerscale_only`** — Test PowerScale metrics and logs in isolation
- **`defaults`** — Use the canonical source configuration unchanged
- **`online_mode`** — Use canonical source defaults with internet access
- **`offline_mode`** — Use canonical source defaults in an air-gapped deployment

**Important: Offline mode requires repo_url configuration**

When using the `offline_mode` profile, you **must** configure `repo_url` in the generated `telemetry_packages.yml`:

```bash
# Generate the dataset
./generate_dataset.py create my_offline --profile offline_mode

# Edit the generated telemetry_packages.yml
nano ../my_offline/input/telemetry_packages.yml
```

Set repo_url to your Pulp repository base URL

# Example Format: https://<ip_or_hostname>:<port>/pulp/content/opt/omnia/offline_repo/cluster/<arch>/<os>/<version>

The `repo_url` is used to construct all offline package URLs:
- Helm charts: `<repo_url>/tarball/<package>/<filename>`
- Git repos: `<repo_url>/git/<package>/<filename>`
- Pip modules: `<repo_url>/pip_module/<package>==<version>/`

Leave `repo_url: ""` for `online_mode` (not needed).

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
./generate_dataset.py profiles idrac_powerscale
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
`ome_metrics_enabled`, and `install_mode`. SFM has no source enablement alias
because it is an external VictoriaMetrics integration. Prefer `--set` for new
automation.

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
