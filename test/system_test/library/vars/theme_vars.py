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

"""Themes: what each integration flavour sets up, cleans and verifies.

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

THEMES: Dict[str, Dict] = {
    "build_stream": {
        "description": "BuildStream: base domains, BuildStream and GitLab, build and "
                       "deploy, cadence, automatic cleanup",
        "test_config_domain": "build_stream",
        "setup_domains": ("build_stream",),
        "cleanup_steps": (
            ("build_stream", ("cleanup", "test")),
            ("build_stream", ("domain_cleanup", "test")),
        ),
        "cases": {
            "build_deploy": BUILD_DEPLOY_STEPS,
            "cadence": (("build_stream", ("execute", "verify", "--suite", "cadence")),),
            "automatic_cleanup": (
                ("build_stream", ("execute", "verify", "--suite", "auto_cleanup")),
            ),
        },
    },
    "standard": {
        "description": "Standard: base domains with omnia.sh --prepare-base, then each "
                       "domain's FVT lifecycle",
        "test_config_domain": "build_stream",
        "setup_domains": ("build_stream", "repo_manager", "image_build_manager",
                          "orchestrator"),
        "cleanup_steps": (("build_stream", ("domain_cleanup", "test")),),
        "cases": {
            "prepare_base": (("build_stream", ("prepare_base", "test")),),
            "repo_manager": (("repo_manager", ("test",)),),
            "image_build_manager": (
                ("image_build_manager", ("precheck", "test")),
                ("image_build_manager", ("validate", "test")),
                ("image_build_manager", ("prepare", "test")),
                ("image_build_manager", ("build", "test")),
            ),
            "orchestrator": (("orchestrator", ("test",)),),
        },
    },
}
# The build_stream cleanup tag needs a BuildStream installation to remove.
STEP_REQUIRES_BUILD_STREAM = frozenset({("build_stream", ("cleanup", "test"))})
