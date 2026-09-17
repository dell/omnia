# Orchestrator Functional Verification Tests

This document is the authoritative test-case registry for
`test/orchestrator/fvt/`. It describes the test layout, ID convention,
lifecycle phases, and execution commands.

All test-case metadata is defined in
`library/vars/test_case_vars.py`. Test files must obtain the ID and title from
that registry; IDs and titles must not be hardcoded in test implementations.

## Test-case ID standard

IDs use `ORCH_FVT_<AREA>_<TYPE><SEQ>`:

| Segment | Meaning | Values or example |
|---------|---------|-------------------|
| `ORCH` | Orchestrator domain | Fixed domain code |
| `FVT` | Functional Verification Test level | Fixed test-level code |
| `AREA` | Lifecycle phase or test area | `PRECHECK`, `VALIDATE`, `PREPARE`, `DEPLOY`, `PROVISION`, `EXECUTE`, `PXEBOOT`, `CHECK`, `CLEANUP`, `ROLLBACK`, `NEGATIVE`, or `PLAYBOOK` |
| `TYPE` | Whether the case changes or inspects state | `E` runs a playbook; `V` verifies postconditions |
| `SEQ` | Stable sequence appended to the type | Three digits, starting at `001` |

For example, `ORCH_FVT_PREPARE_E001` runs the prepare playbook and
`ORCH_FVT_PREPARE_V001` verifies its first postcondition. The sequence is a
stable identifier, not a global execution position.

Kubernetes IDs inherited from PR #5220 remain `TC_K8_###`.

IDs are gap-free within each family and unique across test functions.

## Directory layout

```
fvt/
├── precheck/              Connectivity and environment prerequisites
│   ├── test_connectivity.py
│   └── test_playbook.py
├── validate/              Input configuration validation
│   ├── status/
│   ├── test_dcgm_config.py
│   ├── test_playbook.py
│   └── test_validate_openchami.py
├── prepare/               Infrastructure deployment
│   ├── openchami/
│   ├── openldap/
│   └── test_playbook.py
├── deploy/                OpenCHAMI deployment verification
│   ├── test_openchami_deployed.py
│   └── test_playbook.py
├── provision/             Cluster provisioning
│   ├── kubernetes/
│   ├── slurm/
│   ├── test_playbook.py
│   └── test_provision_status.py
├── execute/               Lifecycle execution tests
│   └── test_playbook.py
├── pxeboot/               PXE boot verification
│   ├── test_pxeboot.py
│   ├── test_pxeboot_contracts.py
│   ├── test_pxeboot_verification.py
│   └── test_playbook.py
├── check/                 Post-deployment verification
│   ├── kubernetes/        Kubernetes cluster health
│   ├── slurm/             Slurm cluster health and features
│   │   ├── additional_cloud_init/
│   │   ├── apptainer/
│   │   ├── gpu/
│   │   ├── hpc_benchmarks/
│   │   ├── platform/
│   │   ├── powervault/
│   │   └── vast/
│   ├── status/
│   └── feature_helpers.py
├── cleanup/               Resource cleanup
│   ├── status/
│   └── test_playbook.py
├── rollback/              Deployment rollback
│   └── test_playbook.py
├── negative/              Invalid input and error scenarios
│   ├── test_input_contracts.py
│   └── test_negative.py
└── playbooks/             Source-contract and structure tests
    └── test_orchestrator_yml.py
```

## Effective execution order

The orchestrator lifecycle phases execute in this order:

| Phase | Suite order |
|-------|-------------|
| precheck | `connectivity` |
| validate | `status` → `dcgm_config` → `validate_openchami` |
| prepare | `openchami` → `openldap` |
| deploy | `openchami_deployed` |
| provision | `kubernetes` → `slurm` |
| execute | lifecycle execution |
| pxeboot | `pxeboot_contracts` → `pxeboot_verification` |
| check | `kubernetes` → `slurm` → `status` |

The `check/slurm/` tree includes feature-specific verification suites:
additional cloud-init, Apptainer, GPU, HPC benchmarks, platform artifacts,
VAST, and PowerVault. Feature checks verify the state produced by the
`provision`/`execute` lifecycle.

## Precheck test cases

These cases confirm that the execution OIM is reachable and that its installed
Omnia environment matches the host.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_PRECHECK_E001 | `test_deploy_precheck` | Runs `orchestrator.yml --tags precheck`. | Playbook exits successfully. |
| ORCH_FVT_PRECHECK_V001 | `test_target_connectivity` | Connects to the configured test target. | Target connection succeeds. |

## Validate test cases

These cases validate the effective runtime inputs without deploying.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_VALIDATE_E001 | `test_deploy_validate` | Runs `orchestrator.yml --tags validate`. | Playbook exits successfully. |
| ORCH_FVT_VALIDATE_V001 | `test_validate_openchami` | Validates OpenCHAMI configuration. | Configuration is valid. |

## Prepare test cases

These cases verify the infrastructure created by the `prepare` flow.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_PREPARE_E001 | `test_deploy_prepare` | Runs `orchestrator.yml --tags prepare`. | Playbook exits successfully. |
| ORCH_FVT_PREPARE_V001 | `test_openchami_services` | Verifies OpenCHAMI services are running. | All services report active. |
| ORCH_FVT_PREPARE_V002 | `test_openldap_deployed` | Verifies OpenLDAP deployment. | OpenLDAP service is running. |

## Deploy test cases

These cases verify the OpenCHAMI deployment state.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_DEPLOY_E001 | `test_deploy_orchestrator` | Runs `orchestrator.yml --tags deploy`. | Playbook exits successfully. |
| ORCH_FVT_DEPLOY_V001 | `test_openchami_deployed` | Verifies OpenCHAMI is fully deployed. | All deployment checks pass. |

## Provision test cases

These cases verify cluster provisioning for both Slurm and Kubernetes.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_PROVISION_E001 | `test_deploy_provision` | Runs `orchestrator.yml --tags provision`. | Playbook exits successfully. |
| ORCH_FVT_PROVISION_V001 | `test_provision_status` | Verifies provisioning status report. | All nodes report provisioned. |

## PXE Boot test cases

These cases verify PXE boot configuration and contracts.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_PXEBOOT_E001 | `test_deploy_pxeboot` | Runs PXE boot playbook. | Playbook exits successfully. |
| ORCH_FVT_PXEBOOT_V001 | `test_pxeboot_contracts` | Verifies PXE boot output contracts. | All contracts are satisfied. |
| ORCH_FVT_PXEBOOT_V002 | `test_pxeboot_verification` | Verifies PXE boot node registration. | Nodes are registered correctly. |

## Check test cases — Kubernetes

Post-deployment verification for Kubernetes clusters.

| TC ID | Test | Suite | Validation | Pass criteria |
|-------|------|-------|------------|---------------|
| TC_K8_001 | `test_k8s_config` | kubernetes | Verifies K8s cluster configuration. | Configuration matches expected state. |
| TC_K8_002 | `test_k8s_nodes` | kubernetes | Verifies K8s node status. | All nodes are Ready. |
| TC_K8_003 | `test_k8s_pods` | kubernetes | Verifies K8s pod health. | All pods are Running/Completed. |
| TC_K8_004 | `test_k8s_services` | kubernetes | Verifies K8s service endpoints. | All services have endpoints. |
| TC_K8_005 | `test_k8s_network` | kubernetes | Verifies K8s network configuration. | Network policies are applied. |
| TC_K8_006 | `test_k8s_storage` | kubernetes | Verifies K8s storage classes. | Storage classes are available. |
| TC_K8_007 | `test_k8s_etcd` | kubernetes | Verifies etcd cluster health. | etcd is healthy. |
| TC_K8_008 | `test_k8s_ha` | kubernetes | Verifies K8s HA configuration. | HA is configured correctly. |
| TC_K8_009 | `test_k8s_ssh` | kubernetes | Verifies SSH access to K8s nodes. | SSH access works. |
| TC_K8_010 | `test_k8s_firewall` | kubernetes | Verifies K8s firewall rules. | Firewall rules are correct. |
| TC_K8_011 | `test_k8s_status` | kubernetes | Verifies overall K8s status. | Cluster status is healthy. |
| TC_K8_012 | `test_k8s_advanced` | kubernetes | Advanced K8s verification. | Advanced checks pass. |

## Check test cases — Slurm

Post-deployment verification for Slurm clusters and feature-specific suites.

| TC ID | Test | Suite | Validation | Pass criteria |
|-------|------|-------|------------|---------------|
| ORCH_FVT_CHECK_V001 | `test_slurm_status` | slurm | Verifies Slurm cluster status. | Slurm reports healthy. |
| ORCH_FVT_CHECK_V002 | `test_slurm_nodes` | slurm | Verifies Slurm node status. | All nodes are idle or allocated. |
| ORCH_FVT_CHECK_V003 | `test_slurm_ssh` | slurm | Verifies SSH access to Slurm nodes. | SSH access works. |
| ORCH_FVT_CHECK_V004 | `test_slurm_infrastructure` | slurm | Verifies Slurm infrastructure. | Infrastructure checks pass. |
| ORCH_FVT_CHECK_V005 | `test_slurm_custom_conf` | slurm | Verifies custom Slurm configuration. | Custom configs are applied. |

### Slurm feature suites

| TC ID | Test | Suite | Validation | Pass criteria |
|-------|------|-------|------------|---------------|
| ORCH_FVT_CHECK_V010 | `test_additional_cloud_init` | slurm/additional_cloud_init | Verifies additional cloud-init templates. | Templates are applied correctly. |
| ORCH_FVT_CHECK_V020 | `test_apptainer` | slurm/apptainer | Verifies Apptainer container runtime. | Apptainer is configured and functional. |
| ORCH_FVT_CHECK_V030 | `test_slurm_gpu` | slurm/gpu | Verifies GPU configuration in Slurm. | GPU resources are detected and schedulable. |
| ORCH_FVT_CHECK_V040 | `test_hpc_benchmarks` | slurm/hpc_benchmarks | Verifies HPC benchmark availability. | Benchmarks are installed and runnable. |
| ORCH_FVT_CHECK_V050 | `test_network_functionality` | slurm/platform | Verifies network functionality. | Network is configured correctly. |
| ORCH_FVT_CHECK_V051 | `test_provisioning_artifacts` | slurm/platform | Verifies provisioning artifacts. | Artifacts are present and valid. |
| ORCH_FVT_CHECK_V060 | `test_vast` | slurm/vast | Verifies VAST storage integration. | VAST mounts are accessible. |
| ORCH_FVT_CHECK_V070 | `test_powervault` | slurm/powervault | Verifies PowerVault storage integration. | PowerVault is accessible. |

## Cleanup test cases

These cases verify the state after the cleanup flow.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_CLEANUP_E001 | `test_deploy_cleanup` | Runs `orchestrator.yml --tags cleanup`. | Cleanup playbook exits successfully. |
| ORCH_FVT_CLEANUP_V001 | `test_cleanup_status` | Verifies cleanup status. | All resources are removed. |

## Rollback test cases

These cases verify the state after the rollback flow.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_ROLLBACK_E001 | `test_deploy_rollback` | Runs rollback playbook. | Rollback playbook exits successfully. |

## Negative test cases

These cases verify error handling for invalid inputs and configurations.

| TC ID | Test | Validation | Pass criteria |
|-------|------|------------|---------------|
| ORCH_FVT_NEGATIVE_V001 | `test_input_contracts` | Feeds invalid input configurations. | Playbook fails with actionable error messages. |
| ORCH_FVT_NEGATIVE_V002 | `test_negative` | Tests error scenarios. | Errors are handled gracefully. |

## Registry summary

| Phase | Area | Total | Notes |
|-------|------|-------|-------|
| Precheck | `precheck/` | 2+ | Execution-host prerequisites. |
| Validate | `validate/` | 3+ | Input and OpenCHAMI validation. |
| Prepare | `prepare/` | 3+ | Infrastructure deployment. |
| Deploy | `deploy/` | 2+ | OpenCHAMI deployment verification. |
| Provision | `provision/` | 2+ | Cluster provisioning (Slurm, K8s). |
| Execute | `execute/` | 1+ | Lifecycle execution. |
| PXE Boot | `pxeboot/` | 3+ | PXE boot and node registration. |
| Check — Kubernetes | `check/kubernetes/` | 12+ | Kubernetes cluster verification. |
| Check — Slurm | `check/slurm/` | 5+ | Slurm cluster verification. |
| Check — Features | `check/slurm/*/` | 8+ | Feature-specific verification. |
| Cleanup | `cleanup/` | 2+ | Resource cleanup verification. |
| Rollback | `rollback/` | 1+ | Rollback verification. |
| Negative | `negative/` | 2+ | Error and invalid input handling. |
| Playbooks | `playbooks/` | 1+ | Source-contract tests. |

At this revision, pytest collects 273 FVT cases. Parameterized tests account
for the difference between function count and collected-case count.

## Live inventory

Use collection rather than maintaining a second hand-written test list:

```bash
cd test/orchestrator
./run_validation.sh fvt_orchestrator list
python3 -m pytest fvt --collect-only -q
```

## Execution commands

Run from `test/orchestrator/`:

```bash
# Deploy and verify one lifecycle phase
./run_validation.sh fvt_orchestrator precheck test
./run_validation.sh fvt_orchestrator validate test
./run_validation.sh fvt_orchestrator prepare test
./run_validation.sh fvt_orchestrator deploy test
./run_validation.sh fvt_orchestrator provision exec --suite slurm
./run_validation.sh fvt_orchestrator provision exec --suite kubernetes

# Verify the existing deployment without running a playbook
./run_validation.sh fvt_orchestrator check verify --suite slurm
./run_validation.sh fvt_orchestrator check verify --suite kubernetes

# Focused feature verification
./run_validation.sh fvt_orchestrator check verify --suite slurm/apptainer
./run_validation.sh fvt_orchestrator check verify --suite slurm/gpu
./run_validation.sh fvt_orchestrator check verify --suite slurm/vast

# Full verification (excludes deploy and cleanup)
./run_validation.sh fvt_orchestrator verify

# Destructive flows; require explicit opt-in
./run_validation.sh fvt_orchestrator cleanup test --marker destructive
./run_validation.sh fvt_orchestrator rollback test --marker destructive
./run_validation.sh fvt_orchestrator pxeboot test --marker destructive
```

`verify` never executes a playbook. The untagged form excludes cleanup,
rollback, and deploy cases. Destructive scenarios run only when explicitly
selected with `--marker destructive`.
