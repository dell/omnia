# Dataset Generator — BuildStream

Creates reproducible BuildStream test datasets from the canonical
`src/build_stream/input/build_stream_config.yml`. Source values and comments
remain authoritative; profiles contain only intentional patches.

## Quick start

Run from `test/build_stream/datasets/generator`:

```bash
./generate_dataset.py profiles
./generate_dataset.py profiles disabled
./generate_dataset.py create my_dataset --profile defaults --dry-run
./generate_dataset.py create my_dataset --profile defaults
./generate_dataset.py create source_snapshot --from-src
```

Legacy creation syntax remains accepted:

```bash
./generate_dataset.py my_dataset defaults
```

## Profiles

| Profile | Purpose |
|---------|---------|
| `defaults` | Source-aligned configuration with BuildStream enabled |
| `disabled` | BuildStream disabled, for skip-path validation |

Profiles use the same document-patch shape as the Image Build Manager
generator:

```yaml
description: Example environment
patches:
  build_stream_config:
    enable_build_stream: true
    gitlab_host: "10.5.0.100"
```

Unknown documents and fields fail instead of silently creating invalid input.

## Overrides

Use typed, existing-field overrides for environment-specific values:

```bash
./generate_dataset.py create my_dataset --profile defaults \
  --set build_stream_config:build_stream_host_ip=10.5.0.28 \
  --set build_stream_config:gitlab_host=10.5.0.100
```

`--var KEY=VALUE` remains supported for top-level fields. Credential-, secret-,
password-, token-, and private-key-like fields are rejected. Credentials are
configured separately on the execution OIM with
`./setup_env.sh --set-domain-creds`.

## Safe generation modes

```bash
# Render and validate in staging without publishing
./generate_dataset.py create my_dataset --profile defaults --dry-run

# Compare an existing dataset with regenerated output
./generate_dataset.py create my_dataset --profile defaults --check

# Atomically replace an existing complete dataset
./generate_dataset.py create my_dataset --profile defaults --force
```

The output is staged first. An existing dataset is retained until the new
output is complete, and a failed generation does not publish partial files.

## Generated files

```text
datasets/<name>/
  input/
    build_stream_config.yml
  dataset_manifest.yml
  README.md
```

The manifest records the source path and SHA-256, applied patches, artifact
hashes, generator version, and remaining replacement-marker count. Empty
required host values are marked `REPLACE WITH REAL VALUE` when BuildStream is
enabled.

To use the dataset, set both values in `test_config.yml`:

```yaml
dataset: "my_dataset"
sync_build_stream_input: true
```
