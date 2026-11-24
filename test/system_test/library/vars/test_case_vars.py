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

"""SVT test registry: stable IDs, titles, order, stage and the FVT step of each test.

ID format ``SVT_<THEME>_<SEQ>`` (theme upper-case); IDs are never reused
(001-003 were the former whole-case tests). Order: theme base + position
(build_stream 1000). ``step`` is ``(domain, runner arguments)`` of
``test/<domain>/_run.py fvt_<domain>``: ``exec`` runs the playbook, ``verify``
runs its verification tests. Within a stage, a test is skipped once an earlier
test of the stage failed.

catalog_build (order 2000+): generated from the plan of the current run
(catalog_vars.catalog_test_cases), one stage per catalog.
"""

from .catalog_vars import CATALOG_PLAN, catalog_test_cases

_BS = "build_stream"
_ORCH = "orchestrator"
_TEL = "telemetry"

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
