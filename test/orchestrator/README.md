# Orchestrator — Test Automation

Functional Verification Tests (FVT) for the `orchestrator` domain.

## Prerequisites

- Python 3.12+
- `omnia-auto` wheel (from `test/plugins/dist/`)
- Access to an OIM server with OpenCHAMI configured (for live tests)
- Provisioned nodes (for provision scenario tests)

## Setup

```bash
source setup_env.sh            # One-time: create .venv, install deps
vi test_config.yml             # Set oim_server_ip, dataset, etc.
```

## Running Tests

```bash
# Show help
./run_validation.sh --help

# Validate inputs exist on target
./run_validation.sh fvt_orchestrator validate verify --marker sanity

# Deploy prepare and verify OpenCHAMI containers
./run_validation.sh fvt_orchestrator prepare test

# Verify only OpenCHAMI containers (no playbook)
./run_validation.sh fvt_orchestrator prepare verify --suite openchami

# Run cleanup and verify removal
./run_validation.sh fvt_orchestrator cleanup test

# List available scenarios
./run_validation.sh fvt_orchestrator list

# Batch run from config
./run_validation.sh --config
```

## Scenarios

| Scenario | Description |
|----------|-------------|
| `validate` | Verify input files (orchestrator_config.yml, network_spec.yml, etc.) |
| `prepare` | Deploy OpenCHAMI + verify containers and API |
| `provision` | Full provisioning (K8s, Slurm, OS nodes) |
| `cleanup` | Cleanup + verify container/service removal |

## Test Cases

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete test case registry.

## Directory Structure

```
test/orchestrator/
├── _run.py                    # ValidationRunner entry point
├── setup_env.sh               # Environment setup
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
│       ├── input/              # orchestrator_config, network_spec
│       └── repo_manager_output/# repo_status.yml
│
├── library/                    # Reusable automation library
│   ├── functions/              # orchestrator_func, host_func, validation_func
│   ├── vars/                   # Constants, paths, commands (common_vars, domain_vars)
│   └── messages/               # Test names, log/assert messages
│
└── fvt/                        # Functional Verification Tests
    ├── TEST_CASES.md
    ├── validate/               # Validate scenario
    │   ├── status/
    │   │   └── test_status.py
    │   └── test_dcgm_config.py
    ├── prepare/                # Prepare scenario
    │   └── openchami/
    │       └── test_openchami.py
    ├── provision/              # Provision scenario
    │   └── test_playbook.py
    └── cleanup/                # Cleanup scenario
        └── status/
            └── test_status.py
```

## Using the omnia-auto Pip Package

This module uses the [omnia-auto](../plugins) package for all common test utilities
(TestLogger, run_playbook, sync_files, ValidationRunner, etc.).
