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
playbook with ``exec``, its verification tests with ``verify``). The SVT never
copies FVT logic. The tests of a stage are listed in test_case_vars.py.
"""

from typing import Dict, Tuple

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
REPORT_SUITES = ("main", "repo_manager", "image_build_manager", "orchestrator",
                 "telemetry", "build_stream")

# Domain credential stores, written by test/<theme creds_suite>/setup_env.sh
# --set-domain-creds at <domain data>/input/<project>/<file> (vault encrypted).
CREDENTIAL_FILES: Dict[str, str] = {
    "repo_manager": "repo_manager_config_credentials.yml",
    "image_build_manager": "image_build_credentials.yml",
    "orchestrator": "orchestrator_credentials.yml",
    "build_stream": "build_stream_credentials.yml",
}

THEMES: Dict[str, Dict] = {
    "build_stream": {
        # Theme name shown on top of the SVT report and in the pipeline email.
        "title": "BuildStream End-to-End Lifecycle",
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
        "fvt_domains": ("repo_manager", "image_build_manager", "orchestrator",
                        "telemetry", "build_stream"),
        # Domains whose input folder omnia.sh -s creates and whose credential
        # store the tests need (./setup_env.sh --set-domain-creds).
        "credential_domains": ("repo_manager", "image_build_manager", "orchestrator",
                               "build_stream"),
        # The FVT suite whose setup_env.sh writes the credential stores.
        "creds_suite": "build_stream",
        # Cleanup steps that only run when the product they remove is installed:
        # step -> file that exists when it is.
        "cleanup_requires": {
            ("build_stream", ("cleanup", "test")):
                "/etc/containers/systemd/omnia_build_stream.container",
        },
        # Cleanup steps of products this theme does not deploy but a previous installation may
        # have: they run only when the domain holds deployed state (a file under its
        # output/ or log/ in the data path, the rule omnia.sh --cleanup --all applies).
        "cleanup_when_deployed": ("telemetry",),
        # ./run_validation.sh svt_build_stream <stage>, in this order (after
        # initialization, before summary).
        "stages": ("prepare_build_stream", "build_deploy", "cadence", "automatic_cleanup"),
        # Stages that do not stop the ones after them when they fail: the later stage
        # still runs (in the pipeline, allow_failed) and the summary still fails. A
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


# Suites that run from their own bootstrap .venv, never from the Omnia venv
# (test/main: omnia.sh --cleanup removes the Omnia venv it would run from).
OWN_VENV_DOMAINS = frozenset({"main"})
