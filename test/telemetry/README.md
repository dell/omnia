# Telemetry Test Automation

Functional Verification Testing (FVT) and Non-Functional Testing (NFT) for the `telemetry` Ansible domain.

## Quick Start

```bash
# 1. One-time setup (installs deps)
bash setup_env.sh

# 2. Configure target server
#    Edit test_config.yml: set oim_server_ip
#    Set SSH credentials:
bash setup_env.sh --set-creds

#    Set playbook/runtime telemetry credentials separately
bash setup_env.sh --set-domain-creds

# 3. Run tests
./run_validation.sh fvt_telemetry precheck verify
```

Interactive secret prompts require two matching entries. For pipeline use,
pipe the OIM SSH password to `--creds-stdin` or a validated domain-credential
JSON object to `--domain-creds-stdin`; secret values are not accepted as CLI
arguments. Domain credentials are written below `TELEMETRY_DATA_PATH` when it
is non-empty, otherwise below `$OMNIA_DATA_PATH/telemetry`. Both flows require
`OMNIA_PROJECT_NAME`.

### Environment and credential setup options

| Option | Purpose |
|--------|---------|
| *(no option)* | Install into the active virtual environment, or use the default bare-metal installation mode |
| `--venv` | Create `test/telemetry/.venv` and install there |
| `--force` | Reinstall dependencies; with `--venv`, recreate the virtual environment |
| `--set-creds` / `--update-creds` | Interactively create or update OIM SSH and enabled OME/SFM test credentials |
| `--creds-stdin` | Read only the OIM SSH password from standard input |
| `--set-domain-creds` / `--update-domain-creds` | Interactively create or update playbook/runtime Telemetry credentials |
| `--domain-creds-stdin` | Read a validated Telemetry credential JSON object from standard input |

`test_creds.yml` is the local Vault-encrypted test-access store. It may contain
`oim_password` and the enabled OME/SFM fields. The separate runtime store is
`telemetry_credentials.yml` with fields for enabled iDRAC, MySQL, PowerScale,
LDMS, UFM, and VAST components. Never commit either Vault key, plaintext
credentials, or locally populated credential files. Run
`bash setup_env.sh --help` for the complete command reference.

## Running Tests

Run from inside the `test/telemetry/` directory:

```
./run_validation.sh fvt_telemetry <command>             # All tags except cleanup
./run_validation.sh fvt_telemetry <tag> <command>        # Specific tag
./run_validation.sh fvt_telemetry list                   # List available tags
./run_validation.sh --config                             # Batch from test_run_config.yml
./run_validation.sh --help                               # Full help
```

### Commands

| Command | Description |
|---------|-------------|
| `exec` | Run the Ansible playbook only (no verification tests) |
| `verify` | Run verification tests only (no playbook) |
| `test` | Full flow: exec + verify |

### FVT Tags

| Tag | Playbook Tag | What It Tests |
|-----|-------------|---------------|
| `precheck` | `--tags precheck` | Env vars, K8s cluster health, connectivity |
| `validate` | `--tags validate` | Input config and credentials validation |
| `deploy` | `--tags deploy` | Deploy sinks + sources (Kafka, VM, VL, iDRAC, etc.) |
| `cleanup` | `--tags cleanup` | Cleanup resources (pods, services, topics) |
| *(none)* | *(no tag)* | Full end-to-end (all tags) |

### NFT Tags

| Tag | What It Tests |
|-----|---------------|
| `performance` | Validate, deploy, and cleanup performance thresholds |
| `idempotency` | Deploy and cleanup idempotency (second run exits 0) |
| `resilience` | Pod recovery, PVC persistence, service availability, node reboot, lifecycle |

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`sinks`, `sources`, `cluster`, `input`) |
| `--marker <expr>` | Filter by pytest marker expression |
| `-v, --verbose` | Increase pytest verbosity |
| `--debug` | Full debug output (pytest `-vvs`) |

### Cleanup: `Delete_volume` Flag (FVT Only)

The `cleanup` tag supports an optional `Delete_volume` flag that controls
whether PersistentVolumeClaims (PVCs) are deleted along with pods,
services, and workloads. It is exposed via the `DELETE_VOLUME`
environment variable, since `run_validation.sh` forwards the calling
shell's environment to pytest:

| `DELETE_VOLUME` | Playbook flag passed | PVC behavior |
|-----------------|----------------------|---------------|
| unset / `false` (default) | *(none — `Delete_volume` defaults to false)* | PVCs are **preserved** |
| `true` | `-e Delete_volume=true` | PVCs are **deleted** |

```bash
# FVT: Default cleanup preserves PVCs (Delete_volume=false)
./run_validation.sh fvt_telemetry cleanup test

# FVT: Cleanup + delete PVCs/volumes (Delete_volume=true)
DELETE_VOLUME=true ./run_validation.sh fvt_telemetry cleanup test
```

When `DELETE_VOLUME=true`, the corresponding PVC-deletion test
(`test_no_pvcs_after_full_cleanup`) runs and the playbook is invoked
with `-e Delete_volume=true`. Otherwise, `test_pvcs_preserved_after_cleanup`
runs instead to confirm PVCs were retained.

**Credential and Log Preservation Tests:**
The FVT cleanup suite also includes tests for `cleanup_credentials` and `cleanup_logs` flags:

```bash
# FVT: Cleanup with credential and log preservation
./run_validation.sh fvt_telemetry cleanup test
```

This runs additional verification tests:
- **TEL_FVT_CLEANUP_V015**: Verify credentials preserved (cleanup_credentials=false)
- **TEL_FVT_CLEANUP_V016**: Verify credentials deleted (cleanup_credentials=true)
- **TEL_FVT_CLEANUP_V017**: Verify logs preserved (cleanup_logs=false)
- **TEL_FVT_CLEANUP_V018**: Verify logs deleted (cleanup_logs=true)

See `fvt/README.md` for the full cleanup test case registry.

### NFT: Consolidated Test Execution

**Recommended approach**: Run the full NFT suite with a single command:

```bash
# Comprehensive NFT execution (both DELETE_VOLUME=false and DELETE_VOLUME=true scenarios)
./run_validation.sh nft_telemetry test
```

This consolidated execution automatically runs:
1. **Phase 1**: All performance, idempotency, and resilience tests with `DELETE_VOLUME=false` (PVCs preserved)
2. **Phase 2**: Cleanup-with-volume deletion tests with `DELETE_VOLUME=true` (all PVCs deleted)

This eliminates the need to run the NFT suite twice with different flags.

**⚠️ IMPORTANT - Data Loss Warning:**
After NFT completion, the cluster is left in a **fully cleaned-up state** with:
- All PVCs deleted (Kafka, VictoriaMetrics, VictoriaLogs)
- Input files deleted (`telemetry_config.yml`, etc.)
- Log files deleted
- Credential files deleted

**Before running NFT, back up any data you need to preserve:**
```bash
# Backup input files
cp -r <OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME> /path/to/backup/

# Backup logs
cp -r <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME> /path/to/backup/
```

See `nft/README.md` for detailed test case descriptions and recovery instructions.

### NFT: Consolidated Test Execution

**Recommended approach**: Run the full NFT suite with a single command:

```bash
# Comprehensive NFT execution (both DELETE_VOLUME=false and DELETE_VOLUME=true scenarios)
./run_validation.sh nft_telemetry test
```

This consolidated execution automatically runs:
1. **Phase 1**: All performance, idempotency, and resilience tests with `DELETE_VOLUME=false` (PVCs preserved)
2. **Phase 2**: Cleanup-with-volume deletion tests with `DELETE_VOLUME=true` (all PVCs deleted)

This eliminates the need to run the NFT suite twice with different flags.

**⚠️ IMPORTANT - Data Loss Warning:**
After NFT completion, the cluster is left in a **fully cleaned-up state** with:
- All PVCs deleted (Kafka, VictoriaMetrics, VictoriaLogs)
- Input files deleted (`telemetry_config.yml`, etc.)
- Log files deleted
- Credential files deleted

**Before running NFT, back up any data you need to preserve:**
```bash
# Backup input files
cp -r <OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME> /path/to/backup/

# Backup logs
cp -r <OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME> /path/to/backup/
```

See `nft/README.md` for detailed test case descriptions and recovery instructions.

### Marker Expressions

| Syntax | Example | Meaning |
|--------|---------|---------|
| Single | `--marker sanity` | Tests with `@pytest.mark.sanity` |
| AND (`+`) | `--marker source+sanity` | Tests with BOTH markers |
| OR (`,`) | `--marker sink,source` | Tests with EITHER marker |

Available markers: `sanity`, `functional`, `sink`, `source`, `deploy`,
`ome`, `ldms`, `sfm`, `ufm`, `vast`, `nft`, `performance`, `idempotency`,
`resilience`

### Examples

```bash
# FVT
./run_validation.sh fvt_telemetry deploy test --marker sanity
./run_validation.sh fvt_telemetry deploy verify --suite sources
./run_validation.sh fvt_telemetry deploy verify --suite sinks
./run_validation.sh fvt_telemetry cleanup test                              # Delete_volume=false (default): PVCs preserved
DELETE_VOLUME=true ./run_validation.sh fvt_telemetry cleanup test           # Delete_volume=true: PVCs deleted

# SFM integration only (requires configure_sfm: true and SFM credentials)
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker sfm

# UFM source only (requires UFM metrics enabled in telemetry_config.yml)
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker ufm

# VAST source on an existing Telemetry deployment
# (verify configures syslog, triggers an event, then verifies it)
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker vast
./run_validation.sh fvt_telemetry list

# NFT
./run_validation.sh nft_telemetry test                          # All NFT tests
./run_validation.sh nft_telemetry test --marker performance     # Performance only
./run_validation.sh nft_telemetry test --marker idempotency     # Idempotency only
./run_validation.sh nft_telemetry test --marker resilience      # Resilience only
DELETE_VOLUME=true ./run_validation.sh nft_telemetry test --marker idempotency  # Idempotency with PVC deletion

# Config-driven batch
./run_validation.sh --config
```

### Typical Workflow

```bash
./run_validation.sh fvt_telemetry precheck test                     # 1. Precheck environment
./run_validation.sh fvt_telemetry validate test                     # 2. Validate inputs
./run_validation.sh fvt_telemetry deploy test --marker sanity        # 3. Deploy + verify sanity
./run_validation.sh fvt_telemetry verify --marker sanity              # 4. Full sanity verification
./run_validation.sh fvt_telemetry cleanup test                       # 5. Cleanup + verify (PVCs preserved)
DELETE_VOLUME=true ./run_validation.sh fvt_telemetry cleanup test    # 5b. Full cleanup incl. PVCs (optional)
```

### SFM Prometheus Remote Write

SFM integration is opt-in because it changes an external SFM appliance. Set
`configure_sfm: true`, `sfm_api_ip`, and `sfm_ssh_ip` in `test_config.yml`,
then collect the required SFM API and SSH credentials in the encrypted
credentials file:

```bash
bash setup_env.sh --set-creds
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker sfm
```

The SFM SSH host key (and the OIM host key in remote-runner mode) must already
be verified in the test runner's `known_hosts`; unknown keys are rejected.
The SFM API address must be directly reachable from the test runner. The SFM
instance is fixed to instance 1. This lab integration does not expose an API CA
bundle or API TLS-verification setting, so run it only on an authorized network.

The SFM cases run in this order:

1. Generate or validate the Victoria export, then verify the Omnia `vminsert`,
   `vmstorage`, and `vmselect` workloads and pods.
2. Verify the corresponding Omnia services, ports, external addresses, and
   ready endpoints.
3. Verify the SFM Prometheus pod, configure its `vminsert` hosts mapping, and
   prove network reachability.
4. Import the CA, configure and read back Remote Write, and prove target-scoped
   forwarding health before accepting the change.
5. Verify three SFM transceiver metrics on one switch/interface series and show
   their earliest and latest original timestamps in the query window.

Warning: this flow may import a certificate, create or update the `victoria`
Remote Write target, and modify `/etc/hosts` inside the SFM Prometheus pod.
The pod-local hosts entry is ephemeral and may need to be restored after a pod
restart. A replaced certificate import is retained as rollback material. Set
`force_external_victoria_playbook: true` to regenerate the export and force a
certificate rotation. Run the suite only against an appliance authorized for
configuration.

---

## Architecture

```
SOURCES (collectors) -> BRIDGES (Vector) -> SINKS (backends)

Sources: iDRAC, LDMS, PowerScale, UFM, VAST, OME, SFM
Sinks:   VictoriaMetrics, VictoriaLogs, Kafka (Strimzi)
```

## Module Structure

```
test/telemetry/
├── setup_env.sh              # Environment setup (--venv, --set-creds, etc.)
├── run_validation.sh         # Shell entry point (delegates to _run.py)
├── _run.py                   # Python entry point (loads domain vars, creates runner)
├── conftest.py               # Pytest hooks, fixtures, report generation
├── test_config.yml           # Non-sensitive settings (IPs, paths)
├── test_creds.yml            # OIM/OME/SFM creds (--set-creds, auto-encrypted)
├── .test_creds.key           # Vault key for test_creds.yml (auto-created)
├── test_run_config.yml       # Batch execution: scenario order, markers, suites
│
├── library/                  # Reusable automation library
│   ├── functions/            # telemetry_func, k8s_func, cleanup_func, resilience_func, etc.
│   ├── vars/                 # Constants, component names (common_vars, test_case_vars)
│   └── messages/             # Test names, log/assert messages
│
├── fvt/                      # Functional Verification Tests
│   ├── precheck/             # Precheck tag tests
│   │   ├── test_playbook.py  # Playbook --tags precheck
│   │   └── cluster/          # Env vars, K8s nodes, kube_vip
│   ├── validate/             # Validate tag tests
│   │   ├── test_playbook.py  # Playbook --tags validate
│   │   └── input/            # Config validation
│   ├── deploy/               # Deploy tag tests
│   │   ├── test_playbook.py  # Playbook --tags execute
│   │   ├── test_namespace.py # All-pods-running check
│   │   ├── sinks/
│   │   │   ├── test_kafka.py
│   │   │   ├── test_victoriametrics.py
│   │   │   └── test_victorialogs.py
│   │   └── sources/
│   │       ├── test_idrac.py
│   │       ├── test_ldms.py
│   │       ├── test_ome.py
│   │       ├── test_powerscale.py
│   │       ├── test_sfm.py
│   │       ├── test_ufm.py
│   │       └── test_vast.py
│   └── cleanup/              # Cleanup tag tests
│       ├── test_playbook.py  # Playbook --tags cleanup
│       └── status/           # Verify sources/sinks/pods/PVCs removed
│           ├── test_cleanup_sources.py
│           ├── test_cleanup_sinks.py
│           └── test_cleanup_final.py
│
└── nft/                      # Non-Functional Tests
    ├── test_performance.py   # Performance thresholds (validate, deploy, cleanup)
    ├── test_idempotency.py   # Idempotency tests (deploy, cleanup)
    └── test_resilience.py    # Resilience tests (pod recovery, reboot, lifecycle)
```

## Test Case Summary

### FVT (Functional Verification Tests)

| Area | TCs | Marker |
|------|-----|--------|
| Precheck | 5 | sanity |
| Validate | 2 | sanity |
| Deploy | 90 | sanity + functional + source + sink |
| Cleanup | 15* | sanity + functional |
| Full-stack alternate ID | 1 | deploy |
| **FVT Total** | **113 reportable IDs / 111 test functions** | |

\* The two final-state PVC IDs are mode-dependent branches of
`test_no_pvcs_after_full_cleanup`; only the ID matching `DELETE_VOLUME` is
reported. `test_cleanup_topics_removed` also skips when
`DELETE_VOLUME` is unset/`false` (KafkaTopic CRDs are preserved in that
mode) — so 14 run when `DELETE_VOLUME=true`, 13 run otherwise.

### NFT (Non-Functional Tests)

| Area | TCs | Marker |
|------|-----|--------|
| Performance | 4 | nft + performance |
| Idempotency | 7 | nft + idempotency |
| Resilience | 9 | nft + resilience |
| **NFT Total** | **20** | |

NFT cleanup tests run in two phases: Phase 1 (without volume deletion,
PVCs preserved) and Phase 2 (with volume deletion, all PVCs deleted).
All 20 tests execute in a single `./run_validation.sh nft_telemetry test` run.

### Grand Total

Optional-source configuration determines which source-related cases
run or skip in a particular environment.

## Output Format

```
  ▶ [TEL_FVT_DEPLOY_V008] Verify all telemetry pods running
  → Checking all pods in telemetry namespace
  ✔ PASS: All 43 pods running

  ▶ [TEL_FVT_DEPLOY_V063] Verify UFM InfiniBand metrics in VictoriaMetrics
  → Querying VictoriaMetrics for UFM InfiniBand metrics
  ✔ PASS: 6 UFM metric(s) found
    │   ✓ infiniband_CBW: 0 (2026-08-24 12:59:50)
    │   ✓ PortXmitDataExtended: 94017600 (2026-08-24 12:59:50)
```

See `fvt/README.md` for the FVT test case registry and `nft/README.md`
for the NFT test case registry (performance, idempotency, resilience).
