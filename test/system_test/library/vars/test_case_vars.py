# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SVT test registry: stable IDs, titles, order, stage and the step of each test.

ID format ``SVT_<THEME>_<SEQ>`` (theme upper-case); IDs are never reused
(001-003 were the former whole-case tests). Order: theme base +
position (build_stream 1000, observability 2000). Each test has one of:

* ``step``: ``(domain, runner arguments)`` of ``test/<domain>/_run.py fvt_<domain>``:
  ``exec`` runs the playbook, ``verify`` runs its verification tests, selected by
  suite and marker like every other theme. The step passes when its exit status is 0.
* ``run``: the arguments of ``src/main/omnia.sh`` (theme_vars.OMNIA_RUN_TAGS), the
  product command a customer runs, e.g. ``("-r", "telemetry", "--tags", "precheck")``.

Within a stage, a test is skipped once an earlier test of the stage failed.

catalog_build (order 2000+): generated from the plan of the current run
(catalog_vars.catalog_test_cases), one stage per catalog.
"""

from .catalog_vars import CATALOG_PLAN, catalog_test_cases

_BS = "build_stream"
_TEL = "telemetry"
_SR = "orchestrator"
_ORCH = "orchestrator"

TEST_CASES = {
    # ---------------------------------------------- stage prepare_build_stream
    "build_stream_prepare_base_exec": {
        "id": "SVT_BUILD_STREAM_004", "order": 1010, "stage": "prepare_build_stream",
        "title": "Prepare base: ./omnia.sh --prepare-base (repo_manager, "
                 "image_build_manager, orchestrator)",
        "step": (_BS, ("prepare_base", "exec")),
    },
    "build_stream_prepare_base_verify": {
        "id": "SVT_BUILD_STREAM_005", "order": 1011, "stage": "prepare_build_stream",
        "title": "Prepare base: verification",
        "step": (_BS, ("prepare_base", "verify")),
    },
    "build_stream_precheck_exec": {
        "id": "SVT_BUILD_STREAM_006", "order": 1012, "stage": "prepare_build_stream",
        "title": "Precheck: build_stream.yml --tags precheck",
        "step": (_BS, ("precheck", "exec")),
    },
    "build_stream_precheck_verify": {
        "id": "SVT_BUILD_STREAM_007", "order": 1013, "stage": "prepare_build_stream",
        "title": "Precheck: verification",
        "step": (_BS, ("precheck", "verify")),
    },
    "build_stream_prepare_exec": {
        "id": "SVT_BUILD_STREAM_008", "order": 1014, "stage": "prepare_build_stream",
        "title": "Prepare BuildStream: build_stream.yml --tags prepare",
        "step": (_BS, ("prepare", "exec")),
    },
    "build_stream_prepare_verify": {
        "id": "SVT_BUILD_STREAM_009", "order": 1015, "stage": "prepare_build_stream",
        "title": "Prepare BuildStream: verification",
        "step": (_BS, ("prepare", "verify")),
    },
    "build_stream_execute_exec": {
        "id": "SVT_BUILD_STREAM_010", "order": 1016, "stage": "prepare_build_stream",
        "title": "Execute: build_stream.yml --tags execute (GitLab server, runner, project)",
        "step": (_BS, ("execute", "exec")),
    },
    "build_stream_gitlab_server_verify": {
        "id": "SVT_BUILD_STREAM_011", "order": 1017, "stage": "prepare_build_stream",
        "title": "Execute: GitLab server verification",
        "step": (_BS, ("execute", "verify", "--suite", "gitlab_server")),
    },
    "build_stream_gitlab_runner_verify": {
        "id": "SVT_BUILD_STREAM_012", "order": 1018, "stage": "prepare_build_stream",
        "title": "Execute: GitLab runner verification",
        "step": (_BS, ("execute", "verify", "--suite", "gitlab_runner")),
    },
    "build_stream_gitlab_project_verify": {
        "id": "SVT_BUILD_STREAM_013", "order": 1019, "stage": "prepare_build_stream",
        "title": "Execute: GitLab project verification",
        "step": (_BS, ("execute", "verify", "--suite", "gitlab_project")),
    },
    # ------------------------------------------------------ stage build_deploy
    # build_automatic + deploy_automatic in one FVT run: the deploy uses the
    # image the build made.
    "build_stream_build_deploy_verify": {
        "id": "SVT_BUILD_STREAM_014", "order": 1030, "stage": "build_deploy",
        "title": "Build and deploy: automatic build pipeline, then the deploy of its image",
        "step": (_BS, ("execute", "verify", "--marker", "automatic_execution")),
    },
    # ----------------------------------------------------------- stage cadence
    # The sanity set of the cadence suite: a new build first, then one cadence cycle
    # and the cadence pipeline (trigger, the seven stages, the records); the image is
    # handed to the automatic cleanup. The suite's other cases (disable / re-enable the
    # cadence live, the artifact checks) are not sanity and are not part of the SVT.
    "build_stream_cadence_verify": {
        "id": "SVT_BUILD_STREAM_015", "order": 1040, "stage": "cadence",
        "title": "Cadence: new build, cadence cycle and cadence pipeline",
        "step": (_BS, ("execute", "verify", "--suite", "cadence", "--marker", "sanity")),
    },
    # ------------------------------------------------- stage automatic_cleanup
    "build_stream_automatic_cleanup_verify": {
        "id": "SVT_BUILD_STREAM_016", "order": 1050, "stage": "automatic_cleanup",
        "title": "Automatic cleanup of the cadence image (S3, registry, NFS)",
        "step": (_BS, ("execute", "verify", "--suite", "auto_cleanup")),
    },

    # =========================================================================
    # THEME: slurm_reboot
    # =========================================================================

    # ---------------------------------------- stage reboot_cluster
    "slurm_reboot_ordered_reboot_verify": {
        "id": "SVT_SLURM_REBOOT_001", "order": 2010, "stage": "reboot_cluster",
        "title": "Ordered Slurm cluster shutdown and power-on",
        "step": (_SR, ("reboot", "verify", "--marker", "reboot")),
    },

    # ---------------------------------------- stage verify_slurm_services
    "slurm_reboot_slurm_membership_verify": {
        "id": "SVT_SLURM_REBOOT_010", "order": 2110, "stage": "verify_slurm_services",
        "title": "Verify Slurm membership after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_cluster",
                        "--marker", "non_disruptive")),
    },

    # ---------------------------------------- stage verify_slurm_jobs
    "slurm_reboot_ldap_jobs_verify": {
        "id": "SVT_SLURM_REBOOT_020", "order": 2210, "stage": "verify_slurm_jobs",
        "title": "Verify LDAP-owned Slurm jobs after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_ldap",
                        "--marker", "non_disruptive")),
    },
    "slurm_reboot_root_jobs_verify": {
        "id": "SVT_SLURM_REBOOT_021", "order": 2211, "stage": "verify_slurm_jobs",
        "title": "Verify root Slurm jobs after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_jobs")),
    },

    # ---------------------------------------- stage verify_gpu_jobs
    "slurm_reboot_gpu_verify": {
        "id": "SVT_SLURM_REBOOT_030", "order": 2310, "stage": "verify_gpu_jobs",
        "title": "Verify GPU inventory and job allocation after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_gpu")),
    },
    "slurm_reboot_dcgm_verify": {
        "id": "SVT_SLURM_REBOOT_031", "order": 2311, "stage": "verify_gpu_jobs",
        "title": "Verify DCGM integration after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_dcgm")),
    },

    # ---------------------------------------- stage verify_mpi_ipoib
    "slurm_reboot_openmpi_verify": {
        "id": "SVT_SLURM_REBOOT_040", "order": 2410, "stage": "verify_mpi_ipoib",
        "title": "Verify OpenMPI installation and job after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_openmpi")),
    },
    "slurm_reboot_infiniband_verify": {
        "id": "SVT_SLURM_REBOOT_041", "order": 2411, "stage": "verify_mpi_ipoib",
        "title": "Verify InfiniBand configuration and connectivity after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "slurm_infiniband")),
    },
    "slurm_reboot_ipoib_verify": {
        "id": "SVT_SLURM_REBOOT_042", "order": 2412, "stage": "verify_mpi_ipoib",
        "title": "Verify IPoIB network and peer mesh after reboot",
        "step": (_SR, ("pxeboot", "verify", "--suite", "ipoib_network")),
    },

    # =========================================================================
    # THEME: k8s_reboot
    # =========================================================================

    # ---------------------------------------- stage reboot_cluster
    "k8s_reboot_ordered_reboot_verify": {
        "id": "SVT_K8S_REBOOT_001", "order": 4010, "stage": "reboot_cluster",
        "title": "Ordered Kubernetes cluster shutdown and power-on",
        "step": (_SR, ("reboot", "verify", "--marker", "reboot+kubernetes")),
    },

    # ---------------------------------------- stage verify_k8s_cluster
    "k8s_reboot_nodes_verify": {
        "id": "SVT_K8S_REBOOT_010", "order": 4110, "stage": "verify_k8s_cluster",
        "title": "Verify Kubernetes node readiness after reboot",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "kubernetes_cluster")),
    },
    "k8s_reboot_etcd_verify": {
        "id": "SVT_K8S_REBOOT_011", "order": 4111, "stage": "verify_k8s_cluster",
        "title": "Verify Kubernetes etcd health after reboot",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "kubernetes_etcd")),
    },

    # ---------------------------------------- stage verify_k8s_storage
    "k8s_reboot_storage_verify": {
        "id": "SVT_K8S_REBOOT_020", "order": 4210, "stage": "verify_k8s_storage",
        "title": "Verify Kubernetes NFS and PowerScale storage after reboot",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "kubernetes_storage")),
    },

    # ---------------------------------------- stage verify_telemetry
    "k8s_reboot_telemetry_sinks_verify": {
        "id": "SVT_K8S_REBOOT_030", "order": 4310, "stage": "verify_telemetry",
        "title": "Verify telemetry sinks (Kafka, VictoriaMetrics, VictoriaLogs) after reboot",
        "step": ("telemetry", ("deploy", "verify", "--suite", "sinks",
                               "--marker", "sanity")),
    },
    "k8s_reboot_telemetry_sources_verify": {
        "id": "SVT_K8S_REBOOT_031", "order": 4311, "stage": "verify_telemetry",
        "title": "Verify telemetry sources (iDRAC, LDMS, OME, PowerScale, UFM, VAST) after reboot",
        "step": ("telemetry", ("deploy", "verify", "--suite", "sources",
                               "--marker", "sanity")),
    },
    # ======================================================== theme observability
    # The cluster stages (prepare_base ... cluster_deploy) are skipped by default
    # (theme default_skip_stages): the theme runs on a deployed cluster.
    # ----------------------------------------------------------- stage prepare_base
    "observability_prepare_base_run": {
        "id": "SVT_OBSERVABILITY_001", "order": 2010, "stage": "prepare_base",
        "title": "Prepare base: ./omnia.sh --prepare-base",
        "run": ("--prepare-base",),
    },
    "observability_prepare_repo_manager_verify": {
        "id": "SVT_OBSERVABILITY_002", "order": 2011, "stage": "prepare_base",
        "title": "Prepare base: repo_manager prepare checks",
        "step": ("repo_manager", ("prepare", "verify", "--marker", "sanity")),
    },
    "observability_prepare_image_build_manager_verify": {
        "id": "SVT_OBSERVABILITY_003", "order": 2012, "stage": "prepare_base",
        "title": "Prepare base: image_build_manager prepare checks",
        "step": ("image_build_manager", ("prepare", "verify", "--marker", "sanity")),
    },
    "observability_prepare_orchestrator_verify": {
        "id": "SVT_OBSERVABILITY_004", "order": 2013, "stage": "prepare_base",
        "title": "Prepare base: orchestrator prepare checks",
        "step": ("orchestrator", ("prepare", "verify", "--marker", "sanity")),
    },
    # -------------------------------------------------------------- stage repo_sync
    "observability_repo_sync_run": {
        "id": "SVT_OBSERVABILITY_005", "order": 2020, "stage": "repo_sync",
        "title": "Repository sync: ./omnia.sh -r repo_manager --tags execute",
        "run": ("-r", "repo_manager", "--tags", "execute"),
    },
    "observability_repo_sync_verify": {
        "id": "SVT_OBSERVABILITY_006", "order": 2021, "stage": "repo_sync",
        "title": "Repository sync: repo_manager execute checks",
        "step": ("repo_manager", ("execute", "verify", "--marker", "sanity")),
    },
    # ------------------------------------------------------------ stage image_build
    "observability_image_build_run": {
        "id": "SVT_OBSERVABILITY_007", "order": 2030, "stage": "image_build",
        "title": "Image build: ./omnia.sh -r image_build_manager --tags build",
        "run": ("-r", "image_build_manager", "--tags", "build"),
    },
    "observability_image_build_verify": {
        "id": "SVT_OBSERVABILITY_008", "order": 2031, "stage": "image_build",
        "title": "Image build: image_build_manager build checks",
        "step": ("image_build_manager", ("build", "verify", "--marker", "sanity")),
    },
    # --------------------------------------------------------- stage cluster_deploy
    "observability_provision_run": {
        "id": "SVT_OBSERVABILITY_009", "order": 2040, "stage": "cluster_deploy",
        "title": "Cluster deploy: ./omnia.sh -r orchestrator --tags provision",
        "run": ("-r", "orchestrator", "--tags", "provision"),
    },
    "observability_provision_verify": {
        "id": "SVT_OBSERVABILITY_010", "order": 2041, "stage": "cluster_deploy",
        "title": "Cluster deploy: orchestrator provision checks",
        "step": ("orchestrator", ("provision", "verify", "--marker", "sanity")),
    },
    "observability_pxeboot_run": {
        "id": "SVT_OBSERVABILITY_011", "order": 2042, "stage": "cluster_deploy",
        "title": "Cluster deploy: ./omnia.sh -r orchestrator --tags pxeboot",
        "run": ("-r", "orchestrator", "--tags", "pxeboot"),
    },
    "observability_kubernetes_verify": {
        "id": "SVT_OBSERVABILITY_012", "order": 2043, "stage": "cluster_deploy",
        "title": "Cluster deploy: Kubernetes cluster checks",
        "step": ("orchestrator", ("pxeboot", "verify", "--suite", "kubernetes_cluster",
                                  "--marker", "sanity")),
    },
    "observability_slurm_verify": {
        "id": "SVT_OBSERVABILITY_013", "order": 2044, "stage": "cluster_deploy",
        "title": "Cluster deploy: Slurm cluster checks",
        "step": ("orchestrator", ("pxeboot", "verify", "--suite", "slurm_cluster",
                                  "--marker", "sanity")),
    },
    # -------------------------------------------------- stage observability_cleanup
    # The iDRAC and LDMS telemetry of an earlier deployment; soft (a cluster without
    # telemetry yet may fail it, the deploy still follows).
    "observability_cleanup_ldms_run": {
        "id": "SVT_OBSERVABILITY_014", "order": 2050, "stage": "observability_cleanup",
        "title": "Cleanup: ./omnia.sh -r telemetry --tags cleanup_ldms",
        "run": ("-r", _TEL, "--tags", "cleanup_ldms"),
    },
    "observability_cleanup_ldms_verify": {
        "id": "SVT_OBSERVABILITY_015", "order": 2051, "stage": "observability_cleanup",
        "title": "Cleanup: LDMS pods removed",
        "step": (_TEL, ("cleanup_ldms", "verify")),
    },
    "observability_cleanup_idrac_run": {
        "id": "SVT_OBSERVABILITY_016", "order": 2052, "stage": "observability_cleanup",
        "title": "Cleanup: ./omnia.sh -r telemetry --tags cleanup_idrac",
        "run": ("-r", _TEL, "--tags", "cleanup_idrac"),
    },
    "observability_cleanup_idrac_verify": {
        "id": "SVT_OBSERVABILITY_017", "order": 2053, "stage": "observability_cleanup",
        "title": "Cleanup: iDRAC pods removed",
        "step": (_TEL, ("cleanup_idrac", "verify")),
    },
    # ------------------------------------------------- stage observability_precheck
    "observability_precheck_run": {
        "id": "SVT_OBSERVABILITY_018", "order": 2060, "stage": "observability_precheck",
        "title": "Precheck: ./omnia.sh -r telemetry --tags precheck",
        "run": ("-r", _TEL, "--tags", "precheck"),
    },
    "observability_precheck_verify": {
        "id": "SVT_OBSERVABILITY_019", "order": 2061, "stage": "observability_precheck",
        "title": "Precheck: omnia.env, Kubernetes nodes Ready, kube_vip reachable",
        "step": (_TEL, ("precheck", "verify", "--marker", "sanity")),
    },
    "observability_validate_run": {
        "id": "SVT_OBSERVABILITY_020", "order": 2062, "stage": "observability_precheck",
        "title": "Validate: ./omnia.sh -r telemetry --tags validate",
        "run": ("-r", _TEL, "--tags", "validate"),
    },
    "observability_validate_verify": {
        "id": "SVT_OBSERVABILITY_021", "order": 2063, "stage": "observability_precheck",
        "title": "Validate: telemetry_config.yml valid",
        "step": (_TEL, ("validate", "verify")),
    },
    # --------------------------------------------------- stage observability_deploy
    "observability_deploy_run": {
        "id": "SVT_OBSERVABILITY_022", "order": 2070, "stage": "observability_deploy",
        "title": "Deploy: ./omnia.sh -r telemetry (enabled sources and sinks)",
        "run": ("-r", _TEL),
    },
    "observability_stack_verify": {
        "id": "SVT_OBSERVABILITY_023", "order": 2071, "stage": "observability_deploy",
        "title": "Deploy: Kafka, VictoriaMetrics, VictoriaLogs, telemetry pods, install mode",
        "step": (_TEL, ("deploy", "verify", "--marker", "sanity")),
    },
    # ---------------------------------------------------- stage observability_idrac
    "observability_idrac_readiness_verify": {
        "id": "SVT_OBSERVABILITY_024", "order": 2080, "stage": "observability_idrac",
        "title": "iDRAC readiness: pods, StatefulSet, containers, VictoriaPump, service",
        "step": (_TEL, ("deploy", "verify", "--suite", "sources", "--marker", "idrac+sanity")),
    },
    "observability_idrac_data_verify": {
        "id": "SVT_OBSERVABILITY_025", "order": 2081, "stage": "observability_idrac",
        "title": "iDRAC data flow: MySQL, receiver, Kafka, VictoriaMetrics",
        "step": (_TEL, ("deploy", "verify", "--suite", "sources", "--marker", "idrac+functional")),
    },
    # ----------------------------------------------------- stage observability_ldms
    "observability_ldms_readiness_verify": {
        "id": "SVT_OBSERVABILITY_026", "order": 2090, "stage": "observability_ldms",
        "title": "LDMS readiness: aggregator, store, Vector-LDMS bridge, Kafka topic",
        "step": (_TEL, ("deploy", "verify", "--suite", "sources", "--marker", "ldms+sanity")),
    },
    "observability_ldms_data_verify": {
        "id": "SVT_OBSERVABILITY_027", "order": 2091, "stage": "observability_ldms",
        "title": "LDMS data flow: samplers, Kafka, VictoriaMetrics",
        "step": (_TEL, ("deploy", "verify", "--suite", "sources", "--marker", "ldms+functional")),
    },
    # ============================================================ theme cluster_lifecycle
    # When use_discovery_mapping=true in the theme's test_config, the
    # orchestrator's pxe_mapping_file.csv is replaced with the latest
    # timestamped bmc_pxe_mapping_file_<ts>.csv from the discovery output.
    # When use_discovery_mapping=false (default), this test is a no-op.
    "cluster_lifecycle_use_discovery_mapping": {
        "id": "SVT_CLUSTER_LIFECYCLE_014", "order": 3005, "stage": "deploy_slurm_cluster",
        "title": "Discovery mapping: copy the latest discovery PXE mapping to orchestrator "
                 "input (use_discovery_mapping=true) or skip (use_discovery_mapping=false)",
        "step": ("svt", ("pxe_use_discovery_mapping",)),
    },
    # deploy_slurm_cluster -------------------------------------------
    "cluster_lifecycle_precheck_exec": {
        "id": "SVT_CLUSTER_LIFECYCLE_001", "order": 3010, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator precheck",
        "step": (_ORCH, ("precheck", "exec")),
    },
    "cluster_lifecycle_precheck_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_002", "order": 3011, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator precheck: verification",
        "step": (_ORCH, ("precheck", "verify")),
    },
    "cluster_lifecycle_prepare_exec": {
        "id": "SVT_CLUSTER_LIFECYCLE_003", "order": 3012, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator prepare",
        "step": (_ORCH, ("prepare", "exec")),
    },
    "cluster_lifecycle_prepare_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_004", "order": 3013, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator prepare: verification",
        "step": (_ORCH, ("prepare", "verify")),
    },
    "cluster_lifecycle_provision_exec": {
        "id": "SVT_CLUSTER_LIFECYCLE_005", "order": 3014, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator provision",
        "step": (_ORCH, ("provision", "exec")),
    },
    "cluster_lifecycle_provision_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_006", "order": 3015, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator provision: verification",
        "step": (_ORCH, ("provision", "verify")),
    },
    "cluster_lifecycle_pxeboot_exec": {
        "id": "SVT_CLUSTER_LIFECYCLE_007", "order": 3016, "stage": "deploy_slurm_cluster",
        "title": "Orchestrator PXE boot",
        "step": (_ORCH, ("pxeboot", "exec")),
    },
    "cluster_lifecycle_pxeboot_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_008", "order": 3017, "stage": "deploy_slurm_cluster",
        "title": "PXE boot: connectivity and cloud-init",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "connectivity")),
    },
    # slurm cluster verification (part of deploy_slurm_cluster) ------
    "cluster_lifecycle_slurm_cluster_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_009", "order": 3030, "stage": "deploy_slurm_cluster",
        "title": "Slurm cluster membership, services and scheduler",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "slurm_cluster")),
    },
    # slurm_jobs ----------------------------------------------------
    "cluster_lifecycle_slurm_jobs_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_010", "order": 3040, "stage": "slurm_jobs",
        "title": "Slurm job submission (control, login, compiler, concurrent)",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "slurm_jobs")),
    },
    "cluster_lifecycle_ipoib_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_011", "order": 3041, "stage": "slurm_jobs",
        "title": "Slurm jobs over IPoIB (IPv4/IPv6/dual-stack traffic path)",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "ipoib_network")),
    },
    # slurm_node_remove ----------------------------------------------
    "cluster_lifecycle_slurm_node_remove": {
        "id": "SVT_CLUSTER_LIFECYCLE_012", "order": 3050, "stage": "slurm_node_remove",
        "title": "Delete a Slurm compute node",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "slurm_lifecycle",
                         "--marker", "node_lifecycle+node_remove")),
    },
    "cluster_lifecycle_slurm_node_add": {
        "id": "SVT_CLUSTER_LIFECYCLE_013", "order": 3051, "stage": "slurm_node_add",
        "title": "Add a Slurm compute node",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "slurm_lifecycle",
                         "--marker", "node_lifecycle+node_add")),
    },
    # ============================================================ Kubernetes stream
    # deploy_k8s_cluster ----------------------------------------------
    "cluster_lifecycle_k8s_cluster_verify": {
        "id": "SVT_CLUSTER_LIFECYCLE_015", "order": 3060, "stage": "deploy_k8s_cluster",
        "title": "Kubernetes cluster health (membership, services, control plane, etcd, storage)",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "kubernetes_cluster")),
    },
    # k8s_telemetry ---------------------------------------------------
    "cluster_lifecycle_k8s_telemetry": {
        "id": "SVT_CLUSTER_LIFECYCLE_016", "order": 3070, "stage": "k8s_telemetry",
        "title": "Telemetry deploy and verify (offline / Pulp)",
        "step": (_TEL, ("deploy", "exec")),
    },
    # k8s_token_renew -------------------------------------------------
    "cluster_lifecycle_k8s_token_renew": {
        "id": "SVT_CLUSTER_LIFECYCLE_017", "order": 3090, "stage": "k8s_token_renew",
        "title": "Renew Kubernetes bootstrap tokens",
        "step": (_ORCH, ("pxeboot", "verify", "--suite", "kubernetes_cluster",
                         "--marker", "token_renew")),
    },
}
# ------------------------------------------------------ theme catalog_build
TEST_CASES.update(catalog_test_cases(CATALOG_PLAN))
