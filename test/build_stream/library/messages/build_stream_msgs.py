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
    "packages_missing": "GitLab packages missing: {packages}",
    "server_unreachable": "GitLab server not reachable at {host}",
    "runner_container_missing": "gitlab-runner container not found",
    "quadlet_missing": "Quadlet file not found: {path}",
    "runner_services_failed": "Runner services not running: {failed}",
    "url_not_accessible": "GitLab URL not accessible: {url}",
    "services_not_running": "Services not running: {services}",
    "resources_insufficient": "Resources insufficient: {failed}",
    "puma_workers_mismatch": "Puma workers mismatch: {actual} != {expected}",
    "sidekiq_mismatch": "Sidekiq mismatch: {actual} != {expected}",
    "project_missing": "Project '{name}' not found",
    "visibility_mismatch": "Visibility mismatch: {actual} != {expected}",
    "branch_mismatch": "Branch mismatch: {actual} != {expected}",
    "pipeline_file_missing": "Pipeline file not found: {file}",
    "variables_missing": "Pipeline variables missing: {missing}",
    "omnia_env_missing": "omnia.env not found or missing variables",
    "domain_dirs_missing": "Domain input files missing: {missing}",

    # --- BuildStream Health ---
    "bsm_disabled": "build_stream not enabled in config",
    "bsm_health_fail": "BSM API unhealthy: {url}",
    "postgres_tables_missing": "Tables missing in {db}: {missing}",
    "venv_missing": "Shared venv or ansible-playbook not found",
    "tls_cert_invalid": "BSM TLS certificate invalid or missing",
    "nfs_queue_fail": "NFS queue directory not accessible",
    "watcher_fail": "Playbook watcher service not running",

    # --- Deploy ---
    # --- GitLab Cleanup ---
    # --- BuildStream Domain Cleanup ---
    # --- Build Pipeline ---
    "job_created": "BSM job created: {job_id} (state: {state})",
    "stage_skipped": "Stage '{stage}' skipped (not in catalog)",


    # --- Prepare base ---
    "prepare_base_precheck_ok": (
        "prepare_base precheck passed: ./omnia.sh --prepare-base can run unattended"
    ),
    "prepare_base_precheck_failed": "prepare_base precheck failed: {count} check(s)",
    "entry_failed_skip": (
        "{entry_id} ({entry_title}) failed earlier in this run, so this "
        "{category} check cannot give a meaningful result. HOW TO FIX: fix the "
        "{entry_id} failure above, then re-run ./run_validation.sh "
        "fvt_build_stream {category}"
    ),
    "prepare_base_ok": "./omnia.sh --prepare-base completed in {duration:.1f}s",
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}) in {duration:.1f}s"
    ),
    "domain_ready_ok": "{domain} is ready for BuildStream",
    "domain_ready_failed": "{domain} is not ready: {count} check(s)",

    # --- Tag scenarios (precheck, prepare, execute, cleanup) ---
    "tag_playbook_ok": "build_stream.yml --tags {tag} completed in {duration:.1f}s",
    "tag_playbook_failed": "build_stream.yml --tags {tag} failed (rc={rc}) in {duration:.1f}s",
    "result_passed": "All checks passed",
    "result_failed": "Check failed: see the items marked with a cross",
    "result_no_error": "See the fields above",
}

# =============================================================================
# ASSERTION MESSAGES
# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    "packages_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GITLAB PACKAGES NOT INSTALLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing: {packages}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ansible-playbook build_stream.yml --tags execute\n"
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
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
        "  2. Verify on GitLab host: podman ps -a --filter name=gitlab-runner\n"
        "  3. Check gitlab_host is correct in build_stream_config.yml"
    ),
    "quadlet_missing": (
        "Quadlet file not found: {path}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
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
        "  2. Check the port: curl --cacert <GitLab CA> -I {url}\n"
        "     (the CA is /root/gitlab-certs/ca.crt on the GitLab host)\n"
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
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
        "  2. Check gitlab_project_name in build_stream_config.yml matches\n"
        "  3. Verify on GitLab: gitlab-rails runner \"puts Project.all.map(&:name)\""
    ),
    "visibility_mismatch": (
        "Visibility: expected {expected}, got {actual}\n"
        "HOW TO FIX:\n"
        "  1. Update in GitLab UI: Settings > General > Visibility\n"
        "  2. Or re-run: ansible-playbook build_stream.yml --tags execute"
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
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
        "  2. Check GitLab repo files manually in the GitLab UI"
    ),
    "variables_missing": (
        "Pipeline variables missing: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
        "  2. Check GitLab project > Settings > CI/CD > Variables"
    ),
    "omnia_env_missing": (
        "omnia.env not found or missing required variables.\n"
        "HOW TO FIX:\n"
        "  1. Run: ansible-playbook build_stream.yml --tags execute\n"
        "  2. Verify omnia.env is committed to the GitLab repo root"
    ),
    "domain_dirs_missing": (
        "Domain input files missing in the GitLab repo: {missing}\n"
        "HOW TO FIX:\n"
        "  1. Check the files exist in <domain data path>/input/<project>/ on the OIM\n"
        "     (the upload skips a missing file silently)\n"
        "  2. Run: ansible-playbook build_stream.yml --tags execute"
    ),
    "bsm_disabled": (
        "build_stream not enabled in build_stream_config.yml.\n"
        "HOW TO FIX:\n"
        "  1. Check config file exists at:\n"
        "     /opt/omnia/build_stream/input/<project>/build_stream_config.yml\n"
        "  2. Set enable_build_stream: true in the config\n"
        "  3. Verify OMNIA_DATA_PATH and OMNIA_PROJECT_NAME on the execution OIM"
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
        "  1. Check: ls -la /opt/omnia/build_stream/ssl/bs_cert.pem\n"
        "  2. Verify: openssl x509 -in /opt/omnia/build_stream/ssl/bs_cert.pem -noout -dates\n"
        "  3. Regenerate certificate if expired or missing"
    ),
    "nfs_queue_fail": (
        "NFS queue directory not accessible: {path}\n"
        "HOW TO FIX:\n"
        "  1. Check directory exists: ls -la /opt/omnia/build_stream/playbook_queue/\n"
        "  2. Check subdirectories: archive, processing, requests, results\n"
        "  3. Create if missing: mkdir -p /opt/omnia/build_stream/playbook_queue/"
    ),
    "watcher_fail": (
        "Playbook watcher service not running.\n"
        "HOW TO FIX:\n"
        "  1. Check: systemctl status playbook-watcher.service\n"
        "  2. Start: systemctl start playbook-watcher.service\n"
        "  3. Logs: journalctl -u playbook-watcher.service"
    ),

    # --- GitLab Cleanup ---
    # --- BuildStream Domain Cleanup ---
    # --- Build Pipeline ---
    # --- Prepare base ---
    "prepare_base_precheck_failed": (
        "prepare_base precheck failed: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Run ./omnia.sh --setup-venv so /etc/omnia/omnia.env and the venv exist\n"
        "  2. Save the base domain credentials: ./setup_env.sh --set-domain-creds\n"
        "  3. Check clone_path in test_config.yml (remote mode)"
    ),
    "prepare_base_failed": (
        "./omnia.sh --prepare-base failed (rc={rc}, {duration:.1f}s). Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Review the streamed omnia.sh output above\n"
        "  2. Re-run on the OIM: cd src/main && ./omnia.sh --prepare-base"
    ),
    "domain_ready_failed": (
        "{domain} is not ready after prepare_base: {failures}\n"
        "HOW TO FIX:\n"
        "  1. Re-run: ansible-playbook {domain}.yml --tags prepare\n"
        "  2. Check the failed containers/units: podman ps -a; systemctl status <unit>"
    ),

    # --- Tag scenarios (precheck, prepare, execute, cleanup) ---
    "tag_playbook_failed": (
        "build_stream.yml --tags {tag} failed (rc={rc}, {duration:.1f}s). Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Review the streamed playbook output above\n"
        "  2. Re-run on the OIM: cd src/build_stream/playbooks && "
        "ansible-playbook build_stream.yml --tags {tag}"
    ),
    "precheck_failed": (
        "Precheck {component} failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. Run ./omnia.sh --prepare-base so pulp, minio-server and registry run\n"
        "  2. Check /etc/omnia/omnia.env (SYSTEM_HOSTNAME, SYSTEM_DOMAIN_NAME,\n"
        "     SYSTEM_ADMIN_NIC_IPV4, OMNIA_DATA_PATH, OMNIA_PROJECT_NAME)\n"
        "  3. Export OMNIA_DATA_PATH with root_squash, then run exportfs -ra"
    ),
    "prepare_check_failed": (
        "Prepare {component} failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. Re-run: ansible-playbook build_stream.yml --tags prepare\n"
        "  2. Check: podman ps -a; systemctl status omnia_build_stream omnia_postgres "
        "playbook-watcher"
    ),
    "cleanup_check_failed": (
        "Cleanup {component} failed: {error}\n"
        "HOW TO FIX:\n"
        "  1. Re-run: ansible-playbook build_stream.yml --tags cleanup\n"
        "  2. Check what is still listening: ss -tlnp"
    ),
}
