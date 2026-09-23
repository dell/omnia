#!/usr/bin/env python3
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

"""Cadence Manager for periodic catalog builds.

Implements the cadence polling loop that:
1. Periodically invokes repo_manager to sync packages for the cadence catalog
2. On successful sync, bumps the catalog version and pushes to GitLab
3. GitLab CI triggers the unified cadence pipeline (build + deploy)
4. Skips cadence sync when a build pipeline is already executing

Architecture:
- CadenceTimerThread runs as a daemon alongside the main request watcher
- Polling interval is configurable (default: 86400 seconds / 24 hours)
- Pipeline idle check uses the NFS processing queue presence
- Catalog version bump follows semver patch increment (e.g., 1.0 -> 1.1)
- Git operations use subprocess to commit and push cadence_catalog_rhel.json

ER Reference: ER-BSM-002 — AC-008, AC-009, AC-015
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# Cadence configuration defaults
DEFAULT_CADENCE_INTERVAL_SECONDS = 86400  # 24 hours
DEFAULT_CADENCE_CATALOG_FILENAME = "cadence_catalog_rhel.json"
DEFAULT_CADENCE_ENABLED = False

# Audit event type for cadence sync completion
CADENCE_SYNC_COMPLETED = "CADENCE_SYNC_COMPLETED"


def log_secure_info(
    level: str,
    message: str,
    identifier: Optional[str] = None,
    exc_info: bool = False,
) -> None:
    """Log information securely with optional identifier truncation.

    Args:
        level: Log level ('info', 'warning', 'error', 'debug', 'critical')
        message: Log message
        identifier: Optional identifier (first 8 chars logged)
        exc_info: If True, append current exception traceback
    """
    if identifier:
        log_message = f"{message}: {identifier[:8]}..."
    else:
        log_message = message
    log_func = getattr(logger, level)
    log_func(log_message, exc_info=exc_info)


def load_cadence_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load cadence polling configuration from YAML file.

    Args:
        config_path: Path to cadence_config.yml. If None, uses
                    CADENCE_CONFIG_PATH env var or default location.

    Returns:
        Dictionary with cadence configuration values.
    """
    if config_path is None:
        config_path = os.getenv(
            "CADENCE_CONFIG_PATH",
            os.path.join(
                os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
                "build_stream", "cadence_config.yml"
            ),
        )

    config = {
        "enabled": DEFAULT_CADENCE_ENABLED,
        "interval_seconds": DEFAULT_CADENCE_INTERVAL_SECONDS,
        "catalog_filename": DEFAULT_CADENCE_CATALOG_FILENAME,
        "gitlab_repo_path": "",
    }

    config_file = Path(config_path)
    if not config_file.exists():
        log_secure_info(
            "info",
            "Cadence config file not found, using defaults"
        )
        return config

    try:
        import yaml  # pylint: disable=import-outside-toplevel
        with open(config_file, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            log_secure_info("warning", "Cadence config is not a dictionary")
            return config

        cadence_section = data.get("cadence", data)
        config["enabled"] = bool(cadence_section.get(
            "enabled", DEFAULT_CADENCE_ENABLED
        ))
        config["interval_seconds"] = int(cadence_section.get(
            "interval_seconds", DEFAULT_CADENCE_INTERVAL_SECONDS
        ))
        config["catalog_filename"] = str(cadence_section.get(
            "catalog_filename", DEFAULT_CADENCE_CATALOG_FILENAME
        ))
        config["gitlab_repo_path"] = str(cadence_section.get(
            "gitlab_repo_path", ""
        ))

        log_secure_info(
            "info",
            f"Cadence config loaded: enabled={config['enabled']}, "
            f"interval={config['interval_seconds']}s"
        )
    except (OSError, ValueError, ImportError):
        log_secure_info(
            "error",
            "Failed to load cadence config, using defaults",
            exc_info=True,
        )

    return config


def is_pipeline_busy(processing_dir: Path) -> bool:
    """Check if a build pipeline is currently executing.

    Determines pipeline activity by checking for active requests in the
    NFS processing queue directory. If any .json files are present in
    the processing directory, a pipeline is considered active.

    Args:
        processing_dir: Path to the NFS processing queue directory.

    Returns:
        True if a build pipeline is currently executing, False otherwise.
    """
    try:
        if not processing_dir.exists():
            return False
        active_files = list(processing_dir.glob("*.json"))
        return len(active_files) > 0
    except OSError:
        log_secure_info(
            "warning",
            "Failed to check processing directory for active pipelines"
        )
        return True  # Assume busy on error (safe default)


def bump_catalog_version(catalog_path: Path) -> Optional[str]:
    """Bump the version field in the cadence catalog file.

    Increments the minor version (e.g., "1.0" -> "1.1", "1.5" -> "1.6").

    Args:
        catalog_path: Path to the cadence_catalog_rhel.json file.

    Returns:
        The new version string, or None on failure.
    """
    try:
        with open(catalog_path, "r", encoding="utf-8") as fh:
            catalog_data = json.JSONDecoder().decode(fh.read())

        catalog_section = catalog_data.get("catalog", {})
        current_version = catalog_section.get("version", "1.0")

        # Parse version (X.Y format)
        version_match = re.match(r'^(\d+)\.(\d+)$', str(current_version))
        if version_match:
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
            new_version = f"{major}.{minor + 1}"
        else:
            # Fallback: append .1 suffix
            new_version = f"{current_version}.1"

        catalog_section["version"] = new_version
        catalog_data["catalog"] = catalog_section

        with open(catalog_path, "w", encoding="utf-8") as fh:
            json.dump(catalog_data, fh, indent=2)
            fh.write("\n")

        log_secure_info(
            "info",
            f"Cadence catalog version bumped: "
            f"{current_version} -> {new_version}"
        )
        return new_version

    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        log_secure_info(
            "error",
            "Failed to bump cadence catalog version",
            exc_info=True,
        )
        return None


def git_commit_and_push(
    repo_path: str,
    catalog_filename: str,
    new_version: str,
) -> bool:
    """Commit the updated cadence catalog and push to GitLab.

    Args:
        repo_path: Path to the GitLab repository clone.
        catalog_filename: Name of the cadence catalog file.
        new_version: The new catalog version string for the commit message.

    Returns:
        True if git commit and push succeeded, False otherwise.
    """
    try:
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "BuildStream Cadence"
        env["GIT_AUTHOR_EMAIL"] = "buildstream@omnia.local"
        env["GIT_COMMITTER_NAME"] = "BuildStream Cadence"
        env["GIT_COMMITTER_EMAIL"] = "buildstream@omnia.local"

        # Stage the catalog file
        result = subprocess.run(
            ["git", "add", catalog_filename],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
            env=env,
        )
        if result.returncode != 0:
            log_secure_info(
                "error",
                f"git add failed: {result.stderr.strip()}"
            )
            return False

        # Commit
        commit_msg = (
            f"cadence: bump catalog version to {new_version}\n\n"
            f"Automated cadence sync — periodic package update"
        )
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
            env=env,
        )
        if result.returncode != 0:
            # Check if nothing to commit (no changes)
            if "nothing to commit" in result.stdout:
                log_secure_info(
                    "info",
                    "No changes to commit for cadence catalog"
                )
                return True
            log_secure_info(
                "error",
                f"git commit failed: {result.stderr.strip()}"
            )
            return False

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            shell=False,
            env=env,
        )
        if result.returncode != 0:
            log_secure_info(
                "error",
                f"git push failed: {result.stderr.strip()}"
            )
            return False

        log_secure_info(
            "info",
            f"Cadence catalog committed and pushed: v{new_version}"
        )
        return True

    except (subprocess.TimeoutExpired, OSError):
        log_secure_info(
            "error",
            "Git operation timed out or failed",
            exc_info=True,
        )
        return False


def submit_repo_sync_request(
    requests_dir: Path,
    job_id: str,
) -> bool:
    """Submit a repo_manager sync request to the NFS playbook queue.

    Creates a JSON request file in the requests directory that the
    playbook watcher will pick up and execute.

    Args:
        requests_dir: Path to the NFS playbook queue requests directory.
        job_id: Unique job ID for this cadence sync request.

    Returns:
        True if the request was submitted successfully, False otherwise.
    """
    request_data = {
        "job_id": job_id,
        "stage_name": "cadence-repo-sync",
        "playbook_path": "repo_manager.yml",
        "correlation_id": job_id,
        "extra_vars": {
            "job_id": job_id,
            "cadence_sync": True,
        },
    }

    request_filename = f"cadence-sync-{job_id}.json"
    request_path = requests_dir / request_filename

    try:
        with open(request_path, "w", encoding="utf-8") as fh:
            json.dump(request_data, fh, indent=2)

        log_secure_info(
            "info",
            "Submitted cadence repo sync request",
            job_id
        )
        return True
    except OSError:
        log_secure_info(
            "error",
            "Failed to submit cadence repo sync request",
            job_id
        )
        return False


def wait_for_sync_result(
    results_dir: Path,
    job_id: str,
    timeout_seconds: int = 3600,
    poll_interval: int = 10,
) -> Optional[Dict[str, Any]]:
    """Wait for the repo sync playbook result file.

    Polls the results directory for the expected result file.

    Args:
        results_dir: Path to the NFS playbook queue results directory.
        job_id: Job ID to match against result files.
        timeout_seconds: Maximum time to wait for result (default: 1 hour).
        poll_interval: Seconds between polls (default: 10).

    Returns:
        The result data dictionary if found, None on timeout.
    """
    request_filename = f"cadence-sync-{job_id}.json"
    result_path = results_dir / request_filename
    start_time = time.monotonic()

    while (time.monotonic() - start_time) < timeout_seconds:
        if result_path.exists():
            try:
                with open(result_path, "r", encoding="utf-8") as fh:
                    result_data = json.JSONDecoder().decode(fh.read())
                log_secure_info(
                    "info",
                    f"Cadence sync result received: "
                    f"status={result_data.get('status', 'unknown')}",
                    job_id,
                )
                return result_data
            except (json.JSONDecodeError, OSError):
                log_secure_info(
                    "error",
                    "Failed to read cadence sync result file",
                    job_id,
                )
                return None

        time.sleep(poll_interval)

    log_secure_info(
        "warning",
        f"Cadence sync result timeout after {timeout_seconds}s",
        job_id,
    )
    return None


def emit_audit_event(
    event_type: str,
    details: Dict[str, Any],
) -> None:
    """Emit an audit event for cadence operations.

    Args:
        event_type: Audit event type (e.g., CADENCE_SYNC_COMPLETED).
        details: Event details dictionary.
    """
    audit_entry = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }
    log_secure_info(
        "info",
        f"AUDIT: {event_type} — {json.dumps(audit_entry)}"
    )


class CadenceTimerThread(Thread):
    """Daemon thread that periodically triggers cadence builds.

    The cadence timer:
    1. Sleeps for the configured interval (default: 24 hours)
    2. Checks if a build pipeline is currently executing
    3. If idle, submits a repo_manager sync request
    4. Waits for sync completion
    5. On success, bumps catalog version and pushes to GitLab
    6. Emits CADENCE_SYNC_COMPLETED audit event

    Attributes:
        interval_seconds: Polling interval in seconds.
        catalog_filename: Name of the cadence catalog file in GitLab.
        gitlab_repo_path: Path to the GitLab repository clone on disk.
        requests_dir: NFS playbook queue requests directory.
        results_dir: NFS playbook queue results directory.
        processing_dir: NFS playbook queue processing directory.
        stop_event: Event to signal graceful shutdown.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        requests_dir: Path,
        results_dir: Path,
        processing_dir: Path,
    ) -> None:
        """Initialize the cadence timer thread.

        Args:
            config: Cadence configuration dictionary.
            requests_dir: Path to NFS requests directory.
            results_dir: Path to NFS results directory.
            processing_dir: Path to NFS processing directory.
        """
        super().__init__(name="CadenceTimerThread", daemon=True)
        self.interval_seconds: int = config.get(
            "interval_seconds", DEFAULT_CADENCE_INTERVAL_SECONDS
        )
        self.catalog_filename: str = config.get(
            "catalog_filename", DEFAULT_CADENCE_CATALOG_FILENAME
        )
        self.gitlab_repo_path: str = config.get("gitlab_repo_path", "")
        self.requests_dir: Path = requests_dir
        self.results_dir: Path = results_dir
        self.processing_dir: Path = processing_dir
        self.stop_event: Event = Event()

    def run(self) -> None:
        """Main cadence polling loop."""
        log_secure_info(
            "info",
            f"CadenceTimerThread started: "
            f"interval={self.interval_seconds}s, "
            f"catalog={self.catalog_filename}"
        )

        while not self.stop_event.is_set():
            # Sleep for the configured interval (interruptible)
            if self.stop_event.wait(timeout=self.interval_seconds):
                log_secure_info(
                    "info",
                    "CadenceTimerThread shutdown requested"
                )
                break

            self._execute_cadence_cycle()

        log_secure_info("info", "CadenceTimerThread stopped")

    def stop(self) -> None:
        """Signal the cadence timer to stop."""
        self.stop_event.set()

    def _execute_cadence_cycle(self) -> None:
        """Execute one cadence polling cycle."""
        log_secure_info("info", "Cadence polling cycle started")

        # Step 1: Check if pipeline is busy (AC-009)
        if is_pipeline_busy(self.processing_dir):
            log_secure_info(
                "info",
                "Cadence sync suppressed — build pipeline in progress"
            )
            return

        # Step 2-3: Sync packages via repo_manager
        job_id = self._sync_packages()
        if job_id is None:
            return

        # Step 4-6: Bump version, push, and emit audit event
        self._bump_and_push(job_id)

    def _sync_packages(self) -> Optional[str]:
        """Submit repo_manager sync and wait for completion.

        Returns:
            The job_id string on success, None on failure.
        """
        job_id = f"cadence-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        if not submit_repo_sync_request(self.requests_dir, job_id):
            log_secure_info("error", "Failed to submit cadence repo sync request")
            return None

        result = wait_for_sync_result(self.results_dir, job_id)
        if result is None:
            log_secure_info("error", "Cadence repo sync did not complete in time")
            return None

        if result.get("status") != "success":
            log_secure_info(
                "warning",
                f"Cadence repo sync failed: "
                f"{result.get('error_summary', 'unknown error')}"
            )
            return None

        return job_id

    def _bump_and_push(self, job_id: str) -> None:
        """Bump catalog version, push to GitLab, and emit audit event.

        Args:
            job_id: The cadence sync job identifier.
        """
        if not self.gitlab_repo_path:
            log_secure_info(
                "error",
                "GitLab repo path not configured for cadence builds"
            )
            return

        catalog_path = Path(self.gitlab_repo_path) / self.catalog_filename
        if not catalog_path.exists():
            log_secure_info(
                "error",
                f"Cadence catalog not found: {self.catalog_filename}"
            )
            return

        new_version = bump_catalog_version(catalog_path)
        if new_version is None:
            log_secure_info("error", "Failed to bump cadence catalog version")
            return

        if not git_commit_and_push(
            self.gitlab_repo_path, self.catalog_filename, new_version,
        ):
            log_secure_info("error", "Failed to push cadence catalog to GitLab")
            return

        emit_audit_event(
            CADENCE_SYNC_COMPLETED,
            {
                "job_id": job_id,
                "catalog_filename": self.catalog_filename,
                "new_version": new_version,
                "sync_status": "success",
            },
        )

        log_secure_info(
            "info",
            f"Cadence cycle completed: catalog {self.catalog_filename} "
            f"bumped to v{new_version}"
        )
