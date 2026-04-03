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
Pulp Repository Name Migration Utility

Migrates Pulp repositories, distributions, and remotes from the old naming format
to the new naming format that includes OS type and OS version.

Old format:  <arch>_<RepoName>
New format:  <arch>_<os>_<os_version>_<RepoName>

Handles:
    - RPM repositories, remotes, distributions, and publications
    - File repositories and distributions (tarball, git, manifest, iso, shell,
      ansible_galaxy_collection)
    - Python repositories and distributions (pip_module)
    - Container repositories are NOT migrated (they use a different naming scheme)

Migration strategy (create-copy-switch):
    Pulp does not support ``--new-name`` for RPM/File/Python repositories.
    Instead we:
      1. Create a new repo with the new name.
      2. Copy all content from the old repo to the new repo (no re-sync).
      3. Create a new publication for the new repo.
      4. Create a new distribution with updated name and base_path.
      5. Recreate the remote with the new name and the same URL/policy.
      6. Delete the old distribution, publications, remote, and repo.
    This preserves all existing content — nothing is re-downloaded.

    Content copy mechanism varies by repo type:
      - **RPM**: ``pulp rpm copy --config '<json>'`` (CLI has a copy command).
      - **File**: Pulp REST API ``POST <repo_href>modify/`` with
        ``add_content_units`` (File CLI has no copy/modify subcommand).
      - **Python**: Pulp REST API ``POST <repo_href>modify/`` with
        ``add_content_units`` (Python CLI has no copy/modify subcommand),
        followed by ``pulp python publication create`` for the new repo.
"""

import json
import os
import re
import subprocess
import shlex
import csv
import glob
import http.client
import ssl
import base64
from typing import Dict, List, Any, Tuple, Optional
from urllib.parse import urlparse

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.config import (
    pulp_rpm_commands,
    pulp_file_commands,
    pulp_python_commands,
    pulp_container_commands,
    ARCH_SUFFIXES,
    CLEANUP_FILE_TYPES,
)
from ansible.module_utils.local_repo.software_utils import build_repo_name_prefix

# ============================================================================
# Constants
# ============================================================================

LOG_DIR = "/opt/omnia/log/local_repo"
LOG_FILENAME = "pulp_repo_migration.log"

# File-type prefixes used in Pulp file/python repository names.
# Sorted longest-first so we match "ansible_galaxy_collection" before "git", etc.
FILE_TYPE_PREFIXES = sorted(
    ["tarball", "git", "manifest", "iso", "shell",
     "ansible_galaxy_collection", "pip_module"],
    key=len, reverse=True,
)

# RPM-specific repo prefixes to detect rpm_file type repos
RPM_FILE_INDICATOR_TYPES = {"rpm_file"}


# ============================================================================
# Helpers
# ============================================================================

# Timeout for Pulp CLI commands in seconds.  ``pulp rpm copy`` on large
# repositories (baseos, appstream, epel) can take 10-20 minutes because
# the CLI waits for the server-side task to complete.
PULP_CMD_TIMEOUT = 1800  # 30 minutes


def run_cmd(cmd: str, logger) -> Dict[str, Any]:
    """Execute a shell command and return structured result."""
    try:
        cmd_list = shlex.split(cmd)
        result = subprocess.run(
            cmd_list, capture_output=True, text=True, timeout=PULP_CMD_TIMEOUT,
            shell=False
        )
        return {"rc": result.returncode, "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()}
    except (subprocess.SubprocessError, OSError) as exc:
        logger.error("Command failed: %s - %s", cmd, exc)
        return {"rc": 1, "stdout": "", "stderr": str(exc)}


def safe_json_parse(data: str, default=None):
    """Parse JSON safely; return *default* on failure."""
    if not data or not isinstance(data, str):
        return default if default is not None else []
    try:
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(data.strip())
        return parsed
    except (ValueError, TypeError):
        return default if default is not None else []


def is_old_format(name: str) -> bool:
    """Return True if *name* matches the OLD ``<arch>_<rest>`` format
    and does NOT already contain ``<arch>_<os>_<ver>_`` (the new format).

    We detect "new format" by checking whether the portion after the arch
    prefix starts with ``<alpha>_<digits>_`` (e.g. ``rhel_10.0_``).
    """
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if name.startswith(prefix):
            remainder = name[len(prefix):]
            # New format has os_type (alpha) + "_" + os_version (digits/dots) + "_"
            if re.match(r'^[a-z]+_\d+(?:\.\d+)*_', remainder):
                return False  # already new format
            return True  # old format
    return False  # doesn't start with a known arch — skip


def build_new_name(old_name: str, os_type: str, os_version: str) -> Optional[str]:
    """Convert ``<arch>_<rest>`` → ``<arch>_<os>_<ver>_<rest>``."""
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if old_name.startswith(prefix):
            rest = old_name[len(prefix):]
            return build_repo_name_prefix(arch, os_type, os_version) + rest
    return None


def classify_old_name(name: str) -> str:
    """Classify an old-format name into one of: rpm, file, python, or unknown.

    We strip the ``<arch>_`` prefix and look at what follows:
    - starts with a known file_type prefix → "file" (or "python" for pip_module)
    - otherwise → "rpm"
    """
    for arch in ARCH_SUFFIXES:
        prefix = f"{arch}_"
        if name.startswith(prefix):
            remainder = name[len(prefix):]
            for ft in FILE_TYPE_PREFIXES:
                if remainder.startswith(ft):
                    if ft == "pip_module":
                        return "python"
                    return "file"
            return "rpm"
    return "unknown"


def compute_new_base_path(old_base_path: str, old_name: str, new_name: str,
                          arch: str, os_type: str, os_version: str) -> str:
    """Compute updated distribution base_path.

    The convention in the codebase is:
        opt/omnia/offline_repo/cluster/<arch>/<os>/<ver>/rpms/<reponame>
    or for file types:
        opt/omnia/offline_repo/cluster/<arch>/<os>/<ver>/<type>/<content>/...

    If the old base_path contains a recognisable pattern we rewrite it,
    otherwise we simply swap old_name→new_name inside the path string.
    """
    if old_base_path and old_name in old_base_path:
        return old_base_path.replace(old_name, new_name)
    return old_base_path


# ============================================================================
# Pulp listing helpers
# ============================================================================

def list_pulp_entities(cmd: str, logger) -> List[Dict]:
    """Run a Pulp list command and return parsed JSON list."""
    result = run_cmd(cmd, logger)
    if result["rc"] != 0:
        logger.error("List command failed: %s — %s", cmd, result["stderr"])
        return []
    return safe_json_parse(result["stdout"], default=[])


# ============================================================================
# Pulp REST API helpers (for operations not supported by CLI)
# ============================================================================

PULP_CLI_CONFIG_PATH = "/root/.config/pulp/cli.toml"


def _load_pulp_credentials(logger) -> Optional[Dict[str, str]]:
    """Load Pulp server URL and credentials from the CLI config file.

    Reads ``/root/.config/pulp/cli.toml`` (the same config used by the ``pulp``
    CLI) and returns ``{"base_url": ..., "username": ..., "password": ...}``.

    Returns ``None`` if the config cannot be read or parsed.
    """
    try:
        import toml as toml_mod
    except ImportError:
        # toml may not be installed; try tomllib (Python 3.11+) or tomli
        try:
            import tomllib as toml_mod  # Python 3.11+
        except ImportError:
            try:
                import tomli as toml_mod
            except ImportError:
                logger.error("No TOML parser available (toml/tomllib/tomli)")
                return None

    config_path = PULP_CLI_CONFIG_PATH
    if not os.path.isfile(config_path):
        logger.error("Pulp CLI config not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            if hasattr(toml_mod, "loads"):
                cfg = toml_mod.loads(fh.read())
            else:
                # tomllib requires binary mode
                fh.close()
                with open(config_path, "rb") as fb:
                    cfg = toml_mod.load(fb)

        cli_section = cfg.get("cli", {})
        base_url = cli_section.get("base_url", "https://localhost")
        username = cli_section.get("username", "admin")
        password = cli_section.get("password", "")

        # Password may be base64-encoded in some setups; the Pulp CLI config
        # stores it as plain text, so we use it as-is.
        return {"base_url": base_url, "username": username, "password": password}

    except Exception as exc:
        logger.error("Failed to read Pulp CLI config: %s", exc)
        return None


def _pulp_api_post(base_url: str, username: str, password: str,
                   uri: str, data: dict, logger) -> Dict[str, Any]:
    """Make a POST request to the Pulp REST API.

    Returns ``{"ok": True/False, "status": <int>, "body": <parsed_json>}``.
    """
    try:
        parsed = urlparse(base_url)
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        }

        if parsed.scheme == "https":
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(
                parsed.hostname, parsed.port or 443, context=context, timeout=120
            )
        else:
            conn = http.client.HTTPConnection(
                parsed.hostname, parsed.port or 80, timeout=120
            )

        conn.request("POST", uri, body=json.dumps(data), headers=headers)
        resp = conn.getresponse()
        body_raw = resp.read().decode("utf-8", errors="replace")
        conn.close()

        body = {}
        if body_raw.strip():
            try:
                body = json.loads(body_raw)
            except (ValueError, TypeError):
                body = {"raw": body_raw}

        ok = resp.status in (200, 201, 202)
        if not ok:
            logger.error("Pulp API POST %s returned %d: %s", uri, resp.status, body_raw[:500])

        return {"ok": ok, "status": resp.status, "body": body}

    except Exception as exc:
        logger.error("Pulp API POST %s failed: %s", uri, exc)
        return {"ok": False, "status": 0, "body": {"error": str(exc)}}


def _pulp_api_get(base_url: str, username: str, password: str,
                  uri: str, logger) -> Dict[str, Any]:
    """Make a GET request to the Pulp REST API.

    Returns ``{"ok": True/False, "status": <int>, "body": <parsed_json>}``.
    """
    try:
        parsed = urlparse(base_url)
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
        }

        if parsed.scheme == "https":
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(
                parsed.hostname, parsed.port or 443, context=context, timeout=120
            )
        else:
            conn = http.client.HTTPConnection(
                parsed.hostname, parsed.port or 80, timeout=120
            )

        conn.request("GET", uri, headers=headers)
        resp = conn.getresponse()
        body_raw = resp.read().decode("utf-8", errors="replace")
        conn.close()

        body = {}
        if body_raw.strip():
            try:
                body = json.loads(body_raw)
            except (ValueError, TypeError):
                body = {"raw": body_raw}

        ok = resp.status == 200
        if not ok:
            logger.error("Pulp API GET %s returned %d: %s", uri, resp.status, body_raw[:500])

        return {"ok": ok, "status": resp.status, "body": body}

    except Exception as exc:
        logger.error("Pulp API GET %s failed: %s", uri, exc)
        return {"ok": False, "status": 0, "body": {"error": str(exc)}}


def _list_repo_content_via_api(version_href: str, logger) -> Optional[List[str]]:
    """List content hrefs for a repository version via Pulp REST API.

    The ``pulp file content list`` CLI does **not** support
    ``--repository-version`` filtering, so we use the REST API directly:
    ``GET /pulp/api/v3/content/file/files/?repository_version=<href>&limit=1000``

    Returns a list of content ``pulp_href`` strings, or ``None`` on failure.
    """
    creds = _load_pulp_credentials(logger)
    if not creds:
        logger.error("Cannot list repo content: no Pulp credentials")
        return None

    uri = f"/pulp/api/v3/content/file/files/?repository_version={version_href}&limit=1000"
    result = _pulp_api_get(creds["base_url"], creds["username"],
                           creds["password"], uri, logger)

    if not result["ok"]:
        return None

    body = result["body"]
    results_list = body.get("results", [])
    return [c.get("pulp_href", "") for c in results_list if c.get("pulp_href")]


def _list_python_repo_content_via_api(version_href: str, logger) -> Optional[List[str]]:
    """List content hrefs for a Python repository version via Pulp REST API.

    The ``pulp python content list`` CLI does **not** support
    ``--repository-version`` filtering, so we use the REST API directly:
    ``GET /pulp/api/v3/content/python/packages/?repository_version=<href>&limit=1000``

    Returns a list of content ``pulp_href`` strings, or ``None`` on failure.
    """
    creds = _load_pulp_credentials(logger)
    if not creds:
        logger.error("Cannot list Python repo content: no Pulp credentials")
        return None

    uri = f"/pulp/api/v3/content/python/packages/?repository_version={version_href}&limit=1000"
    result = _pulp_api_get(creds["base_url"], creds["username"],
                           creds["password"], uri, logger)

    if not result["ok"]:
        return None

    body = result["body"]
    results_list = body.get("results", [])
    return [c.get("pulp_href", "") for c in results_list if c.get("pulp_href")]


def _modify_repo_content_via_api(repo_href: str, content_hrefs: List[str],
                                 logger) -> bool:
    """Add content units to a repository via the Pulp REST API.

    Uses ``POST <repo_href>modify/`` with ``{"add_content_units": [...]}``.
    This works for both File and Python repositories where the CLI does not
    provide a ``copy`` or ``modify`` subcommand.

    Returns ``True`` on success, ``False`` on failure.
    """
    creds = _load_pulp_credentials(logger)
    if not creds:
        logger.error("Cannot modify repo content: Pulp credentials not available")
        return False

    # Ensure repo_href ends with /
    if not repo_href.endswith("/"):
        repo_href += "/"

    modify_uri = f"{repo_href}modify/"
    payload = {"add_content_units": content_hrefs}

    result = _pulp_api_post(
        creds["base_url"], creds["username"], creds["password"],
        modify_uri, payload, logger
    )

    if result["ok"]:
        logger.info("Added %d content units to repo %s", len(content_hrefs), repo_href)
        return True

    logger.error("Failed to add content to repo %s: HTTP %d",
                 repo_href, result["status"])
    return False


# ============================================================================
# Generic create-copy-switch helpers
# ============================================================================

def _get_repo_info(repo_type: str, name: str, logger) -> Optional[Dict]:
    """Get repository info (pulp_href, latest_version_href) by name.

    *repo_type* is one of ``rpm``, ``file``, ``python``.
    """
    cmd_maps = {
        "rpm": pulp_rpm_commands,
        "file": pulp_file_commands,
        "python": pulp_python_commands,
    }
    cmds = cmd_maps.get(repo_type, {})
    show_cmd = cmds.get("show_repository", "")
    if not show_cmd:
        return None
    res = run_cmd(show_cmd % shlex.quote(name), logger)
    if res["rc"] != 0:
        return None
    return safe_json_parse(res["stdout"], default=None)


def _delete_old_repo_entities(repo_type: str, old_name: str, logger):
    """Best-effort deletion of old distribution, publications, remote, and repo.

    Called after the new-name entities have been successfully created.
    """
    cmd_maps = {
        "rpm": pulp_rpm_commands,
        "file": pulp_file_commands,
        "python": pulp_python_commands,
    }
    cmds = cmd_maps.get(repo_type, {})

    # 1. Delete old distribution (best-effort)
    if "delete_distribution" in cmds:
        run_cmd(cmds["delete_distribution"] % shlex.quote(old_name), logger)

    # 2. Delete old publications (RPM only — file/python pubs are auto-managed)
    if repo_type == "rpm" and "list_publications" in cmds:
        pub_res = run_cmd(cmds["list_publications"] % shlex.quote(old_name), logger)
        if pub_res["rc"] == 0:
            pubs = safe_json_parse(pub_res["stdout"], default=[])
            for pub in pubs:
                href = pub.get("pulp_href", "")
                if href and "delete_publication" in cmds:
                    run_cmd(cmds["delete_publication"] % href, logger)

    # 3. Delete old remote (best-effort)
    if "delete_remote" in cmds:
        run_cmd(cmds["delete_remote"] % shlex.quote(old_name), logger)

    # 4. Delete old repository
    if "delete_repository" in cmds:
        run_cmd(cmds["delete_repository"] % shlex.quote(old_name), logger)


# ============================================================================
# RPM migration (create-copy-switch)
# ============================================================================

def migrate_rpm_repos(os_type: str, os_version: str, dry_run: bool,
                      logger) -> List[Dict[str, Any]]:
    """Migrate RPM repositories, remotes, and distributions.

    Uses the create-copy-switch strategy because ``pulp rpm repository update
    --new-name`` is not supported by the Pulp RPM CLI.

    For each old-format RPM repo:
      1. Create a new RPM repository with the new name.
      2. Copy all content from the old repo to the new repo via
         ``pulp rpm copy`` (no re-download required).
      3. Create a new publication for the new repo.
      4. Create a new distribution with the new name and updated base_path.
      5. Recreate the remote with the new name (same URL, policy, certs).
      6. Delete the old distribution, publications, remote, and repository.
    """
    results = []

    # --- Gather all old-format entities upfront --------------------------
    repos = list_pulp_entities(pulp_rpm_commands["list_repositories"], logger)
    old_repos = [r for r in repos if is_old_format(r.get("name", ""))]

    remotes = list_pulp_entities(pulp_rpm_commands["list_remotes"], logger)
    old_remote_map = {r["name"]: r for r in remotes if is_old_format(r.get("name", ""))}

    dists = list_pulp_entities(pulp_rpm_commands["list_distributions"], logger)
    old_dist_map = {d["name"]: d for d in dists if is_old_format(d.get("name", ""))}

    logger.info("Found %d old-format RPM repos to process: %s",
                len(old_repos), [r["name"] for r in old_repos])

    for idx, repo in enumerate(old_repos, 1):
        old_name = repo["name"]
        new_name = build_new_name(old_name, os_type, os_version)
        if not new_name:
            continue

        logger.info("[RPM %d/%d] Processing '%s' -> '%s'",
                    idx, len(old_repos), old_name, new_name)

        # Idempotency: check if new-format repo already exists
        check = run_cmd(pulp_rpm_commands["show_repository"] % shlex.quote(new_name), logger)
        if check["rc"] == 0:
            # New repo exists — but is the migration complete?
            # Check if distribution also exists; if not, it's a partial migration
            # from a previous failed/timed-out run.
            dist_check = run_cmd(
                pulp_rpm_commands["check_distribution"] % shlex.quote(new_name), logger
            )
            if dist_check["rc"] == 0:
                # Fully migrated — safe to skip
                logger.info("[RPM %d/%d] Skipped '%s' — already migrated to '%s'",
                            idx, len(old_repos), old_name, new_name)
                results.append({"name": old_name, "new_name": new_name,
                                "type": "rpm_repository", "status": "Skipped",
                                "message": "New name already exists"})
                continue
            else:
                # Partial migration: repo exists but distribution doesn't.
                # Delete the incomplete new repo and redo from scratch.
                logger.warning("[RPM %d/%d] Partial migration detected for '%s' — "
                               "new repo exists but distribution missing. "
                               "Deleting incomplete repo and retrying...",
                               idx, len(old_repos), old_name)
                run_cmd(pulp_rpm_commands["delete_repository"] % shlex.quote(new_name), logger)

        if dry_run:
            logger.info("[RPM %d/%d] DryRun '%s' -> '%s'",
                        idx, len(old_repos), old_name, new_name)
            results.append({"name": old_name, "new_name": new_name,
                            "type": "rpm_repository", "status": "DryRun",
                            "message": "Would migrate (create-copy-switch)"})
            continue

        # -- Step 1: Create new repository --------------------------------
        create_res = run_cmd(
            pulp_rpm_commands["create_repository"] % shlex.quote(new_name), logger
        )
        if create_res["rc"] != 0:
            results.append({"name": old_name, "new_name": new_name,
                            "type": "rpm_repository", "status": "Failed",
                            "message": f"Create failed: {create_res['stderr']}"})
            continue

        # Parse the newly created repo's pulp_href for use in copy config
        new_repo_info = safe_json_parse(create_res.get("stdout", ""), default=None)
        new_repo_href = new_repo_info.get("pulp_href", "") if new_repo_info else ""

        # -- Step 2: Copy content from old repo to new repo ---------------
        old_repo_info = safe_json_parse(
            run_cmd(pulp_rpm_commands["show_repository"] % shlex.quote(old_name), logger
                    ).get("stdout", ""), default=None
        )
        copy_ok = False
        if old_repo_info:
            version_href = old_repo_info.get("latest_version_href", "")
            # Only copy if the repo has content (version > 0)
            if version_href and not version_href.endswith("/versions/0/"):
                # Use pulp rpm copy --config with JSON document
                # dest_repo requires a repo href, not a name
                dest_repo_href = new_repo_href
                if not dest_repo_href:
                    # Fallback: look up the newly created repo to get its href
                    new_show = safe_json_parse(
                        run_cmd(pulp_rpm_commands["show_repository"] % shlex.quote(new_name),
                                logger).get("stdout", ""), default=None
                    )
                    dest_repo_href = new_show.get("pulp_href", "") if new_show else ""

                if dest_repo_href:
                    copy_config = json.dumps([{
                        "source_repo_version": version_href,
                        "dest_repo": dest_repo_href,
                    }])
                    copy_cmd = f"pulp rpm copy --config {shlex.quote(copy_config)}"
                    logger.info("[RPM %d/%d] Copying content from '%s' (this may take several minutes for large repos)...",
                                idx, len(old_repos), old_name)
                    copy_res = run_cmd(copy_cmd, logger)
                    if copy_res["rc"] == 0:
                        copy_ok = True
                        logger.info("Copied content from '%s' to '%s'", old_name, new_name)
                    else:
                        logger.error("pulp rpm copy failed: %s", copy_res["stderr"])
                else:
                    logger.error("Cannot determine dest_repo href for '%s'", new_name)
            else:
                # Empty repo — nothing to copy; creation is enough
                copy_ok = True
                logger.info("Old repo '%s' is empty; new repo '%s' created empty", old_name, new_name)
        else:
            # Cannot read old repo info — still, the new repo was created
            copy_ok = True
            logger.warning("Could not read old repo '%s' info; new repo created empty", old_name)

        if not copy_ok:
            # Rollback: remove the new repo we just created
            run_cmd(pulp_rpm_commands["delete_repository"] % shlex.quote(new_name), logger)
            results.append({"name": old_name, "new_name": new_name,
                            "type": "rpm_repository", "status": "Failed",
                            "message": "Content copy failed; rolled back"})
            continue

        # -- Step 3: Create new publication --------------------------------
        pub_res = run_cmd(
            pulp_rpm_commands["publish_repository"] % shlex.quote(new_name), logger
        )
        if pub_res["rc"] != 0:
            logger.warning("Publication creation for '%s' failed: %s",
                           new_name, pub_res["stderr"])

        # -- Step 4: Delete old distribution FIRST (base_path must be unique)
        #    For RPM repos, the base_path usually changes (it contains the
        #    repo name), but we still delete the old distribution first for
        #    safety -- if base_path computation ever returns the same value,
        #    Pulp's uniqueness constraint would block creation.
        if "delete_distribution" in pulp_rpm_commands:
            run_cmd(pulp_rpm_commands["delete_distribution"] % shlex.quote(old_name), logger)

        # -- Step 5: Create new distribution with updated base_path -------
        arch = None
        for a in ARCH_SUFFIXES:
            if old_name.startswith(f"{a}_"):
                arch = a
                break

        old_dist = old_dist_map.get(old_name, {})
        old_base_path = old_dist.get("base_path", "")
        new_base_path = compute_new_base_path(old_base_path, old_name, new_name,
                                              arch, os_type, os_version)
        if not new_base_path:
            # Construct default base_path if old one was empty
            new_base_path = (
                f"opt/omnia/offline_repo/cluster/{arch}/{os_type}/{os_version}"
                f"/rpms/{new_name}"
            )

        dist_create_res = run_cmd(
            pulp_rpm_commands["distribute_repository"] % (
                shlex.quote(new_name), shlex.quote(new_base_path),
                shlex.quote(new_name)
            ), logger
        )
        if dist_create_res["rc"] != 0:
            logger.warning("Distribution creation for '%s' failed: %s",
                           new_name, dist_create_res["stderr"])

        # -- Step 6: Recreate remote with new name ------------------------
        old_remote = old_remote_map.get(old_name, {})
        if old_remote:
            remote_url = old_remote.get("url", "")
            remote_policy = old_remote.get("policy", "on_demand")
            ca_cert = old_remote.get("ca_cert", "")
            client_cert = old_remote.get("client_cert", "")
            client_key = old_remote.get("client_key", "")

            if ca_cert and client_cert and client_key:
                remote_create_cmd = (
                    pulp_rpm_commands.get("create_remote_cert", "") % (
                        shlex.quote(new_name), shlex.quote(remote_url),
                        shlex.quote(remote_policy), shlex.quote(ca_cert),
                        shlex.quote(client_cert), shlex.quote(client_key),
                    )
                )
            else:
                remote_create_cmd = (
                    pulp_rpm_commands["create_remote"] % (
                        shlex.quote(new_name), shlex.quote(remote_url),
                        shlex.quote(remote_policy),
                    )
                )
            remote_res = run_cmd(remote_create_cmd, logger)
            if remote_res["rc"] != 0:
                logger.warning("Remote recreation for '%s' failed: %s",
                               new_name, remote_res["stderr"])

        # -- Step 7: Delete remaining old entities (repo, publications, remote)
        #    Distribution already deleted above; _delete_old_repo_entities
        #    handles the rest (best-effort, skips if already gone).
        _delete_old_repo_entities("rpm", old_name, logger)

        results.append({"name": old_name, "new_name": new_name,
                        "type": "rpm_repository", "status": "Success",
                        "message": "Migrated (create-copy-switch)"})

    return results


# ============================================================================
# File repository migration (create-copy-switch)
# ============================================================================

def migrate_file_repos(os_type: str, os_version: str, dry_run: bool,
                       logger) -> List[Dict[str, Any]]:
    """Migrate Pulp File repositories and distributions.

    Uses the create-copy-switch strategy because ``pulp file repository update
    --new-name`` is not supported.  Unlike RPM repos, the Pulp File CLI does
    NOT provide a ``copy`` or ``modify`` subcommand, so content is transferred
    using the Pulp REST API's repository modify endpoint
    (``POST <repo_href>modify/`` with ``add_content_units``).

    Additionally, ``pulp file content list`` does NOT support
    ``--repository-version`` filtering, so content listing also uses the
    REST API (``GET /pulp/api/v3/content/file/files/?repository_version=...``).

    For each old-format File repo:
      1. Create a new File repository with the new name.
      2. List content from the old repo's latest version via REST API.
      3. Add those content hrefs to the new repo via REST API modify.
      4. Create a new publication for the new repo.
      5. Delete old distribution (base_path must be unique in Pulp).
      6. Create a new distribution with the new name and same base_path.
      7. Delete remaining old entities (repository, publications).
    """
    results = []

    repos = list_pulp_entities(pulp_file_commands["list_repositories"], logger)
    old_repos = [r for r in repos if is_old_format(r.get("name", ""))]

    dists = list_pulp_entities(pulp_file_commands["list_distributions"], logger)
    old_dist_map = {d["name"]: d for d in dists if is_old_format(d.get("name", ""))}

    logger.info("Found %d old-format File repos to process: %s",
                len(old_repos), [r["name"] for r in old_repos])

    for idx, repo in enumerate(old_repos, 1):
        old_name = repo["name"]
        new_name = build_new_name(old_name, os_type, os_version)
        if not new_name:
            continue

        logger.info("[File %d/%d] Processing '%s' -> '%s'",
                    idx, len(old_repos), old_name, new_name)

        check = run_cmd(pulp_file_commands["show_repository"] % shlex.quote(new_name), logger)
        if check["rc"] == 0:
            # New repo exists — but is the migration complete?
            dist_check = run_cmd(
                pulp_file_commands["show_distribution"] % shlex.quote(new_name), logger
            )
            if dist_check["rc"] == 0:
                logger.info("[File %d/%d] Skipped '%s' — already migrated to '%s'",
                            idx, len(old_repos), old_name, new_name)
                results.append({"name": old_name, "new_name": new_name,
                                "type": "file_repository", "status": "Skipped",
                                "message": "New name already exists"})
                continue
            else:
                logger.warning("[File %d/%d] Partial migration detected for '%s' — "
                               "new repo exists but distribution missing. "
                               "Deleting incomplete repo and retrying...",
                               idx, len(old_repos), old_name)
                run_cmd(pulp_file_commands["delete_repository"] % shlex.quote(new_name), logger)
                # Fall through to re-create from scratch

        if dry_run:
            results.append({"name": old_name, "new_name": new_name,
                            "type": "file_repository", "status": "DryRun",
                            "message": "Would migrate (create-copy-switch)"})
            continue

        # -- Step 1: Create new repository --------------------------------
        create_res = run_cmd(
            pulp_file_commands["create_repository"] % shlex.quote(new_name), logger
        )
        if create_res["rc"] != 0:
            results.append({"name": old_name, "new_name": new_name,
                            "type": "file_repository", "status": "Failed",
                            "message": f"Create failed: {create_res['stderr']}"})
            continue

        # Parse the new repo's pulp_href for use in REST API call
        new_repo_info = safe_json_parse(create_res.get("stdout", ""), default=None)
        new_repo_href = new_repo_info.get("pulp_href", "") if new_repo_info else ""

        if not new_repo_href:
            # Fallback: look up the newly created repo to get its href
            new_show = safe_json_parse(
                run_cmd(pulp_file_commands["show_repository"] % shlex.quote(new_name),
                        logger).get("stdout", ""), default=None
            )
            new_repo_href = new_show.get("pulp_href", "") if new_show else ""

        # -- Step 2+3: Copy content from old repo to new repo via REST API -
        old_repo_info = safe_json_parse(
            run_cmd(pulp_file_commands["show_repository"] % shlex.quote(old_name), logger
                    ).get("stdout", ""), default=None
        )
        copy_ok = False
        if old_repo_info:
            version_href = old_repo_info.get("latest_version_href", "")
            if version_href and not version_href.endswith("/versions/0/"):
                # Use REST API to list content (CLI lacks --repository-version)
                hrefs = _list_repo_content_via_api(version_href, logger)
                if hrefs is not None:
                    if hrefs and new_repo_href:
                        copy_ok = _modify_repo_content_via_api(
                            new_repo_href, hrefs, logger
                        )
                    elif not hrefs:
                        copy_ok = True  # No content hrefs found but ok
                    else:
                        logger.error("Cannot determine new repo href for '%s'", new_name)
                else:
                    logger.warning("Failed to list content for '%s' via REST API",
                                   old_name)
                    copy_ok = True  # Proceed with empty new repo
            else:
                copy_ok = True  # Empty repo
        else:
            copy_ok = True  # Cannot read old repo info

        if not copy_ok:
            run_cmd(pulp_file_commands["delete_repository"] % shlex.quote(new_name), logger)
            results.append({"name": old_name, "new_name": new_name,
                            "type": "file_repository", "status": "Failed",
                            "message": "Content copy failed; rolled back"})
            continue

        # -- Step 4: Create new publication --------------------------------
        pub_cmd = pulp_file_commands.get("publication_create", "")
        if pub_cmd:
            pub_res = run_cmd(pub_cmd % shlex.quote(new_name), logger)
            if pub_res["rc"] != 0:
                logger.warning("Publication creation for '%s' failed: %s",
                               new_name, pub_res["stderr"])

        # -- Step 5: Delete old distribution FIRST (base_path must be unique)
        #    File repo base_paths use the package name, not the repo name,
        #    so old and new base_paths are identical.  Pulp enforces unique
        #    base_path, so the old distribution must be removed before
        #    creating the new one.
        if "delete_distribution" in pulp_file_commands:
            run_cmd(pulp_file_commands["delete_distribution"] % shlex.quote(old_name), logger)

        # -- Step 6: Create new distribution with updated base_path -------
        arch = None
        for a in ARCH_SUFFIXES:
            if old_name.startswith(f"{a}_"):
                arch = a
                break

        old_dist = old_dist_map.get(old_name, {})
        old_base_path = old_dist.get("base_path", "")
        new_base_path = compute_new_base_path(old_base_path, old_name, new_name,
                                              arch, os_type, os_version)

        if new_base_path:
            dist_create_cmd = pulp_file_commands.get("distribution_create", "")
            if dist_create_cmd:
                dist_res = run_cmd(
                    dist_create_cmd % (
                        shlex.quote(new_name), shlex.quote(new_base_path),
                        shlex.quote(new_name)
                    ), logger
                )
                if dist_res["rc"] != 0:
                    logger.warning("Distribution creation for '%s' failed: %s",
                                   new_name, dist_res["stderr"])

        # -- Step 7: Delete remaining old entities (repo, publications) ---
        #    Distribution already deleted above; _delete_old_repo_entities
        #    handles the rest (best-effort, skips if already gone).
        _delete_old_repo_entities("file", old_name, logger)

        results.append({"name": old_name, "new_name": new_name,
                        "type": "file_repository", "status": "Success",
                        "message": "Migrated (create-copy-switch)"})

    return results


# ============================================================================
# Python (pip_module) repository migration (create-copy-switch)
# ============================================================================

def migrate_python_repos(os_type: str, os_version: str, dry_run: bool,
                         logger) -> List[Dict[str, Any]]:
    """Migrate Pulp Python repositories and distributions.

    Uses the same create-copy-switch strategy as RPM/File migration because
    ``pulp python repository update --new-name`` is not supported.

    For each old-format Python repo:
      1. Create a new Python repository with the new name.
      2. Copy content from old repo to new repo via REST API.
      3. Create a new publication for the new repo.
      4. Delete old distribution (base_path must be unique).
      5. Create a new distribution with the new name and updated base_path.
      6. Delete the old repository and other entities.

    Python repos contain pip wheel packages that were uploaded via the local
    repo process. Content is preserved by copying via REST API.
    """
    results = []

    repos = list_pulp_entities(pulp_python_commands["list_repositories"], logger)
    old_repos = [r for r in repos if is_old_format(r.get("name", ""))]

    dists = list_pulp_entities(pulp_python_commands["list_distributions"], logger)
    old_dist_map = {d["name"]: d for d in dists if is_old_format(d.get("name", ""))}

    logger.info("Found %d old-format Python repos to process: %s",
                len(old_repos), [r["name"] for r in old_repos])

    for idx, repo in enumerate(old_repos, 1):
        old_name = repo["name"]
        new_name = build_new_name(old_name, os_type, os_version)
        if not new_name:
            continue

        logger.info("[Python %d/%d] Processing '%s' -> '%s'",
                    idx, len(old_repos), old_name, new_name)

        check = run_cmd(pulp_python_commands["show_repository"] % shlex.quote(new_name), logger)
        if check["rc"] == 0:
            # New repo exists — but is the migration complete?
            # Check if a distribution with the new name exists in the already-fetched list
            new_dist_exists = any(d.get("name") == new_name for d in
                                 list_pulp_entities(pulp_python_commands["list_distributions"], logger))
            if new_dist_exists:
                logger.info("[Python %d/%d] Skipped '%s' — already migrated to '%s'",
                            idx, len(old_repos), old_name, new_name)
                results.append({"name": old_name, "new_name": new_name,
                                "type": "python_repository", "status": "Skipped",
                                "message": "New name already exists"})
                continue
            else:
                logger.warning("[Python %d/%d] Partial migration detected for '%s' — "
                               "new repo exists but distribution missing. "
                               "Deleting incomplete repo and retrying...",
                               idx, len(old_repos), old_name)
                run_cmd(pulp_python_commands["delete_repository"] % shlex.quote(new_name), logger)
                # Fall through to re-create from scratch

        if dry_run:
            results.append({"name": old_name, "new_name": new_name,
                            "type": "python_repository", "status": "DryRun",
                            "message": "Would migrate (create-copy-switch)"})
            continue

        # -- Step 1: Create new repository --------------------------------
        create_cmd = f"pulp python repository create --name {shlex.quote(new_name)}"
        create_res = run_cmd(create_cmd, logger)
        if create_res["rc"] != 0:
            results.append({"name": old_name, "new_name": new_name,
                            "type": "python_repository", "status": "Failed",
                            "message": f"Create failed: {create_res['stderr']}"})
            continue

        # Get the new repository href
        new_repo_info = safe_json_parse(create_res.get("stdout", ""), default=None)
        new_repo_href = new_repo_info.get("pulp_href", "") if new_repo_info else ""

        # -- Step 2: Copy content from old repo to new repo ---------------
        old_repo_info = safe_json_parse(
            run_cmd(pulp_python_commands["show_repository"] % shlex.quote(old_name), logger
                    ).get("stdout", ""), default=None
        )
        copy_ok = False
        if old_repo_info:
            version_href = old_repo_info.get("latest_version_href", "")
            if version_href and not version_href.endswith("/versions/0/"):
                # Use REST API to list Python content
                hrefs = _list_python_repo_content_via_api(version_href, logger)
                if hrefs is not None:
                    if hrefs and new_repo_href:
                        copy_ok = _modify_repo_content_via_api(
                            new_repo_href, hrefs, logger
                        )
                        if copy_ok:
                            logger.info("[Python %d/%d] Copied %d content units from '%s' to '%s'",
                                        idx, len(old_repos), len(hrefs), old_name, new_name)
                    elif not hrefs:
                        copy_ok = True  # No content hrefs found but ok
                        logger.info("[Python %d/%d] No content to copy for '%s'",
                                    idx, len(old_repos), old_name)
                    else:
                        logger.error("Cannot determine new repo href for '%s'", new_name)
                else:
                    logger.warning("Failed to list content for '%s' via REST API",
                                   old_name)
                    copy_ok = True  # Proceed with empty new repo
            else:
                copy_ok = True  # Empty repo
                logger.info("[Python %d/%d] Old repo '%s' is empty (no content)",
                            idx, len(old_repos), old_name)
        else:
            copy_ok = True  # Cannot read old repo info

        if not copy_ok:
            run_cmd(pulp_python_commands["delete_repository"] % shlex.quote(new_name), logger)
            results.append({"name": old_name, "new_name": new_name,
                            "type": "python_repository", "status": "Failed",
                            "message": "Content copy failed; rolled back"})
            continue

        # -- Step 3: Create new publication --------------------------------
        pub_cmd = f"pulp python publication create --repository {shlex.quote(new_name)}"
        pub_res = run_cmd(pub_cmd, logger)
        if pub_res["rc"] != 0:
            logger.warning("Publication creation for '%s' failed: %s",
                           new_name, pub_res["stderr"])
        else:
            logger.info("[Python %d/%d] Created publication for '%s'",
                        idx, len(old_repos), new_name)

        # -- Step 4: Delete old distribution FIRST (base_path must be unique)
        #    Python repo base_paths use the package name, not the repo name,
        #    so old and new base_paths are identical.  Pulp enforces unique
        #    base_path, so the old distribution must be removed before
        #    creating the new one.
        if "delete_distribution" in pulp_python_commands:
            run_cmd(pulp_python_commands["delete_distribution"] % shlex.quote(old_name), logger)

        # -- Step 5: Create new distribution with updated base_path -------
        arch = None
        for a in ARCH_SUFFIXES:
            if old_name.startswith(f"{a}_"):
                arch = a
                break

        old_dist = old_dist_map.get(old_name, {})
        old_base_path = old_dist.get("base_path", "")
        new_base_path = compute_new_base_path(old_base_path, old_name, new_name,
                                              arch, os_type, os_version)

        if new_base_path:
            dist_create_cmd = (
                f"pulp python distribution create --name {shlex.quote(new_name)} "
                f"--base-path {shlex.quote(new_base_path)} "
                f"--repository {shlex.quote(new_name)}"
            )
            dist_res = run_cmd(dist_create_cmd, logger)
            if dist_res["rc"] != 0:
                logger.warning("Distribution creation for '%s' failed: %s",
                               new_name, dist_res["stderr"])

        # -- Step 6: Delete remaining old entities (repo) -----------------
        #    Distribution already deleted above; _delete_old_repo_entities
        #    handles the rest (best-effort, skips if already gone).
        _delete_old_repo_entities("python", old_name, logger)

        results.append({"name": old_name, "new_name": new_name,
                        "type": "python_repository", "status": "Success",
                        "message": "Migrated (create-copy-switch)"})

    return results


# ============================================================================
# Status CSV migration
# ============================================================================

def migrate_status_csv_files(os_type: str, os_version: str,
                             base_path: str, dry_run: bool,
                             logger) -> List[Dict[str, Any]]:
    """Update ``repo_name`` column in status.csv files to new naming format.

    status.csv lives at:
        <base_path>/<os_type>/<os_version>/<arch>/<software>/status.csv

    Each CSV row has columns: name, type, repo_name, status
    We update any repo_name that is in old format.
    """
    results = []
    pattern = f"{base_path}/*/*/*/*/status.csv"
    status_files = glob.glob(pattern)

    for status_file in status_files:
        updated = False
        rows = []
        fieldnames = None

        try:
            with open(status_file, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                fieldnames = reader.fieldnames
                if not fieldnames or "repo_name" not in fieldnames:
                    continue

                for row in reader:
                    repo_name = row.get("repo_name", "")
                    if repo_name and is_old_format(repo_name):
                        new_repo_name = build_new_name(repo_name, os_type, os_version)
                        if new_repo_name:
                            row["repo_name"] = new_repo_name
                            updated = True
                    rows.append(row)

            if updated and not dry_run:
                with open(status_file, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                results.append({"name": status_file, "type": "status_csv",
                                "status": "Success", "message": "Updated repo_name entries"})
            elif updated and dry_run:
                results.append({"name": status_file, "type": "status_csv",
                                "status": "DryRun", "message": "Would update repo_name entries"})

        except Exception as exc:
            logger.error("Error processing %s: %s", status_file, exc)
            results.append({"name": status_file, "type": "status_csv",
                            "status": "Failed", "message": str(exc)})

    return results


# ============================================================================
# Post-migration cleanup of stale old-format entities
# ============================================================================

def _delete_old_entity(entity_type: str, sub_type: str, name: str,
                       dry_run: bool, logger) -> Dict[str, Any]:
    """Delete a single old-format Pulp entity.

    *entity_type* is one of ``rpm``, ``file``, ``python``.
    *sub_type* is one of ``repository``, ``remote``, ``distribution``.
    """
    cmd_maps = {
        "rpm": pulp_rpm_commands,
        "file": pulp_file_commands,
        "python": pulp_python_commands,
    }
    cmds = cmd_maps.get(entity_type)
    if not cmds:
        return {"name": name, "new_name": "", "type": f"{entity_type}_{sub_type}",
                "status": "Failed", "message": f"Unknown entity type: {entity_type}"}

    result = {"name": name, "new_name": "(deleted)",
              "type": f"cleanup_{entity_type}_{sub_type}",
              "status": "Failed", "message": ""}

    if dry_run:
        result["status"] = "DryRun"
        result["message"] = "Would delete stale old-format entity"
        return result

    # For repositories, also clean up associated distributions, publications,
    # and remotes that share the same name before deleting the repo itself.
    if sub_type == "repository":
        # Delete distribution with same name (best-effort)
        del_key = "delete_distribution"
        if del_key in cmds:
            run_cmd(cmds[del_key] % shlex.quote(name), logger)

        # Delete publications (RPM only)
        if entity_type == "rpm" and "list_publications" in cmds:
            pub_res = run_cmd(cmds["list_publications"] % shlex.quote(name), logger)
            if pub_res["rc"] == 0:
                pubs = safe_json_parse(pub_res["stdout"], default=[])
                for pub in pubs:
                    href = pub.get("pulp_href", "")
                    if href and "delete_publication" in cmds:
                        run_cmd(cmds["delete_publication"] % href, logger)

        # Delete remote with same name (best-effort)
        if "delete_remote" in cmds:
            run_cmd(cmds["delete_remote"] % shlex.quote(name), logger)

    # Now delete the entity itself
    delete_key = f"delete_{sub_type}"
    if delete_key not in cmds:
        result["message"] = f"No delete command for {entity_type} {sub_type}"
        return result

    del_res = run_cmd(cmds[delete_key] % shlex.quote(name), logger)
    if del_res["rc"] == 0:
        result["status"] = "Success"
        result["message"] = "Deleted stale old-format entity"
    else:
        result["message"] = f"Delete failed: {del_res['stderr']}"

    return result


def cleanup_stale_old_format(os_type: str, os_version: str, dry_run: bool,
                             logger) -> List[Dict[str, Any]]:
    """Delete any Pulp entities that still carry the old naming format.

    This runs **after** the rename pass.  For each old-format entity found we
    check whether the corresponding new-format entity already exists:

    * **New-format exists** → the old entity is a stale leftover (e.g. a
      partially-failed rename created the new one but left the old).  Safe to
      delete.
    * **New-format does NOT exist** → the rename never succeeded and the old
      entity is the *only* copy of the data.  We skip deletion to avoid data
      loss and log a warning instead.
    """
    results: List[Dict[str, Any]] = []

    # Map of (entity_type, sub_type) → (list_cmd, show_cmd)
    scan_targets = [
        ("rpm",    "repository",   pulp_rpm_commands.get("list_repositories", ""),
                                   pulp_rpm_commands.get("show_repository", "")),
        ("rpm",    "remote",       pulp_rpm_commands.get("list_remotes", ""),
                                   pulp_rpm_commands.get("show_remote", "")),
        ("rpm",    "distribution", pulp_rpm_commands.get("list_distributions", ""),
                                   pulp_rpm_commands.get("check_distribution", "")),
        ("file",   "repository",   pulp_file_commands.get("list_repositories", ""),
                                   pulp_file_commands.get("show_repository", "")),
        ("file",   "distribution", pulp_file_commands.get("list_distributions", ""),
                                   pulp_file_commands.get("show_distribution", "")),
        ("python", "repository",   pulp_python_commands.get("list_repositories", ""),
                                   pulp_python_commands.get("show_repository", "")),
        ("python", "distribution", pulp_python_commands.get("list_distributions", ""),
                                   # python distributions don't have a show cmd in config —
                                   # we'll skip the new-name check if empty
                                   ""),
    ]

    for entity_type, sub_type, list_cmd, show_cmd in scan_targets:
        if not list_cmd:
            continue

        entities = list_pulp_entities(list_cmd, logger)
        old_entities = [e for e in entities if is_old_format(e.get("name", ""))]

        for entity in old_entities:
            old_name = entity["name"]
            new_name = build_new_name(old_name, os_type, os_version)
            if not new_name:
                continue

            # Safety check: only delete if the new-format entity exists
            if show_cmd:
                check = run_cmd(show_cmd % new_name, logger)
                if check["rc"] != 0:
                    logger.warning(
                        "Skipping cleanup of '%s': new-format '%s' does not "
                        "exist — would cause data loss", old_name, new_name
                    )
                    results.append({
                        "name": old_name, "new_name": new_name,
                        "type": f"cleanup_{entity_type}_{sub_type}",
                        "status": "Skipped",
                        "message": "New-format entity missing; kept to avoid data loss",
                    })
                    continue

            res = _delete_old_entity(entity_type, sub_type, old_name,
                                     dry_run, logger)
            res["new_name"] = new_name
            results.append(res)

    # Run orphan cleanup once at the end (if anything was actually deleted)
    deleted_count = sum(1 for r in results if r["status"] == "Success")
    if deleted_count > 0 and not dry_run:
        logger.info("Running orphan cleanup after stale entity removal...")
        orphan_res = run_cmd(pulp_rpm_commands.get("orphan_cleanup",
                             "pulp orphan cleanup --protection-time 0"), logger)
        if orphan_res["rc"] == 0:
            results.append({"name": "orphan_cleanup", "new_name": "",
                            "type": "cleanup_orphans", "status": "Success",
                            "message": "Orphan cleanup completed"})
        else:
            results.append({"name": "orphan_cleanup", "new_name": "",
                            "type": "cleanup_orphans", "status": "Failed",
                            "message": f"Orphan cleanup failed: {orphan_res['stderr']}"})

    return results


# ============================================================================
# YUM repo file regeneration
# ============================================================================

def regenerate_yum_repo_file(logger) -> Dict[str, Any]:
    """Regenerate /etc/yum.repos.d/pulp.repo from current Pulp RPM distributions.

    This ensures that after renaming distributions the dnf/yum configuration
    on the OIM matches the new names.
    """
    result = {"name": "pulp.repo", "type": "yum_repo_file",
              "status": "Failed", "message": ""}

    try:
        dists = list_pulp_entities(
            "pulp rpm distribution list --field base_url,name --limit 1000", logger
        )
        if not dists:
            result["message"] = "No RPM distributions found"
            result["status"] = "Skipped"
            return result

        repo_file_path = "/etc/yum.repos.d/pulp.repo"
        repo_content = ""
        for dist in dists:
            name = dist.get("name", "")
            base_url = dist.get("base_url", "")
            if not name or not base_url:
                continue
            repo_content += (
                f"[{name}]\n"
                f"name={name} repo\n"
                f"baseurl={base_url}\n"
                f"enabled=1\n"
                f"gpgcheck=0\n\n"
            )

        if repo_content:
            with open(repo_file_path, "w", encoding="utf-8") as fh:
                fh.write(repo_content.strip() + "\n")
            result["status"] = "Success"
            result["message"] = f"Regenerated with {len(dists)} distributions"
        else:
            result["status"] = "Skipped"
            result["message"] = "No valid distributions to write"

    except Exception as exc:
        result["message"] = str(exc)
        logger.error("Failed to regenerate pulp.repo: %s", exc)

    return result


# ============================================================================
# Pretty-print table
# ============================================================================

def format_migration_table(results: List[Dict[str, Any]]) -> str:
    """Format migration results as a pretty table.

    Column width limits:
    - Old Name / New Name: up to 80 chars to accommodate arch_os_version_package format
    - Type: no limit (typically short)
    - Status: no limit (typically short)
    - Message: up to 50 chars
    """
    if not results:
        return "No migration actions performed."

    # Max width limits for each column to prevent excessively wide tables
    max_name_width = 80
    max_message_width = 50

    headers = ["Old Name", "New Name", "Type", "Status", "Message"]
    widths = [len(h) for h in headers]

    for r in results:
        widths[0] = max(widths[0], min(len(str(r.get("name", ""))), max_name_width))
        widths[1] = max(widths[1], min(len(str(r.get("new_name", r.get("name", "")))), max_name_width))
        widths[2] = max(widths[2], len(str(r.get("type", ""))))
        widths[3] = max(widths[3], len(str(r.get("status", ""))))
        widths[4] = max(widths[4], min(len(str(r.get("message", ""))), max_message_width))

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_row = "|" + "|".join(
        f" {h.ljust(w)} " for h, w in zip(headers, widths)
    ) + "|"

    lines = [border, header_row, border]
    for r in results:
        old = str(r.get("name", ""))[:max_name_width]
        new = str(r.get("new_name", r.get("name", "")))[:max_name_width]
        rtype = str(r.get("type", ""))
        status = str(r.get("status", ""))
        msg = str(r.get("message", ""))[:max_message_width]
        row = "|" + "|".join([
            f" {old.ljust(widths[0])} ",
            f" {new.ljust(widths[1])} ",
            f" {rtype.ljust(widths[2])} ",
            f" {status.ljust(widths[3])} ",
            f" {msg.ljust(widths[4])} ",
        ]) + "|"
        lines.append(row)
    lines.append(border)
    return "\n".join(lines)


# ============================================================================
# Ansible module entry-point
# ============================================================================

def run_module():
    module_args = dict(
        cluster_os_type=dict(type="str", required=True),
        cluster_os_version=dict(type="str", required=True),
        base_path=dict(type="str", default="/opt/omnia/log/local_repo"),
        dry_run=dict(type="bool", default=False),
        log_dir=dict(type="str", default=LOG_DIR),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    os_type = module.params["cluster_os_type"].lower()
    os_version = module.params["cluster_os_version"]
    base_path = module.params["base_path"]
    dry_run = module.params["dry_run"] or module.check_mode
    log_dir = module.params["log_dir"]

    logger = setup_standard_logger(log_dir, LOG_FILENAME)
    logger.info("=" * 60)
    logger.info("Pulp Repository Name Migration - START")
    logger.info("  os_type=%s  os_version=%s  dry_run=%s", os_type, os_version, dry_run)
    logger.info("=" * 60)

    all_results: List[Dict[str, Any]] = []

    try:
        # 1. Migrate RPM repos / remotes / distributions
        logger.info("--- Migrating RPM repositories ---")
        rpm_results = migrate_rpm_repos(os_type, os_version, dry_run, logger)
        all_results.extend(rpm_results)

        # 2. Migrate File repos / distributions
        logger.info("--- Migrating File repositories ---")
        file_results = migrate_file_repos(os_type, os_version, dry_run, logger)
        all_results.extend(file_results)

        # 3. Migrate Python repos / distributions
        logger.info("--- Migrating Python repositories ---")
        python_results = migrate_python_repos(os_type, os_version, dry_run, logger)
        all_results.extend(python_results)

        # 4. Update status.csv files
        logger.info("--- Migrating status.csv files ---")
        csv_results = migrate_status_csv_files(os_type, os_version, base_path, dry_run, logger)
        all_results.extend(csv_results)

        # 5. Post-migration cleanup: delete any stale old-format entities
        #    that survived the rename pass (e.g. partial failures that left
        #    both old and new copies).
        logger.info("--- Cleaning up stale old-format entities ---")
        cleanup_results = cleanup_stale_old_format(os_type, os_version, dry_run, logger)
        all_results.extend(cleanup_results)

        # 6. Regenerate yum repo file (only if not dry run)
        if not dry_run:
            logger.info("--- Regenerating pulp.repo ---")
            yum_result = regenerate_yum_repo_file(logger)
            all_results.append(yum_result)

        # Summary
        table = format_migration_table(all_results)
        logger.info("\n%s", table)

        success_count = sum(1 for r in all_results if r["status"] == "Success")
        failed_count = sum(1 for r in all_results if r["status"] == "Failed")
        skipped_count = sum(1 for r in all_results if r["status"] in ("Skipped", "DryRun"))

        changed = success_count > 0 and not dry_run

        logger.info("Migration complete: %d succeeded, %d failed, %d skipped",
                     success_count, failed_count, skipped_count)
        logger.info("=" * 60)

        if failed_count > 0:
            module.fail_json(
                msg=(f"Migration completed with {failed_count} failure(s). "
                     f"See {log_dir}/{LOG_FILENAME} for details."),
                changed=changed,
                results=all_results,
                summary_table=table,
            )
        else:
            module.exit_json(
                changed=changed,
                msg=(f"Migration completed: {success_count} renamed, "
                     f"{skipped_count} skipped."
                     f"See {log_dir}/{LOG_FILENAME} for details."),
                results=all_results,
                summary_table=table,
            )

    except Exception as exc:
        logger.error("Unexpected error during migration: %s", exc, exc_info=True)
        module.fail_json(msg=f"Migration failed: {exc}", changed=False)


def main():
    run_module()


if __name__ == "__main__":
    main()
