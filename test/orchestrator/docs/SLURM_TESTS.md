# SLURM Tests

## Overview

This test suite provides comprehensive testing for the SLURM workload manager within the Omnia Orchestrator domain.

## Running SLURM Tests

```bash
# Run all SLURM tests
./run_validation.sh fvt_orchestrator slurm verify --marker sanity

# Run SLURM provision test
./run_validation.sh fvt_orchestrator provision test --marker slurm

# Run SLURM validation tests
./run_validation.sh fvt_orchestrator validate verify --marker slurm
```

## Test Categories

### Provision Tests
- Deploy SLURM cluster
- Verify playbook execution

### Validation Tests
- Service status checks (slurmctld, slurmd, slurmdbd, munge)
- Directory and file verification
- Node registration and partition checks
- Node state verification

## Test Cases

See [fvt/TEST_CASES.md](fvt/TEST_CASES.md) for the complete list of SLURM test cases with IDs and descriptions.

## Prerequisites

- SLURM must be deployed before running validation tests
- PXE mapping file must be configured for node discovery tests
- SSH connectivity between nodes for job execution tests

## Troubleshooting

### SLURM Service Not Running
- Deploy SLURM first: `./run_validation.sh fvt_orchestrator provision test --marker slurm`
- Check service status: `systemctl status slurmctld slurmd`

### Node Registration Issues
- Verify PXE mapping file exists
- Check node functional groups in PXE mapping
- Ensure nodes are reachable via SSH

### Job Execution Failures
- Verify all nodes are in idle state: `sinfo`
- Check munge authentication
- Verify SSH connectivity between node types
