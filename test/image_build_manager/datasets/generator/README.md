# Image Build Manager Dataset Generator

Creates customer-readable test datasets from the current
`src/image_build_manager` input examples and the Repo Manager output contract.
The source files remain authoritative; profiles contain only intentional
differences.

## Quick start

```bash
cd test/image_build_manager/datasets/generator/

# See the use cases, then inspect the recommended profile
./generate_dataset.py profiles
./generate_dataset.py profiles internet-config

# Preview without publishing
./generate_dataset.py create my_dataset --profile internet-config --dry-run

# Publish the dataset
./generate_dataset.py create my_dataset --profile internet-config
```

Then set `dataset: "my_dataset"` in `test_config.yml`. A dataset is a local
sync source; also enable `sync_image_build_input` and/or `sync_output` when the
files must be copied to the execution target. Selecting a name alone does not
modify the target. With a non-empty name, input sync copies only that dataset's
non-secret `input/`, and output sync copies only its `repo_manager_output/`.
An empty name selects `src/image_build_manager/input/` and
`src/image_build_manager/samples/repo_manager_output/`.

`internet-config` is the easiest independent setup. It uses public CentOS
Stream/EPEL repositories and replaces the source Slurm/login mappings with
minimal `os_x86_64` and `os_aarch64` groups containing `bash`. It therefore
does not depend on the unavailable public `slurm_custom` repository.

## Profiles

| Profile | Repository source | Package source | Additional requirement |
|---------|-------------------|----------------|------------------------|
| `offline-catalog` | Repo Manager | Catalog | Reachable Repo Manager, certificate, and `CATALOG_FILE_PATH` |
| `offline-config` | Repo Manager | Complete source `package_groups.yml` | Reachable Repo Manager and certificate |
| `internet-catalog` | Public internet | Catalog | Outbound internet and `CATALOG_FILE_PATH` |
| `internet-config` | Public internet | Minimal public package groups | Outbound internet; recommended |

The two profile axes are explicit: repository location (`offline` or
`internet`) and package resolution (`catalog` or `config`). Catalog profiles
still include `package_groups.yml` so every dataset has the same layout, but
the playbook ignores that file in catalog mode.

Backward-compatible aliases remain available:

| Alias | Profile |
|-------|---------|
| `defaults` | `offline-catalog` |
| `config` | `offline-config` |
| `internet` | `internet-catalog` |
| `internet_config`, `standalone` | `internet-config` |

Generated manifests always record the canonical profile name, so an alias and
its canonical name produce identical content.

## Customer-ready YAML

All three YAML documents use one shared template,
`templates/document.yml.j2`. The generator round-trip loads the source YAML so
applicable product headings and guidance are retained. Intentional corrections
to stale source comments are recorded as source normalizations in the manifest.
The renderer then adds one generated header and value-aware inline guidance.

The marker wording is deliberately searchable:

```bash
grep -R -n 'REPLACE WITH REAL VALUE' \
  ../my_dataset/input/ ../my_dataset/repo_manager_output/
```

Valid defaults are not replaced with fake active settings:

- MinIO keeps `endpoint_url: ""`; an inline comment explains when PowerScale
  requires a real endpoint.
- `aarch64_inventory_host_ip` stays empty, which safely skips ARM builds.
- The default project path, build controls, and OS metadata stay aligned with
  the source example. Package lists stay source-aligned except where a profile
  explicitly replaces them, as `internet-config` does for public-repo safety.
- Public internet repository URLs remain real, usable test URLs.
- Credentials remain external and are managed outside the dataset.

### Offline repository host

The source offline sample contains literal `{{ admin_nic_ip }}` text, which is
not rendered when it is copied as ordinary YAML. The generator converts every
occurrence to the reserved dummy host `repo.example.invalid`. The 13 active RPM
URLs under `repositories` receive searchable replacement markers because Image
Build Manager reads and reachability-checks them. Producer-only `file_repos` and
legacy top-level URL fields stay in the fixture for Repo Manager output fidelity
but are labelled `REFERENCE ONLY`; Image Build Manager ignores them.

Replace all offline URLs consistently in one step:

```bash
./generate_dataset.py create my_offline \
  --profile offline-config \
  --repo-host repo.company.internal
```

`--repo-host` accepts a hostname or IPv4 address without a scheme, port, or
path. The existing HTTPS scheme, port, and paths are retained. Also verify that
`repo_manager.certificates.server_crt` points to a certificate that exists on
the execution target.

Replace `repo.company.internal` with the real reachable hostname or IP. The
generator rejects reserved documentation-only hosts supplied to `--repo-host`.

The canonical offline fixture has only a partial ARM repository set. If you
enable `aarch64_inventory_host_ip`, add reachable ARM `baseos` and `appstream`
URLs in a custom profile. The generator rejects a partial active set because
any nonempty list disables the playbook's Pulp fallback.

The generated `registries` mapping is empty. Image Build Manager does not
consume it, and the registry fields in its old sample differ from the current
Repo Manager producer contract. Current Repo Manager output with modern
`base_url` and TLS keys remains the authoritative producer shape.

### Credentials

Generated datasets never contain `image_build_credentials.yml`, credential
keys, or credential backups. Never place real or dummy secrets in a dataset.

The runtime credential contract requires `s3_secret_key` in every mode,
`s3_access_id` for PowerScale, and `aarch64_ssh_password` whenever
`aarch64_inventory_host_ip` is set.

From the generator directory, return to `test/image_build_manager` before
configuring the separate encrypted runtime store:

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
./generate_dataset.py profiles offline-config
```

### Preview, publish, replace, and check

```bash
# Build in staging; publish nothing
./generate_dataset.py create my_dataset --profile internet-config --dry-run

# Publish a new dataset
./generate_dataset.py create my_dataset --profile internet-config

# Replace an existing dataset after staging succeeds
./generate_dataset.py create my_dataset --profile internet-config --force

# Regenerate the same recipe and report any drift
./generate_dataset.py create my_dataset --profile internet-config --check
```

For `--check`, repeat the profile and overrides used to create the dataset. The
exact regeneration command is written to the generated `README.md`.

### Override an existing field

`--set` parses values as YAML, preserving booleans and integers. Use a dotted
path for ordinary keys:

```bash
./generate_dataset.py create ssl_disabled --profile offline-config \
  --set image_build_config:build_image.repo_ssl_verify=false \
  --repo-host repo.company.internal
```

Use JSON Pointer syntax when a key itself contains a dot, such as OS version
`10.0`:

```bash
./generate_dataset.py create priority_test --profile offline-config \
  --set repo_status:/repositories/10.0/x86_64/baseos/priority=90 \
  --repo-host repo.company.internal
```

Unknown documents, paths, and legacy variables fail immediately instead of
being silently ignored.

The limited `--var` compatibility aliases remain for common scalar values:

```bash
./generate_dataset.py create powerscale --profile internet-config \
  --var s3_provider=powerscale \
  --var s3_endpoint_url=https://powerscale.company.internal
```

The `company.internal` values in these examples are illustrative; substitute
endpoints that are real and reachable in the customer environment.

The supported aliases are `repo_manager_output_path`, `s3_provider`,
`s3_endpoint_url`, `image_build_type`, `build_image_max_parallel`,
`build_image_build_timeout`, `build_image_force_rebuild`,
`build_image_backup_s3_images`, `repo_ssl_verify`,
`functional_groups_source`, `aarch64_inventory_host_ip`, and
`aarch64_ssh_user`. Prefer `--set` for new automation.

### Source snapshot without a profile

```bash
./generate_dataset.py create source_offline --from-src
./generate_dataset.py create source_offline --from-src \
  --repo-host repo.company.internal
./generate_dataset.py create source_internet --from-src --repo-variant internet
```

`--from-src` uses the same normalization, comment-preserving renderer,
manifest, and publication path as profiles; it simply applies no profile
patch.

## Custom profiles

Profile files live under `profiles/`. A profile normally carries only recursive
patches:

```yaml
---
description: "Example profile"
repo_variant: "internet"
patches:
  image_build_config:
    build_image:
      max_parallel: 4
```

Mappings merge recursively; lists and scalar values replace their source
values. When a complete top-level field must replace inherited source data,
use `replacements`. The recommended internet profile uses this to replace the
entire functional-group mapping without duplicating every source group:

```yaml
replacements:
  package_groups:
    functional_groups:
      os_x86_64:
        packages: [bash]
      os_aarch64:
        packages: [bash]
```

Credentials are not patchable. New keys are allowed only below the intentionally
extensible package-group, repository, registry, and file-repository mappings.

## Authoritative contracts

| Contract | Authoritative source |
|----------|----------------------|
| Image Build Manager settings | `src/image_build_manager/input/image_build_config.yml` |
| Config-mode packages | `src/image_build_manager/input/package_groups.yml` |
| Repository consumer | `src/image_build_manager/plugins/modules/parse_repo_status.py` |
| Repo Manager producer | `src/repo_manager/plugins/modules/generate_local_repo_access.py` |

The runtime consumer reads `repositories.<version>.<architecture>.<name>.url`
and `repo_manager.certificates.server_crt`. Producer-only fields are preserved
where useful, but they are not presented as Image Build Manager requirements.

## Generation and publication safety

Before publication, the generator:

1. Loads the current product examples and records their SHA-256 hashes.
2. Applies a profile, whole-field replacements, and CLI overrides.
3. Renders all YAML through the shared strict Jinja template.
4. Writes a deterministic manifest and customer handoff README.
5. Publishes the staged directory with locking and rollback protection.

The generator does not run product-schema or cross-file dataset validation.
After synchronization, use the Image Build Manager `validate` and `precheck`
flows to verify the effective runtime inputs and environment.

## Generated output

```text
datasets/<name>/
├── input/
│   ├── image_build_config.yml
│   └── package_groups.yml
├── repo_manager_output/
│   └── repo_status.yml
├── dataset_manifest.yml
└── README.md
```

`dataset_manifest.yml` records the canonical profile, source hashes, source
normalizations, effective patches and replacements, repository host override,
YAML artifact hashes, replacement-marker count, and external runtime inputs. It
has no timestamp, so the same inputs produce stable output.

The obsolete `repo_manager_output/functional_group_packages.yml` is not
generated. Current builds use `input/package_groups.yml` in config mode or the
external catalog in catalog mode.

## Dependencies

- Python 3.12+
- PyYAML
- ruamel.yaml
- Jinja2

They are declared in `test/image_build_manager/requirements.txt`. Install them
from that directory so the local wheel path resolves correctly:

```bash
cd ../..
./setup_env.sh
```
