# Orchestrator `test_run_config.yml` reference

`./run_validation.sh --config` processes FVT scenarios in YAML order, followed
by NFT and unit categories.

Each FVT scenario supports:

| Field | Type | Purpose |
|---|---|---|
| `run` | boolean | Enable this scenario |
| `command` | `exec`, `verify`, or `test` | Execute, verify, or execute then verify |
| `suite` | string | Immediate suite folder below the selected tag |
| `marker` | string | Single, comma-OR, or plus-AND marker expression |
| `dataset` | string | Per-scenario generated dataset override |
| `sync_input` | boolean | Override input synchronization |
| `sync_output` | boolean | Override Repo Manager handoff synchronization |
| `sync_image_output` | boolean | Override Image Build Manager handoff synchronization |

Global `dataset_override`, `sync_input_override`, `sync_output_override`, and
`sync_image_output_override` take precedence over per-scenario values when
uncommented. All booleans must be unquoted YAML `true` or `false`.

The checked-in Slurm preset mirrors PR #5220’s Kubernetes workflow:

```yaml
fvt_orchestrator:
  provision:
    run: false
    command: exec
    suite: slurm
    marker: ""
    dataset: slurm_only
    sync_input: true
    sync_output: true
    sync_image_output: true

  check:
    run: false
    command: verify
    suite: slurm
    marker: sanity,functional
    dataset: slurm_only
    sync_input: false
    sync_output: false
    sync_image_output: false
```

Generate `datasets/slurm_only` first, set the desired `run` fields to `true`,
and execute:

```bash
./run_validation.sh --config
```

`skip_on_failure: true` stops after the first failed scenario. Destructive
flows still require their explicit destructive marker even when enabled in
the batch file.
