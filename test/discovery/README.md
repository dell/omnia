# Discovery — Test Automation

Functional Verification Tests (FVT), Non-Functional Tests (NFT), and
Unit Tests (UT) for the `discovery` domain.

## Prerequisites

- Python 3.12+
- `omnia-auto` wheel (from `test/plugins/dist/`)
- Access to an OIM server with OME configured (for FVT and NFT live tests)

## Setup

```bash
source setup_env.sh            # One-time: create .venv, install deps
vi test_config.yml             # Set oim_server_ip, dataset, etc.
```

## Running Tests

```bash
# Show help
./run_validation.sh --help

# ── FVT (Functional Verification Tests) ──────────────────────────────

# Validate inputs exist on target
./run_validation.sh fvt_discovery validate verify --marker sanity

# Run the Discovery prerequisite precheck
./run_validation.sh fvt_discovery precheck test --marker sanity

# Full discovery run + verify outputs
./run_validation.sh fvt_discovery discovery test

# Verify only output files (no playbook)
./run_validation.sh fvt_discovery discovery verify --suite output

# List available scenarios
./run_validation.sh fvt_discovery list

# Batch run from config
./run_validation.sh --config

# ── NFT (Non-Functional Tests) ───────────────────────────────────────

# Run all NFT tests (performance + idempotency)
./run_validation.sh nft_discovery test

# ── UT (Unit Tests) ──────────────────────────────────────────────────

# Run all unit tests (offline, no target server needed)
./run_validation.sh ut_discovery test
```

## Test Categories

### FVT — Functional Verification Tests

| Scenario | Description |
|----------|-------------|
| `precheck` | Validate the data path and OME TCP/443 reachability |
| `validate` | Verify input files (discovery_config.yml, network_spec.yml) |
| `credentials` | Create or update encrypted OME credentials |
| `execute` | Run the tagged OME discovery flow and verify outputs |
| `discovery` | Full end-to-end: deploy discovery.yml + verify outputs |
| `cleanup` | Run cleanup and verify output/credential behavior |

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete FVT test case registry.

### NFT — Non-Functional Tests

| Test | Description |
|------|-------------|
| `test_precheck_performance` | Precheck completes within threshold (60s) |
| `test_execute_performance` | Execute completes within threshold (600s) |
| `test_cleanup_performance` | Cleanup completes within threshold (120s) |
| `test_precheck_idempotent` | Precheck succeeds on repeated execution |
| `test_cleanup_idempotent` | Cleanup succeeds on repeated execution |

See [nft/README.md](nft/README.md) for NFT details and thresholds.

### UT — Unit Tests

| Test File | Description |
|-----------|-------------|
| `test_input_validation_schema.py` | Schema and credential rules validation |
| `test_discovery_config_validator.py` | L2 semantic validator (OME IP) |
| `test_standalone_independence.py` | Standalone independence and repo structure |

See [ut/README.md](ut/README.md) for UT details and test-case IDs.

## Directory Structure

```
test/discovery/
├── _run.py                     # ValidationRunner entry point
├── setup_env.sh                # Environment setup
├── run_validation.sh           # CLI runner (delegates to _run.py)
├── conftest.py                 # Pytest hooks, fixtures, report generation
├── test_config.yml             # Target server and sync settings
├── test_creds.yml              # SSH credentials (Ansible Vault)
├── test_run_config.yml         # Batch execution config
├── requirements.txt            # Python dependencies
│
├── docs/                       # Configuration documentation
│   ├── test_config.md
│   ├── test_creds.md
│   └── test_run_config.md
│
├── datasets/                   # Test input datasets
│   └── data_set_01/
│       └── input/              # discovery_config, network_spec
│
├── library/                    # Reusable automation library
│   ├── functions/              # discovery_func, host_func, validation_func
│   ├── vars/                   # Constants, paths, commands
│   │   ├── common_vars.py
│   │   ├── domain_vars.py
│   │   ├── test_case_vars.py
│   │   └── ut_test_case_vars.py
│   └── messages/               # Test names, log/assert messages
│
├── fvt/                        # Functional Verification Tests
│   ├── TEST_CASES.md
│   ├── cleanup/                # Cleanup behavior and status checks
│   ├── credentials/            # Credential flow checks
│   ├── discovery/              # Full end-to-end flow and outputs
│   ├── execute/                # Tagged execute flow and outputs
│   ├── precheck/               # Discovery prerequisite checks
│   └── validate/               # Validate scenario
│
├── nft/                        # Non-Functional Tests
│   ├── README.md
│   ├── test_performance.py
│   └── test_idempotency.py
│
└── ut/                         # Unit Tests
    ├── README.md
    ├── conftest.py
    ├── test_input_validation_schema.py
    ├── test_discovery_config_validator.py
    └── test_standalone_independence.py
```

## Using the omnia-auto Pip Package

This module uses the [omnia-auto](../plugins) package for all common test utilities
(TestLogger, run_playbook, sync_files, ValidationRunner, etc.).
