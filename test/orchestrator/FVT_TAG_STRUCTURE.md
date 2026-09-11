# Orchestrator FVT Tag Structure

## Overview

The orchestrator test automation framework is aligned with `src/orchestrator/playbooks/` structure. Each FVT tag corresponds to a playbook phase in the orchestrator lifecycle.

## FVT Tag Mapping

| FVT Tag | Playbook Directory | Purpose | Test Suites |
|---------|-------------------|---------|-------------|
| `precheck` | `playbooks/precheck/` | Pre-deployment connectivity checks | - |
| `validate` | `playbooks/validate/` | Input file validation (OpenCHAMI, OpenLDAP, provisioning) | - |
| `prepare` | `playbooks/prepare/` | Preparation tasks (OpenCHAMI setup) | openchami |
| `deploy` | `playbooks/deploy/` | Deployment phase | - |
| `provision` | `playbooks/provision/` | Node provisioning (K8s, Slurm) | kubernetes, slurm |
| `pxeboot` | `playbooks/pxeboot/` | PXE boot configuration | - |
| `check` | *(post-deployment)* | Post-deployment verification (K8s, Slurm cluster health) | kubernetes, slurm, status |
| `cleanup` | `playbooks/cleanup/` | Cleanup and teardown | status |

## Execution Order

Tests are automatically ordered by lifecycle phase (defined in `conftest.py`):

1. **precheck** (order: 0) - Verify connectivity before deployment
2. **validate** (order: 1) - Validate input configuration files
3. **prepare** (order: 2) - Prepare infrastructure components
4. **deploy** (order: 3) - Deploy orchestrator
5. **provision** (order: 4) - Provision K8s/Slurm nodes
6. **pxeboot** (order: 5) - Configure PXE boot
7. **check** (order: 6) - Verify deployed infrastructure
8. **cleanup** (order: 7) - Clean up resources

## Key Distinction: `validate` vs `check`

### `validate` Tag
- **Purpose**: Validates input configuration files (pre-deployment)
- **Aligns with**: `src/orchestrator/playbooks/validate/`
- **Tests**: 
  - DCGM configuration validation
  - Input file schema validation
  - Configuration consistency checks
- **Example**: `./run_validation.sh fvt_orchestrator validate verify`

### `check` Tag
- **Purpose**: Verifies deployed infrastructure (post-deployment)
- **Tests**:
  - Kubernetes cluster health (48 tests)
  - Slurm cluster health (41 tests)
  - Service status checks
- **Suites**: kubernetes, slurm, status
- **Example**: `./run_validation.sh fvt_orchestrator check verify --suite kubernetes`

## Usage Examples

### 1. Pre-Deployment Checks
```bash
# Check connectivity
./run_validation.sh fvt_orchestrator precheck verify

# Validate input files
./run_validation.sh fvt_orchestrator validate verify
```

### 2. Deployment
```bash
# Prepare infrastructure
./run_validation.sh fvt_orchestrator prepare test --suite openchami

# Provision Kubernetes nodes
./run_validation.sh fvt_orchestrator provision test --suite kubernetes

# Provision Slurm nodes
./run_validation.sh fvt_orchestrator provision test --suite slurm
```

### 3. Post-Deployment Verification
```bash
# Verify Kubernetes cluster
./run_validation.sh fvt_orchestrator check verify --suite kubernetes

# Verify Slurm cluster
./run_validation.sh fvt_orchestrator check verify --suite slurm

# Verify all (K8s + Slurm)
./run_validation.sh fvt_orchestrator check verify
```

### 4. Cleanup
```bash
# Run cleanup
./run_validation.sh fvt_orchestrator cleanup test
```

## Directory Structure

```
test/orchestrator/fvt/
├── precheck/                    # Pre-deployment connectivity
│   ├── test_connectivity.py
│   └── test_playbook.py
├── validate/                    # Input file validation
│   ├── test_dcgm_config.py
│   └── test_playbook.py
├── prepare/                     # Preparation tasks
│   └── openchami/
│       ├── test_openchami.py
│       └── test_openchami_config.py
├── provision/                   # Node provisioning
│   ├── kubernetes/
│   │   └── test_k8s_provision.py
│   └── slurm/
│       └── test_slurm_provision.py
├── pxeboot/                     # PXE boot configuration
│   └── test_pxeboot.py
├── check/                       # Post-deployment verification
│   ├── kubernetes/              # 11 test files, 48 tests
│   │   ├── test_k8s_config.py
│   │   ├── test_k8s_etcd.py
│   │   ├── test_k8s_firewall.py
│   │   ├── test_k8s_ha.py
│   │   ├── test_k8s_network.py
│   │   ├── test_k8s_nodes.py
│   │   ├── test_k8s_pods.py
│   │   ├── test_k8s_services.py
│   │   ├── test_k8s_ssh.py
│   │   ├── test_k8s_status.py
│   │   └── test_k8s_storage.py
│   ├── slurm/                   # 5 test files, 41 tests
│   │   ├── test_slurm_custom_conf.py
│   │   ├── test_slurm_infrastructure.py
│   │   ├── test_slurm_nodes.py
│   │   ├── test_slurm_ssh.py
│   │   └── test_slurm_status.py
│   └── status/
│       └── test_status.py
└── cleanup/                     # Cleanup and teardown
    └── status/
        └── test_status.py
```

## Test Counts

| Tag | Test Files | Test Cases | Notes |
|-----|-----------|------------|-------|
| precheck | 2 | 3 | Connectivity checks |
| validate | 2 | 3 | Input validation |
| prepare | 3 | ~10 | OpenCHAMI setup |
| provision | 3 | ~15 | K8s + Slurm provisioning |
| pxeboot | 1 | ~5 | PXE boot config |
| **check** | **17** | **89** | **K8s (48) + Slurm (41)** |
| cleanup | 2 | ~5 | Cleanup verification |

## Commands

All tags support three commands:

- **`verify`**: Run tests only (no playbook execution)
- **`exec`**: Run playbook only (no tests)
- **`test`**: Run playbook + tests (full flow)

## Configuration

Test configuration is managed in:
- `conftest.py` - FVT scenario and suite ordering
- `library/vars/domain_vars.py` - Tag and suite definitions
- `test_config.yml` - Test configuration
- `test_creds.yml` - Encrypted credentials

## Alignment with image_build_manager

The orchestrator test automation follows the same pattern as `image_build_manager`:
- FVT scenario ordering in `conftest.py`
- Suite ordering within each scenario
- Lifecycle-based test execution
- Consistent command structure (verify/exec/test)
