# Telemetry — UT Test Cases

Unit Tests (UT) for telemetry validate individual functions and components in isolation, without requiring a running Kubernetes cluster.

UT IDs use `TEL_UT_<SEQ>`: `TEL` is the stable Telemetry domain code, `UT` identifies the test level, and `SEQ` is a stable three-digit sequence.

UT IDs also use `TEL_UT_CLEANUP_V<SEQ>` for cleanup sink tests: `TEL` is the stable Telemetry domain code, `UT` identifies the test level, `CLEANUP` identifies the subsystem, and `V<SEQ>` is a stable three-digit sequence.

Every registered unit-test function has a stable ID in the range `TEL_UT_001`
through `TEL_UT_056` and `TEL_UT_CLEANUP_V019` through `TEL_UT_CLEANUP_V062`. The centralized mapping is maintained in
`library/vars/test_case_vars.py`; descriptive pytest function names remain
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
| `TEL_UT_CLEANUP_V019`–`TEL_UT_CLEANUP_V035` | `cleanup_sinks/test_cleanup_sinks_deps.py` | Cleanup sink dependency checking for Kafka, VictoriaMetrics, and VictoriaLogs |
| `TEL_UT_CLEANUP_V036`–`TEL_UT_CLEANUP_V045` | `cleanup_sinks/test_cleanup_sinks_shortform.py` | Cleanup sink short-form parameter syntax and normalization |
| `TEL_UT_CLEANUP_V046`–`TEL_UT_CLEANUP_V062` | `test_cleanup_sinks_parameter_normalization.py` | Parameter normalization logic for short-form sink arguments |
## Test Categories

| Category | Description | Marker |
|----------|-------------|--------|
| OME Functions | OME pipeline selection, Kafka configuration, safe API/PFX arguments, exported endpoints, and retry behavior | ut |
| OME Victoria | Victoria metric timestamps, identifiers, disabled pipelines, and log parsing | ut |
| iDRAC Lifecycle | iDRAC enable/disable routing, retained-state restore, status, and fresh Kafka-flow contracts | ut |
| Sink Enablement | Direct source targets and Vector-OME/Vector-LDMS derived sink enablement | ut |
| Cleanup Sinks | Cleanup sink dependency checking, short-form parameter syntax, and parameter normalization | ut |
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

### OME Lifecycle (TEL_UT_040–TEL_UT_046)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_040 | Full deploy always invokes OME playbook | ut |
| TEL_UT_041 | OME dependency validation precedes deployment | ut |
| TEL_UT_042 | All OME channel combinations respected | ut |
| TEL_UT_043 | OME disable is idempotent and non-destructive | ut |
| TEL_UT_044 | OME restore reconciles configuration changes | ut |
| TEL_UT_045 | OME disabled forwarders protect against accidental cleanup | ut |
| TEL_UT_046 | OME status reports each channel as deployed or disabled | ut |

### Kafka Topic Lifecycle (TEL_UT_047–TEL_UT_049)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_047 | Disabled sources remove only their topics | ut |
| TEL_UT_048 | Topic deployment never discovers external topics | ut |
| TEL_UT_049 | Topic readiness wait is limited and fails fast | ut |

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

### Cleanup Sinks Dependency Checking (TEL_UT_CLEANUP_V019–TEL_UT_CLEANUP_V035)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_CLEANUP_V019 | Kafka cleanup allowed when no dependent sources | ut |
| TEL_UT_CLEANUP_V020 | Kafka cleanup blocked by dependent source | ut |
| TEL_UT_CLEANUP_V021 | Kafka cleanup blocked by multiple sources | ut |
| TEL_UT_CLEANUP_V022 | Kafka volumes preserved by default | ut |
| TEL_UT_CLEANUP_V023 | Kafka volumes deleted with delete_sinks_volume=true | ut |
| TEL_UT_CLEANUP_V024 | VictoriaMetrics cleanup allowed | ut |
| TEL_UT_CLEANUP_V025 | VictoriaMetrics cleanup blocked | ut |
| TEL_UT_CLEANUP_V026 | VictoriaMetrics cleanup blocked by multiple sources | ut |
| TEL_UT_CLEANUP_V027 | VictoriaLogs cleanup allowed | ut |
| TEL_UT_CLEANUP_V028 | VictoriaLogs cleanup blocked | ut |
| TEL_UT_CLEANUP_V029 | Sinks preserved on dependency check failure | ut |
| TEL_UT_CLEANUP_V030 | Unrelated sources do not block cleanup | ut |
| TEL_UT_CLEANUP_V031 | Repeated sink cleanup is idempotent | ut |
| TEL_UT_CLEANUP_V032 | Selective cleanup does not affect other sinks | ut |
| TEL_UT_CLEANUP_V033 | Volumes protected during blocked cleanup | ut |
| TEL_UT_CLEANUP_V034 | All-or-nothing — blocked sink prevents cleanup of others | ut |
| TEL_UT_CLEANUP_V035 | Playbook fails when sinks are blocked | ut |

### Cleanup Sinks Short-Form Parameters (TEL_UT_CLEANUP_V036–TEL_UT_CLEANUP_V045)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_CLEANUP_V036 | Short-form parameter -e kafka | ut |
| TEL_UT_CLEANUP_V037 | Comma-separated -e kafka,victoria_metrics | ut |
| TEL_UT_CLEANUP_V038 | All three sinks -e kafka,victoria_metrics,victoria_logs | ut |
| TEL_UT_CLEANUP_V039 | Separate flags -e kafka -e victoria_metrics | ut |
| TEL_UT_CLEANUP_V040 | Short-form and explicit form equivalence | ut |
| TEL_UT_CLEANUP_V042 | Actual resource cleanup for all sinks | ut |
| TEL_UT_CLEANUP_V043 | Dependency checking with short-form | ut |
| TEL_UT_CLEANUP_V045 | Volume preservation with short-form | ut |

### Cleanup Sinks Parameter Normalization (TEL_UT_CLEANUP_V046–TEL_UT_CLEANUP_V062)

| TC ID | Test | Marker |
|-------|------|--------|
| TEL_UT_CLEANUP_V046 | Single sink Kafka normalization | ut |
| TEL_UT_CLEANUP_V047 | Single sink VictoriaMetrics normalization | ut |
| TEL_UT_CLEANUP_V048 | Comma-separated normalization | ut |
| TEL_UT_CLEANUP_V049 | Comma-separated all three sinks | ut |
| TEL_UT_CLEANUP_V050 | Explicit form no change | ut |
| TEL_UT_CLEANUP_V051 | Separate flags normalization | ut |
| TEL_UT_CLEANUP_V052 | Case insensitive Kafka | ut |
| TEL_UT_CLEANUP_V053 | Case insensitive VictoriaMetrics | ut |
| TEL_UT_CLEANUP_V054 | Whitespace in comma-separated | ut |
| TEL_UT_CLEANUP_V055 | Other flags unchanged | ut |
| TEL_UT_CLEANUP_V056 | Multiple -e flags normalization | ut |
| TEL_UT_CLEANUP_V057 | Empty value after -e | ut |
| TEL_UT_CLEANUP_V058 | Normalization preserves order | ut |
| TEL_UT_CLEANUP_V059 | Valid sink names | ut |
| TEL_UT_CLEANUP_V060 | Invalid sink names | ut |
| TEL_UT_CLEANUP_V061 | Marker variable null default | ut |
| TEL_UT_CLEANUP_V062 | Short-form detection logic | ut |

## Execution

```bash
# Run all UT tests
cd /root/automation_testing/omnia/test/telemetry
./run_validation.sh ut_telemetry verify

# Run specific test file
pytest ut/test_ome_func.py -v
pytest ut/test_ome_victoria_func.py -v
pytest ut/test_idrac_lifecycle.py -v
pytest ut/test_sink_enablement.py -v
pytest ut/cleanup_sinks/test_cleanup_sinks_deps.py -v
pytest ut/cleanup_sinks/test_cleanup_sinks_shortform.py -v
pytest ut/test_cleanup_sinks_parameter_normalization.py -v

# Run with coverage
pytest ut/ --cov=src/telemetry --cov-report=html

# Run with verbose output
pytest ut/ -vv -s
```

## Expected Results

All UT tests should **PASS**:

```
Total Tests:           113
├─ Passed:             86 (76%)
├─ Failed:              0 (0%)
└─ Skipped:            27 (24%) — Expected behavior (cleanup_sinks tests skip when no dependencies running)

OME Functions (TEL_UT_001–TEL_UT_022): 22/22 PASS
OME Victoria (TEL_UT_023–TEL_UT_028): 6/6 PASS
iDRAC Lifecycle (TEL_UT_029–TEL_UT_036): 8/8 PASS
Sink Enablement (TEL_UT_037–TEL_UT_039): 3/3 PASS
OME Lifecycle (TEL_UT_040–TEL_UT_046): 7/7 PASS
Kafka Topic Lifecycle (TEL_UT_047–TEL_UT_049): 3/3 PASS
Disabled-State FVT Helpers (TEL_UT_050–TEL_UT_056): 7/7 PASS
Cleanup Sinks Dependency Checking (TEL_UT_CLEANUP_V019–TEL_UT_CLEANUP_V035): 1/17 PASS (16 skipped - no dependencies running)
Cleanup Sinks Short-Form Parameters (TEL_UT_CLEANUP_V036–TEL_UT_CLEANUP_V045): 0/9 PASS (9 skipped - no dependencies running)
Cleanup Sinks Parameter Normalization (TEL_UT_CLEANUP_V046–TEL_UT_CLEANUP_V062): 17/17 PASS
```

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../nft/README.md` for NFT test case registry
- See `../README.md` for overall test automation documentation
