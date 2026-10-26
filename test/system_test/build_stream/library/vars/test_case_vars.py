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

"""BuildStream system test — test case registry.

Keys match the test function names without the ``test_`` prefix. IDs are
``TC_<SCENARIO>_<SEQ>`` (PB prepare_base, IN installation, AC auto_cleanup,
CL cleanup), numbered in execution order: 001 is the scenario precheck,
002 its entry point, then the verification cases.
"""

from typing import Dict

TEST_CASES: Dict[str, Dict[str, str]] = {
    # --- prepare_base ---
    "precheck_prepare_base": {
        "id": "TC_PB_001",
        "title": "Precheck: omnia.env, venv, omnia.sh and base domain credentials are ready",
    },
    "prepare_base": {
        "id": "TC_PB_002",
        "title": "Run ./omnia.sh --prepare-base on the OIM",
    },
    "repo_manager_ready": {
        "id": "TC_PB_003",
        "title": "Verify repo_manager prepare: Pulp quadlet, service and container",
    },
    "image_build_manager_ready": {
        "id": "TC_PB_004",
        "title": "Verify image_build_manager prepare: MinIO and registry serving",
    },
    "orchestrator_ready": {
        "id": "TC_PB_005",
        "title": "Verify orchestrator prepare: OpenCHAMI units, containers, volumes and OpenLDAP",
    },
    # --- installation ---
    "precheck_installation": {
        "id": "TC_IN_001",
        "title": "Precheck: catalog, BuildStream inputs and build_stream.yml --tags precheck",
    },
    "build_stream_installation": {
        "id": "TC_IN_002",
        "title": "Place the selected catalog and run build_stream.yml",
    },
    "build_stream_services": {
        "id": "TC_IN_003",
        "title": "Verify BuildStream containers, watcher, database tables and API health",
    },
    "gitlab_repository": {
        "id": "TC_IN_004",
        "title": "Verify the GitLab project holds the CI files, omnia.env and synced inputs",
    },
    "build_pipeline": {
        "id": "TC_IN_005",
        "title": "Catalog version change auto-triggers the build pipeline; verify stages and DB",
    },
    "deploy_pipeline": {
        "id": "TC_IN_006",
        "title": "PXE mapping change auto-triggers the deploy pipeline; verify stages and DB",
    },
    "cadence_pipeline": {
        "id": "TC_IN_007",
        "title": "Cadence trigger syncs repos, commits the catalog and runs the cadence pipeline",
    },
    # --- auto_cleanup ---
    "precheck_auto_cleanup": {
        "id": "TC_AC_001",
        "title": "Precheck: retention settings, BuildStream container and playbook-watcher",
    },
    "auto_cleanup": {
        "id": "TC_AC_002",
        "title": "Run one automated (retention) cleanup pass and wait for finalization",
    },
    "auto_cleanup_result": {
        "id": "TC_AC_003",
        "title": "Verify the pass cleaned exactly the eligible image groups",
    },
    # --- cleanup ---
    "precheck_cleanup": {
        "id": "TC_CL_001",
        "title": "Precheck: enabled cleanup domains and their playbooks",
    },
    "full_cleanup": {
        "id": "TC_CL_002",
        "title": "Run every enabled domain cleanup playbook in order",
    },
    "build_stream_cleanup": {
        "id": "TC_CL_003",
        "title": "Verify build_stream cleanup postconditions",
    },
    "orchestrator_cleanup": {
        "id": "TC_CL_004",
        "title": "Verify orchestrator cleanup postconditions",
    },
    "image_build_manager_cleanup": {
        "id": "TC_CL_005",
        "title": "Verify image_build_manager cleanup postconditions",
    },
    "repo_manager_cleanup": {
        "id": "TC_CL_006",
        "title": "Verify repo_manager cleanup postconditions",
    },
}
