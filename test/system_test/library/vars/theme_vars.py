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

A theme is data only. Every FVT step is ``(domain, runner arguments)`` and
runs ``test/<domain>/_run.py fvt_<domain> <arguments>``; the SVT never copies
FVT logic. Steps that share in-process state (a build and its deploy) are one
runner call; the cadence build is handed to the automatic cleanup through the
build_stream run state, so those test cases can run separately.
"""

from typing import Dict, Tuple

FvtStep = Tuple[str, Tuple[str, ...]]

BUILD_DEPLOY_STEPS: Tuple[FvtStep, ...] = (
    ("build_stream", ("prepare_base", "test")),
    ("build_stream", ("precheck", "test")),
    ("build_stream", ("prepare", "test")),
    ("build_stream", ("execute", "exec")),
    ("build_stream", ("execute", "verify", "--suite", "gitlab_server")),
    ("build_stream", ("execute", "verify", "--suite", "gitlab_runner")),
    ("build_stream", ("execute", "verify", "--suite", "gitlab_project")),
    # build_automatic + deploy_automatic in one process: deploy uses the build's image.
    ("build_stream", ("execute", "verify", "--marker", "automatic_execution")),
)

# Previous installation, removed in this order before the setup: BuildStream,
# then the base domains in the reverse of --prepare-base, then the Omnia setup.
# Each step is that suite's own cleanup FVT (its test_config.yml flags apply;
# ./setup_env.sh writes them from the SVT test_config.yml "cleanup" block).
CLEANUP_STEPS: Tuple[FvtStep, ...] = (
    ("build_stream", ("cleanup", "test")),
    ("orchestrator", ("cleanup", "test")),
    ("image_build_manager", ("cleanup", "test")),
    ("repo_manager", ("cleanup", "test", "--marker", "destructive")),
    ("main", ("cleanup", "exec")),
)
# Cleanup flags the SVT test_config.yml may set, per suite:
# (section of the suite's test_config.yml, "" = top level; allowed keys).
# Every value is a boolean; "enabled" (SVT only) turns the suite's cleanup
# step on or off and is never written into the suite.
CLEANUP_FLAGS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "build_stream": ("cleanup", ("postgres_backup", "cleanup_credentials")),
    "orchestrator": ("", ("cleanup_credentials", "cleanup_slurm", "cleanup_k8s",
                          "cleanup_benchmark_tools")),
    "image_build_manager": ("", ("cleanup_credentials",)),
    "repo_manager": ("", ("cleanup_credentials",)),
    "main": ("", ()),
}
CLEANUP_ENABLED_KEY = "enabled"

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
        "test_config_domain": "build_stream",
        # dataset_generator/profiles/<profile>.yml: user_inputs.yml -> src inputs.
        "profile": "build_stream",
        "cleanup_steps": CLEANUP_STEPS,
        # Suites whose requirements go into the Omnia venv, in --prepare-base
        # order (./setup_env.sh --install), then BuildStream.
        "fvt_domains": ("repo_manager", "image_build_manager", "orchestrator",
                        "build_stream"),
        # Domains whose input folder omnia.sh -s creates and whose credential
        # store the cases need (./setup_env.sh --set-domain-creds).
        "credential_domains": ("repo_manager", "image_build_manager", "orchestrator",
                               "build_stream"),
        "cases": {
            "build_deploy": BUILD_DEPLOY_STEPS,
            "cadence": (("build_stream", ("execute", "verify", "--suite", "cadence")),),
            "automatic_cleanup": (
                ("build_stream", ("execute", "verify", "--suite", "auto_cleanup")),
            ),
        },
    },
}
# The build_stream cleanup tag needs a BuildStream installation to remove.
STEP_REQUIRES_BUILD_STREAM = frozenset({("build_stream", ("cleanup", "test"))})
# Suites that run from their own bootstrap .venv, never from the Omnia venv
# (test/main: omnia.sh --cleanup removes the Omnia venv it would run from).
OWN_VENV_DOMAINS = frozenset({"main"})
