# Utils Domain — Test Automation

Functional Verification Testing (FVT) for the Omnia utils domain.

## Overview

This module provides automated testing for:

- **Log Collector** (`collect.yml`) — Collects logs from cluster nodes
- **PXE Boot** (`set_pxe_boot.yml`) — Sets PXE boot on Dell iDRAC nodes
- **Install OS** (`install_os.yml`) — Generic OS installation via iDRAC virtual media

## Quick Start

```bash
# 1. Setup environment (one-time)
./setup_env.sh

# 2. Configure target server
# Edit test_config.yml and set oim_server_ip

# 3. Run tests
./run_validation.sh collect test
./run_validation.sh precheck verify
```

## Directory Structure

```
test/utils/
├── conftest.py              # Pytest configuration
├── run_validation.sh        # Test runner script
├── setup_env.sh             # Environment setup
├── test_config.yml          # Test configuration
├── test_creds.yml           # Credentials (auto-encrypted)
├── test_run_config.yml      # Batch execution config
├── requirements.txt         # Python dependencies
│
├── datasets/                # Test input data
│   ├── generator/           # Dataset generator tool
│   └── data_set_*/          # Generated datasets
│
├── library/                 # Domain-specific code
│   ├── functions/           # Verification functions
│   ├── vars/                # Constants and test cases
│   └── messages/            # Log and assertion messages
│
└── fvt/                     # Functional Verification Tests
    ├── precheck/            # Environment checks
    ├── collect/             # Log collector tests
    └── set_pxe_boot/        # PXE boot tests
```

## Scenarios

| Scenario | Description | Tags |
|----------|-------------|------|
| `precheck` | Environment and connectivity checks | sanity |
| `collect` | Log collector tests | setup, prepare, bundle |
| `set_pxe_boot` | PXE boot tests | credentials, pxe_boot |
| `install_os` | OS installation tests | validate, fetch, create, deliver |

## Usage

### Single Scenario

```bash
# Run all tests for a scenario
./run_validation.sh collect test

# Run only deploy tests
./run_validation.sh collect deploy

# Run only verification tests
./run_validation.sh collect verify

# Filter by marker
./run_validation.sh collect test --marker sanity
```

### Batch Execution

```bash
# Run all scenarios from test_run_config.yml
./run_validation.sh --config
```

### Direct pytest

```bash
source .venv/bin/activate
pytest fvt/collect/ -v
pytest fvt/precheck/ -v --marker sanity
```

## Configuration

### test_config.yml

```yaml
oim_server_ip: "192.168.1.100"  # Target server (empty = local mode)
oim_ssh_user: "root"
dataset: ""                     # Dataset name (empty = use src/)
project_name: "project_default"
clone_path: "/root/omnia"
sync_utils_input: true
report_path: "reports"
report_name: "utils_test_report"
```

### test_creds.yml

```yaml
oim_password: ""      # SSH password
bmc_username: ""      # BMC credentials for PXE boot
bmc_password: ""
```

## Test Cases

### Precheck (TC_PC_*)

| ID | Test | Description |
|----|------|-------------|
| TC_PC_001 | target_connectivity | SSH connectivity to target |
| TC_PC_002 | env_vars_present | OMNIA environment variables |
| TC_PC_003 | hostname_domain | Hostname and domain match |
| TC_PC_004 | admin_ip_assigned | Admin IP on interface |
| TC_PC_005 | omnia_setup | omnia.sh setup completed |

### Collect (TC_CL_*)

| ID | Test | Description |
|----|------|-------------|
| TC_CL_001 | deploy_collect_setup | Deploy with setup tag |
| TC_CL_002 | deploy_collect_prepare | Deploy with prepare tag |
| TC_CL_003 | deploy_collect_bundle | Deploy with bundle tag |
| TC_CL_004 | deploy_collect_full | Full deployment |
| TC_CL_010 | collect_input_file_exists | Input file exists |
| TC_CL_011 | collect_input_file_valid | Input file valid YAML |
| TC_CL_012 | collect_functional_groups_valid | Valid functional groups |
| TC_CL_020 | collect_output_dir_exists | Output directory exists |
| TC_CL_021 | collect_bundle_created | Log bundle created |
| TC_CL_022 | collect_metadata_exists | Metadata file exists |
| TC_CL_023 | collect_metadata_valid | Metadata valid JSON |
| TC_CL_024 | collect_metadata_sha256 | SHA256 in metadata |
| TC_CL_025 | collect_bundle_contents | Bundle has expected dirs |

### PXE Boot (TC_PX_*)

| ID | Test | Description |
|----|------|-------------|
| TC_PX_001 | deploy_pxe_credentials | Deploy with credentials tag |
| TC_PX_002 | deploy_pxe_boot | Deploy with pxe_boot tag |
| TC_PX_003 | deploy_pxe_full | Full deployment |
| TC_PX_010 | pxe_config_file_exists | Config file exists |
| TC_PX_011 | pxe_config_valid | Config file valid |
| TC_PX_012 | pxe_inventory_file_exists | Inventory file exists |
| TC_PX_013 | pxe_inventory_valid | Inventory valid INI |
| TC_PX_014 | pxe_credentials_file_exists | Credentials file exists |
| TC_PX_020 | pxe_output_dir_exists | Output directory exists |
| TC_PX_021 | pxe_failed_nodes_file | Failed nodes file created |
| TC_PX_022 | pxe_failed_nodes_valid | Failed nodes valid JSON |

### Install OS (TC_IO_*)

| ID | Test | Description |
|----|------|-------------|
| TC_IO_001 | deploy_install_os_credentials | Deploy with credentials tag |
| TC_IO_002 | deploy_install_os_build_iso | Deploy with build_iso tag |
| TC_IO_003 | deploy_install_os_deploy | Deploy with deploy tag |
| TC_IO_004 | deploy_install_os_generate_ks | Deploy with generate_ks tag |
| TC_IO_005 | deploy_install_os_full | Full deployment |
| TC_IO_010 | install_os_config_file_exists | Config file exists |
| TC_IO_011 | install_os_config_valid | Config file valid |
| TC_IO_012 | install_os_credentials_file_exists | Credentials file exists |
| TC_IO_020 | install_os_output_dir_exists | Output directory exists |
| TC_IO_021 | install_os_status_file_exists | Status file created |
| TC_IO_022 | install_os_status_valid | Status file valid |
| TC_IO_030 | install_os_custom_iso_created | Custom ISO created (optional) |
| TC_IO_031 | install_os_kickstart_generated | Kickstart generated (optional) |

## Reports

Test reports are generated in HTML and JSON formats:

```
reports/
├── utils_test_report.html
└── utils_test_report.json
```

## Dependencies

- Python 3.12+
- pytest 9.0+
- pytest-testinfra 10.0+
- ansible-core 2.15+
- omnia-auto plugin (from test/plugins/)
