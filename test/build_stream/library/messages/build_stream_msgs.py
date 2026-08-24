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

All log messages and assertion messages for the build_stream FVT.
"""

from typing import Dict

# =============================================================================
# LOG MESSAGES
# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # --- GitLab Install ---
    "packages_installed": "GitLab packages installed: {packages}",
    "packages_missing": "GitLab packages missing: {packages}",
    "server_reachable": "GitLab server reachable at {host}",
    "server_unreachable": "GitLab server not reachable at {host}",
    "runner_container_ok": "gitlab-runner container running",
    "runner_container_missing": "gitlab-runner container not found",
    "quadlet_exists": "Quadlet file exists: {path}",
    "quadlet_missing": "Quadlet file not found: {path}",
    "runner_services_ok": "Runner services running: {count}/{total}",
    "runner_services_failed": "Runner services not running: {failed}",
    "url_accessible": "GitLab URL accessible: {url} (HTTP {code})",
    "url_not_accessible": "GitLab URL not accessible: {url}",
    "services_running": "GitLab services running: {count}/{total}",
    "services_not_running": "Services not running: {services}",
    "resources_ok": "Resources meet requirements",
    "resources_insufficient": "Resources insufficient: {failed}",
    "puma_workers_ok": "Puma workers: {actual} (expected {expected})",
    "puma_workers_mismatch": "Puma workers mismatch: {actual} != {expected}",
    "sidekiq_ok": "Sidekiq concurrency: {actual} (expected {expected})",
    "sidekiq_mismatch": "Sidekiq mismatch: {actual} != {expected}",
    "project_exists": "Project '{name}' exists (ID: {project_id})",
    "project_missing": "Project '{name}' not found",
    "visibility_ok": "Visibility: {actual} (expected {expected})",
    "visibility_mismatch": "Visibility mismatch: {actual} != {expected}",
    "branch_ok": "Default branch: {actual} (expected {expected})",
    "branch_mismatch": "Branch mismatch: {actual} != {expected}",
    "pipeline_file_ok": "Pipeline file exists: {file}",
    "pipeline_file_missing": "Pipeline file not found: {file}",
    "variables_ok": "Pipeline variables configured: {count}/{total}",
    "variables_missing": "Pipeline variables missing: {missing}",
    "ci_file_ok": "{file} exists in GitLab repo",
    "ci_file_missing": "{file} not found in GitLab repo",
    "omnia_env_ok": "omnia.env exists with required variables",
    "omnia_env_missing": "omnia.env not found or missing variables",
    "domain_dirs_ok": "Domain input directories found in repo",
    "domain_dirs_missing": "Domain input directories missing: {missing}",

    # --- BuildStream Health ---
    "bsm_enabled": "build_stream enabled in config",
    "bsm_disabled": "build_stream not enabled in config",
    "bsm_health_ok": "BSM API healthy: {url}",
    "bsm_health_fail": "BSM API unhealthy: {url}",
    "postgres_tables_ok": "All {count} tables found in {db}",
    "postgres_tables_missing": "Tables missing in {db}: {missing}",
    "playbook_paths_ok": "playbook_paths.yml has entries: {entries}",
    "playbook_paths_missing": "playbook_paths.yml missing entries: {missing}",
    "playbook_paths_resolved": "All playbook paths resolve to files",
    "playbook_paths_unresolved": "Playbook paths not found: {missing}",
    "venv_ok": "Shared venv exists with ansible-playbook",
    "venv_missing": "Shared venv or ansible-playbook not found",
    "tls_cert_ok": "BSM TLS certificate valid",
    "tls_cert_invalid": "BSM TLS certificate invalid or missing",
    "nfs_queue_ok": "NFS queue directory accessible and writable",
    "nfs_queue_fail": "NFS queue directory not accessible",
    "watcher_ok": "Playbook watcher service running",
    "watcher_fail": "Playbook watcher service not running",

    # --- Deploy ---
    "playbook_success": "Playbook completed (rc=0, duration={duration:.1f}s)",
    "playbook_failed": "Playbook failed (rc={rc}, duration={duration:.1f}s)",
}

# =============================================================================
# ASSERTION MESSAGES
# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
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
        "\u2551   2. Verify build_stream_config.yml settings\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "packages_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GITLAB PACKAGES NOT INSTALLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing: {packages}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "\u2551   2. Verify gitlab_host is set in build_stream_config.yml\n"
        "\u2551      Path: /opt/omnia/build_stream/input/<project>/build_stream_config.yml\n"
        "\u2551   3. Check SSH to GitLab server: ssh root@<gitlab_host>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "server_unreachable": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GITLAB SERVER UNREACHABLE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Host: {host}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify gitlab_host in build_stream_config.yml\n"
        "\u2551      Path: /opt/omnia/build_stream/input/<project>/build_stream_config.yml\n"
        "\u2551   2. Check SSH connectivity: ssh root@{host}\n"
        "\u2551   3. Verify network connectivity and firewall rules\n"
        "\u2551   4. If gitlab_host is empty, config file may be missing\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "runner_container_missing": (
        "gitlab-runner container not found on GitLab server.\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Verify on GitLab host: podman ps -a --filter name=gitlab-runner\n"
        "  3. Check gitlab_host is correct in build_stream_config.yml"
    ),
    "quadlet_missing": (
        "Quadlet file not found: {path}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Check on GitLab host: ls -la /etc/containers/systemd/gitlab-runner.container"
    ),
    "runner_services_failed": (
        "Runner services not running: {failed}\n"
        "HOW TO FIX:\n"
        "  1. On GitLab host: systemctl status gitlab-runner.service\n"
        "  2. Check logs: journalctl -u gitlab-runner.service"
    ),
    "url_not_accessible": (
        "GitLab URL not accessible: {url} (HTTP {code})\n"
        "HOW TO FIX:\n"
        "  1. Check GitLab is running on host: gitlab-ctl status\n"
        "  2. Check port: curl -kI {url}\n"
        "  3. Verify firewall allows gitlab_https_port"
    ),
    "services_not_running": (
        "GitLab services not running: {services}\n"
        "HOW TO FIX:\n"
        "  1. On GitLab host: gitlab-ctl status\n"
        "  2. Reconfigure: gitlab-ctl reconfigure\n"
        "  3. Check logs: gitlab-ctl tail"
    ),
    "resources_insufficient": (
        "Resource requirements not met: {failed}\n"
        "HOW TO FIX:\n"
        "  1. Check CPU: nproc (min 2 cores)\n"
        "  2. Check RAM: free -g (min 4 GB)\n"
        "  3. Check disk: df -BG / (min 20 GB free)"
    ),
    "puma_workers_mismatch": (
        "Puma workers: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. On GitLab host: grep worker_processes /etc/gitlab/gitlab.rb\n"
        "  2. Update and reconfigure: gitlab-ctl reconfigure"
    ),
    "sidekiq_mismatch": (
        "Sidekiq concurrency: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. On GitLab host: grep max_concurrency /etc/gitlab/gitlab.rb\n"
        "  2. Update and reconfigure: gitlab-ctl reconfigure"
    ),
    "project_missing": (
        "GitLab project '{name}' not found.\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Check gitlab_project_name in build_stream_config.yml matches\n"
        "  3. Verify on GitLab: gitlab-rails runner \"puts Project.all.map(&:name)\""
    ),
    "visibility_mismatch": (
        "Visibility: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. Update in GitLab UI: Settings > General > Visibility\n"
        "  2. Or re-run: ansible-playbook build_stream.yml --tags gitlab_install"
    ),
    "branch_mismatch": (
        "Default branch: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. Update in GitLab UI: Settings > Repository > Default branch\n"
        "  2. Verify gitlab_default_branch in build_stream_config.yml"
    ),
    "pipeline_file_missing": (
        "{file} not found in GitLab repository.\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Check GitLab repo files manually in the GitLab UI"
    ),
    "variables_missing": (
        "Pipeline variables missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Check GitLab project > Settings > CI/CD > Variables"
    ),
    "omnia_env_missing": (
        "omnia.env not found or missing required variables.\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Verify omnia.env is committed to the GitLab repo root"
    ),
    "domain_dirs_missing": (
        "Domain input directories missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags gitlab_install\n"
        "  2. Verify input/repo_manager/ and input/image_build_manager/ exist in GitLab repo"
    ),
    "bsm_disabled": (
        "build_stream not enabled in build_stream_config.yml.\n"
        "HOW TO FIX:\n"
        "  1. Check config file exists at:\n"
        "     /opt/omnia/build_stream/input/<project>/build_stream_config.yml\n"
        "  2. Set enable_build_stream: true in the config\n"
        "  3. If file missing, verify project_name and shared_path in test_config.yml"
    ),
    "bsm_health_fail": (
        "BSM API /health not healthy at {url}\n"
        "HOW TO FIX:\n"
        "  1. Check container running: podman ps --filter name=omnia_build_stream\n"
        "  2. Check container logs: podman logs omnia_build_stream\n"
        "  3. Verify build_stream_host_ip and build_stream_port in build_stream_config.yml"
    ),
    "postgres_tables_missing": (
        "Tables missing in {db}: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check container running: podman ps --filter name=omnia_postgres\n"
        "  2. Check logs: podman logs omnia_postgres\n"
        "  3. Run migrations: podman exec omnia_build_stream alembic upgrade head"
    ),
    "playbook_paths_missing": (
        "playbook_paths.yml missing entries: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check: cat <clone_path>/src/build_stream/app/playbook_paths.yml\n"
        "  2. Verify expected entries: repo_manager.yml, image_build_manager.yml"
    ),
    "playbook_paths_unresolved": (
        "Playbook paths not found on host: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Verify clone_path in test_config.yml points to correct location\n"
        "  2. Check playbook files exist at the paths listed above"
    ),
    "venv_missing": (
        "Shared venv or ansible-playbook not found.\n"
        "HOW TO FIX:\n"
        "  1. Check: ls /opt/omnia/venv/bin/ansible-playbook\n"
        "  2. If missing, run: python3 -m venv /opt/omnia/venv\n"
        "  3. Then: /opt/omnia/venv/bin/pip install ansible"
    ),
    "tls_cert_invalid": (
        "BSM TLS certificate invalid or missing.\n"
        "HOW TO FIX:\n"
        "  1. Check: ls -la /opt/omnia/build_stream/certs/tls.crt\n"
        "  2. Verify: openssl x509 -in /opt/omnia/build_stream/certs/tls.crt -noout -dates\n"
        "  3. Regenerate certificate if expired or missing"
    ),
    "nfs_queue_fail": (
        "NFS queue directory not accessible: {path}\n"
        "HOW TO FIX:\n"
        "  1. Check directory exists: ls -la {path}\n"
        "  2. Check NFS mount: mount | grep build_stream\n"
        "  3. Create if missing: mkdir -p {path}"
    ),
    "watcher_fail": (
        "Playbook watcher service not running.\n"
        "HOW TO FIX:\n"
        "  1. Check: systemctl status playbook-watcher.service\n"
        "  2. Start: systemctl start playbook-watcher.service\n"
        "  3. Logs: journalctl -u playbook-watcher.service"
    ),
}
