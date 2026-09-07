# Orchestrator — Test Case Registry

> All test cases for the orchestrator domain FVT automation.

## Test Case ID Convention

|| Area | Prefix | Description |
||------|--------|-------------|
|| Module | `TC_MO_` | Module structure and dependency tests |
|| Playbook | `TC_PB_` | Playbook syntax and tag tests |
|| Role | `TC_RO_` | Role structure and metadata tests |
|| SLURM | `TC_SL_` | SLURM verification and job execution tests |
|| Kubernetes | `TC_K8_` | Kubernetes verification and workload tests |
|| Validate | `TC_VL_` | Input validation tests |
|| Prepare | `TC_PR_` | Prepare/deploy OpenCHAMI tests |
|| Provision | `TC_PV_` | Node provisioning tests |
|| Cleanup | `TC_CL_` | Cleanup verification tests |

---

## Module Tests (`fvt/modules/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_MO_001 | `test_module_structure` | Validate module file structure | sanity |
|| TC_MO_002 | `test_module_dependencies` | Check module dependencies | sanity |
|| TC_MO_003 | `test_module_schema_validation` | Validate module against schema | sanity |

---

## Playbook Tests (`fvt/playbooks/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_PB_001 | `test_playbook_exists` | Verify playbook file exists | sanity |
|| TC_PB_002 | `test_playbook_syntax` | Validate playbook syntax | sanity |
|| TC_PB_003 | `test_playbook_tags` | Extract and verify playbook tags | sanity |
|| TC_PB_004 | `test_playbook_dependencies` | Check playbook role dependencies | sanity |

---

## Role Tests (`fvt/roles/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_RO_001 | `test_role_structure` | Validate role directory structure | sanity |
|| TC_RO_002 | `test_role_tasks` | Verify role tasks file exists | sanity |
|| TC_RO_003 | `test_role_metadata` | Validate role metadata | sanity |
|| TC_RO_004 | `test_role_syntax` | Validate role syntax | sanity |

---

## SLURM Status Tests (`fvt/validate/slurm/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_SL_001 | `test_slurm_enabled` | Verify SLURM is enabled in config | slurm, sanity |
|| TC_SL_003 | `test_slurmctld_running` | Verify slurmctld service running | slurm |
|| TC_SL_004 | `test_slurmd_running` | Verify slurmd service running | slurm |
|| TC_SL_005 | `test_slurmdbd_running` | Verify slurmdbd service running | slurm |
|| TC_SL_006 | `test_munge_running` | Verify munge service running | slurm |
|| TC_SL_007 | `test_slurm_services_running` | Verify all SLURM services running | slurm |
|| TC_SL_008 | `test_slurm_directories_exist` | Verify SLURM directories exist | slurm |
|| TC_SL_009 | `test_slurm_config_files_exist` | Verify SLURM config files exist | slurm |
|| TC_SL_012 | `test_slurmctld_responding` | Verify slurmctld responds to commands | slurm |

---

## SLURM Infrastructure Tests (`fvt/validate/slurm/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_SL_014 | `test_all_pxe_nodes_in_slurm_cluster` | Verify all PXE nodes in SLURM | slurm |
|| TC_SL_015 | `test_slurm_nodes_idle` | Verify SLURM nodes are idle | slurm |
|| TC_SL_016 | `test_login_nodes_idle` | Verify login nodes are idle | slurm |
|| TC_SL_017 | `test_ssh_control_to_compute` | SSH from control to compute | slurm |
|| TC_SL_018 | `test_ssh_control_to_login` | SSH from control to login | slurm |
|| TC_SL_019 | `test_ssh_control_to_login_compiler` | SSH from control to login_compiler | slurm |
|| TC_SL_020 | `test_ssh_compute_to_control` | SSH from compute to control | slurm |
|| TC_SL_021 | `test_ssh_compute_to_login` | SSH from compute to login | slurm |
|| TC_SL_022 | `test_ssh_compute_to_login_compiler` | SSH from compute to login_compiler | slurm |
|| TC_SL_023 | `test_ssh_login_to_control` | SSH from login to control | slurm |
|| TC_SL_024 | `test_ssh_login_to_compute` | SSH from login to compute | slurm |
|| TC_SL_025 | `test_ssh_login_to_login_compiler` | SSH from login to login_compiler | slurm |
|| TC_SL_026 | `test_ssh_login_compiler_to_control` | SSH from login_compiler to control | slurm |
|| TC_SL_027 | `test_ssh_login_compiler_to_compute` | SSH from login_compiler to compute | slurm |
|| TC_SL_028 | `test_ssh_login_compiler_to_login` | SSH from login_compiler to login | slurm |

---

## SLURM Node Tests (`fvt/validate/slurm/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_SL_010 | `test_slurm_nodes_registered` | Verify nodes registered in SLURM | slurm |
|| TC_SL_011 | `test_slurm_partitions_exist` | Verify SLURM partitions exist | slurm |
|| TC_SL_013 | `test_slurm_job_submission` | Test basic job submission | slurm |

---

## SLURM Job Tests (`fvt/slurm/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_SL_029 | `test_slurmctld_on_control_nodes` | Verify slurmctld on control nodes | slurm |
|| TC_SL_030 | `test_slurmd_on_compute_nodes` | Verify slurmd on compute nodes | slurm |
|| TC_SL_031 | `test_munge_on_required_nodes` | Verify munge on required nodes | slurm |
|| TC_SL_032 | `test_srun_execution` | Test srun command execution | slurm |
|| TC_SL_033 | `test_sbatch_job_submission` | Test sbatch job submission | slurm |
|| TC_SL_034 | `test_job_queueing` | Test job queuing functionality | slurm |
|| TC_SL_035 | `test_drain_undrain_nodes` | Test drain/undrain node operations | slurm |
|| TC_SL_036 | `test_ldap_user_login` | Test LDAP user login | slurm |
|| TC_SL_037 | `test_ldap_job_submission` | Test LDAP job submission | slurm |
|| TC_SL_038 | `test_gpu_available` | Verify GPU resources available | slurm |
|| TC_SL_039 | `test_gpu_job_execution` | Test GPU job execution | slurm |
|| TC_SL_040 | `test_infiniband_available` | Verify InfiniBand available | slurm |
|| TC_SL_041 | `test_mpi_available` | Verify MPI available | slurm |
|| TC_SL_042 | `test_mpi_job_execution` | Test MPI job execution | slurm |

---

## Kubernetes Status Tests (`fvt/validate/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_001 | `test_k8s_enabled` | Verify K8s is enabled in config | kubernetes, sanity |
|| TC_K8_005 | `test_kubelet_running` | Verify kubelet running on all nodes | kubernetes, sanity |
|| TC_K8_006 | `test_containerd_running` | Verify containerd running on all nodes | kubernetes, sanity |
|| TC_K8_008 | `test_k8s_apiserver_responding` | Verify K8s API server responding | kubernetes, sanity |
|| TC_K8_009 | `test_k8s_directories_exist` | Verify K8s directories exist | kubernetes, sanity |
|| TC_K8_010 | `test_k8s_config_files_exist` | Verify K8s config files exist | kubernetes, sanity |
|| TC_K8_011 | `test_k8s_pki_certs_exist` | Verify K8s PKI certificates exist | kubernetes, sanity |

---

## Kubernetes Node Tests (`fvt/validate/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_002 | `test_k8s_nodes_ready` | Verify all K8s nodes Ready | kubernetes, sanity |
|| TC_K8_003 | `test_k8s_control_plane_nodes` | Verify control plane nodes Ready | kubernetes, sanity |
|| TC_K8_004 | `test_k8s_worker_nodes` | Verify worker nodes Ready | kubernetes, sanity |

---

## Kubernetes Pod Tests (`fvt/validate/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_007 | `test_k8s_system_pods` | Verify kube-system pods Running | kubernetes, sanity |
|| TC_K8_012 | `test_k8s_etcd_healthy` | Verify etcd cluster healthy | kubernetes, sanity |
|| TC_K8_013 | `test_k8s_coredns_running` | Verify CoreDNS pods Running | kubernetes, sanity |
|| TC_K8_014 | `test_k8s_kube_proxy_running` | Verify kube-proxy pods Running | kubernetes, sanity |

---

## Kubernetes SSH Tests (`fvt/validate/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_016 | `test_ssh_control_plane_to_worker` | SSH from control plane to workers | kubernetes, functional |
|| TC_K8_017 | `test_ssh_worker_to_control_plane` | SSH from workers to control plane | kubernetes, functional |
|| TC_K8_018 | `test_ssh_worker_to_worker` | SSH between worker nodes | kubernetes, functional |

---

## Kubernetes Config Tests (`fvt/validate/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_015 | `test_k8s_nfs_config_exists` | Verify K8s NFS config directory | kubernetes, sanity |
|| TC_K8_024 | `test_k8s_smd_groups` | Verify K8s groups in SMD | kubernetes, sanity |
|| TC_K8_025 | `test_k8s_metadata_configured` | Verify K8s metadata-service config | kubernetes, sanity |

---

## Kubernetes Comprehensive Tests (`fvt/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_022 | `test_k8s_node_labels` | Verify node labels match roles | kubernetes, sanity |
|| TC_K8_023 | `test_k8s_node_taints` | Verify control plane taints | kubernetes, sanity |
|| TC_K8_027 | `test_k8s_apiserver_pod` | Verify kube-apiserver static pod | kubernetes, sanity |
|| TC_K8_028 | `test_k8s_controller_manager_pod` | Verify kube-controller-manager pod | kubernetes, sanity |
|| TC_K8_029 | `test_k8s_scheduler_pod` | Verify kube-scheduler pod | kubernetes, sanity |
|| TC_K8_030 | `test_k8s_cluster_info` | Verify kubectl cluster-info | kubernetes, sanity |
|| TC_K8_019 | `test_k8s_pod_create` | Test pod creation and scheduling | kubernetes, functional |
|| TC_K8_020 | `test_k8s_dns_resolution` | Test DNS resolution in pods | kubernetes, functional |
|| TC_K8_021 | `test_k8s_service_create` | Test Kubernetes service creation | kubernetes, functional |
|| TC_K8_026 | `test_k8s_ldap_integration` | Test OpenLDAP K8s integration | kubernetes, functional |

---

## Kubernetes Provision (`fvt/provision/kubernetes/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_K8_000 | `test_k8s_provision` | Deploy orchestrator.yml --tags provision_kubernetes | deploy, sanity |

---

## Validate Scenario (`fvt/validate/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_VL_000 | `test_deploy_validate` | Deploy orchestrator.yml (validate) | deploy, sanity |
|| TC_VL_001 | `test_input_config_exists` | Verify orchestrator_config.yml exists | sanity |
|| TC_VL_002 | `test_omnia_config_exists` | Verify omnia_config.yml exists | sanity |
|| TC_VL_003 | `test_network_spec_exists` | Verify network_spec.yml exists | sanity |
|| TC_VL_004 | `test_credentials_present` | Verify credentials file present | sanity |
|| TC_VL_005 | `test_repo_status_exists` | Verify repo_status.yml exists | sanity |

---

## Prepare Scenario (`fvt/prepare/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_PR_000 | `test_deploy_prepare` | Deploy orchestrator.yml --tags prepare | deploy, sanity |
|| TC_PR_001 | `test_openchami_containers_running` | Verify all OpenCHAMI containers running | sanity |
|| TC_PR_002 | `test_openchami_services_active` | Verify systemd services active | sanity |
|| TC_PR_003 | `test_openchami_api_reachable` | Verify OpenCHAMI API reachable | functional |
|| TC_PR_004 | `test_openchami_config_files_exist` | Verify OpenCHAMI config files exist | sanity |
|| TC_PR_005 | `test_tokensmith_config_exists` | Verify tokensmith config exists | sanity |
|| TC_PR_006 | `test_postgres_init_script_exists` | Verify postgres init script exists | sanity |
|| TC_PR_007 | `test_rpm_file_integrity` | Verify RPM file integrity | sanity |

---

## Provision Scenario (`fvt/provision/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_SL_000 | `test_slurm_provision` | Test SLURM provisioning | deploy, sanity |
|| TC_PV_000 | `test_deploy_provision` | Deploy orchestrator.yml (full provision) | deploy, sanity |

---

## Cleanup Scenario (`fvt/cleanup/`)

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_CL_000 | `test_deploy_cleanup` | Deploy orchestrator.yml --tags cleanup | deploy, sanity |
|| TC_CL_001 | `test_containers_removed` | Verify containers removed | sanity |
|| TC_CL_002 | `test_services_removed` | Verify services stopped | sanity |
|| TC_CL_003 | `test_firewall_ports_closed` | Verify firewall ports closed | functional |

---

## Rollback Scenario (`fvt/rollback/`)

> Rollback is **not supported** in this release. The OpenCHAMI upgrade from
> v0.1.7-1 to v0.2.0 is a one-way migration. The rollback tag is reserved
> for future releases.

|| TC ID | Test Function | Description | Marker |
||-------|---------------|-------------|--------|
|| TC_RB_000 | `test_deploy_rollback_not_supported` | Verify rollback fails with 'not supported' message | deploy, sanity |

---

## Test Summary

**Total Test Cases: 104**

| Category | Count |
|----------|-------|
| Module Tests | 3 |
| Playbook Tests | 4 |
| Role Tests | 4 |
| SLURM Status Tests | 9 |
| SLURM Infrastructure Tests | 12 |
| SLURM Node Tests | 3 |
| SLURM Job Tests | 14 |
| K8s Status Tests | 7 |
| K8s Node Tests | 3 |
| K8s Pod Tests | 4 |
| K8s SSH Tests | 3 |
| K8s Config Tests | 3 |
| K8s Comprehensive Tests | 10 |
| K8s Provision Tests | 1 |
| Validate Tests | 6 |
| Prepare Tests | 8 |
| Provision Tests | 2 |
| Cleanup Tests | 4 |
| Rollback Tests | 1 |
| DCGM Tests | 3 |
| **Total** | **104** |

**Note**: Some test IDs may be reused across different test files (e.g., TC_SL_001 appears in both status and infrastructure tests). This is intentional as they test different aspects of the same functionality.
