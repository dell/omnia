# test_run_config.yml — Batch Execution Reference

`test_run_config.yml` selects the scenarios of a batch run started with:

```bash
./run_validation.sh --config
```

It only selects operations: every scenario is disabled by default and the
file never contains credentials. All other settings are in
[test_config.yml](test_config.md).

Back to the [suite README](../README.md).

## Scenario order

Enabled `svt_build_stream` scenarios run in this order:

1. `prepare_base`
2. `installation`
3. `auto_cleanup` (deletes the eligible image groups)
4. `cleanup` (destructive; review the `cleanup` blocks in `test_config.yml`)

## Scenario fields

| Field | Type | Purpose |
|---|---|---|
| `run` | Boolean | `true` includes the scenario. |
| `command` | String | `exec`, `verify` or `test`. |
| `suite` | String | Optional suite: `prepare_base`: `readiness`; `installation`: `health`, `repository`, `build`, `deploy`, `cadence`; `auto_cleanup`: `verification`; `cleanup`: `postconditions`. Empty runs the whole scenario. |
| `marker` | String | Optional marker expression: one marker, AND (`+`) or OR (`,`). Empty runs every test. |

`test` runs `exec` (precheck, then entry point) and then `verify`. Whether
the batch stops at the first failed scenario is decided by
`continue_on_failure` in `test_config.yml` (`false` = stop).

Example — only the cadence tests of an installed BuildStream:

```yaml
svt_build_stream:
  installation:
    run: true
    command: "verify"
    suite: "cadence"
    marker: ""
```

## Markers

| Marker | Selects |
|---|---|
| `svt`, `br_86010`, `sanity` | Every test |
| `prepare_base`, `installation`, `auto_cleanup`, `cleanup` | One scenario |
| `pipeline` | The build, deploy and cadence pipeline tests |
| `cadence` | The cadence pipeline test and the cadence disable/re-enable tests |
| `deploy` | Execution cases (`E…`); always selected in the exec phase |
| `precheck` | Scenario prechecks (`E001`) |
| `destructive` | The auto_cleanup pass and the domain cleanup |

List the scenarios, suites and test case IDs with:

```bash
./run_validation.sh svt_build_stream list
```
