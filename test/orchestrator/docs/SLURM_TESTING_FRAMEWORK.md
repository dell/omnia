# SLURM Testing Framework

## Overview

The SLURM testing framework provides comprehensive testing capabilities for SLURM clusters in the Omnia Orchestrator environment.

## Running SLURM Tests

```bash
# Run all SLURM tests
./run_validation.sh fvt_orchestrator slurm verify --marker sanity

# Run specific SLURM test
./run_validation.sh fvt_orchestrator slurm test --marker slurm

# Run with verbose output
./run_validation.sh fvt_orchestrator slurm verify --marker slurm --verbose
```

## Test Categories

### Sanity Tests
- SLURM service health checks (slurmctld, slurmd, slurmdbd, munge)
- Directory and file verification
- Node registration and partition checks

### Functional Tests
- Job submission and execution
- Node state verification
- SSH connectivity between node types

### Hardware Tests (Optional)
- GPU availability and job execution
- InfiniBand verification
- MPI job execution

## Configuration Requirements

### test_config.yml

```yaml
# PXE mapping configuration (for node discovery)
pxe_mapping_path: "/opt/omnia/orchestrator/input/project_default/pxe_mapping_file.csv"

# LDAP credentials (for authentication tests - optional)
ldap_credentials:
  username: "ldapuser"
  password: "encrypted_password_here"
```

### PXE Mapping Format

```csv
hostname,admin_ip,bmc_ip,mac_address,functional_group,ip_address
node1,10.0.0.1,10.0.1.1,00:11:22:33:44:55,slurm_control,10.0.0.1
node2,10.0.0.2,10.0.1.2,00:11:22:33:44:56,slurm,10.0.0.2
```

## Test Markers

- `sanity`: Quick sanity tests
- `slurm`: All SLURM-related tests
- `functional`: Functional verification tests
- `deploy`: Playbook deployment tests

## Troubleshooting

### SLURM Service Not Running
- Check if SLURM is deployed: `./run_validation.sh fvt_orchestrator provision test`
- Verify service status: `systemctl status slurmctld slurmd`

### Node Discovery Issues
- Ensure PXE mapping file exists at configured path
- Verify CSV format matches expected structure
- Check functional_group column contains valid SLURM node types

### Job Execution Failures
- Verify all nodes are in idle state: `sinfo`
- Check SSH connectivity between node types
- Ensure munge authentication is working

## Test Case Registry

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete list of SLURM test cases.
