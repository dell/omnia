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

"""Build Stream FVT — execute pipeline log, assertion and progress messages."""

from typing import Dict

TEST_LOG_MSGS: Dict[str, str] = {
    "precheck_failed": "{scenario} precheck failed: {count} check(s)",
    # --- prepare_base ---
    "prepare_base_ok": "./omnia.sh --prepare-base completed in {duration:.1f}s",
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}) after {duration:.1f}s"
    ),
    # --- auto_cleanup ---
    "auto_cleanup_disabled": (
        "retention.auto_cleanup_enabled is false in {path}: the scheduler runs "
        "no cleanup cycle; nothing to verify"
    ),
    "auto_cleanup_noop": "No image group is eligible; verifying the pass changes nothing",
}

TEST_ASSERT_MSGS: Dict[str, str] = {
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}, {duration:.1f}s). Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Review the streamed omnia.sh output above\n"
        "  2. Re-run on the OIM: cd src/main && ./omnia.sh --prepare-base\n"
    ),
    "build_failed": (
        "Build pipeline failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Open the failed job in GitLab CI/CD > Pipelines\n"
        "  2. Read the stage log_file_path reported above\n"
        "  3. Re-verify without committing: set pipeline.build_job_id\n"
    ),
}

# Live progress lines streamed by long-running library functions.
PROGRESS_MSGS: Dict[str, str] = {
    "catalog_committing": "committing {file} with version {version}",
    "pipeline_auto_triggered": "pipeline #{pipeline_id} auto-triggered by the {source} commit",
    "verify_only_job": "verify-only: using job {job_id}",
    "deploy_target": "deploying image group {group_id} ({source}, status {status})",
    "pxe_rows_swapping": "swapping rows {first} and {second} of {file}",
    "trigger_script_rc": "trigger script rc={rc}",
    # --- busy pipelines ---
    "no_busy_pipelines": "no running or pending GitLab pipeline; {action}",
    "busy_pipelines_found": (
        "running GitLab pipeline(s) found: {pipelines}; allow_pipeline_cancel is true, "
        "cancelling them before {action}"
    ),
    "busy_pipelines_cancelled": "running pipelines cancelled; {action}",
    "busy_pipelines_blocked": (
        "GitLab pipeline(s) {pipelines} are running or pending, so the test does not "
        "start {action}. Cancel them in GitLab, or set pipeline.allow_pipeline_cancel: "
        "true in test_config.yml to let the test cancel them"
    ),
    "pipeline_cancel": "cancel pipeline #{pipeline_id}: {outcome}",
    "pipeline_api_triggered": (
        "pipeline #{pipeline_id} triggered through the API with PIPELINE_TYPE={pipeline_type}"
    ),
    "catalog_committing_skip_ci": (
        "committing {file} with version {version} and [skip ci] (manual mode: no "
        "auto-triggered pipeline)"
    ),
    "job_created": "BuildStream job created: {job_id} (state {state})",
    "job_waiting": "waiting for the BuildStream job (pipeline #{pipeline_id} {status})",
    "gitlab_pipeline_status": "GitLab pipeline #{pipeline_id}: {status}",
    "gitlab_job_status": "GitLab job '{name}' (stage {stage}): {status}",
    "stage_monitoring": "monitoring stage '{stage}' (poll {poll}s)",
    "stage_changed": "[{clock}] stage '{stage}' -> {state}",
    "stage_still": "[{clock}] stage '{stage}' still {state}",
    "stage_skipped": "stage '{stage}' was SKIPPED by BuildStream",
    "stage_log_follow": "stage '{stage}' playbook log: tail -f {path}",
    "stage_log_streaming": "streaming stage '{stage}' playbook log (debug_mode): {path}",
    "stage_log_end": "end of stage '{stage}' playbook log ({lines} line(s))",
    "stage_verifying": "stage '{stage}' finished {state}; verifying job_stages and API",
    "stage_check": "  {label}: {value}",
    "stage_settle": "BuildStream job failed; re-reading stage '{stage}' for its final state",
    "pipeline_finishing": "GitLab pipeline #{pipeline_id} {status}; waiting for it to finish",
    "gitlab_job_waiting": "GitLab job #{job_id}: {status}",
    "image_selection_pipeline": "image selection pipeline #{pipeline_id}",
    "image_group_selected": "selected image group '{group_id}' (GitLab job #{job_id})",
    "deploy_job_started": "deploy job #{job_id} started",
    # --- gitlab_func ---
    "pipeline_detect_wait": "waiting for GitLab to create a pipeline for commit {commit}",
    "bridge_wait": "waiting for '{bridge}' in pipeline #{pipeline_id} to start",
    "cadence_heartbeat": "[{elapsed}s] cadence cycle running{progress}",
    "cadence_sync_progress": "; repo sync at {progress}",
    "cadence_log_follow": "cadence repo sync log: tail -f {path}",
    "cadence_log_streaming": "streaming cadence repo sync log (debug_mode): {path}",
    "cadence_set": "set cadence.enabled: {enabled} in {path} (no service restart)",
    "cadence_catalog_uploading": (
        "uploading {source} to GitLab {file} as v{version} with [skip ci] "
        "(no pipeline; the cadence cycle bumps it to v{expected})"
    ),
    "cadence_catalog_current": "GitLab {file} already holds {source} v{version}; nothing to upload",
    "cadence_upload_no_pipeline": "upload commit {commit}: no pipeline created (as expected)",
    "cadence_trigger_command": "triggering cadence: {command}",
    "cadence_journal_header": "playbook-watcher journal (cadence lines) since the trigger:",
    "cadence_journal_line": "[journal] {line}",
    "cadence_wait_disabled": (
        "waiting up to {timeout}s for playbook-watcher to report the cycle disabled"
    ),
    # --- auto_cleanup_func / cleanup_step_func ---
    "cleanup_statuses": "Cleanup status: {statuses}",
    "cleanup_still_running": "[{elapsed}s] cleanup still running: {statuses}",
    "cleanup_log_follow": "cleanup playbook log: tail -f {path}",
    "cleanup_log_streaming": "streaming cleanup playbook log (debug_mode): {path}",
    "cleanup_target": "cleanup target: image group {group_id} (job {job_id}, status "
                      "{status}, {source})",
    "cadence_build_started": "cadence test: building a dedicated new image first (image group "
                             "{group_id}, job {job_id}); the automated cleanup deletes it later",
    "auto_cleanup_marked": "marked image group {group_id} FAILED in build_stream_db "
                           "(was {previous}, {source}); the automated cleanup deletes it",
    "auto_cleanup_already_failed": "image group {group_id} is already FAILED ({source}); "
                                   "the automated cleanup deletes it",
    "cleanup_job_started": "GitLab cleanup job #{job_id} started (DELETE /api/v1/jobs/{bsm_job})",
}

# Step-by-step pipeline suites (fvt/execute/build, fvt/execute/deploy).
STEP_MSGS: Dict[str, str] = {
    "not_started": "the {pipeline} pipeline was not started in this run (its trigger test "
                   "did not pass)",
    "previous_failed": "the {pipeline} pipeline step '{step}' failed earlier in this run",
    "build_failed": "the {build} pipeline failed earlier in this run, so there is no new "
                    "image group to deploy; every deploy step is skipped",
    "deploy_build_no_group": (
        "the {build} pipeline passed in this run but recorded no image group to deploy\n"
        "HOW TO FIX:\n"
        "  1. Check the build pipeline records step above for the image_groups row\n"
        "  2. Deploy it explicitly: set pipeline.deploy_image_group_id in test_config.yml"
    ),
    "deploy_image_not_set": (
        "image name is not present: no build pipeline ran in this run and "
        "pipeline.deploy_image_group_id is empty in test_config.yml\n"
        "HOW TO FIX:\n"
        "  1. Set pipeline.deploy_image_group_id to the image group to deploy, e.g. "
        "omnia-slurm-k8s-rhel-10-2-x86_64-no-vast-v1.2\n"
        "  2. List image groups: podman exec omnia_postgres sh -c 'psql -U \"$POSTGRES_USER\" "
        "-d build_stream_db -c \"select id, status from image_groups\"'\n"
        "  3. Or run the build pipeline in the same run (--suite build_automatic)"
    ),
    "deploy_image_not_found": (
        "requested image not found: image group {group_id} ({source}) is not in "
        "build_stream_db (table image_groups)\n"
        "HOW TO FIX:\n"
        "  1. Check the ID for typos, or list the image groups in build_stream_db\n"
        "  2. Build it first: --suite build_automatic, then deploy"
    ),
    "deploy_image_not_offered": (
        "requested image not found: the deploy pipeline does not offer image group "
        "{group_id}; offered: {offered}\n"
        "HOW TO FIX:\n"
        "  1. Only BUILT image groups are offered; check the image_groups status\n"
        "  2. Pick an offered group in pipeline.deploy_image_group_id"
    ),
    "cadence_needs_build": (
        "No build pipeline has run on this BuildStream yet: the cadence pipeline needs the "
        "OAuth client the first build pipeline registers. Run the build pipeline at least "
        "once: ./run_validation.sh fvt_build_stream execute verify --suite build_automatic"
    ),
    "cadence_build_failed": (
        "The new image the cadence test builds first failed ({error}), so the cadence cycle "
        "is not triggered and every cadence step is skipped"
    ),
    "cleanup_nothing": (
        "No images to clean: build_stream_db has no BUILT, PASSED or FAILED image group "
        "(every image group is already CLEANED, or none was built). "
        "HOW TO FIX: run a build first, or set pipeline.{key} to an existing image group"
    ),
    "cleanup_already_cleaned": (
        "Image group {group_id} (pipeline.{key}) is already CLEANED. "
        "Nothing to delete, so the cleanup is not triggered"
    ),
    "auto_cleanup_no_cadence_image": (
        "No image to clean: the new image the cadence test builds first failed, so no image "
        "group was created for the automated cleanup. Nothing to delete, so the automated "
        "cleanup is skipped"
    ),
    "auto_cleanup_disabled": (
        "retention.auto_cleanup_enabled is false in {path}: the AutoCleanupScheduler is idle, "
        "so the automated cleanup pass is not run"
    ),
    "auto_cleanup_rules": (
        "retention: auto_cleanup_enabled={auto_cleanup_enabled}, retention_age_days="
        "{retention_age_days}, min_keep_count={min_keep_count}; every FAILED image group "
        "is deleted, retention candidates as listed below"
    ),
    "auto_cleanup_noop": (
        "No FAILED image group and no retention candidate: nothing to delete; verifying "
        "the pass changes nothing"
    ),
    "oauth_variables_missing": (
        "GitLab CI/CD variable(s) {keys} missing: the build pipeline initialization job did "
        "not register the BuildStream OAuth client. HOW TO FIX: read the initialization job "
        "log of the build pipeline (POST /api/v1/auth/register), then rerun the build pipeline"
    ),
    "oauth_client_id_unreadable": (
        "cannot read GitLab CI/CD variable {key}: {error}. HOW TO FIX: check that the GitLab "
        "API token in the build_stream credentials can read project variables"
    ),
    "oauth_client_id_format": (
        "GitLab CI/CD variable {key} does not hold a BuildStream client ID (expected prefix "
        "{prefix}). HOW TO FIX: delete {key} and BSM_CLIENT_SECRET in GitLab and rerun the "
        "build pipeline so the initialization job registers a new client"
    ),
    "oauth_job_client_unreadable": (
        "cannot read jobs.client_id for job {job_id} in build_stream_db. HOW TO FIX: check "
        "the omnia_postgres container and that the job row exists"
    ),
    "oauth_job_client_mismatch": (
        "job {job_id} was created by client {job_client}, not by the BSM_CLIENT_ID client "
        "{ci_client}. HOW TO FIX: the GitLab CI/CD client variables are stale; delete "
        "BSM_CLIENT_ID and BSM_CLIENT_SECRET in GitLab and rerun the build pipeline"
    ),
    "job_group_unreadable": (
        "cannot read image_groups for job {job_id}: {error}. HOW TO FIX: check the "
        "omnia_postgres container"
    ),
    "job_group_count": (
        "job {job_id} maps to {count} image group(s) {groups}; expected exactly one. HOW TO "
        "FIX: a job that maps to no image group did not finish build-image; check its "
        "job_stages rows and the build pipeline"
    ),
    "job_group_other": (
        "job {job_id} maps to image group {found}, not to the deployed image group "
        "{expected}. HOW TO FIX: check the select_image job log and the deploy.env "
        "IMAGE_GROUP_ID of the deploy pipeline"
    ),
    "verify_only_nothing": "verify-only mode: no {step} is performed for an existing job",
    "step_ok": "{step} passed",
    "step_failed": "{step} failed: {count} check(s)",
    "step_skipped": "{step} skipped: {reason}",
    "step_assert": "{step} failed: {failures}\n"
                   "HOW TO FIX:\n"
                   "  1. Review the progress lines and stage log above (debug_mode: true "
                   "streams it)\n"
                   "  2. Check the job: podman exec omnia_postgres psql ... "
                   "select * from job_stages where job_id='<job>'\n"
                   "  3. Check the GitLab pipeline in the project UI",
}
