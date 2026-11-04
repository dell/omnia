# `test_run_config.yml`

This file selects batch execution. Run enabled entries with:

```bash
./run_validation.sh --config
```

Each `fvt_build_stream` scenario supports:

| Field | Values |
|---|---|
| `run` | Unquoted `true` or `false` |
| `command` | `exec`, `verify`, or `test` |
| `suite` | A suite registered for the selected scenario, or empty |
| `marker` | A registered marker expression; empty (default) runs every test |
| `dataset` | A generated dataset name, or empty |
| `sync_input` | Unquoted `true` or `false` |

For an untagged command, `exec`, `verify`, and `test` follow the
`precheck -> prepare -> execute` order. `test` performs execution and
verification for each scenario before advancing. `prepare_base` and the
destructive `cleanup` scenario run only when explicitly selected. Batch entries
remain disabled unless explicitly enabled. Unknown commands, scenarios, suites,
markers, and incompatible values fail closed.

Marker expressions use `+` for AND and `,` for OR. Without a marker every
collected test runs.

| Marker | Selects |
|---|---|
| `sanity` | Baseline positive checks; not on the manual pipeline suites |
| `deploy` | The `test_playbook.py` entry test of each tag (runs the playbook or `omnia.sh`) |
| `pipeline` | Every execute suite that triggers or verifies a real pipeline |
| `build_pipeline` | `build_automatic` and `build_manual` |
| `deploy_pipeline` | `deploy_automatic` and `deploy_manual` |
| `automatic_execution` | Commit-triggered `build_automatic` and `deploy_automatic` |
| `manual_execution` | API-triggered (`PIPELINE_TYPE`) `build_manual` and `deploy_manual` |
| `cadence` | The cadence pipeline suite and the cadence disable/re-enable tests |
| `cleanup_pipeline` | `pipeline_cleanup` (`PIPELINE_TYPE=cleanup`) |
| `automatic_cleanup` | `auto_cleanup` (automated retention cleanup pass) |
| `nft`, `resilience`, `security`, `disruptive` | NFT selection |

Examples for the `execute` entry:

```yaml
  execute:
    run: true
    command: "verify"
    suite: ""
    marker: "manual_execution"          # build_manual, then deploy_manual
```

`marker: "build_pipeline,cadence"` runs both build suites and the cadence
suite; `marker: "deploy_pipeline"` alone is a deploy-only run and needs
`pipeline.deploy_image_group_id` in `test_config.yml`.
