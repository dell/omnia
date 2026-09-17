# Repo Manager Dataset Generator

The generator creates complete, reproducible Repo Manager FVT inputs from
Jinja2 templates or from the canonical public files in
`src/repo_manager/input/`. Credentials are never copied or generated.

## Commands

```bash
cd test/repo_manager/datasets/generator

# Discover profiles
python generate_dataset.py profiles
python generate_dataset.py profiles defaults

# Generate and atomically publish
python generate_dataset.py create my_dataset --profile defaults
python generate_dataset.py my_dataset rhel10

# Preview without publishing
python generate_dataset.py my_dataset defaults --dry-run

# Fail when an existing dataset has drifted
python generate_dataset.py my_dataset defaults --check

# Snapshot only the public source-input allowlist
python generate_dataset.py source_snapshot --from-src

# Replace an existing dataset atomically
python generate_dataset.py my_dataset defaults --force
```

The legacy positional syntax remains supported:

```bash
python generate_dataset.py <dataset_name> <profile>
```

## Options

| Option | Purpose |
|--------|---------|
| `--profile NAME` | Select a profile instead of using the positional form |
| `--var KEY=VALUE` | Override a declared, non-secret top-level variable |
| `--from-src` | Copy the two canonical public input files |
| `--dry-run` | Render and validate in staging without publishing |
| `--check` | Compare deterministic staged output with an existing dataset |
| `--force` | Atomically replace an existing dataset |
| `--list-profiles` | List supported profiles |
| `--show-profile NAME` | Display effective profile variables |

`--dry-run` and `--check` are mutually exclusive. `--check` cannot be combined
with `--force`.

## Output contract

```text
datasets/<name>/
├── input/
│   ├── repo_manager_config.yml
│   └── repo_manager_endpoint_config.yml
├── dataset_manifest.yml
└── README.md
```

`dataset_manifest.yml` records generator version, source hashes, CLI overrides,
and SHA-256 hashes for every generated input. It is deterministic so `--check`
can be used in CI to detect drift.

Publication uses a temporary staging directory. With `--force`, the existing
dataset is first moved to a rollback location and restored if publication
fails. A partially rendered dataset is never exposed as the final output.

## Credential boundary

Only these files may be copied by `--from-src`:

- `repo_manager_config.yml`
- `repo_manager_endpoint_config.yml`

Credential-, password-, secret-, token-, access-key-, and private-key-like CLI
variables are rejected. Configure the encrypted Repo Manager credential file
separately on the execution OIM.

## Using a generated dataset

Set the values in `test_config.yml`:

```yaml
dataset: "my_dataset"
sync_repo_manager_input: true
```

For batch execution, set `dataset` and `sync_input` on an enabled scenario in
`test_run_config.yml`, or use the global `dataset_override` and
`sync_input_override` values.
