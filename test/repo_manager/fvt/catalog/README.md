# Catalog Test Automation

## Overview
This directory contains comprehensive test automation for the repo_manager catalog operations (generate, add, delete, validate).

## Prerequisites
Before running catalog tests, you must provide the required input files with your catalog configuration.

## Path Configuration

### Current Path Handling
The repo_manager test automation currently uses hardcoded paths:
- **Input directory**: `/opt/omnia/repo_manager/input/project_default/`
- **Catalog output**: `/opt/omnia/catalog/catalog_rhel.json`
- **Log directory**: `/opt/omnia/repo_manager/log/catalog/`

These paths match the existing repo_manager test infrastructure and are consistent with the standard OMNIA_DATA_PATH configuration. If your OMNIA installation uses a different OMNIA_DATA_PATH, you will need to adjust the paths accordingly or ensure your environment matches the standard configuration.

### Environment Variables
The test framework loads environment variables from `/etc/omnia/omnia.env` (via conftest.py), but the current repo_manager test infrastructure uses hardcoded paths rather than dynamic path resolution. This is consistent with the existing repo_manager test patterns.

## Input File Setup Options

### Option 1: Manual Input File Creation (Recommended for Custom Testing)
Create input files manually in the target directory with your specific catalog configuration.

### Option 2: Sync from Source Directory (Development Mode)
Set `sync_repo_manager_input: true` in `test_config.yml` to sync input files from the source tree:

```yaml
# In /root/sujal/omnia/test/repo_manager/test_config.yml
sync_repo_manager_input: true
```

This will sync input files from `/root/sujal/omnia/src/repo_manager/input/` to the target system's input directory.

### Option 3: Dataset-Based Testing (Not Currently Available)
Unlike other test domains (utils, image_build_manager, etc.), repo_manager does not currently have a dataset generator system. Input files must be created manually or synced from source.

## Required Input Files

### 1. Catalog Generate Input File
**File Path:** `/opt/omnia/repo_manager/input/project_default/packages.txt`

**Purpose:** Initial catalog generation with functional layers, groups, and packages.

**Format:**
```
[defaults]
arch=x86_64, os=rhel, os_version=10.0

[group_name | type=group_type, description=group_description]
package_name, package_type, package_name, repo_name
package_name, package_type, package_name, repo_name

[functional_layer_name | type=functional_layer]
"group_name",
"group_name"
```

**Example:**
```
[defaults]
arch=x86_64, os=rhel, os_version=10.0

[baseos_group_10.0 | type=base_os, description=base os packages for rhel cluster nodes, os=rhel, os_version=10.0]
systemd, rpm, systemd, baseos
systemd_udev, rpm, systemd-udev, baseos
wget, rpm, wget, appstream

[slurm_custom_group | description=slurm custom packages]
clustershell, rpm, clustershell, epel
papi, tarball, papi, https://github.com/icl-utk-edu/papi/releases/download/papi-7-2-0-t/papi-7.2.0.tar.gz

[slurm_control_node_rhel_10_0_x86_64 | type=functional_layer]
"baseos_group_10.0",
"slurm_custom_group"
```

### 2. Catalog Add Input File
**File Path:** `/opt/omnia/repo_manager/input/project_default/additions.txt`

**Purpose:** Add new packages/groups to existing catalog.

**Format:** Same as generate input file, but adds to existing catalog.

**Example:**
```
[defaults]
arch=x86_64, os=rhel, os_version=10.0

[networking_group | description=Network utilities]
curl, rpm, curl, baseos
net-tools, rpm, net-tools, baseos

[slurm_control_node_rhel_10_0_x86_64 | type=functional_layer]
"networking_group"
```

### 3. Catalog Delete Input File
**File Path:** `/opt/omnia/repo_manager/input/project_default/removals.txt`

**Purpose:** Remove packages/groups from existing catalog.

**Format:**
```
[group_name]
package_name
package_name
```

**Example:**
```
[baseos_group_10.0]
wget
glibc_langpack_en
```

## Environment Setup

### 1. Install Test Dependencies
```bash
cd /root/sujal/omnia/test/repo_manager
bash setup_env.sh --venv
```

### 2. Configure Test Environment
Edit `test_config.yml` to set your target and sync preferences:

```yaml
# Target OIM server IP. Empty = local machine
oim_server_ip: ""

# Sync repo_manager input files from source tree (development mode)
sync_repo_manager_input: false  # Set to true to sync from src/repo_manager/input/

# Project name for input/output paths
project_name: "project_default"
```

### 3. Create Required Directories
```bash
# These should be created automatically, but ensure they exist:
mkdir -p /opt/omnia/repo_manager/input/project_default
mkdir -p /opt/omnia/catalog
mkdir -p /opt/omnia/repo_manager/log/catalog
```

## Running Tests

### Run All Catalog Tests (Including Negative Tests)
```bash
cd /root/sujal/omnia/test/repo_manager
./run_validation.sh catalog test
```

This will run all catalog operations in order:
1. **catalog_generate** (11 tests)
2. **catalog_add** (8 tests) - if additions.txt exists
3. **catalog_delete** (6 tests) - if removals.txt exists
4. **catalog_validate** (4 tests)
5. **catalog_negative** (7 tests) - validation and error scenarios

### Run Specific Catalog Operation
```bash
# Generate only
./run_validation.sh catalog/generate test

# Add only
./run_validation.sh catalog/add test

# Delete only
./run_validation.sh catalog/delete test

# Validate only
./run_validation.sh catalog/validate test

# Negative tests only
./run_validation.sh catalog/negative test
```

### Run with Marker Filtering
```bash
# Run only sanity tests
./run_validation.sh catalog test --marker sanity

# Run only positive tests
./run_validation.sh catalog test --marker positive

# Run only negative tests
./run_validation.sh catalog test --marker negative
```

## Input File Creation from Source

If you want to use the source directory as a reference and sync to target:

### Step 1: Create Input Files in Source Directory
```bash
# Create catalog input files in source directory
cat > /root/sujal/omnia/src/repo_manager/input/project_default/packages.txt << 'EOF'
[slurm_control_node_rhel_10_0_x86_64]
baseos_group_10.0
  systemd rpm https://access.redhat.com/downloads/content/693 ver=10.0 arch=x86_64
  systemd_udev rpm https://access.redhat.com/downloads/content/693 ver=10.0 arch=x86_64
EOF
```

### Step 2: Enable Sync in Test Config
```yaml
# In test_config.yml
sync_repo_manager_input: true
```

### Step 3: Run Tests
The test framework will automatically sync the input files from source to the target before running tests.

## Sync Configuration Notes

### sync_repo_manager_input Behavior
- **When true**: Input files are synced from `/root/sujal/omnia/src/repo_manager/input/` to the target's input directory
- **When false**: Tests use input files that already exist on the target system
- **Use case**: Set to `true` during development to use source files directly; set to `false` for production testing with pre-staged input files

### Dataset vs Sync
- **Dataset system**: Used by other domains (utils, image_build_manager) to generate test data from templates
- **Sync system**: Used by repo_manager to copy existing input files from source to target
- **Current status**: Repo_manager uses sync system, not dataset generation

## Test Scenarios

### Catalog Generate (11 tests)
- TC_RM_CAT_GEN_000: Deploy catalog_generate playbook
- TC_RM_CAT_GEN_001: Verify catalog input directory exists
- TC_RM_CAT_GEN_002: Verify catalog file exists after generate
- TC_RM_CAT_GEN_003: Verify catalog structure is valid
- TC_RM_CAT_GEN_004: Verify catalog has functional layers
- TC_RM_CAT_GEN_005: Verify catalog has groups
- TC_RM_CAT_GEN_006: Verify catalog has packages
- TC_RM_CAT_GEN_007: Verify catalog has specific group
- TC_RM_CAT_GEN_008: Verify catalog has specific package
- TC_RM_CAT_GEN_009: Verify package type is correct
- TC_RM_CAT_GEN_010: Verify catalog log file exists

### Catalog Add (8 tests)
- TC_RM_CAT_ADD_000: Deploy catalog_add playbook
- TC_RM_CAT_ADD_001: Verify catalog add operation completed successfully
- TC_RM_CAT_ADD_002: Verify catalog structure still valid after add
- TC_RM_CAT_ADD_003: Verify packages from input file were added to catalog
- TC_RM_CAT_ADD_004: Verify groups from input file were created in catalog
- TC_RM_CAT_ADD_005: Verify catalog has functional layers after add
- TC_RM_CAT_ADD_006: Verify catalog has groups after add
- TC_RM_CAT_ADD_007: Verify catalog has packages after add

### Catalog Delete (6 tests)
- TC_RM_CAT_DEL_000: Deploy catalog_delete playbook
- TC_RM_CAT_DEL_001: Verify catalog delete operation completed successfully
- TC_RM_CAT_DEL_002: Verify catalog structure still valid after delete
- TC_RM_CAT_DEL_003: Verify packages from input file were removed from catalog
- TC_RM_CAT_DEL_004: Verify catalog has functional layers after delete
- TC_RM_CAT_DEL_005: Verify catalog has groups after delete

### Catalog Validate (4 tests)
- TC_RM_CAT_VAL_000: Deploy catalog_validate playbook
- TC_RM_CAT_VAL_001: Verify catalog validation completed successfully
- TC_RM_CAT_VAL_002: Verify catalog validation log file exists
- TC_RM_CAT_VAL_003: Verify catalog file still valid after validation

### Catalog Negative (7 tests)
- TC_RM_CAT_NEG_001: Verify catalog_generate fails with missing input file
- TC_RM_CAT_NEG_002: Verify catalog_add fails with missing input file
- TC_RM_CAT_NEG_003: Verify catalog_delete fails with missing input file
- TC_RM_CAT_NEG_004: Verify catalog input directory validation
- TC_RM_CAT_NEG_005: Verify catalog structure validation
- TC_RM_CAT_NEG_006: Verify catalog file existence validation
- TC_RM_CAT_NEG_007: Verify catalog log file validation

## Error Messages

### Missing Input File
If you run tests without providing the required input files, you will see clear error messages:

**Example for catalog_generate:**
```
✘ FAIL: Catalog generate input file not provided
│ Required input file: /opt/omnia/repo_manager/input/project_default/packages.txt
│ To run catalog_generate tests, you must provide this file with your catalog configuration.
│ Example format:
│ [functional_layer_name]
│ group_name
│   package_name package_type url
│   package_name package_type url
```

### Catalog Doesn't Exist
If you run add/delete/validate tests before running generate, you will see:

```
✘ FAIL: Catalog structure invalid or catalog doesn't exist.
│ This test requires catalog_generate to complete successfully first.
│ Ensure the input file is provided and catalog_generate test passes.
```

## Test Dependencies

The catalog tests have a natural dependency order:
1. **catalog_generate** must run first to create the catalog
2. **catalog_add** can only run after catalog_generate
3. **catalog_delete** can only run after catalog_generate (or after add)
4. **catalog_validate** can only run after catalog_generate

The test runner automatically handles this order when you run `./run_validation.sh catalog test`.

## Cleaning Up

To run tests from scratch, clean all catalog artifacts:

```bash
# Remove input files
rm -f /opt/omnia/repo_manager/input/project_default/packages.txt
rm -f /opt/omnia/repo_manager/input/project_default/additions.txt
rm -f /opt/omnia/repo_manager/input/project_default/removals.txt

# Remove generated catalog
rm -f /opt/omnia/catalog/catalog_rhel.json

# Remove log files
rm -f /opt/omnia/repo_manager/log/catalog/catalog_manager.log
```

## Key Features

1. **Generic Design**: Tests work with any user-provided input files
2. **Clear Error Messages**: Detailed error messages guide users on what's missing
3. **Actual Result Verification**: Tests parse input files and verify actual results
4. **Graceful Edge Case Handling**: Tests handle packages already existing or already deleted
5. **Same as Manual Execution**: Tests follow the same workflow as manual playbook execution
6. **No Manual Configuration**: All paths and dependencies are handled automatically
