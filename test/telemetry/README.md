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

Available markers: `sanity`, `functional`, `sink`, `source`, `deploy`, `nft`, `performance`, `idempotency`

### Examples

```bash
# FVT
./run_validation.sh fvt_telemetry deploy test --marker sanity
./run_validation.sh fvt_telemetry deploy verify --suite sources
./run_validation.sh fvt_telemetry deploy verify --suite sinks
./run_validation.sh fvt_telemetry cleanup test
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
├── test_creds.yml            # SSH creds (created by --set-creds, auto-encrypted)
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
| Precheck | 4 | sanity |
| Validate | 2 | sanity |
| Deploy | 62 | sanity + functional + source + sink |
| Cleanup | 14 | sanity + functional |
| **FVT Total** | **82** | |

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
