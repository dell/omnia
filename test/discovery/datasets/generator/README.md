# Discovery Dataset Generator

Creates customer-readable test datasets from the current `src/discovery` input
examples. The source files remain authoritative; profiles contain only intentional
differences.

## Quick start

```bash
cd test/discovery/datasets/generator/

# See the available profiles
./generate_dataset.py profiles

# Preview without publishing
./generate_dataset.py create my_dataset \
  --profile defaults --dry-run

# Publish the dataset
./generate_dataset.py create my_dataset \
  --profile defaults
```

Then set `dataset: "my_dataset"` in `test_config.yml`. A dataset is a local
sync source; also enable `sync_discovery_input` when the files must be copied to
the execution target. Selecting a name alone does not modify the target. With a
non-empty name, input sync copies only that dataset's non-secret `input/`. An
empty name selects `src/discovery/input/`.

The `defaults` profile contains standard OME discovery configuration with example
OME IP address and network settings.

## Profiles

| Profile | Description |
|---------|-------------|
| `defaults` | Base profile with standard OME discovery configuration |

Custom profiles can be created to override specific parameters like OME IP,
network settings, or discovery mechanism.

## Customer-ready YAML

The generator round-trip loads the source YAML so applicable product headings
and guidance are retained. The renderer adds generated headers and value-aware
inline guidance.

The marker wording is deliberately searchable:

```bash
grep -R -n 'REPLACE WITH REAL VALUE' \
  ../my_dataset/input/
```

Valid defaults are not replaced with fake active settings:
- OME IP addresses remain as example values that should be replaced
- Network configuration uses example subnets that should be adapted
- Credentials remain external and are managed outside the dataset

### OME Configuration

The source sample contains placeholder OME IP addresses. The generator keeps
these as searchable markers that should be replaced with real OME server
addresses:

```bash
./generate_dataset.py create my_ome_config \
  --profile defaults \
  --var ome_ip=192.168.1.100
```

Replace `192.168.1.100` with the real OME server IP address reachable from the
execution environment.

### Credentials

Generated datasets never contain `discovery_credentials.yml`, credential keys,
or credential backups. Never place real or dummy secrets in a dataset.

The runtime credential contract requires OME username and password for discovery
operations.

From the generator directory, return to `test/discovery` before configuring
the separate encrypted runtime store:

```bash
cd ../..
./setup_env.sh --set-domain-creds
```

Run that command directly on the execution OIM with that OIM's
`OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME`. For remote execution, SSH to the
target OIM and run it there. The framework never syncs the encrypted credential
YAML, its vault key, or backups. `test_creds.yml` remains SSH-only.

## Common commands

### Inspect profiles

```bash
./generate_dataset.py profiles
./generate_dataset.py profiles defaults
```

### Preview, publish, replace, and check

```bash
# Build in staging; publish nothing
./generate_dataset.py create my_dataset \
  --profile defaults --dry-run

# Publish a new dataset
./generate_dataset.py create my_dataset \
  --profile defaults

# Replace an existing dataset after staging succeeds
./generate_dataset.py create my_dataset \
  --profile defaults --force

# Regenerate the same recipe and report any drift
./generate_dataset.py create my_dataset \
  --profile defaults --check
```

For `--check`, repeat the profile and overrides used to create the dataset. The
exact regeneration command is written to the generated `README.md`.

### Override an existing field

`--var` parses values as YAML, preserving booleans and integers:

```bash
./generate_dataset.py create custom_ome \
  --profile defaults \
  --var ome_ip=10.5.0.100 \
  --var admin_network=10.5.0.0
```

The IP addresses in these examples are illustrative; substitute endpoints that
are real and reachable in the customer environment.

### Source snapshot without a profile

```bash
./generate_dataset.py create source_snapshot --from-src
```

`--from-src` uses the same normalization, comment-preserving renderer, manifest,
and publication path as profiles; it simply applies no profile patch.

## Custom profiles

Profile files live under `profiles/`. A profile normally carries only recursive
patches:

```yaml
---
description: "Example profile for production OME"
patches:
  ome_ip: "192.168.100.50"
  admin_network: "10.0.0.0"
  admin_gateway: "10.0.0.1"
```

Credentials are not patchable. New keys are allowed only for configuration
parameters that are not security-sensitive.

## Authoritative contracts

| Contract | Authoritative source |
|----------|----------------------|
| Discovery settings | `src/discovery/input/discovery_config.yml` |
| Network specification | `src/discovery/input/network_spec.yml` |

The runtime consumer reads these files from the configured input directory on
the target server.

## Generation and publication safety

Before publication, the generator:

1. Loads the current product examples and records their SHA-256 hashes.
2. Applies a profile and CLI overrides.
3. Renders all YAML through the shared strict Jinja template.
4. Writes a deterministic manifest and customer handoff README.
5. Publishes the staged directory with locking and rollback protection.

The generator does not run product-schema or cross-file dataset validation.
After synchronization, use the Discovery `validate` and `precheck` flows to verify
the effective runtime inputs and environment.

## Generated output

```
datasets/<name>/
├── input/
│   ├── discovery_config.yml
│   └── network_spec.yml
├── dataset_manifest.yml
└── README.md
```

`dataset_manifest.yml` records the canonical profile, source hashes, source
normalizations, effective patches, YAML artifact hashes, and external runtime
inputs. It has no timestamp, so the same inputs produce stable output.

## Dependencies

- Python 3.12+
- PyYAML
- Jinja2

They are declared in `test/discovery/requirements.txt`. Install them from that
directory so the local wheel path resolves correctly:

```bash
cd ../..
./setup_env.sh
```
