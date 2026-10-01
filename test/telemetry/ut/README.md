# Telemetry — UT Test Cases

Unit Tests (UT) for telemetry validate individual functions and components in isolation, without requiring a running Kubernetes cluster.

UT IDs use `TEL_UT_<SEQ>`: `TEL` is the stable Telemetry domain code, `UT` identifies the test level, and `SEQ` is a stable three-digit sequence.

Every registered unit-test function has a stable ID in the range `TEL_UT_001`
through `TEL_UT_056`. The centralized mapping is maintained in
`library/vars/ut_test_case_vars.py`; descriptive pytest function names remain
unchanged.

| ID range | Test file | Coverage |
|----------|-----------|----------|
| `TEL_UT_001`–`TEL_UT_022` | `test_ome_func.py` | OME pipeline selection, Kafka configuration, safe API/PFX arguments, exported endpoints, and retry behavior |
| `TEL_UT_023`–`TEL_UT_028` | `test_ome_victoria_func.py` | Victoria metric timestamps, identifiers, disabled pipelines, and log parsing |
| `TEL_UT_029`–`TEL_UT_036` | `test_idrac_lifecycle.py` | iDRAC enable/disable routing, retained-state restore, status, and fresh Kafka-flow contracts |
| `TEL_UT_037`–`TEL_UT_039` | `test_sink_enablement.py` | Direct source targets and Vector-OME/Vector-LDMS derived sink enablement |
| `TEL_UT_040`–`TEL_UT_046` | `test_ome_lifecycle.py` | OME independent metrics/logs reconciliation, dependency validation, retained-state restore, isolation, and status contracts |
| `TEL_UT_047`–`TEL_UT_049` | `test_kafka_topic_lifecycle.py` | Non-destructive topic-manifest cleanup, enabled-source application, and readiness gating |
| `TEL_UT_050`–`TEL_UT_056` | `test_disabled_state_fvt.py` | Disabled workload detection, required shared-sink health, and PowerScale quiet-window probes |
## Test Categories

| Category | Description | Marker |
|----------|-------------|--------|
| OME Functions | OME pipeline selection, Kafka configuration, safe API/PFX arguments, exported endpoints, and retry behavior | ut |
| OME Victoria | Victoria metric timestamps, identifiers, disabled pipelines, and log parsing | ut |
| iDRAC Lifecycle | iDRAC enable/disable routing, retained-state restore, status, and fresh Kafka-flow contracts | ut |
| Sink Enablement | Direct source targets and Vector-OME/Vector-LDMS derived sink enablement | ut |
| Disabled-State FVT Helpers | Stopped workloads and required shared-sink health | ut |

## Test Case Registry

### OME Functions (TEL_UT_001–TEL_UT_022)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_001 | OME polling timeouts | ut |
| TEL_UT_002 | OME pipeline context selects metrics channel | ut |
| TEL_UT_002 | OME pipeline context selects logs channel | ut |
| TEL_UT_002 | OME pipeline context selects metrics channel (redundant) | ut |
| TEL_UT_002 | OME pipeline context selects logs channel (redundant) | ut |
| TEL_UT_003 | Configure OME reconciles connection errors | ut |
| TEL_UT_004 | Configure OME retries transient errors | ut |
| TEL_UT_005 | Configure OME accepts spontaneous reconnections | ut |
| TEL_UT_006 | Configure OME stops on authentication failure | ut |
| TEL_UT_007 | Configure OME stops on action handler failure | ut |
| TEL_UT_008 | Configure OME stops at polling timeout | ut |
| TEL_UT_009 | Configure OME retries transient errors (redundant) | ut |
| TEL_UT_010 | OME forwarder actions require destination | ut |
| TEL_UT_011 | OME API values use testinfra queries | ut |
| TEL_UT_012 | OME PFX secret uses testinfra queries | ut |
| TEL_UT_013 | OME connectivity stops on empty endpoints | ut |
| TEL_UT_014 | OME connectivity recognizes both endpoints | ut |
| TEL_UT_015 | Get OME forwarder config reads from OME | ut |
| TEL_UT_016 | External Kafka details reject host without port | ut |
| TEL_UT_017 | External Kafka details accept host:port | ut |
| TEL_UT_018 | External Kafka playbook suppresses TLS when no cert | ut |
| TEL_UT_019 | External Kafka playbook reports TLS when cert present | ut |
| TEL_UT_020 | OME topics retry until all topics present | ut |
| TEL_UT_021 | OME topics accepts expected subset | ut |
| TEL_UT_022 | OME data retries for delayed reconnections | ut |

### OME Victoria Functions (TEL_UT_023–TEL_UT_028)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_023 | Collect metric results uses original metric names | ut |
| TEL_UT_024 | Collect metric results keeps metric names | ut |
| TEL_UT_025 | Verify metrics normalizes custom OME identifier | ut |
| TEL_UT_026 | Verify logs skips when bridge is disabled | ut |
| TEL_UT_027 | Parse log timestamp accepts ISO and nanoseconds | ut |
| TEL_UT_028 | Extract log fields returns readable names | ut |

### iDRAC Lifecycle (TEL_UT_029–TEL_UT_036)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_029 | iDRAC enable/disable routing (enable) | ut |
| TEL_UT_030 | iDRAC enable/disable routing (disable) | ut |
| TEL_UT_031 | iDRAC enable/disable routing (re-enable) | ut |
| TEL_UT_032 | iDRAC retained-state restore | ut |
| TEL_UT_033 | iDRAC status verification | ut |
| TEL_UT_034 | iDRAC fresh Kafka-flow contracts (enable) | ut |
| TEL_UT_035 | iDRAC fresh Kafka-flow contracts (disable) | ut |
| TEL_UT_036 | iDRAC fresh Kafka-flow contracts (re-enable) | ut |

### Sink Enablement (TEL_UT_037–TEL_UT_039)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_037 | Direct source targets enablement | ut |
| TEL_UT_038 | Vector-OME derived sink enablement | ut |
| TEL_UT_039 | Vector-LDMS derived sink enablement | ut |

### Disabled-State FVT Helpers (TEL_UT_050–TEL_UT_056)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_050 | Retained zero-replica workload is stopped | ut |
| TEL_UT_051 | Remaining disabled-source pod fails verification | ut |
| TEL_UT_052 | Only configured shared sinks are required | ut |
| TEL_UT_053 | Vector agent cannot satisfy the shared-agent check | ut |
| TEL_UT_054 | PowerScale quiet-window metrics count fresh samples | ut |
| TEL_UT_055 | PowerScale test event carries a unique marker | ut |
| TEL_UT_056 | PowerScale VL query matches only its marker | ut |

## Additional Tests (No TEL_UT IDs)

### Cleanup Sinks Parameter Normalization

| Test | Description | Status |
|------|-------------|--------|
| test_single_sink_kafka_normalization | Single sink normalization: `-e kafka` → `-e kafka=true` | PASS |
| test_single_sink_victoria_metrics_normalization | VictoriaMetrics normalization: `-e victoria_metrics` → `-e victoria_metrics=true` | PASS |
| test_comma_separated_normalization | Comma-separated: `-e kafka,victoria_metrics` → `-e sinks=kafka,victoria_metrics` | PASS |
| test_comma_separated_all_three_sinks | All three sinks: `-e kafka,victoria_metrics,victoria_logs` → `-e sinks=...` | PASS |
| test_explicit_form_no_change | Explicit form: `-e sinks=kafka` (no change) | PASS |
| test_separate_flags_normalization | Separate flags: `-e kafka -e victoria_metrics` | PASS |
| test_case_insensitive_kafka | Case sensitivity: `-e Kafka` → `-e Kafka=true` | PASS |
| test_case_insensitive_victoria_metrics | Case sensitivity: `-e Victoria_metrics` → `-e Victoria_metrics=true` | PASS |
| test_whitespace_in_comma_separated | Whitespace handling in comma-separated values | PASS |
| test_invalid_sink_name_no_normalization | Invalid sink rejection | SKIPPED (expected) |
| test_mixed_valid_invalid_no_normalization | Mixed valid/invalid rejection | SKIPPED (expected) |
| test_other_flags_unchanged | Other flags preservation | PASS |
| test_multiple_e_flags_normalization | Multiple -e flags handling | PASS |
| test_empty_value_after_e | Empty value handling | PASS |
| test_normalization_preserves_order | Argument order preservation | PASS |
| test_valid_sink_names | Valid sink names validation | PASS |
| test_invalid_sink_names | Invalid sink names rejection | PASS |
| test_marker_variable_null_default | Marker variable null defaults | PASS |
| test_short_form_detection_logic | Short-form detection logic | PASS |

**Note**: These tests do not have TEL_UT IDs as they test shell script functionality (`normalize_extra_args()` in `omnia.sh`) rather than Python functions.

## Execution

```bash
# Run all UT tests
cd /root/automation_testing/omnia/test/telemetry
./run_validation.sh ut_telemetry test

# Run specific test file
pytest ut/test_ome_func.py -v
pytest ut/test_ome_victoria_func.py -v
pytest ut/test_idrac_lifecycle.py -v
pytest ut/test_sink_enablement.py -v
pytest ut/test_cleanup_sinks_parameter_normalization.py -v

# Run with coverage
pytest ut/ --cov=src/telemetry --cov-report=html

# Run with verbose output
pytest ut/ -vv -s
```

## Expected Results

All UT tests should **PASS**:

```
Total Tests:           66
├─ Passed:             64 (97%)
├─ Failed:              0 (0%)
└─ Skipped:             2 (3%) — Expected behavior

OME Functions (TEL_UT_001–TEL_UT_022): 22/22 PASS
OME Victoria (TEL_UT_023–TEL_UT_028): 6/6 PASS
iDRAC Lifecycle (TEL_UT_029–TEL_UT_036): 8/8 PASS
Sink Enablement (TEL_UT_037–TEL_UT_039): 3/3 PASS
Cleanup Sinks Parameter Normalization: 18/20 PASS (2 skipped)
```

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../nft/README.md` for NFT test case registry
- See `../README.md` for overall test automation documentation
