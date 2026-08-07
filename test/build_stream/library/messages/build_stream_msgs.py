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

"""
Build Stream — Test Messages

All test names, log messages, assertion messages, and function messages
for the build_stream FVT automation.
"""

# =============================================================================
# TEST NAMES (displayed in test output header)
# =============================================================================

TEST_NAMES = {
    # Deploy
    "deploy_playbook": (
        "Deploy: build_stream.yml --tags {tag}"
    ),
    "deploy_playbook_full": (
        "Deploy: build_stream.yml (default: prepare + build)"
    ),

    # Infrastructure — containers
    "bsm_container_running": (
        "Verify omnia_build_stream container is running"
    ),
    "postgres_container_running": (
        "Verify omnia_postgres container is running"
    ),
    "gitlab_server_running": (
        "Verify GitLab server is running and accessible"
    ),
    "gitlab_runner_running": (
        "Verify GitLab runner container is running"
    ),

    # API health
    "bsm_api_health": (
        "Verify build_stream API /health endpoint returns healthy"
    ),

    # Database
    "postgres_tables": (
        "Verify all expected tables exist in build_stream_db"
    ),

    # Build stream enabled
    "build_stream_enabled": (
        "Verify build_stream is enabled in build_stream_config.yml"
    ),

    # Input config
    "input_config_exists": (
        "Verify build_stream_config.yml exists on target"
    ),

    # Pipeline
    "catalog_upload": "Catalog Upload and Pipeline Trigger",
    "pipeline_triggered": "Pipeline Auto-Triggered Check",
    "stage_monitor": "Stage '{stage}' Monitor",
    "stage_db_verify": "Stage '{stage}' Database Verification",
    "images_created": "Images Created Check",
    "image_groups_created": "Image Groups Created Check",
    "catalog_roles": "Catalog Roles and Architectures Check",
    "registry_images": "Registry Images Verification",
    "s3_boot_images": "S3 Boot Images Verification",
    "build_pipeline_result": "Build Pipeline Final Result",
    "verify_generated_inputs": "Verify Generated Input Config Files",
    "deploy_pipeline_trigger": "Deploy Pipeline Trigger",
    "deploy_image_select": "Deploy Image Selection",
    "cleanup_pipeline_trigger": "Cleanup Pipeline Trigger",
    "cleanup_image_select": "Cleanup Image Selection",
    "cleanup_verify": "Cleanup Verification",

    # Cleanup verification
    "containers_removed": (
        "Verify build_stream containers removed after cleanup"
    ),
    "postgres_removed": (
        "Verify PostgreSQL container removed after cleanup"
    ),
    "gitlab_removed": (
        "Verify GitLab containers removed after cleanup"
    ),
    "ports_closed": (
        "Verify service ports closed after cleanup"
    ),

    # Prepare verification
    "ports_listening": (
        "Verify service ports are listening after prepare"
    ),
}

# =============================================================================
# TEST LOG MESSAGES
# =============================================================================

TEST_LOG_MSGS = {
    # Container messages
    "container_running": "Container {container} is running",
    "container_not_running": (
        "Container {container} is NOT running"
    ),

    # API health
    "health_ok": "Build stream API health check passed",
    "health_fail": "Build stream API health check failed: {error}",

    # PostgreSQL
    "postgres_ok": "All expected tables found in build_stream_db",
    "postgres_fail": "Missing tables in build_stream_db: {missing}",

    # Build stream enabled
    "build_stream_enabled_ok": (
        "build_stream is enabled in build_stream_config.yml"
    ),
    "build_stream_enabled_fail": (
        "build_stream is NOT enabled in build_stream_config.yml"
    ),

    # GitLab
    "gitlab_server_ok": "GitLab server is running and accessible",
    "gitlab_server_fail": "GitLab server check failed: {error}",
    "gitlab_runner_ok": "GitLab runner container is running",
    "gitlab_runner_fail": "GitLab runner check failed: {error}",

    # Input config
    "input_config_ok": "build_stream_config.yml present",
    "input_config_missing": "build_stream_config.yml not found",

    # Cleanup
    "containers_removed_ok": "All build_stream containers removed",
    "containers_still_running": (
        "{count} container(s) still running"
    ),
    "ports_closed_ok": "All service ports closed",
    "ports_still_open": "{count} port(s) still open",

    # Prepare
    "ports_listening_ok": "All service ports listening",
    "ports_not_listening": "{count} port(s) not listening",

    # Deploy
    "playbook_start": (
        "Running: ansible-playbook {playbook} --tags {tag}"
    ),
    "playbook_success": (
        "Playbook completed (rc=0, duration={duration:.1f}s)"
    ),
    "playbook_failed": (
        "Playbook failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Pipeline
    "catalog_upload_ok": "Catalog uploaded successfully",
    "catalog_upload_fail": "Failed to upload catalog: {error}",
    "pipeline_triggered_ok": "Pipeline {pipeline_id} triggered successfully",
    "pipeline_triggered_fail": "Pipeline not triggered: {error}",
    "stage_running": "Stage '{stage}' is running...",
    "stage_completed": "Stage '{stage}' completed successfully ({elapsed}s)",
    "stage_failed": "Stage '{stage}' failed: {error}",
    "stage_db_ok": "Stage '{stage}' verified in database (state: {state})",
    "stage_db_fail": "Stage '{stage}' database verification failed: {error}",
    "images_ok": "Found {count} images for job {job_id}",
    "images_fail": "No images found for job {job_id}",
    "image_groups_ok": "Found {count} image groups for job {job_id}",
    "image_groups_fail": "No image groups found for job {job_id}",
    "catalog_roles_ok": "Catalog roles retrieved: {roles} (architectures: {archs})",
    "catalog_roles_fail": "Failed to get catalog roles: {error}",
    "registry_ok": "All {count} role images found in registry",
    "registry_fail": "Missing {count} role image(s) in registry: {missing}",
    "s3_ok": "All {count} role boot images found in S3",
    "s3_fail": "Missing {count} role boot image(s) in S3: {missing}",
    "pipeline_result_ok": "Build pipeline completed — all stages passed",
    "pipeline_result_fail": "Build pipeline completed with failures",
    "clone_ok": "Omnia repo cloned (branch: {branch})",
    "clone_fail": "Failed to clone Omnia repo: {error}",
    "generated_inputs_ok": "All generated input configs match source",
    "generated_inputs_fail": "Generated input config verification failed",
}

# =============================================================================
# SKIP MESSAGES
# =============================================================================

SKIP_MSGS = {
    "build_stream_disabled": (
        "build_stream is not enabled — skipping test"
    ),
    "no_job_id": "Test skipped - no job_id available",
    "previous_stage_failed": "Test skipped - previous stage '{stage}' failed",
    "build_failed": "Test skipped - build pipeline failed",
    "pipeline_not_triggered": "Test skipped - pipeline not triggered",
    "clone_failed": "Test skipped - Omnia repo clone failed",
}

# =============================================================================
# TEST ASSERT MESSAGES (user-friendly with instructions)
# =============================================================================

_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS = {
    "container_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINER CHECK FAILED: {container}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Status: {status}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps -a | grep {container}\n"
        "\u2551   2. Check logs: podman logs {container}\n"
        "\u2551   3. Restart: podman restart {container}\n"
        "\u2551   4. Re-run: ansible-playbook build_stream.yml"
        " --tags prepare\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "health_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 BUILD STREAM API HEALTH CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps | grep omnia_build_stream\n"
        "\u2551   2. Check logs: podman logs omnia_build_stream\n"
        "\u2551   3. Re-run: ansible-playbook build_stream.yml"
        " --tags prepare\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "postgres_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 POSTGRESQL TABLE CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps | grep omnia_postgres\n"
        "\u2551   2. Check logs: podman logs omnia_postgres\n"
        "\u2551   3. Re-run: ansible-playbook build_stream.yml"
        " --tags prepare\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "gitlab_server_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GITLAB SERVER CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps | grep gitlab\n"
        "\u2551   2. Check logs: podman logs gitlab\n"
        "\u2551   3. Verify GitLab is deployed: gitlab.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "gitlab_runner_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GITLAB RUNNER CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps | grep gitlab-runner\n"
        "\u2551   2. Check logs: podman logs gitlab-runner\n"
        "\u2551   3. Verify runner is registered with GitLab server\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "build_stream_not_enabled": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 BUILD STREAM NOT ENABLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 enable_build_stream is false or not set\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Set enable_build_stream: true in"
        " build_stream_config.yml\n"
        "\u2551   2. Re-run: ansible-playbook build_stream.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "playbook_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Playbook: {playbook}\n"
        "\u2551 Tag: {tag}\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check the playbook output above\n"
        "\u2551   2. Check logs: {log_path}\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}

# =============================================================================
# FUNCTION MESSAGES (for library functions)
# =============================================================================

BUILD_STREAM_MSGS = {
    "validation_summary": (
        "\nValidation Summary:\n"
        "- Total: {total}\n"
        "- Passed: {passed}\n"
        "- Failed: {failed}\n"
        "- Skipped: {skipped}\n"
    ),
}

# =============================================================================
# PIPELINE MESSAGES (for real-time logging)
# =============================================================================

PIPELINE_MSGS = {
    "checking_pipelines": "Checking for existing pipelines...",
    "pipeline_running": "⚠ WARNING: Pipeline #{id} is already {status}",
    "pipeline_source": "  Source: {source}",
    "pipeline_created": "  Created: {created_at}",
    "cancel_instructions": (
        "\nPlease cancel the running pipeline in GitLab before triggering a new one:\n"
        "  1. Go to GitLab > CI/CD > Pipelines\n"
        "  2. Cancel pipeline #{id}\n"
        "  3. Re-run this test"
    ),
    "no_running_pipelines": "No running/pending pipelines. Latest pipeline ID: {id}",
    "uploading_catalog": "Uploading catalog file to GitLab...",
    "catalog_uploaded": "Catalog uploaded successfully",
    "waiting_pipeline": "Waiting for pipeline to be triggered...",
    "pipeline_triggered": "Pipeline #{id} triggered (status: {status})",
    "waiting_job_db": "Waiting for job to be created in database...",
    "job_created": "Job created: {job_id} (state: {state})",
    "job_not_found": "Warning: Job not found in DB within timeout",
    "pipeline_already_running": "Pipeline #{id} is already {status}. Please cancel it first.",
}

# =============================================================================
# STAGE POLLING MESSAGES (for real-time logging)
# =============================================================================

STAGE_POLL_MSGS = {
    "polling_start": "Polling stage '{stage}' (interval: {interval}s, timeout: {timeout} min)",
    "stage_not_created": "[{time}] Stage '{stage}' not yet created, waiting...",
    "stage_state_change": "[{time}] Stage '{stage}' → {state}",
    "stage_completed": "[{time}] Stage '{stage}' COMPLETED ✓",
    "stage_failed": "[{time}] Stage '{stage}' FAILED ✗",
    "stage_error": "  Error: {error}",
    "pipeline_status": "[{time}] Pipeline #{id} status: {status}",
    "pipeline_failed": "  ⚠ Pipeline failed! Check GitLab CI/CD for error details.",
    "pipeline_canceled": "  ⚠ Pipeline was canceled!",
    "stage_still_running": "[{time}] Stage '{stage}' still {state}...",
    "stage_timeout": "[{time}] TIMEOUT - Stage '{stage}' did not complete",
}
