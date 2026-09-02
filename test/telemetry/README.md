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

# 3. Run tests
./run_validation.sh fvt_telemetry precheck verify
```

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

### Options

| Option | Description |
|--------|-------------|
| `--suite <name>` | Filter by subfolder (`sinks`, `sources`, `cluster`, `input`) |
| `--marker <expr>` | Filter by pytest marker expression |
| `-v, --verbose` | Increase pytest verbosity |
| `--debug` | Full debug output (pytest `-vvs`) |

### Marker Expressions

| Syntax | Example | Meaning |
|--------|---------|---------|
| Single | `--marker sanity` | Tests with `@pytest.mark.sanity` |
| AND (`+`) | `--marker source+sanity` | Tests with BOTH markers |
| OR (`,`) | `--marker sink,source` | Tests with EITHER marker |

Available markers: `sanity`, `functional`, `sink`, `source`, `deploy`,
`ome`, `ldms`, `sfm`, `ufm`, `nft`, `performance`, `idempotency`

### Examples

```bash
# FVT
./run_validation.sh fvt_telemetry deploy test --marker sanity
./run_validation.sh fvt_telemetry deploy verify --suite sources
./run_validation.sh fvt_telemetry deploy verify --suite sinks
./run_validation.sh fvt_telemetry cleanup test

# SFM integration only (requires configure_sfm: true and SFM credentials)
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker sfm

# UFM source only (requires UFM metrics enabled in telemetry_config.yml)
./run_validation.sh fvt_telemetry deploy verify --suite sources --marker ufm
./run_validation.sh fvt_telemetry list

# NFT
./run_validation.sh nft_telemetry test                          # All NFT tests
./run_validation.sh nft_telemetry test --marker performance     # Performance only
./run_validation.sh nft_telemetry test --marker idempotency     # Idempotency only

# Config-driven batch
./run_validation.sh --config
```

### Typical Workflow

```bash
./run_validation.sh fvt_telemetry precheck test                     # 1. Precheck environment
./run_validation.sh fvt_telemetry validate test                     # 2. Validate inputs
./run_validation.sh fvt_telemetry deploy test --marker sanity        # 3. Deploy + verify sanity
./run_validation.sh fvt_telemetry verify --marker sanity              # 4. Full sanity verification
./run_validation.sh fvt_telemetry cleanup test                       # 5. Cleanup + verify
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
│   ├── functions/            # telemetry_func, k8s_func, cleanup_func, etc.
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
    └── test_idempotency.py   # Idempotency tests (deploy, cleanup)
```

## Test Case Summary

### FVT (Functional Verification Tests)

| Area | TCs | Marker |
|------|-----|--------|
| Precheck | 7 | sanity |
| Validate | 6 | sanity |
| Deploy | 62 | sanity + functional + source + sink |
| Cleanup | 14 | sanity + functional |
| **FVT Total** | **89** | |

### NFT (Non-Functional Tests)

| Area | TCs | Marker |
|------|-----|--------|
| Performance | 3 | nft + performance |
| Idempotency | 4 | nft + idempotency |
| **NFT Total** | **7** | |

### Grand Total: **89 Tests**

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

See `fvt/README.md` for the complete test case registry.
