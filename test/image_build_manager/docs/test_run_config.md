# test_run_config.yml — Batch Execution Reference

`test_run_config.yml` controls batch runs started with
`./run_validation.sh --config`. It selects test entries and supplies their
order, command, suite, marker, dataset, and sync overrides.

This file is separate from `test_config.yml`: `test_config.yml` describes the
target and default inputs, while `test_run_config.yml` selects what the batch
runner executes.

---

## Usage

```bash
# Edit the tracked batch configuration
vi test_run_config.yml

# Run every enabled entry
./run_validation.sh --config
```

All entries are disabled in the tracked file. Set `run: true` only for the
flows that should execute.

---

## Top-Level Structure

```yaml
skip_on_failure: false

# Optional global overrides for FVT entries
# dataset_override: "my_dataset"
# sync_input_override: true
# sync_output_override: true

fvt_image_build_manager:
  precheck:
    order: 1
    run: false
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: ""
    sync_input: false
    sync_output: false

nft_image_build_manager:
  run: false
  command: "test"
  marker: ""

ut_image_build_manager:
  run: false
  command: "test"
  marker: ""
```

Do not add a `scenarios:` wrapper. FVT tags belong directly under
`fvt_image_build_manager`.

---

## Order and Failure Handling

FVT entries with an `order` value run from the lowest value to the highest.
`order` must be a non-negative integer. Equal values retain their YAML file
order. Entries without `order` retain their YAML order after explicitly
ordered entries.

After FVT, the runner processes `nft_image_build_manager` and then
`ut_image_build_manager` when they are enabled.

The tracked FVT order is:

1. `precheck`
2. `validate`
3. `prepare`
4. `build`
5. `cleanup_images`
6. `cleanup`

Keep `cleanup_images` before `cleanup` when both are enabled. Image-only
cleanup deletes built S3 and registry images while the services remain
available. Full cleanup then removes the local infrastructure, data, output,
configuration, and domain credentials.

`skip_on_failure` is a Boolean:

| Value | Batch behavior |
|-------|----------------|
| `false` | Attempt every enabled entry and return non-zero if any entry failed. |
| `true` | After the first failed entry, report every later enabled FVT/NFT/UT entry as skipped and return non-zero. |

This setting does not stop the currently running pytest suite at its first test
failure; it controls whether later batch entries are scheduled.

---

## FVT Entry Fields

Each key under `fvt_image_build_manager` must be an existing FVT tag.

| Field | Type | Required | Behavior |
|-------|------|----------|----------|
| `order` | int | No | Batch order. Missing values run after explicitly ordered entries. |
| `run` | bool | Yes | `true` executes the entry; `false` reports it as skipped. |
| `command` | string | No | `exec`, `verify`, or `test`. Default: `test`. |
| `suite` | string | No | Verification subfolder. Empty selects the complete tag. |
| `marker` | string | No | Pytest marker expression. Empty selects all applicable tests. |
| `dataset` | string | No | Non-empty dataset environment override for this entry. |
| `sync_input` | bool | No | Overrides `sync_image_build_input` for this entry. |
| `sync_output` | bool | No | Overrides `sync_output` for this entry. |

If `sync_input` or `sync_output` is present, both `true` and `false` are
explicit overrides. Omit the field to leave the corresponding value from
`test_config.yml` unchanged. An empty `dataset` does not set a dataset
environment override.

### Command Modes

| Command | FVT behavior |
|---------|--------------|
| `exec` | Run the selected tag's deploy test only; no verification. |
| `verify` | Run non-deploy verification tests only; no playbook execution. |
| `test` | Run `exec`, then run `verify` only if execution succeeds. |

Use `test` for the normal tag lifecycle. `exec` and `verify` are phase-specific
commands for intentional deployment-only or verification-only runs.

For `command: "test"`, `marker` applies to both phases. Every deploy test has
the `sanity` marker, but architecture markers such as `x86_64` and `aarch64`
are not present on deploy tests. Use `marker: ""` to run every applicable case,
or `marker: "sanity"` for a sanity deploy-and-verify entry. Apply architecture
filters to a later `verify` entry or direct CLI rerun.

### Available FVT Tags and Suites

| Tag | Suite values |
|-----|--------------|
| `precheck` | `connectivity` |
| `validate` | `status` |
| `prepare` | `container`, `s3` |
| `build` | `s3`, `registry`, `naming`, `aarch64`, `image_verification` |
| `cleanup_images` | `cleanup_images` |
| `cleanup` | `cleanup` |

Suite filtering affects verification only; `exec` searches the complete tag
for its deploy test. If the configured suite directory does not exist, the
current runner falls back to the complete tag rather than failing. Confirm
suite names with:

```bash
./run_validation.sh fvt_image_build_manager list
```

### Marker Expressions

| Expression | Meaning |
|------------|---------|
| `sanity` | Match one marker. |
| `x86_64+sanity` | Match both markers (AND). |
| `x86_64,aarch64` | Match either marker (OR). |

Only marker names, `+`, and `,` are accepted in the batch file; whitespace and
shell metacharacters are rejected. Use either AND or OR in one expression; do
not mix `+` and `,`.

---

## Global FVT Overrides

The optional top-level values take precedence over matching per-entry values:

| Global field | Per-entry field | Environment variable passed to FVT |
|--------------|-----------------|------------------------------------|
| `dataset_override` | `dataset` | `OMNIA_DATASET_OVERRIDE` |
| `sync_input_override` | `sync_input` | `OMNIA_SYNC_INPUT_OVERRIDE` |
| `sync_output_override` | `sync_output` | `OMNIA_SYNC_OUTPUT_OVERRIDE` |

These batch overrides are passed only to FVT subprocesses. NFT and UT load
their settings from `test_config.yml` directly.

---

## NFT and UT Entries

NFT and UT use a flat top-level entry with `run`, `command`, and `marker`.
Although the shared parser accepts `exec`, `verify`, and `test`, all three
names execute the same complete pytest directory for NFT or UT. Use `test` as
the conventional and least ambiguous value.

Leave the NFT and UT marker empty unless their tests carry the selected marker.
NFT tests use `nft`; UT tests do not define the FVT quality or architecture
markers. A marker that matches nothing can produce an all-skipped run.

NFT is destructive: it runs repeated prepare plus timed prepare, build, and
cleanup operations. Its final test executes full cleanup. Do not enable FVT
`cleanup` and NFT in the same unattended batch unless domain credentials are
re-provisioned between them, because FVT cleanup removes the credentials that
the later NFT build needs.

---

## Complete FVT Batch Example

This example exercises every applicable FVT case and both cleanup tags in
dependency order. NFT remains a separate destructive run.

```yaml
skip_on_failure: true

fvt_image_build_manager:
  precheck:
    order: 1
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false
  validate:
    order: 2
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false
  prepare:
    order: 3
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false
  build:
    order: 4
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false
  cleanup_images:
    order: 5
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false
  cleanup:
    order: 6
    run: true
    command: "test"
    suite: ""
    marker: ""
    dataset: ""
    sync_input: false
    sync_output: false

nft_image_build_manager:
  run: false
  command: "test"
  marker: ""

ut_image_build_manager:
  run: false
  command: "test"
  marker: ""
```

The complete `command: "test"` cleanup example assumes the default MinIO
backend. With PowerScale, full cleanup intentionally retains the external S3
buckets and `/root/.s3cfg`, while `TC_CL_005` and `TC_CL_006` currently expect
them to be absent. Configure the final cleanup entry with `command: "exec"`
for PowerScale and verify the applicable local cleanup state separately.
