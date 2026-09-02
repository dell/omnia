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
| `precheck` | Read-only input validation (no system changes) |
| `validate` | Verify input files (orchestrator_config.yml, network_spec.yml, etc.) |
| `prepare` | Credentials + functional groups + OpenLDAP config prep |
| `deploy` | Deploy OpenCHAMI + OpenLDAP + validate readiness gates |
| `provision` | Full provisioning (K8s, Slurm, OS nodes) |
| `pxeboot` | PXE boot on iDRAC nodes (physical servers only) |
| `cleanup` | Cleanup + verify container/service removal |
| `upgrade` | In-place upgrade of OpenCHAMI + OpenLDAP |
| `rollback` | Revert OpenCHAMI + OpenLDAP to previous state |

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

├── docs/                       # Configuration documentation
│   ├── test_config.md
│   ├── test_creds.md
│   └── test_run_config.md

├── datasets/                   # Test input datasets
│   ├── data_set_01/
│   │   ├── input/              # orchestrator_config, network_spec
│   │   └── repo_manager_output/ # repo_status.yml
│   ├── slurm_only/             # SLURM-specific test dataset
│   │   └── input/
│   └── generator/               # Dataset generation tools
│       └── generate_dataset.py

├── library/                    # Reusable automation library
│   ├── functions/              # Test helper functions
│   │   ├── slurm_func.py       # SLURM verification functions
│   │   ├── orchestrator_module_tester.py   # Module structure testing
│   │   ├── orchestrator_playbook_tester.py  # Playbook testing
│   │   ├── orchestrator_role_tester.py     # Role structure testing
│   │   ├── openchami_config_func.py  # OpenCHAMI config testing
│   │   ├── validation_func.py # Validation utilities
│   │   └── __init__.py
│   ├── vars/                   # Constants, paths, commands
│   │   ├── common_vars.py      # Common variables and paths
│   │   ├── domain_vars.py      # Domain-specific variables
│   │   ├── slurm_vars.py       # SLURM-specific variables
│   │   └── __init__.py
│   └── messages/               # Test names, log/assert messages
│       ├── orchestrator_msgs.py
│       ├── orchestrator_test_msgs.py
│       ├── slurm_msgs.py       # SLURM test messages
│       └── __init__.py

└── fvt/                        # Functional Verification Tests
    ├── TEST_CASES.md
    ├── precheck/               # Precheck scenario (read-only validation)
    │   └── test_playbook.py
    ├── modules/                 # Module structure validation tests
    │   └── test_validate_orchestrator_config.py
    ├── playbooks/                # Playbook validation tests
    │   └── test_orchestrator_yml.py
    ├── roles/                    # Role structure validation tests
    │   └── test_orchestrator_setup.py
    ├── validate/               # Validate scenario
    │   ├── status/
    │   │   └── test_status.py
    │   ├── slurm/              # SLURM validation tests
    │   │   ├── test_slurm_status.py
    │   │   ├── test_slurm_infrastructure.py
    │   │   ├── test_slurm_nodes.py
    │   │   └── test_slurm_ssh.py
    │   └── test_dcgm_config.py
    ├── prepare/                 # Prepare scenario
    │   └── openchami/
    │       └── test_openchami.py
    ├── deploy/                 # Deploy scenario (OpenCHAMI + OpenLDAP)
    │   ├── status/
    │   │   └── test_status.py
    │   └── test_playbook.py
    ├── provision/              # Provision scenario
    │   ├── slurm/
    │   │   └── test_slurm_provision.py
    │   └── test_playbook.py
    ├── pxeboot/                # PXE Boot scenario (iDRAC)
    │   └── test_playbook.py
    ├── slurm/                   # SLURM comprehensive tests
    │   └── test_slurm.py
    ├── cleanup/                # Cleanup scenario
    │   └── status/
    │       └── test_status.py
    ├── upgrade/                # Upgrade scenario
    │   └── test_playbook.py
    └── rollback/               # Rollback scenario
        └── test_playbook.py
```

## Test Categories

The test framework is organized into several categories:

| Category | Description | Test Count |
|----------|-------------|------------|
| **Module Tests** | Validate Ansible module structure and dependencies | 3 |
| **Playbook Tests** | Validate playbook syntax and tags | 4 |
| **Role Tests** | Validate role structure and metadata | 4 |
| **SLURM Status Tests** | Verify SLURM services, directories, config files | 9 |
| **SLURM Infrastructure Tests** | Verify SLURM nodes, partitions, SSH connectivity | 12 |
| **SLURM Job Tests** | Test SLURM job execution (srun, sbatch, queueing) | 15 |
| **OpenCHAMI Tests** | Validate OpenCHAMI configuration and services | 7 |
| **Status Tests** | Verify input files and configurations | 5 |
| **Deploy Tests** | Full deployment playbook tests (skipped by default) | 5 |

## Test Markers

Tests can be filtered using pytest markers:

- `sanity`: Quick sanity tests
- `slurm`: SLURM-related tests
- `modules`: Module validation tests
- `playbooks`: Playbook validation tests
- `roles`: Role validation tests
- `openchami`: OpenCHAMI configuration tests
- `deploy`: Full deployment tests (requires `--marker deploy`)

## Using the omnia-auto Pip Package

This module uses the [omnia-auto](../plugins) package for all common test utilities
(TestLogger, run_playbook, sync_files, ValidationRunner, etc.).
