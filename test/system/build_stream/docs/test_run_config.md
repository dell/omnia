# test_run_config.yml — Batch Execution Reference

`test_run_config.yml` controls batch runs started with:

```bash
./run_validation.sh --config
```

It selects operations only; every entry is disabled by default and it never
contains credentials.

## Scenario order

Enabled `e2e_build_stream` entries run in YAML order:

1. `prepare_base`
2. `installation`
3. `auto_cleanup` (deletes eligible image groups)
4. `cleanup` (destructive; review the cleanup blocks in `test_config.yml`)

## Entry fields

| Field | Type | Purpose |
|---|---|---|
| `run` | Boolean | Include this entry. |
| `command` | String | `exec`, `verify` or `test`. |
| `suite` | String | Optional suite: `prepare_base`: `readiness`; `installation`: `health`, `repository`, `build`, `deploy`, `cadence`; `auto_cleanup`: `verification`; `cleanup`: `postconditions`. |
| `marker` | String | Single marker, AND (`+`) or OR (`,`) expression. |

`test` runs `exec` (precheck, then entry point) and then `verify` only when
execution succeeded.
`skip_on_failure: true` stops the batch at the first failed entry.

## Markers

`sanity`, `deploy`, `precheck`, `destructive`, `e2e`, `br_86010`,
`prepare_base`, `installation`, `pipeline`, `cadence`, `cleanup`,
`auto_cleanup`. List the live tags and suites with:

```bash
./run_validation.sh e2e_build_stream list
```
