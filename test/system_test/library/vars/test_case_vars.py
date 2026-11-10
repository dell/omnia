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
"""

_BS = "build_stream"

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
}
