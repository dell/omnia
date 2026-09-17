# test_run_config.yml — Batch Execution Reference

`test_run_config.yml` selects scenarios for a config-driven run:

```bash
cd test/telemetry
./run_validation.sh --config
```

The shipped configuration contains the four FVT scenarios in dependency
order. Every scenario is disabled by default.

## Global fields

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| `skip_on_failure` | No | Stop launching later scenarios after a failure. Must be an unquoted boolean. | `false` |
| `dataset_override` | No | Dataset name used for every enabled FVT scenario. | `""` |
| `sync_input_override` | No | Input-sync setting used for every enabled FVT scenario. Must be an unquoted boolean when set. | unset |

Global overrides take precedence over the matching per-scenario values.

## FVT scenarios

The `fvt_telemetry` mapping supports these scenario names:

| Scenario | Playbook tag | Available suites |
|----------|--------------|------------------|
| `precheck` | `precheck` | `cluster` |
| `validate` | `validate` | `input` |
| `deploy` | `deploy` | `sinks`, `sources` |
| `cleanup` | `cleanup` | `cleanup` |

Each scenario accepts:

| Field | Description | Default |
|-------|-------------|---------|
| `run` | Enable the scenario. Must be an unquoted boolean. | `false` |
| `command` | `exec` (playbook only), `verify` (pytest only), or `test` (both). | `test` |
| `suite` | Optional suite subdirectory from the table above. Empty runs the whole tag. | `""` |
| `marker` | Optional marker expression. | `""` |
| `dataset` | Per-scenario dataset override. | `""` |
| `sync_input` | Per-scenario override for `sync_telemetry_input`. | `false` |

FVT marker expressions use `+` for AND and `,` for OR. Registered Telemetry
markers include `sanity`, `functional`, `precheck`, `sink`, `source`, `deploy`,
`ome`, `ldms`, `vast`, `sfm`, `ufm`, `nft`, `performance`, and `idempotency`.

## Optional NFT and UT batch entries

The shared runner also accepts simple `nft_telemetry` and `ut_telemetry`
mappings. They are not present in the shipped file, but can be added when a
single batch should include those levels:

```yaml
nft_telemetry:
  run: false
  command: "test"
  marker: ""

ut_telemetry:
  run: false
  command: "test"
  marker: ""
```

For these categories, `run`, `command`, and `marker` are supported. The current
batch-runner allowlist supports the `performance` and `idempotency` NFT
markers. Current unit tests are unmarked, so leave their marker empty to run
the complete UT suite.

## Complete FVT example

```yaml
skip_on_failure: true

fvt_telemetry:
  precheck:
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: ""
    sync_input: false
  validate:
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: ""
    sync_input: false
  deploy:
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: ""
    sync_input: false
  cleanup:
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: ""
    sync_input: false
```

`cleanup` is intentionally excluded from an unqualified FVT run and should be
enabled explicitly. Sink PVC deletion is not a YAML field: use
`--delete-sinks-volume true` for a direct pytest invocation or set
`DELETE_SINKS_VOLUME=true` for the validation runner. The matching Ansible
variable is `Delete_sinks_volume`.
