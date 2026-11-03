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
                 "build_stream")

# Domain credential stores, written by test/<CREDS_SUITE>/setup_env.sh
# --set-domain-creds at <domain data>/input/<project>/<file> (vault encrypted).
CREDS_SUITE = "build_stream"
CREDENTIAL_FILES: Dict[str, str] = {
    "repo_manager": "repo_manager_config_credentials.yml",
    "image_build_manager": "image_build_credentials.yml",
    "orchestrator": "orchestrator_credentials.yml",
    "build_stream": "build_stream_credentials.yml",
}

THEMES: Dict[str, Dict] = {
    "build_stream": {
        "description": "BuildStream: base domains, BuildStream and GitLab, build and "
                       "deploy, cadence, automatic cleanup",
        # dataset_generator/profiles/<profile>.yml: user_inputs.yml -> src inputs.
        "profile": "build_stream",
        "cleanup_steps": CLEANUP_STEPS,
        # Suites whose requirements go into the Omnia venv, in --prepare-base
        # order (./setup_env.sh --install), then BuildStream.
        "fvt_domains": ("repo_manager", "image_build_manager", "orchestrator",
                        "build_stream"),
        # Domains whose input folder omnia.sh -s creates and whose credential
        # store the tests need (./setup_env.sh --set-domain-creds).
        "credential_domains": ("repo_manager", "image_build_manager", "orchestrator",
                               "build_stream"),
        # ./run_validation.sh svt_build_stream <stage>, in this order (after
        # initialization, before summary).
        "stages": ("prepare_build_stream", "build_deploy", "cadence", "automatic_cleanup"),
        # <theme>_test_config.yml block -> the FVT suite's test_config.yml,
        # written by ./setup_env.sh --configure:
        # key -> (suite, section, key there, kind).
        "fvt_settings": {
            "catalog": ("build_stream", "installation", "catalog", "catalog"),
            "cadence_catalog": ("build_stream", "installation", "cadence_catalog", "catalog"),
            "allow_pipeline_cancel": ("build_stream", "pipeline", "allow_pipeline_cancel",
                                      "bool"),
        },
    },
}
# Stage and section titles shown in the report.
STAGE_TITLES: Dict[str, str] = {
    "initialization": "Initialization",
    "prepare_build_stream": "Prepare BuildStream",
    "build_deploy": "Build and Deploy",
    "cadence": "Cadence",
    "automatic_cleanup": "Automatic Cleanup",
    "cleanup": "Cleanup",
    "install": "Install",
}
# The build_stream cleanup tag needs a BuildStream installation to remove.
STEP_REQUIRES_BUILD_STREAM = frozenset({("build_stream", ("cleanup", "test"))})
# Suites that run from their own bootstrap .venv, never from the Omnia venv
# (test/main: omnia.sh --cleanup removes the Omnia venv it would run from).
OWN_VENV_DOMAINS = frozenset({"main"})
