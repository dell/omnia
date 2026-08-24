# Telemetry Test Automation

Functional Verification Testing (FVT) for the `telemetry` Ansible domain.

## Quick Start

```bash
# 1. One-time setup (creates venv, installs deps)
source setup_env.sh

# 2. Configure target server
#    Edit test_config.yml: set oim_server_ip, project_name
#    Edit test_creds.yml: set SSH credentials (auto-encrypted)

# 3. Run tests
./run_validation.sh telemetry verify               # All tests except cleanup
./run_validation.sh telemetry deploy verify          # Deploy tag tests only
./run_validation.sh telemetry verify --marker sanity  # Sanity tests only
```

## CLI

```
./run_validation.sh telemetry <command>             # All except cleanup
./run_validation.sh telemetry <tag> <command>        # Specific tag

Commands:
  exec      Run playbook only (no verification)
  verify    Run verification tests only (no playbook)
  test      exec + verify (full flow)

Tags (match ansible --tags):
  precheck  validate  deploy  cleanup
```

## Architecture

```
SOURCES (collectors) -> BRIDGES (Vector) -> SINKS (backends)

Sources: iDRAC, LDMS, DCGM, PowerScale, UFM, VAST, OME, SFM, Skyway, PowerVault
Sinks:   VictoriaMetrics, VictoriaLogs, Kafka (Strimzi)
```

## Module Structure

```
test/telemetry/
├── conftest.py               # Session setup, omnia_auto.configure()
├── run_validation.sh         # CLI runner
├── setup_env.sh              # One-time venv setup
├── test_config.yml           # Non-sensitive settings (IPs, paths)
├── test_creds.yml            # Credentials (auto-encrypted)
├── library/                  # Functions, vars, messages
│   ├── functions/
│   │   ├── __init__.py       # Public API (re-exports)
│   │   ├── telemetry_func.py # Common: kube_vip, config, VM/VL queries
│   │   ├── k8s_func.py       # K8s: pods, deploys, sts, services
│   │   ├── powerscale_func.py# PowerScale source verification
│   │   ├── ufm_func.py       # UFM source verification
│   │   ├── ome_func.py       # OME Kafka connectivity
│   │   └── validation_func.py# Config validation
│   ├── vars/
│   │   ├── common_vars.py    # Constants, component names, CMDS
│   │   └── test_case_vars.py # TEST_CASES dict (TC IDs + titles)
│   └── messages/
│       └── telemetry_msgs.py # TEST_LOG_MSGS, TEST_ASSERT_MSGS
└── fvt/
    ├── precheck/             # Precheck tag tests
    │   ├── test_playbook.py  # Playbook --tags precheck
    │   └── cluster/          # Env vars, K8s nodes, kube_vip
    ├── validate/             # Validate tag tests
    │   ├── test_playbook.py  # Playbook --tags validate
    │   └── input/            # Config validation
    ├── deploy/               # Deploy tag tests
    │   ├── test_playbook.py  # Playbook (tag from OMNIA_DEPLOY_TAG)
    │   ├── test_namespace.py # All-pods-running check
    │   ├── sinks/
    │   │   ├── test_kafka.py
    │   │   ├── test_victoriametrics.py
    │   │   └── test_victorialogs.py
    │   └── sources/
    │       ├── test_idrac.py
    │       ├── test_ldms.py
    │       ├── test_ome.py
    │       ├── test_powerscale.py
    │       └── test_ufm.py
    └── cleanup/              # Cleanup tag tests
        ├── test_playbook.py  # Playbook --tags cleanup
        └── cleanup/          # Verify pods removed, topics removed
```

## Test Case Summary

| Area | TCs | Marker |
|------|-----|--------|
| Namespace | 1 | sanity |
| Sinks: Kafka | 3 | sanity |
| Sinks: VictoriaMetrics | 2 | sanity |
| Sinks: VictoriaLogs | 2 | sanity |
| Sources: iDRAC | 6 | sanity + functional |
| Sources: LDMS | 2 | sanity |
| Sources: OME | 3 | sanity + functional |
| Sources: PowerScale | 6 | sanity + functional |
| Sources: UFM | 4 | sanity + functional |
| **Total** | **29** | |

## Output Format

```
  ▶ [TC_NS_001] Verify all telemetry pods running
  → Checking all pods in telemetry namespace
  ✔ PASS: All 43 pods running

  ▶ [TC_SR_019] Verify UFM InfiniBand metrics in VictoriaMetrics
  → Querying VictoriaMetrics for UFM InfiniBand metrics
  ✔ PASS: 6 UFM metric(s) found
    │   ✓ infiniband_CBW: 0 (2026-08-24 12:59:50)
    │   ✓ PortXmitDataExtended: 94017600 (2026-08-24 12:59:50)
```

## Tab Completion

```bash
eval "$(./run_validation.sh --completion)"
```

See `fvt/README.md` for the complete test case registry.
