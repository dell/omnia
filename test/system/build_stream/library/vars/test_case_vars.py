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

"""Canonical registry for BuildStream system (SVT) test cases.

IDs use ``BSM_SVT_<SCENARIO>_<TYPE><NUMBER>``:

- ``E`` is an execution case: it runs a product entry point (a precheck
  playbook, ``./omnia.sh``, a domain playbook or a cleanup pass).
- ``V`` is a verification case: it checks what an execution produced (or
  triggers and verifies a pipeline).

Keys match the pytest function names without the ``test_`` prefix; test
files read them as ``TC["<key>"]``. IDs are never reused: a retired ID stays
retired even when its test is removed.
"""

PREPARE_BASE_TEST_CASES: dict[str, dict[str, str]] = {
    "precheck_prepare_base": {
        "id": "BSM_SVT_PREPARE_BASE_E001",
        "title": "Precheck: validate omnia.env, venv, omnia.sh, credentials and "
                 "catalog placement",
    },
    "run_prepare_base": {
        "id": "BSM_SVT_PREPARE_BASE_E002",
        "title": "Execute ./omnia.sh --prepare-base and wait for all domains to initialize",
    },
    "verify_repo_manager_readiness": {
        "id": "BSM_SVT_PREPARE_BASE_V001",
        "title": "Verify repo_manager is ready: Pulp quadlet active, service running, "
                 "container healthy",
        "component": "repo_manager",
    },
    "verify_image_build_manager_readiness": {
        "id": "BSM_SVT_PREPARE_BASE_V002",
        "title": "Verify image_build_manager is ready: MinIO and registry containers serving",
        "component": "image_build_manager",
    },
    "verify_orchestrator_readiness": {
        "id": "BSM_SVT_PREPARE_BASE_V003",
        "title": "Verify orchestrator is ready: OpenCHAMI units, containers, volumes and "
                 "OpenLDAP",
        "component": "orchestrator",
    },
}

INSTALLATION_TEST_CASES: dict[str, dict[str, str]] = {
    "precheck_installation": {
        "id": "BSM_SVT_INSTALLATION_E001",
        "title": "Precheck: validate catalog, BuildStream inputs and run "
                 "build_stream.yml --tags precheck",
    },
    "run_build_stream_installation": {
        "id": "BSM_SVT_INSTALLATION_E002",
        "title": "Place the selected catalog at CATALOG_FILE_PATH and run "
                 "build_stream.yml to deploy BuildStream",
    },
    "verify_build_stream_services": {
        "id": "BSM_SVT_INSTALLATION_V001",
        "title": "Verify BuildStream runtime: containers running, watcher active, "
                 "DB tables present, API healthy",
        "component": "BuildStream services",
    },
    "verify_gitlab_repository_sync": {
        "id": "BSM_SVT_INSTALLATION_V002",
        "title": "Verify the GitLab project holds all CI files, omnia.env and "
                 "domain input files match the OIM",
        "component": "GitLab repository",
    },
    "build_pipeline_trigger_and_verify": {
        "id": "BSM_SVT_INSTALLATION_V003",
        "title": "Commit the selected catalog with the next version to trigger the "
                 "build pipeline; verify stages and DB",
        "component": "Build pipeline",
    },
    "deploy_pipeline_trigger_and_verify": {
        "id": "BSM_SVT_INSTALLATION_V004",
        "title": "Swap PXE mapping rows to trigger the deploy pipeline; verify stages, "
                 "image group PASSED and DB",
        "component": "Deploy pipeline",
    },
    "cadence_pipeline_trigger_and_verify": {
        "id": "BSM_SVT_INSTALLATION_V005",
        "title": "Upload the selected catalog for cadence ([skip ci]), trigger cadence; "
                 "verify repo sync, bump and pipeline",
        "component": "Cadence pipeline",
    },
    "cadence_disable_takes_effect_live": {
        "id": "BSM_SVT_INSTALLATION_V006",
        "title": "Disable cadence in build_stream_config.yml (no restart); verify the "
                 "next triggered cycle is skipped",
        "component": "Cadence enable/disable",
    },
    "cadence_reenable_resumes_cycle": {
        "id": "BSM_SVT_INSTALLATION_V007",
        "title": "Re-enable cadence in build_stream_config.yml (no restart); verify a "
                 "triggered cycle runs to completion",
        "component": "Cadence enable/disable",
    },
}

AUTO_CLEANUP_TEST_CASES: dict[str, dict[str, str]] = {
    "precheck_auto_cleanup": {
        "id": "BSM_SVT_AUTO_CLEANUP_E001",
        "title": "Precheck: validate retention settings, BuildStream container and "
                 "playbook-watcher",
    },
    "run_auto_cleanup_pass": {
        "id": "BSM_SVT_AUTO_CLEANUP_E002",
        "title": "Execute one automated retention cleanup pass inside omnia_build_stream "
                 "and wait for finalization",
    },
    "verify_auto_cleanup_eligible_groups": {
        "id": "BSM_SVT_AUTO_CLEANUP_V001",
        "title": "Verify the cleanup pass removed exactly the eligible FAILED and "
                 "retention-expired image groups",
        "component": "Automated cleanup",
    },
}

CLEANUP_TEST_CASES: dict[str, dict[str, str]] = {
    "precheck_cleanup": {
        "id": "BSM_SVT_CLEANUP_E001",
        "title": "Precheck: validate enabled cleanup domains and their playbooks exist "
                 "in the checkout",
    },
    "run_full_domain_cleanup": {
        "id": "BSM_SVT_CLEANUP_E002",
        "title": "Execute every enabled domain cleanup playbook in order: build_stream, "
                 "orchestrator, IBM, repo_manager",
    },
    "postcondition_build_stream_cleanup": {
        "id": "BSM_SVT_CLEANUP_V001",
        "title": "Postcondition: verify build_stream containers stopped, DB removed, "
                 "credentials handled per flags",
        "component": "build_stream",
    },
    "postcondition_orchestrator_cleanup": {
        "id": "BSM_SVT_CLEANUP_V002",
        "title": "Postcondition: verify orchestrator OpenCHAMI and OpenLDAP containers "
                 "removed, credentials handled",
        "component": "orchestrator",
    },
    "postcondition_image_build_manager_cleanup": {
        "id": "BSM_SVT_CLEANUP_V003",
        "title": "Postcondition: verify image_build_manager MinIO and registry stopped, "
                 "ports closed, credentials handled",
        "component": "image_build_manager",
    },
    "postcondition_repo_manager_cleanup": {
        "id": "BSM_SVT_CLEANUP_V004",
        "title": "Postcondition: verify repo_manager Pulp container and quadlet removed, "
                 "data cleaned per flags",
        "component": "repo_manager",
    },
}

TEST_CASES: dict[str, dict[str, str]] = {
    **PREPARE_BASE_TEST_CASES,
    **INSTALLATION_TEST_CASES,
    **AUTO_CLEANUP_TEST_CASES,
    **CLEANUP_TEST_CASES,
}
