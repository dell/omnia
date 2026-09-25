# Telemetry Unit Tests

The Telemetry unit-test suite validates OME Kafka endpoint handling, retry and
timeout behavior, safe command argument transport, and VictoriaMetrics and
VictoriaLogs result processing without deploying Telemetry.

## Test identification

Every current unit-test function has a stable ID in the range `TEL_UT_001`
through `TEL_UT_039`. The centralized mapping is maintained in
`library/vars/ut_test_case_vars.py`; descriptive pytest function names remain
unchanged.

| ID range | Test file | Coverage |
|----------|-----------|----------|
| `TEL_UT_001`–`TEL_UT_022` | `test_ome_func.py` | OME pipeline selection, Kafka configuration, safe API/PFX arguments, exported endpoints, and retry behavior |
| `TEL_UT_023`–`TEL_UT_028` | `test_ome_victoria_func.py` | Victoria metric timestamps, identifiers, disabled pipelines, and log parsing |
| `TEL_UT_029`–`TEL_UT_036` | `test_idrac_lifecycle.py` | iDRAC enable/disable routing, retained-state restore, status, and fresh Kafka-flow contracts |
| `TEL_UT_037`–`TEL_UT_039` | `test_sink_enablement.py` | Direct source targets and Vector-OME/Vector-LDMS derived sink enablement |

The runner resolves each ID from the test file and function portion of the
pytest node ID and includes it in summaries and generated reports.
Parameterized variants of one function intentionally share that function's
ID. Every mapping stores its sequence explicitly, so source reordering cannot
renumber published cases. Add new functions with the next available ID.

## Execution

Run the complete suite from `test/telemetry/`:

```bash
./run_validation.sh ut_telemetry test
```

These tests use mocks and deterministic clocks; they do not require a live OME
or Kubernetes deployment.
