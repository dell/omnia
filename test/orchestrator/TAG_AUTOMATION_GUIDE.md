# Orchestrator Test Automation - Complete Tag Guide

## Overview

This document provides a comprehensive guide to the orchestrator test automation framework, including all available tags, commands, and their behavior.

## Commands

The test automation framework supports three commands:

### 1. `verify` - Run Tests Only (No Playbook)
Executes pytest with marker `-m 'not deploy'` to run verification tests without executing Ansible playbooks.

```bash
./run_validation.sh fvt_orchestrator <tag> verify [options]
```

**What it does**:
- Runs only test functions that verify existing infrastructure
- Skips any test marked with `@pytest.mark.deploy`
- Does NOT execute Ansible playbooks
- Ideal for validating an already-deployed environment

**Example**:
```bash
# Verify Kubernetes cluster health
./run_validation.sh fvt_orchestrator validate verify --suite kubernetes
```

### 2. `exec` - Run Playbook Only (No Tests)
Executes pytest with marker `-m deploy` to run only deployment tests that execute Ansible playbooks.

```bash
./run_validation.sh fvt_orchestrator <tag> exec [options]
```

**What it does**:
- Runs only test functions marked with `@pytest.mark.deploy`
- Executes Ansible playbooks through pytest fixtures
- Skips verification tests
- Ideal for deployment/provisioning without validation

**Example**:
```bash
# Execute Kubernetes provisioning playbook
./run_validation.sh fvt_orchestrator provision exec --suite kubernetes
```

### 3. `test` - Run Playbook + Tests (Full Flow)
Executes `exec` followed by `verify` in sequence.

```bash
./run_validation.sh fvt_orchestrator <tag> test [options]
```

**What it does**:
1. **Step 1/2**: Runs `exec` (playbook execution with `-m deploy`)
2. **Step 2/2**: Runs `verify` (verification tests with `-m 'not deploy'`)
3. Combines results and provides unified summary
4. Skips Step 2 if Step 1 fails

**Example**:
```bash
# Deploy and validate Kubernetes
./run_validation.sh fvt_orchestrator provision test --suite kubernetes
```

---

## Available FVT Tags

All tags map to directories under `fvt/` and align with the orchestrator playbook lifecycle.

### 1. `connectivity` - Precheck Connectivity
**Purpose**: Verify SSH and network connectivity before deployment

**Test Files**:
- `fvt/connectivity/test_connectivity.py` - SSH connectivity tests
- `fvt/connectivity/test_playbook.py` - Playbook execution tests

**Usage**:
```bash
# Verify connectivity only
./run_validation.sh fvt_orchestrator connectivity verify

# Run connectivity playbook + verify
./run_validation.sh fvt_orchestrator connectivity test
```

**Test Cases**: 3 tests
- TC_PC_001: Target SSH Connectivity
- TC_PC_002: Orchestrator Directories
- TC_PC_003: Input Directory Structure

---

### 2. `pxeboot` - PXE Boot Configuration
**Purpose**: Validate PXE boot configuration and node discovery

**Test Files**:
- `fvt/pxeboot/test_pxeboot.py` - PXE boot validation

**Usage**:
```bash
# Verify PXE boot configuration
./run_validation.sh fvt_orchestrator pxeboot verify

# Execute PXE boot setup + verify
./run_validation.sh fvt_orchestrator pxeboot test
```

---

### 3. `provision` - Node Provisioning
**Purpose**: Provision Kubernetes and Slurm nodes

**Suites**:
- `kubernetes` - Kubernetes node provisioning
- `slurm` - Slurm node provisioning

**Test Files**:
- `fvt/provision/kubernetes/test_k8s_provision.py`
- `fvt/provision/slurm/test_slurm_provision.py`
- `fvt/provision/test_playbook.py`

**Usage**:
```bash
# Verify Kubernetes provisioning
./run_validation.sh fvt_orchestrator provision verify --suite kubernetes

# Execute Kubernetes provisioning playbook
./run_validation.sh fvt_orchestrator provision exec --suite kubernetes

# Full flow: provision + verify Kubernetes
./run_validation.sh fvt_orchestrator provision test --suite kubernetes

# Provision both K8s and Slurm
./run_validation.sh fvt_orchestrator provision test
```

---

### 4. `validate` - Post-Deployment Validation
**Purpose**: Comprehensive validation of deployed infrastructure

**Suites**:
- `kubernetes` - Kubernetes cluster validation (19 test files)
- `slurm` - Slurm cluster validation
- `status` - Overall status checks

**Test Files** (Kubernetes):
- `test_k8s_config.py` - Configuration validation
- `test_k8s_etcd.py` - etcd cluster health
- `test_k8s_firewall.py` - Firewall configuration
- `test_k8s_ha.py` - High availability
- `test_k8s_network.py` - Network configuration
- `test_k8s_nodes.py` - Node status
- `test_k8s_pods.py` - Pod health
- `test_k8s_services.py` - Service validation
- `test_k8s_ssh.py` - SSH connectivity
- `test_k8s_status.py` - Overall status
- `test_k8s_storage.py` - Storage validation

**Usage**:
```bash
# Verify all (K8s + Slurm)
./run_validation.sh fvt_orchestrator validate verify

# Verify only Kubernetes
./run_validation.sh fvt_orchestrator validate verify --suite kubernetes

# Verify only Slurm
./run_validation.sh fvt_orchestrator validate verify --suite slurm

# Run validation playbook + verify
./run_validation.sh fvt_orchestrator validate test --suite kubernetes
```

**Test Count**: 89 total tests
- 48 Kubernetes tests
- 41 Slurm tests (skipped if not configured)

---

### 5. `prepare` - Preparation Tasks
**Purpose**: Prepare infrastructure components (OpenCHAMI, etc.)

**Suites**:
- `openchami` - OpenCHAMI configuration

**Test Files**:
- `fvt/prepare/openchami/test_openchami.py`
- `fvt/prepare/openchami/test_openchami_config.py`
- `fvt/prepare/test_playbook.py`

**Usage**:
```bash
# Verify OpenCHAMI preparation
./run_validation.sh fvt_orchestrator prepare verify --suite openchami

# Execute preparation + verify
./run_validation.sh fvt_orchestrator prepare test
```

---

### 6. `cleanup` - Cleanup and Teardown
**Purpose**: Clean up deployed resources

**Suites**:
- `status` - Status checks during cleanup

**Test Files**:
- `fvt/cleanup/status/test_status.py`
- `fvt/cleanup/test_playbook.py`

**Usage**:
```bash
# Verify cleanup status
./run_validation.sh fvt_orchestrator cleanup verify

# Execute cleanup + verify
./run_validation.sh fvt_orchestrator cleanup test
```

---

### 7. `rollback` - Rollback Operations
**Purpose**: Rollback deployed configurations

**Test Files**:
- `fvt/rollback/test_playbook.py`

**Usage**:
```bash
# Verify rollback
./run_validation.sh fvt_orchestrator rollback verify

# Execute rollback + verify
./run_validation.sh fvt_orchestrator rollback test
```

---

### 8. `modules` - Module-Level Tests
**Purpose**: Test individual Ansible modules

**Test Files**:
- `fvt/modules/test_validate_orchestrator_config.py`

**Usage**:
```bash
# Verify module functionality
./run_validation.sh fvt_orchestrator modules verify
```

---

### 9. `playbooks` - Playbook Structure Tests
**Purpose**: Validate playbook structure and syntax

**Test Files**:
- `fvt/playbooks/test_orchestrator_yml.py`

**Usage**:
```bash
# Verify playbook structure
./run_validation.sh fvt_orchestrator playbooks verify
```

---

### 10. `roles` - Role-Level Tests
**Purpose**: Test individual Ansible roles

**Test Files**:
- `fvt/roles/test_orchestrator_setup.py`

**Usage**:
```bash
# Verify role functionality
./run_validation.sh fvt_orchestrator roles verify
```

---

### 11. `network` - Network Functionality Tests
**Purpose**: Test network functionality and configuration

**Test Files**:
- `fvt/network/test_network_functionality.py`

**Usage**:
```bash
# Verify network functionality
./run_validation.sh fvt_orchestrator network verify
```

---

### 12. `negative` - Negative Test Cases
**Purpose**: Test error handling and edge cases

**Test Files**:
- `fvt/negative/test_negative.py`

**Usage**:
```bash
# Run negative tests
./run_validation.sh fvt_orchestrator negative verify
```

---

## Additional Options

### Filter by Marker
```bash
# Run only sanity tests
./run_validation.sh fvt_orchestrator validate verify --marker sanity

# Run only functional tests
./run_validation.sh fvt_orchestrator validate verify --marker functional

# Run only Kubernetes tests
./run_validation.sh fvt_orchestrator validate verify --marker kubernetes
```

### Verbose Output
```bash
# Increase verbosity
./run_validation.sh fvt_orchestrator validate verify -v

# Full debug output
./run_validation.sh fvt_orchestrator validate verify --debug
```

---

## Complete Workflow Examples

### Example 1: Full Kubernetes Deployment and Validation
```bash
# 1. Verify connectivity
./run_validation.sh fvt_orchestrator connectivity verify

# 2. Provision Kubernetes nodes
./run_validation.sh fvt_orchestrator provision test --suite kubernetes

# 3. Validate Kubernetes cluster
./run_validation.sh fvt_orchestrator validate verify --suite kubernetes
```

### Example 2: Quick Validation of Existing Cluster
```bash
# Verify existing Kubernetes cluster
./run_validation.sh fvt_orchestrator validate verify --suite kubernetes
```

### Example 3: Provision and Validate Both K8s and Slurm
```bash
# Full deployment and validation
./run_validation.sh fvt_orchestrator provision test
./run_validation.sh fvt_orchestrator validate verify
```

---

## Test Markers

Available pytest markers for filtering:

- `@pytest.mark.sanity` - Quick sanity tests
- `@pytest.mark.functional` - Functional verification tests
- `@pytest.mark.deploy` - Deployment/playbook execution tests
- `@pytest.mark.kubernetes` - Kubernetes-specific tests
- `@pytest.mark.slurm` - Slurm-specific tests
- `@pytest.mark.negative` - Negative test cases
- `@pytest.mark.network` - Network functionality tests

---

## Command Behavior Summary

| Command | Marker Filter | Executes Playbook | Runs Verification | Use Case |
|---------|---------------|-------------------|-------------------|----------|
| `verify` | `-m 'not deploy'` | ❌ No | ✅ Yes | Validate existing infrastructure |
| `exec` | `-m deploy` | ✅ Yes | ❌ No | Deploy/provision only |
| `test` | Both | ✅ Yes | ✅ Yes | Full deployment + validation |

---

## Report Locations

All test reports are saved to `/opt/omnia/reports/`:
- JSON: `orchestrator_test_report.json`
- HTML: `orchestrator_test_report.html`

---

## Configuration

Test configuration is located at:
- `test_config.yml` - Non-sensitive settings
- `test_creds.yml` - Encrypted credentials (Ansible Vault)

---

## Troubleshooting

### Issue: Tests not found
**Solution**: Ensure you're in the correct directory and virtual environment is activated:
```bash
cd /root/multidomain/omnia/test/orchestrator
source .venv/bin/activate
./run_validation.sh fvt_orchestrator list
```

### Issue: Playbook not executing with `exec` command
**Solution**: Ensure test functions are marked with `@pytest.mark.deploy`:
```python
@pytest.mark.deploy
def test_deploy_kubernetes(host):
    # Playbook execution logic
    pass
```

### Issue: Verification tests running during `exec`
**Solution**: Ensure verification tests are NOT marked with `@pytest.mark.deploy`

---

## Summary

The orchestrator test automation framework provides comprehensive coverage of the entire deployment lifecycle:

1. **Precheck** (`connectivity`) - Verify prerequisites
2. **PXE Boot** (`pxeboot`) - Configure node discovery
3. **Provision** (`provision`) - Deploy nodes
4. **Validate** (`validate`) - Verify deployment
5. **Prepare** (`prepare`) - Additional setup
6. **Cleanup** (`cleanup`) - Teardown
7. **Rollback** (`rollback`) - Undo changes

All tags support `verify`, `exec`, and `test` commands with consistent behavior across the framework.
