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
| `marker` | A registered marker expression, or empty |
| `dataset` | A generated dataset name, or empty |
| `sync_input` | Unquoted `true` or `false` |

For an untagged command, `exec`, `verify`, and `test` follow install, build
pipeline, then deploy pipeline order. `test` performs execution and
verification for each scenario before advancing. Cleanup runs only when the
`buildstream_cleanup` scenario is explicitly selected. Batch entries remain
disabled unless explicitly enabled. Unknown commands, scenarios, suites,
markers, and incompatible values fail closed.

Marker expressions use `+` for AND and `,` for OR. Build Stream currently uses
`sanity` for all FVT cases; execution entry points additionally use `deploy`.
