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

"""
GitLab Project Setup Script for Omnia Pipeline

Creates or updates a GitLab project with pipeline configuration files,
input file templates sourced from the omnia src/ directory, and CI/CD
variables for cluster management.

This script does NOT install GitLab — it assumes an existing GitLab instance.

Usage:
  # Create a new project with pipeline files and input templates
  python3 setup_gitlab_project.py --create \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline \\
    --omnia-src /path/to/omnia/src \\
    --clusters cluster1,cluster2

  # Update an existing project with latest files
  python3 setup_gitlab_project.py --update \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline

  # Validate pipeline YAML via GitLab CI lint API
  python3 setup_gitlab_project.py --validate \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx

  # Update a specific file in the project
  python3 setup_gitlab_project.py --update-file \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline \\
    --file /path/to/local/.gitlab-ci-cluster.yml \\
    --repo-path .gitlab-ci-cluster.yml

  # Update a cluster input file
  python3 setup_gitlab_project.py --update-file \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline \\
    --file /path/to/omnia.env \\
    --repo-path clusters/cluster1/inputs/omnia.env \\
    --commit-message "Update omnia.env for cluster1"

  # Upload a local directory (recursive) to the repo
  python3 setup_gitlab_project.py --upload-dir \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline \\
    --dir /path/to/local/test_configs/ \\
    --repo-path clusters/cluster1/inputs/test/orchestrator/

  # List CI/CD variables (names only)
  python3 setup_gitlab_project.py --list-vars \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline

  # Delete a project
  python3 setup_gitlab_project.py --delete \\
    --gitlab-url https://gitlab.example.com \\
    --token glpat-xxxx \\
    --project-name omnia-pipeline
"""

import argparse
import getpass
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote as urlquote, urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None  # Optional — only needed when --config is used

# Suppress SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
_VALID_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9._-]{0,253}[a-zA-Z0-9])?$')
_VALID_TOKEN_RE = re.compile(r'^[a-zA-Z0-9._-]+$')
_VALID_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
_VALID_PROJECT_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')


def _validate_url(url):
    """Validate and sanitize a GitLab URL."""
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.hostname or not _VALID_HOSTNAME_RE.match(parsed.hostname):
        raise ValueError(f"Invalid hostname in URL: {url}")
    return url.rstrip("/")


def _validate_token(token):
    """Validate a GitLab API token format."""
    token = token.strip()
    if not token:
        raise ValueError("Token cannot be empty")
    if not _VALID_TOKEN_RE.match(token):
        raise ValueError("Token contains invalid characters")
    return token


def _validate_project_name(name):
    """Validate a GitLab project name."""
    name = name.strip()
    if not name:
        raise ValueError("Project name cannot be empty")
    if not _VALID_PROJECT_RE.match(name):
        raise ValueError(f"Invalid project name: {name}")
    return name


# ---------------------------------------------------------------------------
# Pipeline config file parser
# ---------------------------------------------------------------------------

def load_pipeline_config(config_path):
    """Load and parse pipeline_config.yml into a flat CI/CD variable map.

    Returns:
        (cluster_names, variables) where:
            cluster_names: list of cluster names from the config
            variables: dict of {VAR_NAME: value} ready for GitLab CI/CD
    """
    if yaml is None:
        print("ERROR: 'pyyaml' library is required for --config. Install with: pip install pyyaml")
        sys.exit(1)

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    if not cfg:
        print(f"ERROR: Config file is empty: {config_path}")
        sys.exit(1)

    # Extract global settings
    global_cfg = cfg.get("global", {}) or {}
    clusters_str = global_cfg.get("clusters", "cluster1")
    cluster_names = [c.strip() for c in clusters_str.split(",") if c.strip()]

    variables = {}
    variables["CLUSTERS"] = ",".join(cluster_names)

    # -- Global Omnia repository configuration
    omnia_cfg = global_cfg.get("omnia", {}) or {}
    if omnia_cfg.get("repo"):
        variables["OMNIA_REPO"] = omnia_cfg["repo"]
    if omnia_cfg.get("branch"):
        variables["OMNIA_BRANCH"] = omnia_cfg["branch"]
    if omnia_cfg.get("install_path"):
        variables["OMNIA_INSTALL_PATH"] = omnia_cfg["install_path"]

    # -- Global email configuration
    email_cfg = global_cfg.get("email", {}) or {}
    if email_cfg.get("recipients"):
        variables["EMAIL_RECIPIENTS"] = email_cfg["recipients"]
    if email_cfg.get("sender"):
        variables["EMAIL_SENDER"] = email_cfg["sender"]
    if email_cfg.get("smtp_server"):
        variables["SMTP_SERVER"] = email_cfg["smtp_server"]
    if email_cfg.get("smtp_port"):
        variables["SMTP_PORT"] = email_cfg["smtp_port"]

    for cluster in cluster_names:
        cluster_cfg = cfg.get(cluster)
        if not cluster_cfg:
            print(f"WARNING: No configuration section found for '{cluster}' — skipping")
            continue

        prefix = cluster.upper()

        # -- Connection details
        conn = cluster_cfg.get("connection", {}) or {}
        if conn.get("target_ip"):
            variables[f"{prefix}_TARGET_IP"] = conn["target_ip"]
        if conn.get("target_user"):
            variables[f"{prefix}_TARGET_USER"] = conn["target_user"]

        # Prompt for password at runtime (never stored in config file)
        target_ip = conn.get("target_ip", cluster)
        password = getpass.getpass(f"  Enter SSH password for {cluster} ({target_ip}): ")
        if password:
            variables[f"{prefix}_TARGET_PASS"] = password

        # -- Pipeline behaviour
        pipeline = cluster_cfg.get("pipeline", {}) or {}
        var_map = {
            "pipeline_mode": "PIPELINE_MODE",
            "domains": "DOMAINS",
            "enable_setup": "ENABLE_SETUP",
            "test_mode": "TEST_MODE",
            "dry_run": "DRY_RUN",
            "verbose": "VERBOSE",
            "skip_stages": "SKIP_STAGES",
        }
        for cfg_key, var_suffix in var_map.items():
            val = pipeline.get(cfg_key)
            if val is not None:
                variables[f"{prefix}_{var_suffix}"] = str(val)

        # -- Deploy tags
        deploy_tags = cluster_cfg.get("deploy_tags", {}) or {}
        tag_map = {
            "repo_manager": "REPO_MANAGER_TAGS",
            "image_build_manager": "IMAGE_BUILD_MANAGER_TAGS",
            "orchestrator": "ORCHESTRATOR_TAGS",
            "telemetry": "TELEMETRY_TAGS",
        }
        for cfg_key, var_suffix in tag_map.items():
            val = deploy_tags.get(cfg_key)
            if val is not None:
                variables[f"{prefix}_{var_suffix}"] = str(val)

        # -- Test tags
        test_tags = cluster_cfg.get("test_tags", {}) or {}
        test_tag_map = {
            "repo_manager": "TEST_REPO_MANAGER_TAGS",
            "image_build_manager": "TEST_IMAGE_BUILD_MANAGER_TAGS",
            "orchestrator": "TEST_ORCHESTRATOR_TAGS",
            "telemetry": "TEST_TELEMETRY_TAGS",
        }
        for cfg_key, var_suffix in test_tag_map.items():
            val = test_tags.get(cfg_key)
            if val is not None:
                variables[f"{prefix}_{var_suffix}"] = str(val)

        # -- Credential file paths (stored as File type variables)
        creds = cluster_cfg.get("credentials", {}) or {}
        cred_map = {
            "repo_manager_creds": "REPO_MANAGER_CREDS",
            "image_build_creds": "IMAGE_BUILD_CREDS",
            "orchestrator_creds": "ORCHESTRATOR_CREDS",
            "telemetry_creds": "TELEMETRY_CREDS",
            "test_creds": "TEST_CREDS",
        }
        for cfg_key, var_suffix in cred_map.items():
            val = creds.get(cfg_key)
            if val and os.path.isfile(val):
                variables[f"{prefix}_{var_suffix}"] = val

    return cluster_names, variables


# Credential variable suffixes — these use File type in GitLab
_FILE_TYPE_VARS = {
    "REPO_MANAGER_CREDS", "IMAGE_BUILD_CREDS",
    "ORCHESTRATOR_CREDS", "TELEMETRY_CREDS", "TEST_CREDS",
}


def apply_config_variables(client, project_id, variables):
    """Apply CI/CD variables from the parsed config to a GitLab project.

    File-type credential variables are uploaded with their file content.
    All other variables are set as regular env_var type.
    """
    print("\nApplying CI/CD variables from config...")
    for var_name, value in sorted(variables.items()):
        # Determine if this is a file-type credential variable
        suffix = var_name.split("_", 1)[1] if "_" in var_name else var_name
        # Check all possible suffixes (strip cluster prefix)
        is_file_var = any(var_name.endswith(f"_{s}") for s in _FILE_TYPE_VARS)

        if is_file_var and os.path.isfile(value):
            file_content = Path(value).read_text(encoding="utf-8")
            is_sensitive = "PASS" in var_name or "CREDS" in var_name
            status = client.set_variable(
                project_id, var_name, file_content,
                var_type="file", masked=False,
            )
            print(f"  {status}: {var_name} (file: {value})")
        else:
            is_sensitive = "PASS" in var_name
            display = "********" if is_sensitive and value else value
            status = client.set_variable(project_id, var_name, value)
            print(f"  {status}: {var_name} = {display}")


# ---------------------------------------------------------------------------
# GitLab API client
# ---------------------------------------------------------------------------
class GitLabClient:
    """Thin wrapper around the GitLab REST API."""

    def __init__(self, url, token, verify_ssl=False):
        self.url = url
        self.token = token
        self.verify = verify_ssl
        self._headers = {"PRIVATE-TOKEN": token}
        self._check_ssl_cert(url)

    def _check_ssl_cert(self, url):
        """Use self-signed cert file if present on the filesystem."""
        hostname = urlparse(url).hostname
        if hostname:
            cert = f"/etc/gitlab/ssl/{hostname}.crt"
            if os.path.isfile(cert):
                self.verify = cert

    # -- low-level helpers --------------------------------------------------

    def _get(self, path, **kwargs):
        return requests.get(
            f"{self.url}/api/v4{path}",
            headers=self._headers,
            verify=self.verify,
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )

    def _post(self, path, **kwargs):
        return requests.post(
            f"{self.url}/api/v4{path}",
            headers=self._headers,
            verify=self.verify,
            timeout=kwargs.pop("timeout", 60),
            **kwargs,
        )

    def _put(self, path, **kwargs):
        return requests.put(
            f"{self.url}/api/v4{path}",
            headers=self._headers,
            verify=self.verify,
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )

    def _delete(self, path, **kwargs):
        return requests.delete(
            f"{self.url}/api/v4{path}",
            headers=self._headers,
            verify=self.verify,
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )

    # -- project management -------------------------------------------------

    def find_project(self, project_path):
        """Find a project by its full path (e.g. 'root/omnia-pipeline').
        Returns project dict or None.
        """
        encoded = urlquote(project_path, safe="")
        resp = self._get(f"/projects/{encoded}")
        if resp.status_code == 200:
            return resp.json()
        return None

    def create_project(self, name, namespace_path=None):
        """Create a new project. Returns project dict or raises."""
        data = {"name": name, "path": name, "visibility": "private"}
        if namespace_path:
            ns = self._find_namespace(namespace_path)
            if ns:
                data["namespace_id"] = ns["id"]
        resp = self._post("/projects", json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        # Handle "already taken"
        if resp.status_code == 400:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if "already been taken" in json.dumps(body):
                project_path = f"{namespace_path}/{name}" if namespace_path else f"root/{name}"
                existing = self.find_project(project_path)
                if existing:
                    return existing
        raise RuntimeError(f"Failed to create project: {resp.status_code} {resp.text[:300]}")

    def _find_namespace(self, name):
        resp = self._get("/namespaces", params={"search": name})
        if resp.status_code == 200:
            for ns in resp.json():
                if ns.get("path") == name or ns.get("full_path") == name:
                    return ns
            if resp.json():
                return resp.json()[0]
        return None

    # -- file management (commits API) --------------------------------------

    def commit_files(self, project_id, actions, message, branch="main"):
        """Commit a batch of file actions (create/update/delete).
        Returns True on success.
        """
        data = {
            "branch": branch,
            "commit_message": message,
            "actions": actions,
        }
        resp = self._post(
            f"/projects/{project_id}/repository/commits",
            json=data,
            timeout=120,
        )
        if resp.status_code in (200, 201):
            return True
        raise RuntimeError(f"Commit failed: {resp.status_code} {resp.text[:300]}")

    def file_exists(self, project_id, file_path, ref="main"):
        """Check if a file exists in the repo."""
        encoded = urlquote(file_path, safe="")
        resp = self._get(
            f"/projects/{project_id}/repository/files/{encoded}",
            params={"ref": ref},
        )
        return resp.status_code == 200

    def build_file_action(self, project_id, local_path, repo_path):
        """Build a create/update action dict for a single file."""
        content = Path(local_path).read_text(encoding="utf-8")
        action_type = "update" if self.file_exists(project_id, repo_path) else "create"
        return {
            "action": action_type,
            "file_path": repo_path,
            "content": content,
        }

    def list_tree(self, project_id, path="", ref="main", recursive=True):
        """List all files under a directory in the repo.
        Returns a list of file paths (blobs only, no directories).
        """
        files = []
        page = 1
        while True:
            params = {
                "ref": ref,
                "per_page": 100,
                "page": page,
                "recursive": str(recursive).lower(),
            }
            if path:
                params["path"] = path
            resp = self._get(f"/projects/{project_id}/repository/tree", params=params)
            if resp.status_code != 200:
                break
            items = resp.json()
            if not items:
                break
            for item in items:
                if item.get("type") == "blob":
                    files.append(item["path"])
            page += 1
        return files

    # -- CI/CD variables ----------------------------------------------------

    def set_variable(self, project_id, key, value, var_type="env_var",
                     protected=False, masked=False):
        """Create or update a CI/CD variable."""
        resp = self._get(f"/projects/{project_id}/variables/{key}")
        payload = {
            "key": key,
            "value": value,
            "variable_type": var_type,
            "protected": protected,
            "masked": masked,
        }
        if resp.status_code == 200:
            resp = self._put(f"/projects/{project_id}/variables/{key}", json=payload)
            return "updated"
        else:
            resp = self._post(f"/projects/{project_id}/variables", json=payload)
            if resp.status_code in (200, 201):
                return "created"
            raise RuntimeError(f"Failed to set variable {key}: {resp.status_code} {resp.text[:200]}")

    def list_variables(self, project_id):
        """List all CI/CD variable names (no values)."""
        resp = self._get(f"/projects/{project_id}/variables", params={"per_page": 100})
        if resp.status_code == 200:
            return [v["key"] for v in resp.json()]
        return []

    # -- CI lint ------------------------------------------------------------

    def lint_ci(self, project_id, content):
        """Validate CI YAML via the project CI lint endpoint."""
        resp = self._post(
            f"/projects/{project_id}/ci/lint",
            json={"content": content},
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"CI lint failed: {resp.status_code} {resp.text[:200]}")


# ---------------------------------------------------------------------------
# File sourcing - collect files from omnia src/ tree
# ---------------------------------------------------------------------------
# Domain input files source mapping:
#   src/repo_manager/input/        -> clusters/<name>/inputs/repo_manager/
#   src/image_build_manager/input/  -> clusters/<name>/inputs/image_build_manager/
#   src/orchestrator/input/         -> clusters/<name>/inputs/orchestrator/
#   src/main/samples/catalog_rhel.json -> clusters/<name>/catalogs/catalog_rhel.json
#   src/main/omnia.env              -> clusters/<name>/inputs/omnia.env

DOMAIN_INPUT_MAP = {
    "repo_manager": "src/repo_manager/input",
    "image_build_manager": "src/image_build_manager/input",
    "orchestrator": "src/orchestrator/input",
    "telemetry": "src/telemetry/input",
}

# Test configuration files per domain.
# Maps domain -> (test_dir_in_repo, list_of_config_files_to_collect)
# These template files are sourced from test/<test_dir>/ and committed
# to clusters/<cluster>/inputs/test/<domain>/ in the GitLab repo.
DOMAIN_TEST_MAP = {
    "main": {
        "src_dir": "test/main",
        "files": ["test_config.yml", "test_run_config.yml"],
    },
    "repo_manager": {
        "src_dir": "test/repo_manager",
        "files": ["test_config.yml", "test_run_config.yml"],
    },
    "image_build_manager": {
        "src_dir": "test/image_build_manager",
        "files": ["test_config.yml", "test_run_config.yml"],
    },
    "orchestrator": {
        "src_dir": "test/orchestrator",
        "files": ["test_config.yml", "test_run_config.yml"],
    },
    "telemetry": {
        "src_dir": "test/telemetry",
        "files": ["test_config.yml", "test_run_config.yml"],
    },
}
# NOTE: test_creds.yml files contain sensitive data and are NOT committed to the repo.
# They should be set as a CI/CD File Variable (CLUSTER1_TEST_CREDS) in GitLab UI.


def _find_omnia_root(omnia_src_path):
    """Resolve the omnia root from a src path or direct root path."""
    p = Path(omnia_src_path).resolve()
    # If the user passed the src/ directory itself
    if p.name == "src" and (p / "main").is_dir():
        return p.parent
    # If the user passed the omnia root
    if (p / "src" / "main").is_dir():
        return p
    # Try parent
    if (p.parent / "src" / "main").is_dir():
        return p.parent
    raise FileNotFoundError(
        f"Cannot locate omnia repo root from: {omnia_src_path}\n"
        "Expected to find src/main/ under the given path."
    )


def collect_input_files(omnia_root, cluster_names):
    """Collect all input files from omnia src/ for each cluster.

    Returns a list of (local_path, repo_path) tuples.
    """
    files = []
    omnia_root = Path(omnia_root)

    for cluster in cluster_names:
        # Domain input files
        for domain, src_rel in DOMAIN_INPUT_MAP.items():
            src_dir = omnia_root / src_rel
            if src_dir.is_dir():
                for f in sorted(src_dir.iterdir()):
                    if f.is_file():
                        repo_path = f"clusters/{cluster}/inputs/{domain}/{f.name}"
                        files.append((str(f), repo_path))

        # Catalog files (all files from src/main/samples/)
        samples_dir = omnia_root / "src" / "main" / "samples"
        if samples_dir.is_dir():
            for f in sorted(samples_dir.iterdir()):
                if f.is_file():
                    files.append((str(f), f"clusters/{cluster}/catalogs/{f.name}"))

        # omnia.env template
        omnia_env = omnia_root / "src" / "main" / "omnia.env"
        if omnia_env.exists():
            files.append((str(omnia_env), f"clusters/{cluster}/inputs/omnia.env"))

    return files


def collect_test_files(omnia_root, cluster_names):
    """Collect test configuration template files for each domain per cluster.

    These are the test_config.yml and test_run_config.yml files that users
    customize per cluster before triggering the pipeline.
    NOTE: test_creds.yml is excluded — it is set as a CI/CD File Variable.

    Returns a list of (local_path, repo_path) tuples.
    Files are placed at: clusters/<cluster>/inputs/test/<domain>/<file>
    """
    files = []
    omnia_root = Path(omnia_root)

    for cluster in cluster_names:
        for domain, info in DOMAIN_TEST_MAP.items():
            src_dir = omnia_root / info["src_dir"]
            if not src_dir.is_dir():
                continue
            for fname in info["files"]:
                src_file = src_dir / fname
                if src_file.exists():
                    repo_path = f"clusters/{cluster}/inputs/test/{domain}/{fname}"
                    files.append((str(src_file), repo_path))

    return files


def collect_pipeline_files():
    """Collect pipeline YAML and helper files from this directory.

    Returns a list of (local_path, repo_path) tuples.
    """
    script_dir = Path(__file__).resolve().parent
    files = []
    for name, repo_name in [
        (".gitlab-ci.yml", ".gitlab-ci.yml"),
        (".gitlab-ci-cluster.yml", ".gitlab-ci-cluster.yml"),
        ("send_email.py", "send_email.py"),
        ("pipeline_config.yml", "pipeline_config.yml"),
    ]:
        fpath = script_dir / name
        if fpath.exists():
            files.append((str(fpath), repo_name))
    return files


# ---------------------------------------------------------------------------
# Dynamic cluster trigger job generation
# ---------------------------------------------------------------------------

def generate_cluster_trigger_job(cluster_name):
    """Generate a trigger job for a cluster in .gitlab-ci.yml format."""
    prefix = cluster_name.lower()
    upper_prefix = cluster_name.upper()
    return f"""trigger_cluster_{prefix}:
  stage: trigger
  trigger:
    include:
      - local: .gitlab-ci-cluster.yml
    strategy: depend
  variables:
    CLUSTER: "{prefix}"
    PIPELINE_MODE: "${{{upper_prefix}_PIPELINE_MODE}}"
    DOMAINS: "${{{upper_prefix}_DOMAINS}}"
    ENABLE_SETUP: "${{{upper_prefix}_ENABLE_SETUP}}"
    TEST_MODE: "${{{upper_prefix}_TEST_MODE}}"
    DRY_RUN: "${{{upper_prefix}_DRY_RUN}}"
    VERBOSE: "${{{upper_prefix}_VERBOSE}}"
    REPO_MANAGER_TAGS: "${{{upper_prefix}_REPO_MANAGER_TAGS}}"
    IMAGE_BUILD_MANAGER_TAGS: "${{{upper_prefix}_IMAGE_BUILD_MANAGER_TAGS}}"
    ORCHESTRATOR_TAGS: "${{{upper_prefix}_ORCHESTRATOR_TAGS}}"
    TELEMETRY_TAGS: "${{{upper_prefix}_TELEMETRY_TAGS}}"
    TEST_REPO_MANAGER_TAGS: "${{{upper_prefix}_TEST_REPO_MANAGER_TAGS}}"
    TEST_IMAGE_BUILD_MANAGER_TAGS: "${{{upper_prefix}_TEST_IMAGE_BUILD_MANAGER_TAGS}}"
    TEST_ORCHESTRATOR_TAGS: "${{{upper_prefix}_TEST_ORCHESTRATOR_TAGS}}"
    TEST_TELEMETRY_TAGS: "${{{upper_prefix}_TEST_TELEMETRY_TAGS}}"
    SKIP_STAGES: "${{{upper_prefix}_SKIP_STAGES}}"
  allow_failure: true
  rules:
    - if: '$CLUSTERS =~ /{prefix}/'
      when: on_success
"""


def generate_cluster_variables(cluster_name):
    """Generate cluster-level variables for .gitlab-ci.yml."""
    upper_prefix = cluster_name.upper()
    return f"""  {upper_prefix}_PIPELINE_MODE: "default"
  {upper_prefix}_DOMAINS: "default"
  {upper_prefix}_ENABLE_SETUP: "false"
  {upper_prefix}_TEST_MODE: "false"
  {upper_prefix}_DRY_RUN: "false"
  {upper_prefix}_VERBOSE: "false"
  {upper_prefix}_REPO_MANAGER_TAGS: ""
  {upper_prefix}_IMAGE_BUILD_MANAGER_TAGS: ""
  {upper_prefix}_ORCHESTRATOR_TAGS: ""
  {upper_prefix}_TELEMETRY_TAGS: ""
  {upper_prefix}_TEST_REPO_MANAGER_TAGS: ""
  {upper_prefix}_TEST_IMAGE_BUILD_MANAGER_TAGS: ""
  {upper_prefix}_TEST_ORCHESTRATOR_TAGS: ""
  {upper_prefix}_TEST_TELEMETRY_TAGS: ""
  {upper_prefix}_SKIP_STAGES: ""
"""


def update_gitlab_ci_yml_with_clusters(clusters):
    """Update .gitlab-ci.yml to add trigger jobs for additional clusters.
    
    Keeps cluster1 in YAML, adds cluster2+ dynamically.
    """
    script_dir = Path(__file__).resolve().parent
    gitlab_ci_path = script_dir / ".gitlab-ci.yml"
    
    if not gitlab_ci_path.exists():
        print(f"WARNING: {gitlab_ci_path} not found. Skipping YAML update.")
        return False
    
    with open(gitlab_ci_path, 'r') as f:
        content = f.read()
    
    # Find the insertion point (after cluster1 trigger job)
    marker = "trigger_cluster_cluster1:"
    if marker not in content:
        print("WARNING: Could not find trigger_cluster_cluster1 in .gitlab-ci.yml")
        return False
    
    # Find the end of cluster1 trigger job (look for next section or EOF)
    cluster1_start = content.find(marker)
    cluster1_end = content.find("\n\n", cluster1_start)
    if cluster1_end == -1:
        cluster1_end = len(content)
    
    # Generate trigger jobs for additional clusters (cluster2+)
    additional_jobs = ""
    for cluster in clusters:
        if cluster.lower() != "cluster1":
            additional_jobs += "\n" + generate_cluster_trigger_job(cluster)
    
    if additional_jobs:
        # Insert after cluster1 job
        new_content = content[:cluster1_end] + additional_jobs + content[cluster1_end:]
        
        with open(gitlab_ci_path, 'w') as f:
            f.write(new_content)
        
        print(f"  Updated .gitlab-ci.yml with trigger jobs for: {', '.join([c for c in clusters if c.lower() != 'cluster1'])}")
        return True
    
    return True


# ---------------------------------------------------------------------------
# cluster.env generation
# ---------------------------------------------------------------------------

def generate_cluster_env(cluster_name, target_ip="", target_user="root"):
    """Generate cluster.env content for a cluster."""
    prefix = cluster_name.upper()
    return (
        f'# {cluster_name} Configuration\n'
        f'# Connection details for this cluster.\n'
        f'# Sensitive credentials (TARGET_PASS) are stored as GitLab CI/CD masked variables.\n'
        f'CLUSTER_NAME="{cluster_name}"\n'
        f'TARGET_IP="{target_ip}"\n'
        f'TARGET_USER="{target_user}"\n'
        f'TARGET_PASS="${{{prefix}_TARGET_PASS}}"  '
        f'# Resolved from GitLab CI/CD variable (masked)\n'
    )


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt_cluster_details(cluster_names):
    """Prompt for target IP and user for each cluster.

    Returns dict: {cluster_name: {"ip": ..., "user": ...}}
    """
    details = {}
    for name in cluster_names:
        print(f"\n  Cluster: {name}")
        ip = input(f"    Target IP [{name}]: ").strip()
        user = input(f"    Target User [root]: ").strip() or "root"
        details[name] = {"ip": ip, "user": user}
    return details


def prompt_credentials(cluster_names, domains):
    """Prompt for credential file paths per cluster per domain.

    Returns dict: {var_name: file_path}
    Only prompts if user wants to configure credentials now.
    """
    answer = input("\nConfigure credential files now? (yes/no) [no]: ").strip().lower()
    if answer not in ("yes", "y"):
        print("  Skipping credentials. Set them later in GitLab UI: Settings > CI/CD > Variables")
        return {}

    cred_map = {
        "repo_manager": "REPO_MANAGER_CREDS",
        "image_build_manager": "IMAGE_BUILD_CREDS",
        "orchestrator": "ORCHESTRATOR_CREDS",
        "telemetry": "TELEMETRY_CREDS",
    }

    creds = {}
    for cluster in cluster_names:
        prefix = cluster.upper()
        print(f"\n  Credentials for {cluster}:")

        for domain in domains:
            var_suffix = cred_map.get(domain)
            if not var_suffix:
                continue
            var_name = f"{prefix}_{var_suffix}"
            path = input(f"    Path to {domain} credentials file [{var_name}]: ").strip()
            if path and os.path.isfile(path):
                creds[var_name] = path
            elif path:
                print(f"    WARNING: File not found: {path} — skipping")
            else:
                print(f"    Skipping {var_name}")

    return creds


# ---------------------------------------------------------------------------
# Main commands
# ---------------------------------------------------------------------------

def cmd_create(args, client):
    """Create a new GitLab project with pipeline files and input templates."""
    print("\n" + "=" * 60)
    print("Creating GitLab Project")
    print("=" * 60)

    # Resolve omnia root
    omnia_root = _find_omnia_root(args.omnia_src)
    print(f"Omnia root: {omnia_root}")

    # Parse clusters — from config file or --clusters arg
    config_vars = {}
    if args.config:
        config_cluster_names, config_vars = load_pipeline_config(args.config)
        print(f"Loaded config: {args.config}")
        cluster_names = config_cluster_names
    else:
        cluster_names = [c.strip() for c in args.clusters.split(",") if c.strip()]

    if not cluster_names:
        print("ERROR: No clusters specified. Use --clusters cluster1,cluster2 or --config pipeline_config.yml")
        return False

    domains = ["repo_manager", "image_build_manager", "orchestrator", "telemetry"]
    print(f"Clusters: {', '.join(cluster_names)}")
    print(f"Domains:  {', '.join(domains)}")

    # Create or find project
    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    existing = client.find_project(project_path)
    if existing:
        print(f"Project already exists: {existing.get('web_url', project_path)}")
        project = existing
    else:
        print(f"Creating project: {project_path}")
        project = client.create_project(project_name, namespace)
        print(f"Project created: {project.get('web_url', project_path)}")

    project_id = project["id"]

    # Collect files
    print("\nCollecting files...")
    pipeline_files = collect_pipeline_files()
    input_files = collect_input_files(omnia_root, cluster_names)
    test_files = collect_test_files(omnia_root, cluster_names)
    print(f"  Pipeline files: {len(pipeline_files)}")
    print(f"  Input files:    {len(input_files)}")
    print(f"  Test files:     {len(test_files)}")

    # Prompt for cluster details (skip if config file provides them)
    if not config_vars:
        print("\nCluster connection details:")
        cluster_details = prompt_cluster_details(cluster_names)
    else:
        cluster_details = None

    # Build commit actions
    actions = []
    file_list = []

    # Pipeline files
    for local_path, repo_path in pipeline_files:
        actions.append(client.build_file_action(project_id, local_path, repo_path))
        file_list.append(repo_path)

    # Input template files
    for local_path, repo_path in input_files:
        actions.append(client.build_file_action(project_id, local_path, repo_path))
        file_list.append(repo_path)

    # Test configuration template files
    for local_path, repo_path in test_files:
        actions.append(client.build_file_action(project_id, local_path, repo_path))
        file_list.append(repo_path)

    # NOTE: cluster.env files are NOT committed to the repo.
    # All cluster connection details are stored as CI/CD variables instead.
    # This allows dynamic cluster configuration without modifying the repository.

    # Commit all files
    print(f"\nCommitting {len(actions)} files to GitLab...")
    # Split into batches of 50 to avoid oversized commits
    batch_size = 50
    for i in range(0, len(actions), batch_size):
        batch = actions[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(actions) + batch_size - 1) // batch_size
        msg = (
            f"Add/update pipeline and input files (batch {batch_num}/{total_batches})\n\n"
            "Auto-committed by setup_gitlab_project.py"
        )
        client.commit_files(project_id, batch, msg)
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} files committed")
        if i + batch_size < len(actions):
            time.sleep(2)

    print(f"\nCommitted {len(file_list)} files:")
    for f in file_list[:20]:
        print(f"    {f}")
    if len(file_list) > 20:
        print(f"    ... and {len(file_list) - 20} more")

    # Update .gitlab-ci.yml with additional cluster trigger jobs
    if len(cluster_names) > 1:
        print("\nUpdating .gitlab-ci.yml with additional cluster jobs...")
        update_gitlab_ci_yml_with_clusters(cluster_names)

    # Configure CI/CD variables
    print("\n" + "=" * 60)
    print("Configuring CI/CD Variables")
    print("=" * 60)

    if config_vars:
        # ---- Config-file mode: apply all variables from pipeline_config.yml
        apply_config_variables(client, project_id, config_vars)

        # Also set global defaults that aren't in the config file
        global_keys = [
            ("OMNIA_REPO", "https://github.com/dell/omnia.git"),
            ("OMNIA_BRANCH", "main"),
            ("OMNIA_INSTALL_PATH", "/root/omnia"),
            ("EMAIL_RECIPIENTS", ""),
            ("EMAIL_SENDER", ""),
            ("SMTP_SERVER", ""),
            ("SMTP_PORT", "25"),
        ]
        for key, default_val in global_keys:
            if key not in config_vars:
                status = client.set_variable(project_id, key, default_val)
                print(f"  {status}: {key} = {default_val}")

    else:
        # ---- Interactive mode: prompt for details and set defaults

        # CLUSTERS variable
        clusters_val = ",".join(cluster_names)
        status = client.set_variable(project_id, "CLUSTERS", clusters_val)
        print(f"  {status}: CLUSTERS = {clusters_val}")

        # Cluster connection details (from cluster_details)
        for cluster in cluster_names:
            prefix = cluster.upper()
            details = cluster_details[cluster]
            
            var_name = f"{prefix}_TARGET_IP"
            status = client.set_variable(project_id, var_name, details["ip"])
            print(f"  {status}: {var_name} = {details['ip']}")
            
            var_name = f"{prefix}_TARGET_USER"
            status = client.set_variable(project_id, var_name, details["user"])
            print(f"  {status}: {var_name} = {details['user']}")
            
            var_name = f"{prefix}_TARGET_PASS"
            status = client.set_variable(
                project_id, var_name, "CHANGE_ME_IN_GITLAB_UI", masked=True
            )
            print(f"  {status}: {var_name} (masked, placeholder — update in GitLab UI)")

        # Global pipeline variables
        global_keys = [
            ("OMNIA_REPO", "https://github.com/dell/omnia.git"),
            ("OMNIA_BRANCH", "main"),
            ("OMNIA_INSTALL_PATH", "/root/omnia"),
            ("EMAIL_RECIPIENTS", ""),
            ("EMAIL_SENDER", ""),
            ("SMTP_SERVER", ""),
            ("SMTP_PORT", "25"),
        ]
        for key, default_val in global_keys:
            status = client.set_variable(project_id, key, default_val)
            print(f"  {status}: {key} = {default_val}")

        # Cluster-level configuration variables
        per_cluster_keys = [
            ("PIPELINE_MODE", "default"),
            ("DOMAINS", "default"),
            ("ENABLE_SETUP", "false"),
            ("TEST_MODE", "false"),
            ("DRY_RUN", "false"),
            ("VERBOSE", "false"),
            ("REPO_MANAGER_TAGS", ""),
            ("IMAGE_BUILD_MANAGER_TAGS", ""),
            ("ORCHESTRATOR_TAGS", ""),
            ("TELEMETRY_TAGS", ""),
            ("TEST_REPO_MANAGER_TAGS", ""),
            ("TEST_IMAGE_BUILD_MANAGER_TAGS", ""),
            ("TEST_ORCHESTRATOR_TAGS", ""),
            ("TEST_TELEMETRY_TAGS", ""),
            ("SKIP_STAGES", ""),
        ]
        for cluster in cluster_names:
            prefix = cluster.upper()
            for key, default_val in per_cluster_keys:
                var_name = f"{prefix}_{key}"
                status = client.set_variable(project_id, var_name, default_val)
                print(f"  {status}: {var_name} = {default_val}")

        # Credential files (optional)
        creds = prompt_credentials(cluster_names, domains)
        for var_name, file_path in creds.items():
            content = Path(file_path).read_text(encoding="utf-8")
            status = client.set_variable(
                project_id, var_name, content, var_type="file", masked=False
            )
            print(f"  {status}: {var_name} (file variable)")

    # Summary
    clusters_val = ",".join(cluster_names)
    print("\n" + "=" * 60)
    print("Setup Complete")
    print("=" * 60)
    print(f"Project URL:  {project.get('web_url', f'{client.url}/{project_path}')}")
    print(f"Clusters:     {clusters_val}")
    print(f"Files:        {len(file_list)} committed")
    if config_vars:
        print(f"Config:       {args.config}")
        print(f"Variables:    {len(config_vars)} applied from config")
    print(f"\nNext steps:")
    if not config_vars:
        print(f"  1. Update cluster passwords in GitLab UI: Settings > CI/CD > Variables")
        print(f"     Variables: {', '.join(c.upper() + '_TARGET_PASS' for c in cluster_names)}")
        print(f"  2. Set credential file variables (if not done above):")
        for cluster in cluster_names:
            prefix = cluster.upper()
            for suffix in ["REPO_MANAGER_CREDS", "IMAGE_BUILD_CREDS", "ORCHESTRATOR_CREDS", "TELEMETRY_CREDS"]:
                print(f"     - {prefix}_{suffix} (File type)")
    print(f"  {'3' if not config_vars else '1'}. Edit cluster-specific input files in the GitLab repo (clusters/<name>/inputs/)")
    print(f"  {'4' if not config_vars else '2'}. Trigger pipeline: CI/CD > Pipelines > Run pipeline")
    return True


def cmd_update(args, client):
    """Update an existing project with latest pipeline and input files."""
    print("\n" + "=" * 60)
    print("Updating GitLab Project")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        print("  Use --create to create a new project.")
        return False

    project_id = project["id"]
    print(f"Found project: {project.get('web_url', project_path)} (ID: {project_id})")

    # Collect pipeline files
    pipeline_files = collect_pipeline_files()
    actions = []
    for local_path, repo_path in pipeline_files:
        actions.append(client.build_file_action(project_id, local_path, repo_path))

    # Optionally update input files from src
    if args.omnia_src:
        omnia_root = _find_omnia_root(args.omnia_src)
        # Auto-detect clusters from existing CI/CD variable
        clusters_val = None
        try:
            resp = client._get(f"/projects/{project_id}/variables/CLUSTERS")
            if resp.status_code == 200:
                clusters_val = resp.json().get("value", "")
        except Exception:
            pass

        if args.clusters:
            cluster_names = [c.strip() for c in args.clusters.split(",") if c.strip()]
        elif clusters_val:
            cluster_names = [c.strip() for c in clusters_val.split(",") if c.strip()]
        else:
            print("WARNING: No clusters detected. Use --clusters to specify.")
            cluster_names = []

        if cluster_names:
            input_files = collect_input_files(omnia_root, cluster_names)
            for local_path, repo_path in input_files:
                actions.append(client.build_file_action(project_id, local_path, repo_path))
            print(f"  Input files refreshed for clusters: {', '.join(cluster_names)}")

            test_files = collect_test_files(omnia_root, cluster_names)
            for local_path, repo_path in test_files:
                actions.append(client.build_file_action(project_id, local_path, repo_path))
            print(f"  Test files refreshed for clusters: {', '.join(cluster_names)} ({len(test_files)} files)")

    print(f"  Committing {len(actions)} file updates...")
    client.commit_files(
        project_id, actions,
        "Update pipeline and input files\n\nAuto-committed by setup_gitlab_project.py --update"
    )
    print(f"  {len(actions)} files updated successfully")

    # Get cluster names for variable updates
    update_clusters = cluster_names if cluster_names else []
    if not update_clusters:
        # Try to read from CLUSTERS CI/CD variable
        try:
            resp = client._get(f"/projects/{project_id}/variables/CLUSTERS")
            if resp.status_code == 200:
                cv = resp.json().get("value", "")
                update_clusters = [c.strip() for c in cv.split(",") if c.strip()]
        except Exception:
            pass

    # Update .gitlab-ci.yml if clusters changed
    if update_clusters and len(update_clusters) > 1:
        print("\nUpdating .gitlab-ci.yml with cluster trigger jobs...")
        update_gitlab_ci_yml_with_clusters(update_clusters)

    # Apply CI/CD variables from config file or --update-vars
    if args.config:
        config_cluster_names, config_vars = load_pipeline_config(args.config)
        print(f"\nApplying variables from config: {args.config}")
        apply_config_variables(client, project_id, config_vars)
        print(f"  {len(config_vars)} variables applied")
    elif args.update_vars:
        print("\nUpdating CI/CD variables (defaults)...")

        # Global pipeline variables
        global_keys = [
            ("OMNIA_REPO", "https://github.com/dell/omnia.git"),
            ("OMNIA_BRANCH", "main"),
            ("OMNIA_INSTALL_PATH", "/root/omnia"),
            ("EMAIL_RECIPIENTS", ""),
            ("EMAIL_SENDER", ""),
            ("SMTP_SERVER", ""),
            ("SMTP_PORT", "25"),
        ]
        for key, default_val in global_keys:
            status = client.set_variable(project_id, key, default_val)
            print(f"  {status}: {key} = {default_val}")

        # Cluster-level configuration variables
        per_cluster_keys = [
            ("PIPELINE_MODE", "default"),
            ("DOMAINS", "default"),
            ("ENABLE_SETUP", "false"),
            ("TEST_MODE", "false"),
            ("DRY_RUN", "false"),
            ("VERBOSE", "false"),
            ("REPO_MANAGER_TAGS", ""),
            ("IMAGE_BUILD_MANAGER_TAGS", ""),
            ("ORCHESTRATOR_TAGS", ""),
            ("TELEMETRY_TAGS", ""),
            ("TEST_REPO_MANAGER_TAGS", ""),
            ("TEST_IMAGE_BUILD_MANAGER_TAGS", ""),
            ("TEST_ORCHESTRATOR_TAGS", ""),
            ("TEST_TELEMETRY_TAGS", ""),
            ("SKIP_STAGES", ""),
        ]
        for cluster in update_clusters:
            prefix = cluster.upper()
            for key, default_val in per_cluster_keys:
                var_name = f"{prefix}_{key}"
                status = client.set_variable(project_id, var_name, default_val)
                print(f"  {status}: {var_name} = {default_val}")

    print("\nUpdate complete.")
    return True


def cmd_validate(args, client):
    """Validate pipeline YAML via GitLab CI lint API."""
    print("\n" + "=" * 60)
    print("Validating Pipeline YAML")
    print("=" * 60)

    script_dir = Path(__file__).resolve().parent

    # We need a project for the lint endpoint
    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"WARNING: Project {project_path} not found. Using global lint.")
        # Fall back to global lint (may not resolve includes)
        ci_file = script_dir / ".gitlab-ci.yml"
        if not ci_file.exists():
            print("ERROR: .gitlab-ci.yml not found")
            return False
        content = ci_file.read_text()
        resp = client._post("/ci/lint", json={"content": content})
        if resp.status_code == 200:
            result = resp.json()
        else:
            print(f"ERROR: Lint API failed: {resp.status_code}")
            return False
    else:
        project_id = project["id"]
        ci_file = script_dir / ".gitlab-ci.yml"
        if not ci_file.exists():
            print("ERROR: .gitlab-ci.yml not found")
            return False
        content = ci_file.read_text()
        result = client.lint_ci(project_id, content)

    valid = result.get("valid", False)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if valid:
        print("VALID: Pipeline YAML is valid")
    else:
        print("INVALID: Pipeline YAML has errors")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    return valid


def cmd_list_vars(args, client):
    """List CI/CD variable names for a project."""
    print("\n" + "=" * 60)
    print("CI/CD Variables")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        return False

    variables = client.list_variables(project["id"])
    if variables:
        print(f"Found {len(variables)} variables:")
        for v in sorted(variables):
            print(f"  - {v}")
    else:
        print("No CI/CD variables configured.")
    return True


def cmd_update_file(args, client):
    """Update a specific file in the GitLab project repository."""
    print("\n" + "=" * 60)
    print("Updating File in GitLab Project")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        print("  Use --create to create a new project.")
        return False

    project_id = project["id"]
    print(f"Found project: {project.get('web_url', project_path)} (ID: {project_id})")

    local_path = args.file
    repo_path = args.repo_path

    # Validate local file exists
    if not os.path.isfile(local_path):
        print(f"ERROR: Local file not found: {local_path}")
        return False

    # If no repo_path specified, derive it from the local file name
    if not repo_path:
        repo_path = os.path.basename(local_path)
        print(f"  No --repo-path specified, using filename: {repo_path}")
    elif repo_path.endswith("/"):
        # repo_path is a directory — append the source filename
        repo_path = repo_path + os.path.basename(local_path)
        print(f"  --repo-path is a directory, resolved to: {repo_path}")

    print(f"  Local file:  {local_path}")
    print(f"  Repo path:   {repo_path}")

    # Read local file content
    content = Path(local_path).read_text(encoding="utf-8")

    actions = []

    # Check if a conflicting file exists at a parent path
    # e.g. if repo_path is "a/b/file.json", check if "a/b/" exists as a file (not a dir)
    # This can happen if a previous run accidentally created a file with a trailing slash
    parts = repo_path.rstrip("/").split("/")
    for i in range(1, len(parts)):
        parent = "/".join(parts[:i])
        if client.file_exists(project_id, parent):
            print(f"  WARNING: Conflicting file found at '{parent}' — deleting it first")
            actions.append({"action": "delete", "file_path": parent})
            break  # only one conflict possible per path

    # Check if file exists in repo to decide create vs update
    exists = client.file_exists(project_id, repo_path)
    action_type = "update" if exists else "create"
    print(f"  Action:      {action_type} ({'overwrite existing' if exists else 'new file'})")

    actions.append({
        "action": action_type,
        "file_path": repo_path,
        "content": content,
    })

    commit_msg = args.commit_message or f"Update {repo_path}\n\nAuto-committed by setup_gitlab_project.py --update-file"
    print(f"\nCommitting {len(actions)} action(s) for {repo_path}...")
    client.commit_files(project_id, actions, commit_msg)
    print(f"  File {action_type}d successfully: {repo_path}")

    print(f"\nFile updated in project: {project.get('web_url', project_path)}")
    return True


def cmd_upload_dir(args, client):
    """Upload all files from a local directory to a GitLab repo path."""
    print("\n" + "=" * 60)
    print("Uploading Directory to GitLab Project")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        print("  Use --create to create a new project.")
        return False

    project_id = project["id"]
    print(f"Found project: {project.get('web_url', project_path)} (ID: {project_id})")

    local_dir = args.dir
    repo_dir = args.repo_path

    # Validate local directory exists
    if not os.path.isdir(local_dir):
        print(f"ERROR: Local directory not found: {local_dir}")
        return False

    # Ensure repo_dir ends with /
    if repo_dir and not repo_dir.endswith("/"):
        repo_dir += "/"

    # If no repo_path specified, use the directory basename
    if not repo_dir:
        repo_dir = os.path.basename(local_dir.rstrip("/")) + "/"
        print(f"  No --repo-path specified, using: {repo_dir}")

    # Collect all files from the local directory (recursively)
    local_dir_path = Path(local_dir)
    collected = []
    for fpath in sorted(local_dir_path.rglob("*")):
        if fpath.is_file():
            rel = fpath.relative_to(local_dir_path)
            # Skip hidden files and common non-essential files
            if any(part.startswith(".") for part in rel.parts):
                continue
            if rel.name.endswith((".pyc", ".pyo")):
                continue
            if "__pycache__" in rel.parts:
                continue
            collected.append((str(fpath), f"{repo_dir}{rel}"))

    if not collected:
        print(f"ERROR: No files found in {local_dir}")
        return False

    print(f"  Local dir:   {local_dir}")
    print(f"  Repo dir:    {repo_dir}")
    print(f"  Files found: {len(collected)}")
    for _, repo_file in collected[:15]:
        print(f"    {repo_file}")
    if len(collected) > 15:
        print(f"    ... and {len(collected) - 15} more")

    # Build commit actions
    actions = []
    created = 0
    updated = 0
    for local_path, repo_file_path in collected:
        try:
            content = Path(local_path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"  SKIP (binary): {repo_file_path}")
            continue

        exists = client.file_exists(project_id, repo_file_path)
        action_type = "update" if exists else "create"
        if exists:
            updated += 1
        else:
            created += 1
        actions.append({
            "action": action_type,
            "file_path": repo_file_path,
            "content": content,
        })

    print(f"\n  New files:     {created}")
    print(f"  Updated files: {updated}")

    # Commit in batches
    commit_msg = args.commit_message or f"Upload directory {repo_dir}\n\nAuto-committed by setup_gitlab_project.py --upload-dir"
    batch_size = 50
    total_batches = (len(actions) + batch_size - 1) // batch_size

    print(f"\nCommitting {len(actions)} files...")
    for i in range(0, len(actions), batch_size):
        batch = actions[i:i + batch_size]
        batch_num = i // batch_size + 1
        msg = commit_msg if total_batches == 1 else f"{commit_msg} (batch {batch_num}/{total_batches})"
        client.commit_files(project_id, batch, msg)
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} files committed")
        if i + batch_size < len(actions):
            time.sleep(2)

    print(f"\n{len(actions)} files uploaded to {repo_dir} in project: {project.get('web_url', project_path)}")
    return True


def cmd_delete_dir(args, client):
    """Delete a directory and all its files from the GitLab project repo."""
    print("\n" + "=" * 60)
    print("Deleting Directory from GitLab Project")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        return False

    project_id = project["id"]
    print(f"Found project: {project.get('web_url', project_path)} (ID: {project_id})")

    repo_dir = args.repo_path
    if not repo_dir:
        print("ERROR: --repo-path is required (directory to delete)")
        return False

    # Strip trailing slash for the tree API
    repo_dir = repo_dir.rstrip("/")

    # List all files under the directory
    print(f"\n  Scanning: {repo_dir}/")
    files = client.list_tree(project_id, path=repo_dir)

    if not files:
        print(f"  No files found under {repo_dir}/ — nothing to delete")
        return True

    print(f"  Found {len(files)} file(s) to delete:")
    for f in files[:20]:
        print(f"    {f}")
    if len(files) > 20:
        print(f"    ... and {len(files) - 20} more")

    # Build delete actions
    actions = [{"action": "delete", "file_path": f} for f in files]

    commit_msg = args.commit_message or f"Delete directory {repo_dir}/\n\nAuto-committed by setup_gitlab_project.py --delete-dir"

    # Commit in batches
    batch_size = 50
    total_batches = (len(actions) + batch_size - 1) // batch_size

    print(f"\nDeleting {len(actions)} files...")
    for i in range(0, len(actions), batch_size):
        batch = actions[i:i + batch_size]
        batch_num = i // batch_size + 1
        msg = commit_msg if total_batches == 1 else f"{commit_msg} (batch {batch_num}/{total_batches})"
        client.commit_files(project_id, batch, msg)
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} files deleted")
        if i + batch_size < len(actions):
            time.sleep(2)

    print(f"\nDeleted {len(files)} files from {repo_dir}/ in project: {project.get('web_url', project_path)}")
    return True


def cmd_delete(args, client):
    """Delete a GitLab project."""
    print("\n" + "=" * 60)
    print("Deleting GitLab Project")
    print("=" * 60)

    namespace = args.namespace or "root"
    project_name = _validate_project_name(args.project_name)
    project_path = f"{namespace}/{project_name}"

    project = client.find_project(project_path)
    if not project:
        print(f"ERROR: Project not found: {project_path}")
        return False

    project_id = project["id"]
    project_url = project.get("web_url", project_path)

    # Confirmation prompt
    print(f"\nProject to delete: {project_url}")
    print(f"Project ID: {project_id}")
    print("\nWARNING: This action cannot be undone!")
    confirmation = input("Type 'DELETE' to confirm deletion: ").strip()

    if confirmation != "DELETE":
        print("Deletion cancelled.")
        return False

    # Delete the project
    print(f"\nDeleting project: {project_path}...")
    try:
        resp = client._delete(f"/projects/{project_id}")
        if resp.status_code in [200, 202, 204]:
            print(f"✓ Project deleted successfully: {project_path}")
            return True
        else:
            print(f"ERROR: Failed to delete project (HTTP {resp.status_code})")
            if resp.text:
                print(f"Response: {resp.text}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to delete project: {e}")
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    script_dir = Path(__file__).resolve().parent
    # Auto-detect omnia root (go up from test/pipeline/ to repo root)
    default_omnia_src = str(script_dir.parent.parent)

    parser = argparse.ArgumentParser(
        description="Setup GitLab project for Omnia pipeline automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Commands (mutually exclusive)
    cmd_group = parser.add_mutually_exclusive_group(required=True)
    cmd_group.add_argument("--create", action="store_true",
                           help="Create a new project with pipeline files and input templates")
    cmd_group.add_argument("--update", action="store_true",
                           help="Update an existing project with latest files")
    cmd_group.add_argument("--validate", action="store_true",
                           help="Validate pipeline YAML via GitLab CI lint API")
    cmd_group.add_argument("--list-vars", action="store_true",
                           help="List CI/CD variable names for the project")
    cmd_group.add_argument("--update-file", action="store_true",
                           help="Update a specific file in the GitLab project repo")
    cmd_group.add_argument("--upload-dir", action="store_true",
                           help="Upload all files from a local directory to the GitLab project")
    cmd_group.add_argument("--delete-dir", action="store_true",
                           help="Delete a directory and all its files from the GitLab project repo")
    cmd_group.add_argument("--delete", action="store_true",
                           help="Delete a GitLab project (requires confirmation)")

    # Connection
    parser.add_argument("--gitlab-url", required=True,
                        help="GitLab instance URL (e.g. https://gitlab.example.com)")
    parser.add_argument("--token",
                        help="GitLab Personal Access Token with 'api' scope "
                             "(prompted if not provided)")

    # Project
    parser.add_argument("--project-name", required=True,
                        help="GitLab project name (required)")
    parser.add_argument("--namespace", default="root",
                        help="GitLab namespace/group (default: root)")

    # Files
    parser.add_argument("--omnia-src", default=default_omnia_src,
                        help=f"Path to omnia repo root or src/ (default: {default_omnia_src})")
    parser.add_argument("--clusters", default="cluster1",
                        help="Comma-separated cluster names (default: cluster1)")

    # Config file
    parser.add_argument("--config",
                        help="Path to pipeline_config.yml — sets CI/CD variables from the file "
                             "instead of prompting interactively")

    # Update options
    parser.add_argument("--update-vars", action="store_true",
                        help="Also update CI/CD variables when using --update")

    # File update options (for --update-file / --upload-dir)
    parser.add_argument("--file",
                        help="Local file path to upload (required for --update-file)")
    parser.add_argument("--dir",
                        help="Local directory to upload (required for --upload-dir)")
    parser.add_argument("--repo-path",
                        help="Destination path in the GitLab repo (default: same as filename/dirname)")
    parser.add_argument("--commit-message",
                        help="Custom commit message (default: auto-generated)")

    # SSL
    parser.add_argument("--no-verify-ssl", action="store_true",
                        help="Disable SSL certificate verification (for self-signed certs)")

    args = parser.parse_args()

    # Get token
    if not args.token:
        args.token = getpass.getpass("GitLab Personal Access Token: ")
        if not args.token:
            print("ERROR: Token is required")
            sys.exit(1)

    # Validate inputs
    try:
        gitlab_url = _validate_url(args.gitlab_url)
        token = _validate_token(args.token)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Create client
    verify_ssl = not args.no_verify_ssl
    client = GitLabClient(gitlab_url, token, verify_ssl=verify_ssl)

    # Verify connectivity
    print(f"Connecting to GitLab at {gitlab_url}...")
    try:
        resp = client._get("/version")
        if resp.status_code == 200:
            version = resp.json().get("version", "unknown")
            print(f"Connected to GitLab v{version}")
        elif resp.status_code == 401:
            print("ERROR: Authentication failed. Check your token.")
            sys.exit(1)
        else:
            print(f"WARNING: Unexpected response: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {gitlab_url}")
        sys.exit(1)

    # Dispatch command
    try:
        if args.create:
            success = cmd_create(args, client)
        elif args.update:
            success = cmd_update(args, client)
        elif args.update_file:
            if not args.file:
                print("ERROR: --file is required with --update-file")
                print("  Example: --update-file --file /path/to/local/file.yml --repo-path .gitlab-ci-cluster.yml")
                sys.exit(1)
            success = cmd_update_file(args, client)
        elif args.upload_dir:
            if not args.dir:
                print("ERROR: --dir is required with --upload-dir")
                print("  Example: --upload-dir --dir /path/to/local/dir --repo-path clusters/cluster1/inputs/telemetry/")
                sys.exit(1)
            success = cmd_upload_dir(args, client)
        elif args.delete_dir:
            if not args.repo_path:
                print("ERROR: --repo-path is required with --delete-dir")
                print("  Example: --delete-dir --repo-path clusters/cluster1/inputs/test/orchestrator")
                sys.exit(1)
            success = cmd_delete_dir(args, client)
        elif args.validate:
            success = cmd_validate(args, client)
        elif args.list_vars:
            success = cmd_list_vars(args, client)
        elif args.delete:
            success = cmd_delete(args, client)
        else:
            parser.print_help()
            success = False
    except Exception as e:
        print(f"\nERROR: {e}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
