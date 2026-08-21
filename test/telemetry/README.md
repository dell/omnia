# Telemetry Test Automation

Functional Verification Testing (FVT) and Non-Functional Testing (NFT)
for the `telemetry` Ansible domain.

## Quick Start

```bash
# 1. One-time setup (creates venv, installs deps)
source setup_env.sh

# 2. Configure target server
#    Edit test_config.yml: set target_host, project_name
#    Edit test_creds.yml: set SSH credentials

# 3. Run tests
./run_validation.sh precheck test      # Precheck scenario
./run_validation.sh validate test      # Validation scenario
./run_validation.sh all test           # All FVT scenarios
```

## Architecture

```
SOURCES (10 collectors) -> BRIDGES (Vector) -> SINKS (3 backends)

Sources: iDRAC, LDMS, DCGM, PowerScale, UFM, VAST, OME, SFM, Skyway, PowerVault
Sinks:   VictoriaMetrics, VictoriaLogs, Kafka (Strimzi)
```

## Test Tags (match playbook tags)

| Tag | Scope |
|-----|-------|
| precheck | K8s cluster readiness |
| validate | Input file L1+L2 validation |
| deploy/execute | Full telemetry deployment |
| cleanup | Tag-based component removal |

## Module Structure

```
test/telemetry/
├── conftest.py           # Session setup
├── run_validation.sh     # CLI runner
├── setup_env.sh          # Venv setup
├── test_config.yml       # Target server settings
├── test_creds.yml        # SSH credentials (auto-encrypted)
├── datasets/             # Test input data + generator
├── library/              # Functions, vars, messages
│   ├── functions/        # Verification logic
│   ├── vars/             # Constants, TC IDs, CMDS
│   └── messages/         # Log + assert messages
├── fvt/                  # Functional Verification Tests
│   ├── precheck/         # Precheck scenario (7 TCs)
│   ├── validate/         # Validate scenario (6 TCs)
│   ├── deploy/           # Deploy scenario
│   │   ├── test_playbook.py    # TC_DP_001 (deploy playbook)
│   │   ├── sinks/              # Sink verification
│   │   │   ├── vm/             # VictoriaMetrics (6 TCs)
│   │   │   ├── vl/             # VictoriaLogs (2 TCs)
│   │   │   └── kafka/          # Kafka (4 TCs)
│   │   └── sources/            # Source verification
│   │       ├── idrac/          # iDRAC (5 TCs)
│   │       ├── ldms/           # LDMS (5 TCs)
│   │       └── ome/            # OME (3 TCs)
│   └── cleanup/          # Cleanup scenario (planned)
└── nft/                  # Non-Functional Tests (planned)
```

## Phase Summary

| Phase | TCs | Status |
|-------|-----|--------|
| Phase 1: precheck + validate | 13 | Implemented |
| Phase 2: sinks (VM, VL, Kafka) | 13 | Implemented |
| Phase 3: sources (iDRAC, LDMS, OME) | 13 | Implemented |
| Phase 4: sources (PowerScale, UFM, VAST, SFM) | 8 | Planned |
| Phase 5: cleanup (tag-wise) | 12 | Planned |
| Phase 6: NFT (perf, idempotency) | 5 | Planned |
| **Total** | **64** | |

See `fvt/README.md` for the complete test case registry.
See `PLAN.md` for the detailed phased implementation plan.
