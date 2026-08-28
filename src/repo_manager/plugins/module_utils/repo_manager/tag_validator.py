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
Tag validation via Pulp sync with task inspection.

CRITICAL: Exit code from sync is NOT a reliable signal for tag existence.
- Exit 0 + manifest.total=0 → tag does NOT exist
- Exit 1 + manifest.total≥1 → tag DOES exist (rate-limited or transient error)

The ONLY reliable signals are from task progress_reports:
- tag_list.state="failed"    → Image does not exist
- manifest.total=0           → Tag does not exist
- manifest.total≥1           → Tag exists (regardless of sync success/failure)
"""

import json
import logging
import re
import uuid
from time import time as current_time


def validate_tag_via_pulp_sync(image_name, tag, logger,
                                pulp_container_commands, execute_command,
                                create_container_repository,
                                get_repo_url_and_content):
    """
    Validate that a tag exists in upstream registry.

    Uses Pulp sync + task progress inspection for accuracy.
    Validation always uses on_demand policy (bandwidth optimization).

    Returns:
        bool: True if tag exists upstream, False if definitively not found.
              Returns True on ambiguous results (safe default for airgap).
    """
    unique_id = uuid.uuid4().hex[:8]
    sanitized_image = image_name.replace('/', '_').replace(':', '_')
    sanitized_tag = tag.replace('/', '_').replace('.', '_').replace('-', '_')
    temp_remote_name = f"temp_val_{sanitized_image}_{sanitized_tag}_{unique_id}"
    temp_repo_name = f"temp_repo_{sanitized_image}_{sanitized_tag}_{unique_id}"

    try:
        # Step 1: Create temp remote (always on_demand for validation)
        base_url, package_content = get_repo_url_and_content(image_name)
        create_remote_cmd = pulp_container_commands["create_container_remote"] % (
            temp_remote_name, base_url, package_content,
            "on_demand",  # Always on_demand for validation
            tag
        )
        remote_created = execute_command(create_remote_cmd, logger)
        if not remote_created:
            logger.error(
                f"Cannot create validation remote for {image_name}:{tag}. "
                f"Infrastructure failure — assuming tag is valid."
            )
            return True

        # Step 2: Create temp repository
        repo_created = create_container_repository(temp_repo_name, logger)
        if not repo_created:
            logger.error(
                f"Cannot create validation repo for {image_name}:{tag}. "
                f"Infrastructure failure — assuming tag is valid."
            )
            return True

        # Step 3: Sync (capture full output for task href extraction)
        sync_cmd = pulp_container_commands["sync_container_repository"] % (
            temp_repo_name, temp_remote_name
        )
        sync_result = execute_command(sync_cmd, logger, enhanced_error_info=True)

        # Step 4: Extract task href from output (works for success AND failure)
        task_href = _extract_task_href(sync_result)

        if not task_href:
            logger.warning(
                f"Cannot extract task href for {image_name}:{tag} — "
                f"assuming tag is valid"
            )
            return True

        # Step 5: Inspect task progress reports
        task_cmd = f"pulp task show --href {task_href}"
        task_result = execute_command(task_cmd, logger, type_json=True)

        if not task_result or not isinstance(task_result, dict):
            logger.warning(
                f"Cannot inspect task for {image_name}:{tag} — "
                f"assuming tag is valid"
            )
            return True

        task_data = task_result.get("stdout", {})
        if not isinstance(task_data, dict):
            return True

        progress_reports = task_data.get("progress_reports", [])
        error_desc = ""
        error_obj = task_data.get("error")
        if error_obj and isinstance(error_obj, dict):
            error_desc = error_obj.get("description", "")

        # Step 6: Classify based on progress reports
        is_valid, reason = _classify_tag_validation(progress_reports)

        # Step 7: Log result
        if is_valid is True:
            if reason == "tag_found_and_synced":
                logger.info(f"✓ Tag VALIDATED: {image_name}:{tag}")
            else:
                logger.warning(
                    f"⚠ Tag EXISTS but sync issue for {image_name}:{tag} "
                    f"({reason}). Detail: {error_desc}"
                )
        elif is_valid is False:
            logger.error(f"✗ Tag NOT FOUND: {image_name}:{tag} ({reason})")
        else:
            logger.warning(
                f"Ambiguous validation for {image_name}:{tag} ({reason}) — "
                f"assuming tag is valid"
            )

        return is_valid if is_valid is not None else True

    except Exception as e:
        logger.error(
            f"Validation exception for {image_name}:{tag}: {e} — "
            f"assuming tag is valid"
        )
        return True

    finally:
        _cleanup_temp_resources(
            temp_remote_name, temp_repo_name,
            pulp_container_commands, execute_command, logger
        )


def _classify_tag_validation(progress_reports):
    """
    Classify tag validation based on Pulp task progress reports.

    Returns:
        tuple: (is_valid: bool|None, reason: str)

    The ONLY reliable signals:
        tag_list.state="failed"   → Image does not exist
        manifest.total=0          → Tag does not exist
        manifest.total≥1          → Tag exists
    """
    tag_list = _find_report(progress_reports, "sync.downloading.tag_list")
    manifest = _find_report(progress_reports, "sync.processing.manifest")

    # Signal 1: Did tag list download succeed?
    if not tag_list or tag_list.get("state") != "completed":
        return False, "image_not_found"

    # Signal 2: Is there a manifest report?
    if not manifest:
        return None, "no_manifest_report"

    manifest_total = manifest.get("total", 0) or 0

    # Signal 3: manifest.total — THE definitive answer
    if manifest_total == 0:
        return False, "tag_not_found"

    if manifest_total >= 1:
        manifest_done = manifest.get("done", 0) or 0
        manifest_state = manifest.get("state", "")

        if manifest_done >= 1 and manifest_state == "completed":
            return True, "tag_found_and_synced"
        elif manifest_state == "failed":
            return True, "tag_exists_sync_failed"
        elif manifest_state == "canceled":
            return True, "tag_exists_sync_canceled"
        else:
            return True, "tag_exists"

    return None, "ambiguous"


def _find_report(progress_reports, code):
    """Find a progress report by its code field."""
    for report in progress_reports:
        if report.get("code") == code:
            return report
    return None


def _extract_task_href(sync_result):
    """
    Extract task href from Pulp CLI output.

    Works for both success and failure:
      Success: "Started background task /pulp/api/v3/tasks/UUID/\\n..Done."
      Failure: "Error: Task /pulp/api/v3/tasks/UUID/ failed: '...'"
    """
    if not isinstance(sync_result, dict):
        return None

    for field in ['stderr', 'stdout']:
        text = sync_result.get(field, '') or ''
        if isinstance(text, dict):
            continue
        match = re.search(r'(/pulp/api/v3/tasks/[a-f0-9-]+/)', str(text))
        if match:
            return match.group(1)
    return None


def _cleanup_temp_resources(temp_remote_name, temp_repo_name,
                             pulp_container_commands, execute_command, logger):
    """Clean up temporary validation resources. Always called."""
    try:
        destroy_repo_cmd = (
            f"pulp container repository destroy --name {temp_repo_name}"
        )
        execute_command(destroy_repo_cmd, logger)
    except Exception as e:
        logger.debug(f"Cleanup repo {temp_repo_name} failed: {e}")

    try:
        destroy_remote_cmd = (
            f"pulp container remote destroy --name {temp_remote_name}"
        )
        execute_command(destroy_remote_cmd, logger)
    except Exception as e:
        logger.debug(f"Cleanup remote {temp_remote_name} failed: {e}")