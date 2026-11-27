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

"""Themes: what each integration flavour loads, cleans, installs and verifies.

A theme is data only. Its settings file is ``<theme>_test_config.yml`` next to
the SVT runner. Its stages run in order with ``./run_validation.sh svt_<theme>
<stage>``; each stage is a set of SVT tests (svt/<theme>/), and each SVT test
runs one FVT step ``test/<domain>/_run.py fvt_<domain> <arguments>`` (the
playbook with ``exec``, its verification tests with ``verify``) or one product
command ``./omnia.sh ...`` (a RUN step, OMNIA_RUN_TAGS). The SVT never copies FVT
logic. The tests of a stage are listed in test_case_vars.py.
"""

from typing import Dict, Tuple

from .catalog_vars import CATALOG_PLAN, catalog_soft_stages, catalog_stage_info, catalog_stages

FvtStep = Tuple[str, Tuple[str, ...]]

# Previous installation, removed in this order before the setup: BuildStream,
# then the base domains in the reverse of --prepare-base, then the Omnia setup.
# Each step is that suite's own cleanup FVT (its test_config.yml flags apply;
# ./setup_env.sh writes them from the "cleanup" block of <theme>_test_config.yml).
CLEANUP_STEPS: Tuple[FvtStep, ...] = (
    ("build_stream", ("cleanup", "test")),
    # Telemetry runs on the Kubernetes cluster the orchestrator deploys, so it is removed
    # before the orchestrator (the order of omnia.sh: telemetry first).
    ("telemetry", ("cleanup", "test")),
    ("orchestrator", ("cleanup", "test")),
    # Discovery feeds the orchestrator (bmc_pxe_mapping_file.csv), so it is removed after it
    # and before image_build_manager (the reverse of the --prepare-base / workflow order).
    ("discovery", ("cleanup", "test")),
    ("image_build_manager", ("cleanup", "test")),
    ("repo_manager", ("cleanup", "test", "--marker", "destructive")),
    ("main", ("cleanup", "test")),
)
# Cleanup flags <theme>_test_config.yml may set, per suite:
# (section of the suite's test_config.yml, "" = top level; allowed keys).
# Every value is a boolean; "enabled" (SVT only) turns the suite's cleanup
# step on or off and is never written into the suite.
CLEANUP_FLAGS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "build_stream": ("cleanup", ("postgres_backup", "cleanup_credentials")),
    # delete_sinks_volume also removes the sink PVCs and the log, input and output
    # directories, which omnia.sh --cleanup --all needs to find empty.
    "telemetry": ("", ("delete_sinks_volume", "cleanup_credentials", "cleanup_logs")),
    "orchestrator": ("", ("cleanup_credentials", "cleanup_slurm", "cleanup_k8s",
                          "cleanup_benchmark_tools")),
    # Discovery's cleanup_credentials and cleanup_logs are playbook variables that its
    # cleanup FVT sets per test case, not test_config.yml keys: only "enabled" applies.
    "discovery": ("", ()),
    "image_build_manager": ("", ("cleanup_credentials",)),
    "repo_manager": ("", ("cleanup_credentials",)),
    # cleanup_all: omnia.sh --cleanup --all (the whole OMNIA_DATA_PATH). omnia.sh
    # runs every domain-init.sh --cleanup itself, but only after a preflight that
    # refuses while <data>/<domain>/log holds a file (the validate playbooks
    # write logs there and no domain cleanup tag removes them), so the SVT runs
    # domain-init.sh --cleanup first.
    "main": ("", ("cleanup_all",)),
}
CLEANUP_ENABLED_KEY = "enabled"
MAIN_CLEANUP_ALL_KEY = "cleanup_all"

# Report settings written into every suite's test_config.yml (top-level keys),
# so all FVT results, the setup steps and the SVT cases go into one report.
REPORT_KEYS = ("report_path", "report_name", "run_id")
REPORT_SUITES = ("main", "repo_manager", "image_build_manager", "discovery", "orchestrator",
                 "telemetry", "build_stream")

# Domain credential stores, written by test/<theme creds_suite>/setup_env.sh
# --set-domain-creds at <domain data>/input/<project>/<file> (vault encrypted).
CREDENTIAL_FILES: Dict[str, str] = {
    "repo_manager": "repo_manager_config_credentials.yml",
    "image_build_manager": "image_build_credentials.yml",
    "orchestrator": "orchestrator_credentials.yml",
    "build_stream": "build_stream_credentials.yml",
    # test/telemetry/setup_env.sh --domain-creds-stdin (one flat JSON object).
    "telemetry": "telemetry_credentials.yml",
}

# RUN steps (test_case_vars "run"): the omnia.sh command lines an SVT test may run, as a
# customer runs them. "-r <domain>" (the domain's default flow) or "-r <domain> --tags <tag>"
# with a tag of this list; "--prepare-base" alone. Anything else is refused.
OMNIA_RUN_TAGS: Dict[str, Tuple[str, ...]] = {
    "repo_manager": ("execute",),
    "image_build_manager": ("build",),
    "orchestrator": ("provision", "pxeboot"),
    "telemetry": ("precheck", "validate", "cleanup_idrac", "cleanup_ldms"),
}
OMNIA_PREPARE_BASE = ("--prepare-base",)

# A previous BuildStream installation (even a half one: Postgres up, API quadlet gone) has
# to be cleaned, or omnia.sh --cleanup --all refuses to start. Shared by every theme.
BUILD_STREAM_CLEANUP_REQUIRES: Dict[FvtStep, Tuple[str, ...]] = {
    ("build_stream", ("cleanup", "test")): (
        "/etc/containers/systemd/omnia_build_stream.container",
        "/etc/containers/systemd/omnia_postgres.container",
        "{domain_data}/postgres",
        "{domain_data}/build_stream_root",
    ),
}

THEMES: Dict[str, Dict] = {
    "build_stream": {
        # Theme name shown on top of the SVT report and in the pipeline email.
        "title": "BuildStream End-to-End Lifecycle",
        # Starts from scratch: its own first CI job (clean_install) runs the shared cleanup and
        # omnia.sh -s again, so it must be the first or the last theme of a cluster (the other
        # themes share one initialization).
        "clean_install": True,
        "description": "BuildStream: base domains, BuildStream and GitLab, build and "
                       "deploy, cadence, automatic cleanup",
        # dataset_generator/profiles/<profile>.yml: user_inputs.yml -> src inputs.
        "profile": "build_stream",
        "cleanup_steps": CLEANUP_STEPS,
        # cleanup.nfs flag -> name of the storage_config.yml mount whose NFS share the
        # cleanup empties (nfs_func.py).
        "nfs_shares": {"slurm_share": "nfs_slurm", "k8s_share": "nfs_k8s"},
        # Suites whose requirements go into the Omnia venv, in --prepare-base
        # order (./setup_env.sh --install), then BuildStream.
        "fvt_domains": ("repo_manager", "image_build_manager", "discovery", "orchestrator",
                        "telemetry", "build_stream"),
        # Domains whose input folder omnia.sh -s creates and whose credential
        # store the tests need (./setup_env.sh --set-domain-creds).
        "credential_domains": ("repo_manager", "image_build_manager", "orchestrator",
                               "build_stream"),
        # The FVT suite whose setup_env.sh writes the credential stores.
        "creds_suite": "build_stream",
        # Cleanup steps that only run when the product they remove is installed:
        # step -> the files and folders it leaves; the step runs when ANY of them exists
        # ({domain_data} is the data folder of the step's domain). A half installed
        # product (BuildStream: Postgres up, API quadlet gone) still has to be cleaned,
        # or omnia.sh --cleanup --all refuses to start.
        "cleanup_requires": BUILD_STREAM_CLEANUP_REQUIRES,
        # Cleanup steps of products this theme does not deploy but a previous installation may
        # have: they run only when the domain holds deployed state (a file under its
        # output/ or log/ in the data path, the rule omnia.sh --cleanup --all applies).
        "cleanup_when_deployed": ("telemetry", "discovery"),
        # ./run_validation.sh svt_build_stream <stage>, in this order (after
        # initialization, before summary).
        "stages": ("prepare_build_stream", "build_deploy", "cadence", "automatic_cleanup"),
        # Stages that do not stop the ones after them when they fail: the later stage
        # still runs (in the pipeline, allow_failure) and the summary still fails. A
        # stage not listed here is a hard stage: when it fails, the stages after it do
        # not run. initialization and prepare_build_stream are hard: everything after
        # them needs the installed BuildStream.
        "soft_stages": ("build_deploy", "cadence", "automatic_cleanup"),
        # Title and one-line description of each theme stage (report, pipeline).
        "stage_info": {
            "prepare_build_stream": (
                "Prepare BuildStream",
                "omnia.sh --prepare-base, then build_stream.yml precheck, prepare and "
                "execute; GitLab server, runner and project verified"),
            "build_deploy": (
                "Build and Deploy",
                "Catalog commit -> automatic build pipeline, then the deploy, restart and "
                "validate of the image it built"),
            "cadence": (
                "Cadence",
                "A new build, one cadence cycle (repo sync, catalog bump) and the cadence "
                "pipeline"),
            "automatic_cleanup": (
                "Automatic Cleanup",
                "The cadence image marked FAILED, one cleanup_cron pass, then S3, registry "
                "and NFS checked"),
        },
        # Read-only probe of the product state, run before and after every theme
        # stage and in summary: what a stage created or changed becomes its
        # "outputs" (run.json and the report); summary lists what this run left.
        # command: argument list, no shell on the host; prints one row per line,
        # fields separated by "|", in the order of columns; key: the row identity;
        # created: the column holding the creation time; leftover: statuses a
        # run should not leave behind.
        "state_probe": {
            "label": "BuildStream image groups",
            "command": ("podman", "exec", "omnia_postgres", "sh", "-c",
                        'psql -U "$POSTGRES_USER" -d build_stream_db -At -F "|" -c "'
                        "select g.id, g.job_id, g.status, coalesce(j.job_state, ''), "
                        "g.created_at from image_groups g left join jobs j "
                        'on j.job_id = g.job_id order by g.created_at"'),
            "columns": ("image_group_id", "job_id", "group_status", "job_state", "created_at"),
            "key": "image_group_id",
            "created": "created_at",
            "leftover": {"group_status": ("BUILT", "FAILED"), "job_state": ("IN_PROGRESS",)},
        },
        # <theme>_test_config.yml block -> the FVT suite's test_config.yml,
        # written by ./setup_env.sh --configure:
        # key -> (suite, section, key there, kind).
        "fvt_settings": {
            "catalog": ("build_stream", "installation", "catalog", "catalog"),
            "cadence_catalog": ("build_stream", "installation", "cadence_catalog", "catalog"),
            "allow_pipeline_cancel": ("build_stream", "pipeline", "allow_pipeline_cancel",
                                      "bool"),
            "debug_mode": ("build_stream", "", "debug_mode", "bool"),
        },
    },
    "slurm_reboot": {
        "title": "Slurm Ordered Reboot Verification",
        "description": "Ordered Slurm cluster shutdown and power-on, then Slurm "
                       "services, LDAP jobs, GPU jobs, MPI jobs, and IPoIB verification",
        "profile": "slurm_reboot",
        "cleanup_steps": (),
        "nfs_shares": {"slurm_share": "nfs_slurm", "k8s_share": "nfs_k8s"},
        "fvt_domains": ("orchestrator",),
        "credential_domains": ("orchestrator",),
        "creds_suite": "orchestrator",
        "stages": (
            "reboot_cluster",
            "verify_slurm_services",
            "verify_slurm_jobs",
            "verify_gpu_jobs",
            "verify_mpi_ipoib",
        ),
        "soft_stages": (
            "verify_slurm_jobs",
            "verify_gpu_jobs",
            "verify_mpi_ipoib",
        ),
        "stage_info": {
            "reboot_cluster": (
                "Ordered Cluster Reboot",
                "Graceful shutdown (compute -> login/compiler -> controller), then "
                "Redfish power-on (controller -> login/compiler -> compute) with "
                "per-group cloud-init verification"),
            "verify_slurm_services": (
                "Slurm Services Verification",
                "Slurm membership, scheduler, services, cross-node SSH, configless "
                "mode, and configuration consistency on all node roles"),
            "verify_slurm_jobs": (
                "LDAP Job Verification",
                "LDAP-owned Slurm jobs submitted from controller, login, and "
                "login-compiler nodes with PAM access checks"),
            "verify_gpu_jobs": (
                "GPU Job Verification",
                "GPU inventory, GPU job allocation, and bounded GPU memory stress "
                "workload through Slurm"),
            "verify_mpi_ipoib": (
                "MPI and IPoIB Verification",
                "OpenMPI installation and job, InfiniBand configuration and "
                "connectivity, IPoIB peer mesh and Slurm NodeAddr"),
        },
        "fvt_settings": {},
    },
    "k8s_reboot": {
        "title": "Kubernetes Ordered Reboot Verification",
        "description": "Ordered Kubernetes cluster shutdown and power-on, then "
                       "Kubernetes cluster health, storage, PowerScale, and "
                       "telemetry verification",
        "profile": "k8s_reboot",
        "cleanup_steps": (),
        "nfs_shares": {"slurm_share": "nfs_slurm", "k8s_share": "nfs_k8s"},
        "fvt_domains": ("orchestrator", "telemetry"),
        "credential_domains": ("orchestrator",),
        "creds_suite": "orchestrator",
        "stages": (
            "reboot_cluster",
            "verify_k8s_cluster",
            "verify_k8s_storage",
            "verify_telemetry",
        ),
        "soft_stages": (
            "verify_k8s_storage",
            "verify_telemetry",
        ),
        "stage_info": {
            "reboot_cluster": (
                "Ordered Cluster Reboot",
                "Graceful shutdown (worker -> control-plane), then "
                "Redfish power-on (control-plane -> worker) with "
                "per-group cloud-init verification"),
            "verify_k8s_cluster": (
                "Kubernetes Cluster Verification",
                "Node readiness, control-plane readiness, system pods, "
                "etcd health, and virtual IP ownership"),
            "verify_k8s_storage": (
                "Kubernetes Storage Verification",
                "NFS and CSI storage, default StorageClass, PowerScale "
                "snapshot components and dynamic provisioning"),
            "verify_telemetry": (
                "Telemetry Verification",
                "PowerScale telemetry deployment, metrics, logs, and "
                "CSI driver health after reboot"),
        },
        "fvt_settings": {},
    },
    "observability": {
        "title": "Observability End-to-End (iDRAC, LDMS)",
        "description": "Telemetry of a deployed cluster: the iDRAC and LDMS sources deployed "
                       "with omnia.sh -r telemetry, then the telemetry FVT checks by test ID",
        "profile": "observability",
        "cleanup_steps": CLEANUP_STEPS,
        "nfs_shares": {"slurm_share": "nfs_slurm", "k8s_share": "nfs_k8s"},
        # build_stream: its setup_env.sh writes the repo_manager, image_build_manager and
        # orchestrator stores (creds_suite), and its cleanup FVT removes a previous BuildStream.
        "fvt_domains": ("repo_manager", "image_build_manager", "discovery", "orchestrator",
                        "telemetry", "build_stream"),
        "credential_domains": ("repo_manager", "image_build_manager", "orchestrator",
                               "telemetry"),
        "creds_suite": "build_stream",
        # Stores written by another suite than creds_suite: the suite takes one flat JSON
        # object on --domain-creds-stdin and has no --domain option.
        "creds_suites": {"telemetry": "telemetry"},
        "cleanup_requires": BUILD_STREAM_CLEANUP_REQUIRES,
        "cleanup_when_deployed": ("telemetry", "discovery"),
        # Cluster stages first (repo_manager -> image_build_manager -> orchestrator, the order
        # omnia.sh recommends), then observability last: telemetry needs the Kubernetes and
        # Slurm nodes the orchestrator brings up.
        "stages": ("prepare_base", "repo_sync", "image_build", "cluster_deploy",
                   "observability_cleanup", "observability_precheck", "observability_deploy",
                   "observability_idrac", "observability_ldms"),
        "soft_stages": ("observability_cleanup", "observability_idrac", "observability_ldms"),
        # Default: an already deployed cluster. ./run_validation.sh svt_observability all and
        # the pipeline leave these stages out (--skip-stages none / skip_stages "none" runs them),
        # and the pipeline does no clean reinstall unless clean_reinstall is "true".
        "default_skip_stages": ("initialization", "prepare_base", "repo_sync", "image_build",
                                "cluster_deploy"),
        # The stages the report counts as scenarios: cleanup (when enabled), then the deploy
        # stage and the stages after it that ran. Precheck is a gate, not a scenario.
        "scenario_stages": ("observability_cleanup", "observability_deploy",
                            "observability_idrac", "observability_ldms"),
        # Stages that are off unless <theme>_test_config.yml stages: turns them on.
        "optional_stages": ("observability_cleanup",),
        "default_clean_reinstall": False,
        # omnia.sh -r <domain> RUN steps allowed in this theme (OMNIA_RUN_TAGS).
        "run_domains": ("repo_manager", "image_build_manager", "orchestrator", "telemetry"),
        "stage_info": {
            "prepare_base": (
                "Prepare Base",
                "omnia.sh --prepare-base (repo_manager, image_build_manager, orchestrator), "
                "then their prepare checks"),
            "repo_sync": (
                "Repository Sync",
                "omnia.sh -r repo_manager --tags execute, then its checks"),
            "image_build": (
                "Image Build",
                "omnia.sh -r image_build_manager --tags build, then its checks"),
            "cluster_deploy": (
                "Cluster Deploy",
                "omnia.sh -r orchestrator provision and PXE boot: Kubernetes and Slurm nodes "
                "up"),
            "observability_cleanup": (
                "Observability Cleanup",
                "The iDRAC and LDMS telemetry of an earlier deployment removed "
                "(omnia.sh -r telemetry --tags cleanup_ldms, cleanup_idrac)"),
            "observability_precheck": (
                "Observability Precheck",
                "omnia.sh -r telemetry --tags precheck and validate: the cluster is healthy "
                "and the telemetry inputs are valid"),
            "observability_deploy": (
                "Observability Deploy",
                "omnia.sh -r telemetry (enabled sources and sinks), then Kafka, "
                "VictoriaMetrics, VictoriaLogs and the telemetry pods"),
            "observability_idrac": (
                "iDRAC Telemetry",
                "iDRAC pods and containers, then iDRAC data in MySQL, Kafka and "
                "VictoriaMetrics"),
            "observability_ldms": (
                "LDMS Telemetry",
                "LDMS aggregator, store and bridge, then the samplers and LDMS data in Kafka "
                "and VictoriaMetrics"),
        },
        "fvt_settings": {
            "sync_telemetry_input": ("telemetry", "", "sync_telemetry_input", "bool"),
            "configure_ome": ("telemetry", "", "configure_ome", "bool"),
            "configure_sfm": ("telemetry", "", "configure_sfm", "bool"),
        },
    },
    "catalog_build": {
        "title": "Catalog Build",
        "description": "Catalog build: for every catalog, ./omnia.sh --select-catalog, then "
                       "the repo_manager and image_build_manager FVT steps",
        "profile": "catalog_build",
        # Same cleanup as build_stream: an earlier BuildStream, telemetry or orchestrator
        # deployment must not block omnia.sh --cleanup --all.
        "cleanup_steps": CLEANUP_STEPS,
        "nfs_shares": {},
        # discovery, orchestrator, telemetry and build_stream: their requirements are installed
        # only for their cleanup FVT; they get no stage and no credentials.
        "fvt_domains": ("repo_manager", "image_build_manager", "discovery", "orchestrator",
                        "telemetry", "build_stream"),
        "credential_domains": ("repo_manager", "image_build_manager"),
        "creds_suite": "build_stream",
        "cleanup_requires": {
            ("build_stream", ("cleanup", "test")): (
                "/etc/containers/systemd/omnia_build_stream.container",
                "/etc/containers/systemd/omnia_postgres.container",
                "{domain_data}/postgres",
                "{domain_data}/build_stream_root",
            ),
        },
        "cleanup_when_deployed": ("telemetry", "discovery"),
        # One stage per catalog of the plan --configure wrote (catalog_vars.py); the
        # stage titles name the catalog. With continue_on_failure every catalog stage is
        # soft: a failed catalog does not stop the next one, the summary still fails.
        "stages": catalog_stages(CATALOG_PLAN),
        "soft_stages": catalog_soft_stages(CATALOG_PLAN),
        "stage_info": catalog_stage_info(CATALOG_PLAN),
        # The theme block is the catalog settings (catalog_settings.py), not FVT settings.
        "catalog_plan": True,
        "fvt_settings": {},
    },
    "cluster_lifecycle": {
        "title": "Cluster Lifecycle (Slurm + Kubernetes)",
        "description": "Cluster lifecycle: deploy Slurm and Kubernetes clusters, "
                       "run workloads, remove/add nodes, telemetry and token renewal",
        "profile": "cluster_lifecycle",
        "cleanup_steps": CLEANUP_STEPS,
        "nfs_shares": {"slurm_share": "nfs_slurm", "k8s_share": "nfs_k8s"},
        "fvt_domains": ("orchestrator", "telemetry"),
        "credential_domains": ("orchestrator",),
        "creds_suite": "build_stream",
        "cleanup_requires": {},
        "cleanup_when_deployed": ("telemetry",),
        "stages": ("deploy_slurm_cluster", "slurm_jobs",
                   "slurm_node_remove", "slurm_node_add",
                   "deploy_k8s_cluster", "k8s_telemetry",
                   "k8s_token_renew"),
        "soft_stages": ("slurm_jobs", "slurm_node_remove", "slurm_node_add",
                        "k8s_telemetry",
                        "k8s_token_renew"),
        "stage_info": {
            "deploy_slurm_cluster": (
                "Deploy Slurm Cluster",
                "Orchestrator precheck, prepare, provision, PXE boot and "
                "Slurm cluster verification (membership, services, "
                "configuration consistency, hardware discovery)"),
            "slurm_jobs": (
                "Run Jobs",
                "Job submission from control, login and compiler nodes; "
                "IPoIB traffic path (IPv4/IPv6/dual-stack)"),
            "slurm_node_remove": (
                "Delete Slurm Node",
                "Remove a Slurm compute node from the PXE mapping, "
                "re-provision and verify removal"),
            "slurm_node_add": (
                "Add Slurm Node",
                "Restore the removed node, re-provision and verify "
                "re-addition to Slurm membership"),
            "deploy_k8s_cluster": (
                "Deploy Kubernetes Cluster",
                "Verify Kubernetes cluster health: node membership, "
                "services, control plane, system pods, VIP, etcd and storage"),
            "k8s_telemetry": (
                "Telemetry (Offline)",
                "Deploy and verify telemetry in offline mode "
                "(nodes pull packages from Pulp, no internet required)"),
            "k8s_token_renew": (
                "Renew Tokens",
                "Run the bootstrap token refresh script and verify "
                "each renewed token has the configured TTL"),
        },
        "state_probe": None,
        "fvt_settings": {},
    },
}
# Sections every theme has (title, description); the theme stages come from
# THEMES[theme]["stage_info"]. In the report, cleanup and install (run by
# ./setup_env.sh) are shown inside the Initialization stage.
COMMON_STAGE_INFO: Dict[str, Tuple[str, str]] = {
    "initialization": (
        "Initialization",
        "Clean reinstall of this OIM (./setup_env.sh: cleanup, install), then the "
        "readiness checks"),
    "cleanup": (
        "Cleanup",
        "The previous installation removed: each suite's cleanup FVT, then "
        "omnia.sh --cleanup"),
    "install": (
        "Install",
        "omnia.sh -s (venv, domain-init, catalog, omnia-cli), then the FVT suites' test "
        "requirements in the Omnia venv"),
    "readiness": (
        "Readiness",
        "Inputs configured, Omnia installed, test requirements and credential stores "
        "present"),
    "summary": (
        "Summary",
        "The run printed and its report rendered; fails when any stage of the run failed"),
}


def stage_info(theme: str, name: str) -> Tuple[str, str]:
    """Return (title, description) of a section of ``theme`` (common or theme stage)."""
    info = {**COMMON_STAGE_INFO, **(THEMES.get(theme, {}).get("stage_info") or {})}
    return info.get(name, (name.replace("_", " ").title(), ""))


def soft_stages(theme: str) -> Tuple[str, ...]:
    """Return the stages of ``theme`` whose failure does not stop the following stages."""
    return tuple(THEMES.get(theme, {}).get("soft_stages") or ())


def theme_title(theme: str) -> str:
    """Return the display name of ``theme``."""
    return str(THEMES.get(theme, {}).get("title") or theme.replace("_", " ").title())


def starts_clean(theme: str) -> bool:
    """Return whether ``theme`` cleans and installs Omnia again in its own first job."""
    return bool(THEMES.get(theme, {}).get("clean_install", False))


def default_skip_stages(theme: str) -> Tuple[str, ...]:
    """Return the stages of ``theme`` that 'all' and the pipeline leave out by default."""
    return tuple(THEMES.get(theme, {}).get("default_skip_stages") or ())


def default_clean_reinstall(theme: str) -> bool:
    """Return whether the pipeline's initialization does a clean reinstall by default."""
    return bool(THEMES.get(theme, {}).get("default_clean_reinstall", True))


def creds_suite_of(theme: str, domain: str) -> str:
    """Return the FVT suite whose setup_env.sh writes the credential store of ``domain``."""
    return str((THEMES[theme].get("creds_suites") or {}).get(domain)
               or THEMES[theme]["creds_suite"])


# Suites that run from their own bootstrap .venv, never from the Omnia venv
# (test/main: omnia.sh --cleanup removes the Omnia venv it would run from).
OWN_VENV_DOMAINS = frozenset({"main"})
