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

"""BuildStream system test — log, assertion and live-progress messages."""

from typing import Dict

TEST_LOG_MSGS: Dict[str, str] = {
    # --- every scenario: precheck (first exec test) ---
    "precheck_ok": "{scenario} precheck passed: the entry point can run unattended",
    "precheck_failed": "{scenario} precheck failed: {count} check(s)",
    "precheck_gate": (
        "Skipped: the {scenario} precheck did not pass, so its entry point "
        "and verification do not run (dependent test)"
    ),
    "exec_gate": (
        "Skipped: the {scenario} entry point ({tc_id}) failed, so there is "
        "nothing for this verification to check (dependent test; skipped even "
        "with continue_on_failure: true)"
    ),
    "stop_on_failure": (
        "Skipped: {test} failed and continue_on_failure is false in "
        "test_config.yml, so the run stops here. Set continue_on_failure: true "
        "to keep running the independent tests"
    ),
    # --- exec -> verify hand-off ---
    "state_missing": (
        "Nothing to verify: {error}. Run '{scenario} exec' (or 'test') first"
    ),
    "state_used": "Verifying the {scenario} exec recorded at {saved_at}",
    # --- prepare_base ---
    "prepare_base_ok": "./omnia.sh --prepare-base completed in {duration:.1f}s",
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}) after {duration:.1f}s"
    ),
    "ready_ok": "{domain} is ready for BuildStream",
    "ready_failed": "{domain} is not ready: {count} check(s)",
    # --- installation ---
    "installation_start": "Placing catalog '{catalog}' and running build_stream.yml",
    "installation_ok": "Catalog placed and build_stream.yml completed",
    "installation_failed": "BuildStream installation failed: {count} check(s)",
    "services_ok": "BuildStream containers, watcher, database and API are healthy",
    "services_failed": "BuildStream services: {count} check(s) failed",
    "repository_ok": "GitLab project holds the CI files, omnia.env and synced inputs",
    "repository_failed": "GitLab repository: {count} check(s) failed",
    "pipeline_skip_build_failed": (
        "Skipped: the build pipeline test ({build_id}) failed in this run. The "
        "{pipeline} pipeline deploys the image group that build creates, so it "
        "cannot run (dependent test; skipped even with continue_on_failure: true)"
    ),
    "cadence_disabled_skip": (
        "Skipped: cadence.enabled is false in build_stream_config.yml, so a "
        "trigger only logs 'Cadence polling is disabled'. Set cadence.enabled: "
        "true to run the cadence pipeline test ({disable_id}/{reenable_id} "
        "cover the disabled behaviour)"
    ),
    "pipeline_mode_trigger": "Triggering the {pipeline} pipeline",
    "pipeline_mode_verify": (
        "Job ID used: {job_id} (pipeline.{pipeline}_job_id). Nothing is "
        "triggered or committed; verifying stages and DB only"
    ),
    "pipeline_ok": "{pipeline} pipeline: every stage COMPLETED and DB verified",
    "pipeline_failed": "{pipeline} pipeline failed: {count} check(s)",
    # --- cleanup ---
    "cleanup_start": "Cleaning {name} ({command})",
    "cleanup_skipped": "{name}: disabled in test_config.yml; skipped",
    "cleanup_not_run": "{name}: not run (an earlier domain failed with fail_fast)",
    "cleanup_playbook_ok": "{name}: playbook completed in {duration:.1f}s",
    "cleanup_playbook_failed": "{name}: playbook failed (rc={rc})",
    "cleanup_exec_ok": "Every enabled domain cleanup playbook completed",
    "cleanup_exec_failed": "{count} domain cleanup playbook(s) failed",
    "cleanup_verify_skip": "{name}: cleanup {status}; nothing to verify",
    "cleanup_verify_ok": "{name}: postconditions verified",
    "cleanup_verify_failed": "{name}: {count} postcondition(s) failed",
    # --- auto_cleanup ---
    "auto_cleanup_disabled": (
        "retention.auto_cleanup_enabled is false in {path}: the scheduler runs "
        "no cleanup cycle; nothing to verify"
    ),
    "auto_cleanup_settings": (
        "Retention settings: retention_age_days={retention_age_days}, "
        "min_keep_count={min_keep_count}, evaluation_interval_hours="
        "{evaluation_interval_hours}"
    ),
    "auto_cleanup_expected": (
        "Expected: FAILED phase {failed}, retention phase {retention} "
        "of {total} image group(s)"
    ),
    "auto_cleanup_noop": "No image group is eligible; verifying the pass changes nothing",
    "auto_cleanup_pass": "Running cleanup_cron.main() in omnia_build_stream",
    "auto_cleanup_wait": "Waiting for the cleanup playbook to finalize {count} group(s)",
    "auto_cleanup_pass_ok": (
        "Cleanup pass finished (rc={rc}); {count} submitted group(s) finalized"
    ),
    "auto_cleanup_pass_failed": "Cleanup pass failed: {error}",
    "auto_cleanup_ok": "Automated cleanup removed exactly the eligible image groups",
    "auto_cleanup_failed": "Automated cleanup verification failed: {count} check(s)",
}

TEST_ASSERT_MSGS: Dict[str, str] = {
    "precheck_prepare_base_failed": (
        "prepare_base precheck failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Run ./omnia.sh --setup-venv so /etc/omnia/omnia.env and the venv exist\n"
        "  2. Save the base domain credentials: ./setup_env.sh --set-domain-creds\n"
        "  3. Check clone_path in test_config.yml (remote mode)\n"
    ),
    "precheck_installation_failed": (
        "installation precheck failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Run prepare_base first; build_stream.yml --tags precheck needs it\n"
        "  2. Check installation.catalog (./omnia.sh --list-catalogs)\n"
        "  3. Save the BuildStream credentials: ./setup_env.sh --set-domain-creds "
        "--domain build_stream\n"
        "  4. Add at least two node rows to pxe_mapping_file.csv\n"
    ),
    "precheck_auto_cleanup_failed": (
        "auto_cleanup precheck failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Fix the retention group in build_stream_config.yml if reported\n"
        "  2. Check: podman ps omnia_build_stream; systemctl status playbook-watcher\n"
    ),
    "precheck_cleanup_failed": (
        "cleanup precheck failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Enable at least one block under cleanup in test_config.yml\n"
        "  2. Check clone_path and that the domain playbooks exist in the checkout\n"
    ),
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}, {duration:.1f}s). Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Review the streamed omnia.sh output above\n"
        "  2. Re-run on the OIM: cd src/main && ./omnia.sh --prepare-base\n"
    ),
    "ready_failed": (
        "{domain} is not ready after prepare_base: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Re-run: ansible-playbook {domain}.yml --tags prepare\n"
        "  2. Check the failed containers/units with podman ps -a and systemctl status\n"
    ),
    "installation_failed": (
        "BuildStream installation failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Check installation.catalog (number from ./omnia.sh --list-catalogs "
        "or full path)\n"
        "  2. Review the streamed build_stream.yml output above\n"
    ),
    "services_failed": (
        "BuildStream services are not healthy: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Check: podman ps -a; systemctl status playbook-watcher\n"
        "  2. Check: podman logs omnia_build_stream\n"
    ),
    "repository_failed": (
        "GitLab repository is incomplete: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Re-run build_stream.yml; push_ci_files.yml syncs CI and input files\n"
        "  2. A DIFFERS input was changed in GitLab or on the OIM after the sync\n"
    ),
    "build_failed": (
        "Build pipeline failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Open the failed job in GitLab CI/CD > Pipelines\n"
        "  2. Read the stage log_file_path reported above\n"
        "  3. Re-verify without committing: set pipeline.build_job_id\n"
    ),
    "deploy_failed": (
        "Deploy pipeline failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Check the deploy/restart/validate logs reported above\n"
        "  2. Ensure the image group is BUILT and offered by list_images\n"
        "  3. Re-verify without committing: set pipeline.deploy_job_id\n"
    ),
    "cadence_failed": (
        "Cadence failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. journalctl -u playbook-watcher.service --since '-2h'\n"
        "  2. Review the repo sync log and repo_resync_status.yml\n"
        "  3. Re-verify an existing run: set pipeline.cadence_job_id\n"
    ),
    "cleanup_exec_failed": (
        "Cleanup playbook failed for: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Review the streamed playbook output above\n"
        "  2. Re-run that domain's cleanup command shown in the report fields\n"
    ),
    "cleanup_verify_failed": (
        "{name} postconditions failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Compare each failed postcondition with the flags in test_config.yml\n"
        "  2. Re-run that domain's cleanup command shown in the exec report\n"
    ),
    "auto_cleanup_pass_failed": (
        "Automated cleanup pass failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. podman logs omnia_build_stream | grep -i cleanup\n"
        "  2. Check build_stream_db connectivity from omnia_build_stream\n"
    ),
    "auto_cleanup_failed": (
        "Automated cleanup failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Compare the per-group decisions logged above with the retention rules\n"
        "  2. Read the cleanup playbook log under build_stream/log/<job_id>/\n"
        "  3. podman logs omnia_build_stream | grep -i cleanup\n"
    ),
}

# Live progress lines streamed by long-running library functions.
PROGRESS_MSGS: Dict[str, str] = {
    # --- installation_func ---
    "catalog_placing": "placing catalog '{catalog}' at CATALOG_FILE_PATH",
    "playbook_running": "running {playbook}",
    "catalog_committing": "committing {file} with version {version}",
    "pipeline_auto_triggered": "pipeline #{pipeline_id} auto-triggered by the {source} commit",
    "verify_only_job": "verify-only: using job {job_id}",
    "deploy_target": "deploying image group {group_id} ({source}, status {status})",
    "pxe_rows_swapping": "swapping rows {first} and {second} of {file}",
    "trigger_script_rc": "trigger script rc={rc}",
    # --- pipeline_func ---
    "no_busy_pipelines": "no running or pending GitLab pipelines",
    "pipeline_cancel": "cancel pipeline #{pipeline_id}: {outcome}",
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
    # --- cadence_func ---
    "cadence_event": "[{event}] {message}",
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
    # --- auto_cleanup_func ---
    "cleanup_statuses": "Cleanup status: {statuses}",
}
