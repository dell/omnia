# SVT Theme `cluster_lifecycle`

Status: **Phase 1 implemented** (Slurm stream), **Phase 2 implemented** (Kubernetes stream).

## 1. Goal

An end-to-end system verification test of the Omnia cluster lifecycle on one
OIM: deploy, run workloads, remove a node, add it back. Two streams cover the
two schedulers Omnia supports (Slurm and Kubernetes); a stream runs only when
its scheduler is in the active catalog.

## 2. Nine test cases in two streams

| # | Stream | Test case | FVT coverage |
|---|--------|-----------|-------------|
| 1 | Slurm | Deploy the Slurm cluster | orchestrator precheck/prepare/provision/pxeboot + slurm_cluster |
| 2 | Slurm | Run jobs over IPv4, IPv6 and dual-stack | slurm_jobs + ipoib_network |
| 3 | Slurm | Delete a node | slurm_lifecycle (marker node_remove) |
| 4 | Slurm | Add a node | slurm_lifecycle (marker node_add) |
| 5 | K8s | Deploy the Kubernetes cluster | kubernetes_cluster (membership, services, control plane, etcd, storage) |
| 6 | K8s | Start and monitor telemetry in offline mode | telemetry deploy exec + verify (offline / Pulp) |
| 7 | K8s | Delete a node | **Deferred** -- orchestrator does not yet support K8s node removal |
| 8 | K8s | Add a node | **Deferred** -- depends on delete node |
| 9 | K8s | Renew tokens | kubernetes_cluster (marker token_renew) |

## 3. Phased implementation

### Phase 1 -- Slurm stream (implemented)

All four Slurm FVTs exist. The only prerequisite was adding `node_remove` and
`node_add` markers to the existing `test_slurm_lifecycle.py`.

**Stages (4, plus initialization):**

| Stage | Hard/Soft | SVT cases | What it runs |
|-------|-----------|-----------|-------------|
| `deploy_slurm_cluster` | hard | 001-009 | orchestrator precheck, prepare, provision, pxeboot exec + connectivity verify + slurm_cluster suite (membership, services, SSH, configless, config consistency, reconfigure, hardware discovery, custom config) |
| `slurm_jobs` | soft | 010-011 | slurm_jobs suite + ipoib_network suite |
| `slurm_node_remove` | soft | 012 | slurm_lifecycle suite with node_lifecycle+node_remove marker |
| `slurm_node_add` | soft | 013 | slurm_lifecycle suite with node_lifecycle+node_add marker |

### Phase 2 -- Kubernetes stream (implemented)

The cluster is already deployed with K8s nodes. The K8s stream verifies the
cluster, deploys telemetry in offline mode (nodes pull from Pulp, no internet),
and renews bootstrap tokens. Node remove/add are deferred until the orchestrator
src supports `kubectl drain` / `kubectl delete node` during provision.

**Stages (3, plus initialization):**

| Stage | Hard/Soft | SVT cases | What it runs |
|-------|-----------|-----------|-------------|
| `deploy_k8s_cluster` | hard | 014 | kubernetes_cluster suite (membership, services, control plane, system pods, VIP, versions, workload scheduling, etcd, storage) |
| `k8s_telemetry` | soft | 015 | telemetry deploy exec + verify (offline / Pulp) |
| `k8s_token_renew` | soft | 018 | kubernetes_cluster suite with token_renew marker |

## 4. SVT test cases

| ID | Order | Stage | Title | FVT step |
|----|-------|-------|-------|----------|
| SVT_CLUSTER_LIFECYCLE_001 | 3010 | deploy_slurm_cluster | Orchestrator precheck | orchestrator precheck exec |
| SVT_CLUSTER_LIFECYCLE_002 | 3011 | deploy_slurm_cluster | Orchestrator precheck: verification | orchestrator precheck verify |
| SVT_CLUSTER_LIFECYCLE_003 | 3012 | deploy_slurm_cluster | Orchestrator prepare | orchestrator prepare exec |
| SVT_CLUSTER_LIFECYCLE_004 | 3013 | deploy_slurm_cluster | Orchestrator prepare: verification | orchestrator prepare verify |
| SVT_CLUSTER_LIFECYCLE_005 | 3014 | deploy_slurm_cluster | Orchestrator provision | orchestrator provision exec |
| SVT_CLUSTER_LIFECYCLE_006 | 3015 | deploy_slurm_cluster | Orchestrator provision: verification | orchestrator provision verify |
| SVT_CLUSTER_LIFECYCLE_007 | 3016 | deploy_slurm_cluster | Orchestrator PXE boot | orchestrator pxeboot exec |
| SVT_CLUSTER_LIFECYCLE_008 | 3017 | deploy_slurm_cluster | PXE boot: connectivity and cloud-init | orchestrator pxeboot verify --suite connectivity |
| SVT_CLUSTER_LIFECYCLE_009 | 3030 | deploy_slurm_cluster | Slurm cluster membership, services and scheduler | orchestrator pxeboot verify --suite slurm_cluster |
| SVT_CLUSTER_LIFECYCLE_010 | 3040 | slurm_jobs | Slurm job submission (control, login, compiler, concurrent) | orchestrator pxeboot verify --suite slurm_jobs |
| SVT_CLUSTER_LIFECYCLE_011 | 3041 | slurm_jobs | Slurm jobs over IPoIB (IPv4/IPv6/dual-stack traffic path) | orchestrator pxeboot verify --suite ipoib_network |
| SVT_CLUSTER_LIFECYCLE_012 | 3050 | slurm_node_remove | Delete a Slurm compute node | orchestrator pxeboot verify --suite slurm_lifecycle --marker node_lifecycle+node_remove |
| SVT_CLUSTER_LIFECYCLE_013 | 3051 | slurm_node_add | Add a Slurm compute node | orchestrator pxeboot verify --suite slurm_lifecycle --marker node_lifecycle+node_add |
| SVT_CLUSTER_LIFECYCLE_014 | 3060 | deploy_k8s_cluster | Kubernetes cluster health | orchestrator pxeboot verify --suite kubernetes_cluster |
| SVT_CLUSTER_LIFECYCLE_015 | 3070 | k8s_telemetry | Telemetry deploy and verify (offline) | telemetry deploy exec + telemetry deploy verify |
| SVT_CLUSTER_LIFECYCLE_018 | 3090 | k8s_token_renew | Renew Kubernetes bootstrap tokens | orchestrator pxeboot verify --suite kubernetes_cluster --marker token_renew |

## 5. Files

| Action | File | Purpose |
|--------|------|---------|
| Create | `test/system_test/cluster_lifecycle_test_config.yml` | Theme settings (report; the cleanup is the shared block of `user_inputs.yml`) |
| Create | `test/system_test/dataset_generator/profiles/cluster_lifecycle.yml` | Input profile: `omnia.env` + orchestrator inputs |
| Modify | `test/system_test/library/vars/theme_vars.py` | Add `"cluster_lifecycle"` entry to `THEMES` dict with Slurm + K8s stages |
| Modify | `test/system_test/library/vars/test_case_vars.py` | Add `cluster_lifecycle_*` entries to `TEST_CASES` |
| Modify | `test/orchestrator/fvt/pxeboot/slurm_lifecycle/test_slurm_lifecycle.py` | Add `node_remove` and `node_add` markers |
| Modify | `test/orchestrator/library/vars/domain_vars.py` | Register `node_remove`, `node_add`, `token_renew` markers; register `kubernetes_lifecycle` suite |
| Create | `test/orchestrator/fvt/pxeboot/kubernetes_lifecycle/test_kubernetes_lifecycle.py` | K8s node remove/add FVT tests |
| Create | `test/orchestrator/fvt/pxeboot/kubernetes_lifecycle/__init__.py` | Package init |
| Create | `test/orchestrator/library/functions/kubernetes_lifecycle_pxeboot_func.py` | K8s node remove/add check functions |
| Modify | `test/orchestrator/fvt/pxeboot/kubernetes_cluster/test_bootstrap_token_security.py` | Add `token_renew` marker to `test_kubernetes_bootstrap_token_ttl` |

## 6. Execution

```
./setup_env.sh --theme cluster_lifecycle
./run_validation.sh svt_cluster_lifecycle list
./run_validation.sh svt_cluster_lifecycle all
./run_validation.sh svt_cluster_lifecycle deploy_slurm_cluster
./run_validation.sh svt_cluster_lifecycle slurm_jobs
./run_validation.sh svt_cluster_lifecycle slurm_node_remove
./run_validation.sh svt_cluster_lifecycle slurm_node_add
./run_validation.sh svt_cluster_lifecycle deploy_k8s_cluster
./run_validation.sh svt_cluster_lifecycle k8s_telemetry
./run_validation.sh svt_cluster_lifecycle k8s_token_renew
./run_validation.sh svt_cluster_lifecycle slurm_node_remove --retry
```
