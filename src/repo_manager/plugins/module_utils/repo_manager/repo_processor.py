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
Single repository processor for RPM repository synchronization.
"""

import subprocess
import threading
import time
from ansible.module_utils.repo_manager.repo_logger import RepoLogger
from ansible.module_utils.repo_manager.config import get_caching_policy, POLICY_CACHING_MAP, DEFAULT_POLICY


class StepError(Exception):
    """Custom exception for step failures."""
    def __init__(self, step_num, step_name, error):
        self.step_num = step_num
        self.step_name = step_name
        self.error = error


def run_pulp_command(cmd_list, timeout):
    """
    Run a Pulp CLI command with timeout.

    Args:
        cmd_list (list): Command list to execute
        timeout (int): Timeout in seconds

    Returns:
        subprocess.CompletedProcess: Result of command execution
    """
    return subprocess.run(
        cmd_list,
        timeout=timeout,
        capture_output=True,
        text=True
    )


def check_exists(resource_type, repo_name, timeout):
    """
    Check if a Pulp resource exists.

    Args:
        resource_type (str): Type of resource (repository, remote, distribution)
        repo_name (str): Repository name
        timeout (int): Timeout in seconds

    Returns:
        bool: True if resource exists, False otherwise
    """
    try:
        if resource_type == "repository":
            cmd_list = ["pulp", "rpm", "repository", "show", "--name", repo_name]
        elif resource_type == "remote":
            cmd_list = ["pulp", "rpm", "remote", "show", "--name", repo_name]
        elif resource_type == "distribution":
            cmd_list = ["pulp", "rpm", "distribution", "show", "--name", repo_name]
        else:
            return False

        result = run_pulp_command(cmd_list, timeout)

        # For distributions, check if it has repository or publication (has content)
        if resource_type == "distribution" and result.returncode == 0:
            try:
                import json
                dist_data = json.loads(result.stdout)
                has_repo = dist_data.get("repository") is not None
                has_pub = dist_data.get("publication") is not None
                return has_repo or has_pub
            except (json.JSONDecodeError, ValueError):
                return False

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def check_repo_state(repo_name, repo_logger, timeout):
    """
    Check the current state of a repository.

    Args:
        repo_name (str): Repository name
        repo_logger (RepoLogger): Logger instance
        timeout (int): Timeout in seconds

    Returns:
        str: State of the repository (complete, partial, new)
    """
    repo_logger.log_repo(repo_name, "INFO", "Step 1/5: Check existing state")

    # Check distribution first (if exists = fully complete)
    repo_logger.log_repo(repo_name, "INFO", "  Check distribution...")
    if check_exists("distribution", repo_name, timeout):
        repo_logger.log_repo(repo_name, "INFO", "  Check distribution... EXISTS")
        repo_logger.log_repo(repo_name, "INFO", "  Result: Fully complete — nothing to do")
        return "complete"
    else:
        repo_logger.log_repo(repo_name, "INFO", "  Check distribution... NOT FOUND")

    # Check repository
    repo_logger.log_repo(repo_name, "INFO", "  Check repository...")
    if not check_exists("repository", repo_name, timeout):
        repo_logger.log_repo(repo_name, "INFO", "  Check repository... NOT FOUND")
        repo_logger.log_repo(repo_name, "INFO", "  Result: New repo — full processing needed")
        return "new"
    else:
        repo_logger.log_repo(repo_name, "INFO", "  Check repository... EXISTS")

    # Check remote
    repo_logger.log_repo(repo_name, "INFO", "  Check remote...")
    if not check_exists("remote", repo_name, timeout):
        repo_logger.log_repo(repo_name, "INFO", "  Check remote... NOT FOUND")
        repo_logger.log_repo(repo_name, "WARN", "  Result: Partially complete — resuming from Step 3/5")
        return "partial"
    else:
        repo_logger.log_repo(repo_name, "INFO", "  Check remote... EXISTS")

    repo_logger.log_repo(repo_name, "WARN", "  Result: Partially complete — resuming from Step 4/5")
    return "partial"


def process_single_repo(repo_config, repo_logger, settings, cluster_os_version="10.0", config_data=None):
    """
    Process a single repository with 5-step process and 3-state re-run handling.

    Args:
        repo_config (dict): Repository configuration
        repo_logger (RepoLogger): Logger instance
        settings (dict): Settings dictionary
        cluster_os_version (str): Cluster OS version for base path construction
        config_data (dict, optional): Full repo_manager_config.yml data for caching policy

    Returns:
        dict: Result with repo_name, status, failed_step, error, duration, is_rerun
    """
    repo_name = repo_config["package"]
    thread_name = threading.current_thread().name
    start = time.time()
    is_rerun = False
    is_subscription = repo_config.get("is_subscription", False)  # Check if subscription repo

    result = {
        "repo_name": repo_name,
        "status": "SUCCESS",
        "failed_step": None,
        "failed_step_num": None,
        "error": None,
        "duration": 0,
        "is_rerun": False
    }

    # Log START
    repo_type = "subscription" if is_subscription else "URL-based"
    repo_logger.log_repo(repo_name, "INFO", f"START REPO ({repo_type})")

    try:
        # Step 1: Check existing state
        repo_logger.log_repo(repo_name, "INFO", "Step 1/5: Check state")
        state = check_repo_state(repo_name, repo_logger, settings["pulp_timeout"])

        if state == "complete":
            result["status"] = "SKIPPED"
            repo_logger.log_repo(repo_name, "INFO", "END REPO — SKIPPED (already complete) (0s)")
            return result

        is_rerun = (state == "partial")
        result["is_rerun"] = is_rerun

        if is_rerun:
            repo_logger.log_repo(repo_name, "WARN", "Re-run detected — resuming from Step 4/5")

        # Step 2: Create repository
        repo_logger.log_repo(repo_name, "INFO", "Step 2/5: Create repository")
        if check_exists("repository", repo_name, settings["pulp_timeout"]):
            repo_logger.log_repo(repo_name, "INFO", "  Step 2/5: Create repository — SKIPPED (already exists)")
        else:
            repo_logger.log_repo(repo_name, "INFO", "  Creating repository...")
            cmd_list = ["pulp", "rpm", "repository", "create", "--name", repo_name]
            result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
            if result_cmd.returncode != 0:
                raise StepError(2, "Step 2/5: Create repository", result_cmd.stderr)
            repo_logger.log_repo(repo_name, "INFO", "  Result: CREATED")

        # Step 3: Create remote
        repo_logger.log_repo(repo_name, "INFO", "Step 3/5: Create remote")
        if check_exists("remote", repo_name, settings["pulp_timeout"]):
            repo_logger.log_repo(repo_name, "INFO", "  Step 3/5: Create remote — SKIPPED (already exists)")
        else:
            url = repo_config.get("url")

            # Handle subscription repos - skip remote creation if no URL
            if is_subscription and not url:
                repo_logger.log_repo(repo_name, "INFO", "  Step 3/5: Create remote — SKIPPED (subscription repo - uses RHEL subscription)")
            elif not url:
                raise StepError(3, "Step 3/5: Create remote", "URL not found in repo_config")
            else:
                # Resolve policy with caching support
                policy_str = repo_config.get("policy", config_data.get("repo_config", DEFAULT_POLICY))
                caching = get_caching_policy(config_data, repo_config) if config_data else True
                policy = POLICY_CACHING_MAP.get((policy_str, caching), "on_demand")

                # Log policy source
                policy_source = "per-repo" if repo_config.get("policy") else "global"
                repo_logger.log_repo(repo_name, "INFO", f"  Policy source: {policy_source}, resolved: {policy}")

                repo_logger.log_repo(repo_name, "INFO", "  Creating remote...")
                repo_logger.log_repo(repo_name, "INFO", f"  URL: {url}")
                repo_logger.log_repo(repo_name, "INFO", f"  Policy: {policy}")

                cmd_list = ["pulp", "rpm", "remote", "create", "--name", repo_name, "--url", url, "--policy", policy]

                # Add optional parameters (with @ prefix for file paths)
                if repo_config.get("client_cert"):
                    cmd_list.extend(["--client-cert", f"@{repo_config['client_cert']}"])
                if repo_config.get("client_key"):
                    cmd_list.extend(["--client-key", f"@{repo_config['client_key']}"])
                if repo_config.get("ca_cert"):
                    cmd_list.extend(["--ca-cert", f"@{repo_config['ca_cert']}"])
                    repo_logger.log_repo(repo_name, "INFO", f"  CA cert: {repo_config['ca_cert']}")

                result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
                if result_cmd.returncode != 0:
                    raise StepError(3, "Step 3/5: Create remote", result_cmd.stderr)
                repo_logger.log_repo(repo_name, "INFO", "  Result: CREATED")

        # Attach remote to repository (needed for sync to work)
        # Skip for subscription repos since they don't have remotes
        if is_subscription and not repo_config.get("url"):
            repo_logger.log_repo(repo_name, "INFO", "  Attaching remote to repository — SKIPPED (subscription repo)")
        else:
            repo_logger.log_repo(repo_name, "INFO", "  Attaching remote to repository...")
            cmd_list = ["pulp", "rpm", "repository", "update", "--name", repo_name, "--remote", repo_name]
            result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
            if result_cmd.returncode != 0:
                raise StepError(3, "Step 3/5: Attach remote to repository", result_cmd.stderr)
            repo_logger.log_repo(repo_name, "INFO", "  Remote attached to repository")

        # Step 4: Sync repository
        repo_logger.log_repo(repo_name, "INFO", "Step 4/5: Sync repository")
        # Skip sync for subscription repos since they use RHEL subscription directly
        if is_subscription and not repo_config.get("url"):
            repo_logger.log_repo(repo_name, "INFO", "  Syncing from remote — SKIPPED (subscription repo - uses RHEL subscription)")
            sync_duration = 0
            result_cmd = None  # No sync command executed
        else:
            repo_logger.log_repo(repo_name, "INFO", "  Syncing from remote...")
            cmd_list = ["pulp", "rpm", "repository", "sync", "--name", repo_name, "--remote", repo_name]
            if is_rerun:
                repo_logger.log_repo(repo_name, "INFO", "  Waiting for sync to complete (incremental)...")
            else:
                repo_logger.log_repo(repo_name, "INFO", "  Waiting for sync to complete...")

            sync_start = time.time()
            poll_interval = 30  # Log progress every 30 seconds
            last_log_time = sync_start

            # Run sync with progress monitoring
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            while True:
                # Check if process has completed
                return_code = process.poll()
                if return_code is not None:
                    stdout, stderr = process.communicate()
                    result_cmd = subprocess.CompletedProcess(
                        args=cmd_list,
                        returncode=return_code,
                        stdout=stdout,
                        stderr=stderr
                    )
                    break

                # Log progress periodically
                current_time = time.time()
                if current_time - last_log_time >= poll_interval:
                    elapsed = int(current_time - sync_start)
                    repo_logger.log_repo(repo_name, "INFO", f"  Sync in progress... ({elapsed}s elapsed)")
                    last_log_time = current_time

                # Small sleep to avoid busy waiting
                time.sleep(1)

            sync_duration = int(time.time() - sync_start)

            if result_cmd.returncode != 0:
                raise StepError(4, "Step 4/5: Sync repository", result_cmd.stderr)

        # Only log sync result if we actually performed a sync
        if not (is_subscription and not repo_config.get("url")):
            suffix = " (incremental)" if is_rerun else ""
            repo_logger.log_repo(repo_name, "INFO", f"  Result: SYNCED ({sync_duration}s){suffix}")
        else:
            repo_logger.log_repo(repo_name, "INFO", "  Result: SKIPPED (subscription repo)")

        # Step 5: Create publication + distribution
        repo_logger.log_repo(repo_name, "INFO", "Step 5/5: Create publication + distribution")

        # Publication
        repo_logger.log_repo(repo_name, "INFO", "  Creating publication...")
        cmd_list = ["pulp", "rpm", "publication", "create", "--repository", repo_name]
        result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
        if result_cmd.returncode != 0:
            raise StepError(5, "Step 5/5: Create publication", result_cmd.stderr)
        repo_logger.log_repo(repo_name, "INFO", "  Publication: CREATED")

        # Get publication href
        import json
        pub_info = json.loads(result_cmd.stdout)
        pub_href = pub_info.get("pulp_href")

        # Distribution
        sw_arch = repo_config.get("sw_arch", "x86_64")
        version = repo_config.get("version")
        package_name = repo_config["package"]

        if version and version != "null":
            base_path = f"offline_repo/cluster/{sw_arch}/rhel/{cluster_os_version}/rpms/{package_name}/{version}"
        else:
            base_path = f"offline_repo/cluster/{sw_arch}/rhel/{cluster_os_version}/rpms/{package_name}"

        # Check if distribution exists (raw check)
        repo_logger.log_repo(repo_name, "INFO", "  Creating distribution...")
        show_result = run_pulp_command(["pulp", "rpm", "distribution", "show", "--name", repo_name], settings["pulp_timeout"])

        if show_result.returncode == 0:
            # Distribution exists - update it with publication
            repo_logger.log_repo(repo_name, "INFO", "  Distribution exists - updating with publication")
            cmd_list = ["pulp", "rpm", "distribution", "update", "--name", repo_name, "--publication", pub_href]
            result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
            if result_cmd.returncode != 0:
                raise StepError(5, "Step 5/5: Update distribution", result_cmd.stderr)
            repo_logger.log_repo(repo_name, "INFO", "  Distribution: UPDATED")
        else:
            # Distribution doesn't exist - create it
            cmd_list = ["pulp", "rpm", "distribution", "create", "--name", repo_name, "--base-path", base_path, "--publication", pub_href]
            result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
            if result_cmd.returncode != 0:
                raise StepError(5, "Step 5/5: Create distribution", result_cmd.stderr)
            repo_logger.log_repo(repo_name, "INFO", "  Distribution: CREATED")

        # Get the actual base URL from Pulp
        cmd_list = ["pulp", "rpm", "distribution", "show", "--name", repo_name]
        result_cmd = run_pulp_command(cmd_list, settings["pulp_timeout"])
        if result_cmd.returncode == 0:
            dist_info = json.loads(result_cmd.stdout)
            base_url = dist_info.get("base_url", "unknown")
            repo_logger.log_repo(repo_name, "INFO", f"  Base URL: {base_url}")

        repo_logger.log_repo(repo_name, "INFO", "  Result: CREATED")

    except StepError as e:
        result["status"] = "FAILED"
        result["failed_step"] = e.step_name
        result["failed_step_num"] = e.step_num
        result["error"] = str(e.error)
        repo_logger.log_repo(repo_name, "ERROR", f"  Result: FAILED — {str(e.error)}")

        # Add fix command for common errors
        if e.step_num == 3 and "certificate" in str(e.error).lower():
            url = repo_config.get("url", "")
            ca_cert = repo_config.get("ca_cert", "")
            repo_logger.log_repo(repo_name, "ERROR", f"  Fix: pulp rpm remote create --name '{repo_name}' --url '{url}' --ca-cert '{ca_cert}'")
        elif e.step_num == 4:
            repo_logger.log_repo(repo_name, "ERROR", f"  Fix: pulp rpm repository sync --name '{repo_name}' --remote '{repo_name}'")

    except subprocess.TimeoutExpired:
        result["status"] = "FAILED"
        result["failed_step"] = "Timeout"
        result["error"] = f"Timeout after {settings['pulp_timeout']}s"
        repo_logger.log_repo(repo_name, "ERROR", f"  Result: FAILED — Timeout after {settings['pulp_timeout']}s")
        repo_logger.log_repo(repo_name, "ERROR", f"  Fix: Increase pulp_timeout or check network connectivity")

    except Exception as e:
        result["status"] = "FAILED"
        result["failed_step"] = "Unknown"
        result["error"] = str(e)
        repo_logger.log_repo(repo_name, "ERROR", f"  Result: FAILED — Unexpected error: {str(e)}")

    # Calculate duration
    duration = int(time.time() - start)
    result["duration"] = duration

    # Log END
    if result["status"] == "SUCCESS":
        suffix = " (re-run)" if is_rerun else ""
        repo_logger.log_repo(repo_name, "INFO", f"END REPO — SUCCESS{suffix} ({duration}s)")
    elif result["status"] == "FAILED":
        repo_logger.log_repo(repo_name, "ERROR", f"END REPO — FAILED at {result['failed_step']} ({duration}s)")
    else:
        repo_logger.log_repo(repo_name, "INFO", f"END REPO — {result['status']} ({duration}s)")

    return result
