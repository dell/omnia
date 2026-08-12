# Discovery — Test Automation

Functional Verification Tests (FVT) for the `omnia.discovery` Ansible collection.

## Prerequisites

- Python 3.12+
- `omnia-auto` wheel (from `test/plugins/dist/`)
- Access to an OIM server with OME configured (for live tests)

## Setup

```bash
bash setup_env.sh            # One-time: create .venv, install deps
source .venv/bin/activate
vi test_config.yml           # Set oim_server_ip, dataset, etc.
```

## Running Tests

```bash
# Show help
run_validation --help

# Validate inputs exist on target
run_validation validate verify --marker sanity

# Full discovery run + verify outputs
run_validation discovery test

# Verify only output files (no playbook)
run_validation discovery verify --suite output

# Run all scenarios
run_validation all test

# Batch run from config
run_validation --config
```

## Scenarios

| Scenario | Description |
|----------|-------------|
| `validate` | Verify input files (discovery_config.yml, network_spec.yml) |
| `discovery` | Full end-to-end: deploy discovery.yml + verify outputs |

## Test Cases

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete test case registry.

## Directory Structure

```
test/discovery/
├── setup_env.sh               # Environment setup
├── run_validation.sh           # CLI runner
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
│   ├── vars/                   # Constants, paths, commands (common_vars)
│   └── messages/               # Test names, log/assert messages
│
└── fvt/                        # Functional Verification Tests
    ├── TEST_CASES.md
    ├── validate/               # Validate scenario
    │   └── status/
    │       └── test_status.py
    └── discovery/              # Full end-to-end
        └── output/
            └── test_output.py
```

## Using the omnia-auto Pip Package

This module uses the [omnia-auto](../plugins) package for all common test utilities
(TestLogger, run_playbook, sync_files, etc.).
