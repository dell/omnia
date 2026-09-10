# Utils Domain — Test Automation

Functional Verification Testing (FVT) for the Omnia utils domain.

## Overview

This module provides automated testing for:

- **Log Collector** (`collect.yml`) — Collects logs from cluster nodes
- **Install OS** (`install_os.yml`) — Generic OS installation via iDRAC virtual media
- **Precheck** (`precheck`) — Environment validation and connectivity checks
- **Setup** (`setup`) — Domain setup and configuration
- **Cleanup** (`cleanup`) — Cleanup of log collection and OS installation artifacts

## Prerequisites

**IMPORTANT: Run setup_env.sh Before Any Test Execution**

Before running any tests, you MUST run the setup script to configure credentials and the test environment:

```bash
cd /root/sujal/omnia/test/utils
./setup_env.sh
```

**What setup_env.sh does:**
- Creates Python virtual environment (`.venv/`)
- Installs required dependencies (pytest, testinfra, ansible-core)
- Installs the `omnia_auto` plugin
- **Prompts for and configures credentials** (SSH, BMC, OS passwords)
- Encrypts credentials using Ansible Vault
- Sets up test configuration files

**Why this is required:**
- Credentials are needed for remote execution and install_os tests
- The credentials tag in playbooks requires pre-configured credential files
- Without setup_env.sh, tests will fail with "Credential file not found" errors

**After running setup_env.sh:**
- Credentials are stored in `test_creds.yml` (encrypted)
- Virtual environment is ready at `.venv/`
- Test configuration is initialized in `test_config.yml`

## Table of Contents

- [Quick Start](#quick-start)
- [Step-by-Step Setup](#step-by-step-setup)
- [Running Tests](#running-tests)
- [Test Scenarios](#test-scenarios)
- [Configuration](#configuration)
- [Dataset Mode](#dataset-mode)
- [Test Reports](#test-reports)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Setup environment (one-time)
cd /root/sujal/omnia/test/utils
./setup_env.sh

# 2. Configure test settings
vi test_config.yml  # Edit configuration

# 3. Run tests
./run_validation.sh collect test
```

---

## Step-by-Step Setup

### Step 1: Environment Setup

Navigate to the test automation directory and run the setup script:

```bash
cd /root/sujal/omnia/test/utils
./setup_env.sh
```

**What this does:**
- Creates a Python virtual environment (`.venv/`)
- Installs required Python packages (pytest, testinfra, etc.)
- Installs the `omnia_auto` plugin from `test/plugins/`
- Verifies the installation

**Expected output:**
```
[INFO] Setting up Python virtual environment...
[INFO] Installing dependencies...
[OK] Environment setup complete
```

### Step 2: Configure Test Settings

Edit the test configuration file:

```bash
vi test_config.yml
```

**Key configuration options:**

```yaml
# --- Target Server ---
# Leave empty for local mode (tests run on the same machine)
oim_server_ip: ""              # e.g., "10.0.0.100" for remote testing
oim_ssh_user: "root"
oim_ssh_port: 22

# --- Project ---
# Dataset name (directory under datasets/)
# Leave empty to use src/utils/input/ directly
dataset: "test_data"           # Use dataset mode
project_name: "project_default"
clone_path: "/opt/omnia"

# --- Sync ---
# Sync input files from dataset or src/ to target
sync_utils_input: true         # true = sync files, false = use existing files

# --- Report ---
report_path: "reports"
report_name: "utils_test_report"
```

### Step 3: Configure Credentials (Optional)

If testing requires credentials (for install_os tests):

```bash
vi test_creds.yml
```

```yaml
oim_password: ""           # SSH password for remote server
bmc_username: "root"       # BMC credentials for install_os
bmc_password: "calvin"
os_root_password: "P@ssw0rd"  # OS root password for install_os
```

**Note:** Credentials are automatically encrypted when tests run.

### Step 4: Prepare Input Files

#### Option A: Use Dataset Mode (Recommended)

1. **Use existing dataset:**
   ```bash
   # List available datasets
   ls datasets/
   
   # Configure to use a dataset
   vi test_config.yml
   # Set: dataset: "test_data"
   # Set: sync_utils_input: true
   ```

2. **Create custom dataset:**
   ```bash
   cd datasets/test_data/input/
   
   # Edit collect_pxe.yml
   vi collect_pxe.yml
   ```
   
   Example `collect_pxe.yml`:
   ```yaml
   ---
   # Kubernetes control plane nodes (x86_64)
   service_kube_control_plane_x86_64:
     - 192.168.1.10
   
   # Slurm controller nodes (x86_64)
   slurm_control_node_x86_64:
     - 182.10.0.50
   
   # Slurm compute nodes (x86_64)
   slurm_node_x86_64:
     - 192.168.1.40
     - 192.168.1.41
   ```

#### Option B: Use Source Files Directly

```bash
# Configure to use source files
vi test_config.yml
# Set: dataset: ""
# Set: sync_utils_input: false

# Manually place files on target
scp src/utils/input/collect_pxe.yml root@target:/opt/omnia/utils/input/project_default/
```

### Step 5: Set Environment Variables (Automatic)

The test runner automatically sets these environment variables:

```bash
export OMNIA_DATA_PATH="/opt/omnia"
export OMNIA_PROJECT_NAME="project_default"
```

**To override defaults:**
```bash
export OMNIA_DATA_PATH="/custom/path"
export OMNIA_PROJECT_NAME="my_project"
./run_validation.sh collect test
```

---

## Running Tests

### Basic Test Execution

#### Run All Tests for a Scenario

```bash
# Log collector tests (all)
./run_validation.sh collect test

# Install OS tests (all)
./run_validation.sh install_os test

# Precheck tests (verification only)
./run_validation.sh precheck verify
```

#### Run Specific Test Phases

```bash
# Run only deployment tests (playbook execution)
./run_validation.sh collect deploy

# Run only verification tests (no playbook execution)
./run_validation.sh collect verify
```

#### Filter by Test Markers

```bash
# Run only sanity tests
./run_validation.sh collect test --marker sanity

# Run only functional tests
./run_validation.sh collect test --marker functional

# Run only deployment tests
./run_validation.sh collect test --marker deploy
```

### Advanced Test Execution

#### Run Specific Test Suite

```bash
# Run specific test file
./run_validation.sh collect test --suite log_collector
```

#### Batch Execution (Multiple Scenarios)

```bash
# Run all scenarios defined in test_run_config.yml
./run_validation.sh --config
```

Edit `test_run_config.yml` to configure batch execution:
```yaml
skip_on_failure: false

scenarios:
  precheck:
    order: 1
    run: true
    command: "verify"
    marker: "sanity"
    
  collect:
    order: 2
    run: true
    command: "test"
    marker: "sanity"
    dataset: "test_data"
    sync_input: true
    
  install_os:
    order: 3
    run: false
    command: "test"
```

#### Direct pytest Execution

```bash
# Activate virtual environment
source .venv/bin/activate

# Run specific test file
pytest fvt/collect/test_collect.py -v

# Run with markers
pytest fvt/collect/ -v -m sanity

# Run specific test
pytest fvt/collect/test_collect.py::test_collect_input_file_exists -v
```

---

## Test Scenarios

### Scenario: `collect` (Log Collector)

**Purpose:** Test log collection from cluster nodes

**Test Execution Order:**
1. **Environment variable tests** (order 0-1) - Verify OMNIA_DATA_PATH and OMNIA_PROJECT_NAME
2. **Input validation tests** (order 2-4) - Verify collect_pxe.yml exists and is valid
3. **Playbook deployment tests** (order 5-8) - Execute collect.yml playbook
4. **Output verification tests** (order 9-15) - Verify log bundles and metadata

**Commands:**
```bash
# Full test (all phases)
./run_validation.sh collect test

# Only deploy playbook
./run_validation.sh collect deploy

# Only verify outputs
./run_validation.sh collect verify
```

**Input Files Required:**
- `collect_pxe.yml` - Node inventory with functional groups

**Expected Outputs:**
- Log bundle: `/opt/omnia/utils/output/project_default/collect/omnia_logs_YYYYMMDD-HHMMSS/`
- Metadata: `metadata.json`
- Tarball: `omnia_logs_YYYYMMDD-HHMMSS.tar.gz`

### Scenario: `install_os` (OS Installation)

**Purpose:** Test OS installation via iDRAC virtual media

**Commands:**
```bash
# Full test
./run_validation.sh install_os test

# Only build ISO
./run_validation.sh install_os deploy --marker build_iso
```

**Input Files Required:**
- `install_os_config.yml` - OS installation configuration
- `install_os_credentials.yml` - BMC and OS credentials

### Scenario: `precheck` (Environment Checks)

**Purpose:** Verify environment setup and connectivity

**Commands:**
```bash
# Run precheck
./run_validation.sh precheck verify
```

**Tests:**
- SSH connectivity to target
- Environment variables present
- Hostname and domain configuration
- Admin IP assignment

---

## Configuration

### Directory Structure

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
│   └── test_data/           # Test datasets
│       ├── input/           # Input files (collect_pxe.yml, etc.)
│       └── README.md
│
├── library/                 # Domain-specific code
│   ├── functions/           # Verification functions
│   ├── vars/                # Constants and test cases
│   └── messages/            # Log and assertion messages
│
├── fvt/                     # Functional Verification Tests
│   ├── precheck/            # Environment checks
│   ├── collect/             # Log collector tests
│   │   └── test_collect.py  # All collect tests (merged)
│   └── install_os/          # Install OS tests
│
└── reports/                 # Test reports (generated)
    ├── utils_test_report.html
    └── utils_test_report.json
```

### Test Configuration Files

#### `test_config.yml` - Main Configuration

```yaml
# --- Target Server ---
oim_server_ip: ""              # Target server IP (empty = local mode)
oim_ssh_user: "root"           # SSH user
oim_ssh_port: 22               # SSH port

# --- Project ---
dataset: "test_data"           # Dataset name (empty = use src/)
project_name: "project_default"
clone_path: "/opt/omnia"

# --- Sync ---
sync_utils_input: true         # Sync input files to target

# --- Report ---
report_path: "reports"
report_name: "utils_test_report"
```

#### `test_creds.yml` - Credentials

```yaml
oim_password: ""               # SSH password
bmc_username: "root"           # BMC username
bmc_password: "calvin"         # BMC password
os_root_password: "P@ssw0rd"   # OS root password
```

#### `test_run_config.yml` - Batch Execution

```yaml
skip_on_failure: false

scenarios:
  collect:
    order: 1
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: "test_data"
    sync_input: true
```

---

## Dataset Mode

### What is Dataset Mode?

Dataset mode allows you to:
- Store multiple test configurations as datasets
- Switch between datasets easily
- Version control test inputs
- Share test configurations across teams

### Using Existing Datasets

```bash
# List available datasets
ls datasets/

# Configure to use a dataset
vi test_config.yml
```

```yaml
dataset: "test_data"      # Use test_data dataset
sync_utils_input: true    # Sync files to target
```

### Creating Custom Datasets

```bash
# Create dataset directory
mkdir -p datasets/my_dataset/input

# Create collect_pxe.yml
cat > datasets/my_dataset/input/collect_pxe.yml << 'EOF'
---
service_kube_control_plane_x86_64:
  - 192.168.1.10

slurm_control_node_x86_64:
  - 182.10.0.50
EOF

# Use the dataset
vi test_config.yml
# Set: dataset: "my_dataset"
```

### Dataset vs Manual Mode

| Mode | Configuration | Use Case |
|------|---------------|----------|
| **Dataset** | `dataset: "test_data"`, `sync_utils_input: true` | Automated testing, CI/CD |
| **Manual** | `dataset: ""`, `sync_utils_input: false` | Manual testing, debugging |

### Using Test Automation with Dataset vs Without Dataset

#### Option 1: With Dataset (Recommended for Testing)

Dataset mode uses pre-configured test data files from the `datasets/` directory for consistent testing.

**Configuration:**
```yaml
# test_config.yml
dataset: "test_data"           # Use datasets/test_data/input/ files
sync_utils_input: true         # Sync dataset files to target
```

**Benefits:**
- Version-controlled test data
- Consistent test inputs across environments
- Easy scenario switching
- Shareable test configurations
- No need to manually manage input files

**Usage:**
```bash
# Run collect scenario with test_data dataset
./run_validation.sh collect test

# Run install_os scenario with test_data dataset
./run_validation.sh install_os test
```

**Dataset Structure:**
```
test/utils/datasets/
└── test_data/
    ├── README.md           # Dataset documentation
    └── input/
        ├── collect_pxe.yml         # Sample collect configuration
        └── install_os_config.yml   # Sample install_os configuration
```

**When to use Dataset mode:**
- CI/CD pipelines
- Automated regression testing
- Testing with consistent, version-controlled inputs
- Sharing test configurations across teams
- Quick scenario switching

#### Option 2: Without Dataset (Using Runtime Files)

In this mode, tests use the actual input files from the target system's runtime directory. This is useful for testing with production-like configurations.

**Configuration:**
```yaml
# test_config.yml
dataset: ""                  # Empty = use runtime files
sync_utils_input: false      # Don't sync, use existing files
```

**Benefits:**
- Tests actual runtime configuration
- No test data management overhead
- Validates production-like environment
- Useful for debugging with real data

**Usage:**
```bash
# Run tests using runtime input files
./run_validation.sh collect test
```

**Prerequisites:**
Ensure input files exist at the target location before running tests:
- `/opt/omnia/utils/input/project_default/collect_pxe.yml`
- `/opt/omnia/utils/input/project_default/install_os_config.yml`

**When to use without Dataset mode:**
- Testing with actual production configuration
- Debugging with real data
- Validating runtime environment
- When test data management is not needed

**Important Note:**
- Without dataset mode, you must manually ensure input files exist on the target system
- The test framework will NOT sync files when `sync_utils_input: false`
- If files are missing, tests will fail with "Input file not found" errors

---

## Test Reports

### Report Generation

Test reports are automatically generated after each test run:

```
reports/
├── utils_test_report.html    # Human-readable HTML report
└── utils_test_report.json    # Machine-readable JSON report
```

### Viewing Reports

```bash
# View HTML report in browser
firefox reports/utils_test_report.html

# View JSON report
cat reports/utils_test_report.json | jq .
```

### Report Contents

**HTML Report includes:**
- Test execution summary (passed/failed/skipped)
- Individual test results with timestamps
- Error messages and stack traces
- Test duration and performance metrics

**JSON Report includes:**
- Structured test results
- Test case metadata
- Execution timestamps
- Error details

### Sample Report Output

```
=====================================================================================
  TEST EXECUTION SUMMARY
=====================================================================================
  TC ID        Test Name                                Status     Duration
  ------------ ---------------------------------------- ---------- --------
  TC_CL_001    test_deploy_collect_setup                PASSED                38.20s
  TC_CL_002    test_deploy_collect_prepare              PASSED                38.11s
  TC_CL_010    test_collect_input_file_exists           PASSED                 0.01s
  TC_CL_012    test_collect_functional_groups_valid     PASSED                 0.02s
  TC_CL_021    test_collect_bundle_created              PASSED                 0.04s
  TC_CL_032    test_collect_bundle_log_files_content    PASSED                 0.14s
  ------------ ---------------------------------------- ---------- --------
  16 passed, 0 failed, 0 skipped / 16 total (151.81s)
=====================================================================================
```

---

## Test Cases

### Collect Scenario (TC_CL_*)

| ID | Test Name | Description | Order |
|----|-----------|-------------|-------|
| TC_CL_030 | test_collect_env_vars_loaded | Verify OMNIA_DATA_PATH loaded | 0 |
| TC_CL_031 | test_collect_project_name_loaded | Verify OMNIA_PROJECT_NAME loaded | 1 |
| TC_CL_010 | test_collect_input_file_exists | Verify collect_pxe.yml exists | 2 |
| TC_CL_011 | test_collect_input_file_valid | Verify valid YAML structure | 3 |
| TC_CL_012 | test_collect_functional_groups_valid | Verify valid functional groups | 4 |
| TC_CL_001 | test_deploy_collect_setup | Deploy with setup tag | 5 |
| TC_CL_002 | test_deploy_collect_prepare | Deploy with prepare tag | 6 |
| TC_CL_003 | test_deploy_collect_bundle | Deploy with bundle tag | 7 |
| TC_CL_004 | test_deploy_collect_full | Full deployment | 8 |
| TC_CL_020 | test_collect_output_dir_exists | Output directory exists | 9 |
| TC_CL_021 | test_collect_bundle_created | Log bundle created | 10 |
| TC_CL_022 | test_collect_metadata_exists | Metadata file exists | 11 |
| TC_CL_023 | test_collect_metadata_valid | Metadata valid JSON | 12 |
| TC_CL_024 | test_collect_metadata_sha256 | SHA256 in metadata | 13 |
| TC_CL_025 | test_collect_bundle_contents | Bundle has expected dirs | 14 |
| TC_CL_032 | test_collect_bundle_log_files_content | Log files have content | 15 |

### Test Execution Flow

```
Environment Variables (0-1)
    ↓
Input Validation (2-4)
    ↓
Playbook Deployment (5-8)
    ↓
Output Verification (9-15)
```

**Key Features:**
- **Input validation runs FIRST** - Tests fail fast if input is invalid
- **Playbook tests validate input** - Won't run playbook with invalid input
- **Timestamp verification** - Ensures tests check current execution artifacts
- **Empty bundle detection** - Fails if no log files collected

---

## Troubleshooting

### Common Issues

#### 1. Virtual Environment Not Found

**Error:**
```
[ERROR] Virtual environment not found. Run ./setup_env.sh first.
```

**Solution:**
```bash
./setup_env.sh
```

#### 2. Input File Missing

**Error:**
```
TC_CL_010    test_collect_input_file_exists           FAILED
AssertionError: Input file not found: /opt/omnia/utils/input/project_default/collect_pxe.yml
```

**Solution:**
```bash
# Option 1: Use dataset mode
vi test_config.yml
# Set: dataset: "test_data"
# Set: sync_utils_input: true

# Option 2: Manually create file
mkdir -p /opt/omnia/utils/input/project_default/
cp datasets/test_data/input/collect_pxe.yml /opt/omnia/utils/input/project_default/
```

#### 3. Invalid Functional Groups

**Error:**
```
TC_CL_012    test_collect_functional_groups_valid     FAILED
Invalid functional group found: ['invalid_group_name']
```

**Solution:**
Edit `collect_pxe.yml` and use only valid functional groups:
- `service_kube_control_plane_x86_64`
- `service_kube_node_x86_64`
- `slurm_control_node_x86_64`
- `slurm_node_x86_64`
- `slurm_node_aarch64`
- `login_node_x86_64`
- `login_compiler_node_aarch64`

#### 4. Playbook Fails with Invalid Input

**Error:**
```
TC_CL_001    test_deploy_collect_setup                FAILED
Cannot run playbook - input validation failed
```

**Solution:**
This is correct behavior! The test automation now validates input BEFORE running playbooks to save time. Fix the input file validation errors first.

#### 5. Empty Log Bundles

**Error:**
```
TC_CL_032    test_collect_bundle_log_files_content    FAILED
Log bundle is empty - no log files were collected
```

**Cause:**
- No nodes configured in `collect_pxe.yml` (all IPs commented out)
- Nodes are unreachable

**Solution:**
```bash
# Add valid node IPs to collect_pxe.yml
vi datasets/test_data/input/collect_pxe.yml
```

```yaml
slurm_control_node_x86_64:
  - 182.10.0.50  # Uncomment and add valid IP
```

#### 6. Environment Variables Not Set

**Error:**
```
TC_CL_030    test_collect_env_vars_loaded             FAILED
Environment variable 'OMNIA_DATA_PATH' is not set
```

**Solution:**
The test runner automatically sets these. If still failing, manually export:
```bash
export OMNIA_DATA_PATH="/opt/omnia"
export OMNIA_PROJECT_NAME="project_default"
./run_validation.sh collect test
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Run with pytest verbose mode
source .venv/bin/activate
pytest fvt/collect/test_collect.py -v -s

# Show full error traces
pytest fvt/collect/test_collect.py -v --tb=long
```

### Logs and Artifacts

Check test artifacts:

```bash
# View test reports
cat reports/utils_test_report.json | jq .

# Check playbook output
ls -la /opt/omnia/utils/output/project_default/collect/

# View log bundles
tar -tzf /opt/omnia/utils/output/project_default/collect/omnia_logs_*/omnia_logs_*.tar.gz
```

---

## Dependencies

- Python 3.12+
- pytest 9.0+
- pytest-testinfra 10.0+
- pytest-order 1.0+
- ansible-core 2.15+
- omnia-auto plugin (from test/plugins/)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review test reports in `reports/`
3. Check GitHub issues: https://github.com/dell/omnia/issues
4. Contact: Omnia development team

---

## Version

- **Test Automation Version:** 1.0
- **Last Updated:** 2026-09-08
- **Compatible with:** Omnia 2.0+
