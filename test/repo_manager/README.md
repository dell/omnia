# Repo Manager — Test Automation

Functional Verification Tests (FVT) for the `repo_manager` domain.

## Prerequisites

- Python 3.12+
- `omnia-auto` wheel (from `test/plugins/dist/`)
- Access to a target server with Pulp configured (for live tests)

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
./run_validation.sh fvt_repo_manager validate verify --marker sanity

# Deploy Pulp and verify
./run_validation.sh fvt_repo_manager prepare test

# Download and sync repositories
./run_validation.sh fvt_repo_manager execute verify

# Generate repo_status.yml
./run_validation.sh fvt_repo_manager status verify

# Run cleanup and verify removal
./run_validation.sh fvt_repo_manager cleanup test

# List available scenarios
./run_validation.sh fvt_repo_manager list

# Batch run from config
./run_validation.sh --config
```

## Scenarios

| Scenario | Description |
|----------|-------------|
| `validate` | Verify input files (repo_manager_config.yml, endpoint config, etc.) |
| `prepare` | Deploy Pulp server and verify container/services |
| `execute` | Download and sync repositories |
| `status` | Generate and verify repo_status.yml |
| `cleanup` | Cleanup Pulp server and verify removal |
| `policy` | Test repository policy configurations |
| `negative` | Test error scenarios |

## Test Cases

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete test case registry.

## Directory Structure

```
test/repo_manager/
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
│   ├── data_set_01/
│   │   ├── input/              # repo_manager_config, endpoint config
│   │   └── repo_manager_output/ # repo_status.yml
│   └── generator/               # Dataset generation tools
│
├── library/                    # Reusable automation library
│   ├── functions/              # Test helper functions
│   │   ├── repo_manager_func.py # Core repo_manager functions
│   │   └── __init__.py
│   ├── vars/                   # Constants, paths, commands
│   │   ├── common_vars.py      # Common variables and paths
│   │   ├── domain_vars.py      # Domain-specific variables
│   │   └── __init__.py
│   └── messages/               # Test names, log/assert messages
│       ├── repo_manager_msgs.py
│       └── __init__.py
│
└── fvt/                        # Functional Verification Tests
    ├── validate/               # Validate scenario
    │   └── test_status.py
    ├── prepare/                 # Prepare scenario
    │   └── test_status.py
    ├── execute/                 # Execute scenario
    │   └── test_status.py
    ├── status/                  # Status scenario
    │   └── test_status.py
    ├── cleanup/                 # Cleanup scenario
    │   └── test_status.py
    ├── policy/                  # Policy tests
    │   ├── test_integration_pulp_policies.py
    │   ├── test_partial_override.py
    │   ├── test_policy_combinations.py
    │   ├── test_priority_order.py
    │   ├── test_pulp_mode.py
    │   └── test_repo_types.py
    └── negative/                # Negative test scenarios
        └── error_scenarios/
            └── test_error_scenarios.py
```

## Test Categories

The test framework is organized into several categories:

| Category | Description | Test Count |
|----------|-------------|------------|
| **Validate Tests** | Verify input files and configurations | 4 |
| **Prepare Tests** | Deploy Pulp server and verify | 5 |
| **Execute Tests** | Download and sync repositories | 3 |
| **Status Tests** | Generate and verify repo_status.yml | 3 |
| **Cleanup Tests** | Cleanup Pulp server | 3 |
| **Policy Tests** | Test repository policies | 6 |
| **Negative Tests** | Test error scenarios | 1 |

## Test Markers

Tests can be filtered using pytest markers:

- `sanity`: Quick sanity tests
- `functional`: Functional verification
- `positive`: Positive test cases
- `negative`: Negative test cases
- `deploy`: Playbook deployment tests
- `x86_64`: x86_64 architecture tests
- `aarch64`: aarch64 architecture tests

## Using the omnia-auto Pip Package

This module uses the [omnia-auto](../plugins) package for all common test utilities
(TestLogger, run_playbook, sync_files, ValidationRunner, etc.).
