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

"""Themes: what each integration flavour cleans, sets up and verifies.

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
# Each step is that suite's own cleanup FVT (its test_config.yml flags apply).
CLEANUP_STEPS: Tuple[FvtStep, ...] = (
    ("build_stream", ("cleanup", "test")),
    ("orchestrator", ("cleanup", "test")),
    ("image_build_manager", ("cleanup", "test")),
    ("repo_manager", ("cleanup", "test", "--marker", "destructive")),
    ("main", ("cleanup", "exec")),
)
# omnia.sh --setup-venv, then every domain-init.sh (test/main).
SETUP_STEPS: Tuple[FvtStep, ...] = (
    ("main", ("setup", "test")),
    ("main", ("init", "test")),
)

THEMES: Dict[str, Dict] = {
    "build_stream": {
        "description": "BuildStream: base domains, BuildStream and GitLab, build and "
                       "deploy, cadence, automatic cleanup",
        "test_config_domain": "build_stream",
        "cleanup_steps": CLEANUP_STEPS,
        "setup_steps": SETUP_STEPS,
        # Suites whose requirements go into the Omnia venv (cleanup and cases).
        "fvt_domains": ("build_stream", "orchestrator", "image_build_manager",
                        "repo_manager"),
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
