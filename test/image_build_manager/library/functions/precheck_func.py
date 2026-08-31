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

"""Prepare / validate / precheck verification functions."""

import json
import os
from typing import Dict, Any

import yaml

from omnia_auto import read_remote_env, resolve_domain_input_path

from .host_func import resolve_target_source_root
from ._config_helpers import (
    _retry_run,
    _get_remote_ibm_config_path,
)
from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    REGISTRY_PORT,
    S3CMD_CONFIG_PATH,
    CMDS,
    LISTENING_PORTS,
    SYSTEMD_SERVICES,
    CREDENTIALS_FILE_NAME,
)


# =============================================================================
# PREPARE VERIFICATION — EXTENDED
# =============================================================================

def check_s3cmd_configured(host) -> Dict[str, Any]:
    """Verify s3cmd is installed and s3cfg config exists.

    Returns:
        Dict with 'success', 's3cmd_available', 'config_exists', 'details'.
    """
    which_cmd = host.run(CMDS["which_cmd"].format(binary="s3cmd"))
    s3cmd_available = which_cmd.rc == 0

    cfg_cmd = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    config_exists = cfg_cmd.rc == 0 and "exists" in cfg_cmd.stdout

    details_lines = [
        f"  s3cmd binary: {'found' if s3cmd_available else 'NOT FOUND'}",
        f"  {S3CMD_CONFIG_PATH}: "
        f"{'exists' if config_exists else 'NOT FOUND'}",
    ]

    return {
        "success": s3cmd_available and config_exists,
        "s3cmd_available": s3cmd_available,
        "config_exists": config_exists,
        "details": "\n".join(details_lines),
    }


def check_firewall_ports_open(host) -> Dict[str, Any]:
    """Verify container ports are listening (via ss -tlnp).

    Checks that MinIO (9000, 9001) and registry (5000) ports
    are bound and accepting connections.

    Returns:
        Dict with 'success', 'open_ports', 'missing_ports', 'details'.
    """
    open_ports = []
    missing = []

    for port in LISTENING_PORTS:
        cmd = host.run(
            CMDS["ss_listen_port"].format(port=port)
        )
        if cmd.rc == 0 and str(port) in cmd.stdout:
            open_ports.append(port)
        else:
            missing.append(port)

    details_lines = []
    for port in LISTENING_PORTS:
        status = "listening" if port in open_ports else "NOT LISTENING"
        details_lines.append(f"  {port}/tcp: {status}")

    return {
        "success": len(missing) == 0,
        "open_ports": open_ports,
        "missing_ports": missing,
        "details": "\n".join(details_lines),
    }


def check_services_active(host) -> Dict[str, Any]:
    """Verify MinIO and registry systemd services are active.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_active = True

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip() if cmd.rc == 0 else "inactive"
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state,
            "active": is_active,
        })
        if not is_active:
            all_active = False

    details_lines = []
    for r in results:
        details_lines.append(f"  {r['service']}: {r['state']}")

    return {
        "success": all_active,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_credentials_present(host) -> Dict[str, Any]:
    """Verify credentials are configured on the execution OIM.

    Returns:
        Dict with 'success', 'details'.
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )
    cred_path = f"{input_dir}/{CREDENTIALS_FILE_NAME}"

    cmd = host.run(CMDS["file_exists"].format(path=cred_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "details": (
            f"  {CREDENTIALS_FILE_NAME}: present at {cred_path}"
            if exists
            else f"  {CREDENTIALS_FILE_NAME}: NOT FOUND at {cred_path}"
        ),
    }


def check_clone_status(host) -> Dict[str, Any]:
    """Verify the project code is available on the execution target.

    Local execution checks the current checkout.  Remote execution checks
    ``clone_path`` and its expected domain directory structure.

    Returns:
        Dict with 'success', 'clone_path', 'details'.
    """
    try:
        source_root = resolve_target_source_root()
    except ValueError as exc:
        return {
            "success": False,
            "clone_path": "",
            "details": f"  Project path unavailable: {exc}",
        }

    dir_cmd = host.run(CMDS["dir_exists"].format(path=source_root))
    if dir_cmd.rc != 0 or "exists" not in dir_cmd.stdout:
        return {
            "success": False,
            "clone_path": source_root,
            "details": f"  Project path NOT FOUND: {source_root}",
        }

    # Check for domain directory as a basic sync validation
    ibm_dir = os.path.join(source_root, "src", "image_build_manager")
    ibm_check = host.run(CMDS["dir_exists"].format(path=ibm_dir))
    has_ibm = ibm_check.rc == 0 and "exists" in ibm_check.stdout

    details_lines = [
        f"  Path: {source_root}",
        f"  image_build_manager: {'present' if has_ibm else 'NOT FOUND'}",
    ]

    return {
        "success": has_ibm,
        "clone_path": source_root,
        "details": "\n".join(details_lines),
    }


def check_registry_reachable(host) -> Dict[str, Any]:
    """Verify registry is reachable and report catalog info.

    Returns:
        Dict with 'success', 'registry_url', 'repo_count', 'repos',
        'details'.
    """
    hostname_cmd = host.run(CMDS["hostname_fqdn"])
    fqdn = (
        hostname_cmd.stdout.strip()
        if hostname_cmd.rc == 0 else "localhost"
    )
    registry_url = f"{fqdn}:{REGISTRY_PORT}"

    cmd = host.run(
        CMDS["curl_registry_catalog_http"].format(port=REGISTRY_PORT)
    )
    if cmd.rc != 0 or "repositories" not in cmd.stdout:
        return {
            "success": False,
            "registry_url": registry_url,
            "repo_count": 0,
            "repos": [],
            "details": f"  Registry NOT reachable at {registry_url}",
        }

    try:
        data = json.loads(cmd.stdout)
        repos = data.get("repositories", [])
    except (json.JSONDecodeError, ValueError):
        repos = []

    details_lines = [
        f"  URL: http://{registry_url}",
        f"  Repositories: {len(repos)}",
    ]
    for repo in repos:
        details_lines.append(f"    - {repo}")
    if not repos:
        details_lines.append("    (empty — no images pushed yet)")

    return {
        "success": True,
        "registry_url": registry_url,
        "repo_count": len(repos),
        "repos": repos,
        "details": "\n".join(details_lines),
    }


# =============================================================================
# VALIDATE VERIFICATION — EXTENDED
# =============================================================================

def check_input_config_exists(host) -> Dict[str, Any]:
    """Verify image_build_config.yml exists on target.

    Returns:
        Dict with 'success', 'details'.
    """
    cfg_path = _get_remote_ibm_config_path(host)

    cmd = host.run(CMDS["file_exists"].format(path=cfg_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": exists,
        "path": cfg_path,
        "details": (
            f"  image_build_config.yml: present at {cfg_path}"
            if exists
            else f"  image_build_config.yml: NOT FOUND at {cfg_path}"
        ),
    }


# =============================================================================
# VALIDATE — repo_ssl_verify CONFIG
# =============================================================================

def check_repo_ssl_verify_config(host) -> Dict[str, Any]:
    """Resolve the effective repo_ssl_verify value on the target.

    An omitted ``build_image.repo_ssl_verify`` is valid and resolves to
    ``True``, matching the product schema, Ansible role, and templates.
    Explicit values must be YAML booleans; nulls, strings, and numbers are
    rejected instead of being coerced with Python truthiness.

    Returns:
        Dict with 'success', 'ssl_verify', 'used_default', and 'details'.
    """
    cfg_path = _get_remote_ibm_config_path(host)

    # Read config YAML from target
    cat_cmd = host.run(CMDS["cat_file"].format(path=cfg_path))
    if cat_cmd.rc != 0 or not cat_cmd.stdout.strip():
        return {
            "success": False,
            "ssl_verify": None,
            "used_default": False,
            "details": (
                f"  image_build_config.yml not readable at {cfg_path}"
            ),
        }

    try:
        config = yaml.safe_load(cat_cmd.stdout)
    except yaml.YAMLError:
        return {
            "success": False,
            "ssl_verify": None,
            "used_default": False,
            "details": "  image_build_config.yml: failed to parse YAML",
        }

    if not isinstance(config, dict):
        return {
            "success": False,
            "ssl_verify": None,
            "used_default": False,
            "details": (
                "  image_build_config.yml: expected a YAML mapping"
            ),
        }

    if "build_image" not in config:
        build_image = {}
    else:
        build_image = config["build_image"]
        if not isinstance(build_image, dict):
            return {
                "success": False,
                "ssl_verify": None,
                "used_default": False,
                "details": (
                    "  build_image: expected a YAML mapping"
                ),
            }

    if "repo_ssl_verify" not in build_image:
        return {
            "success": True,
            "ssl_verify": True,
            "used_default": True,
            "details": (
                "  build_image.repo_ssl_verify: true "
                "(runtime default; key not set)"
            ),
        }

    ssl_verify = build_image["repo_ssl_verify"]
    if not isinstance(ssl_verify, bool):
        value_type = type(ssl_verify).__name__
        return {
            "success": False,
            "ssl_verify": None,
            "used_default": False,
            "details": (
                "  build_image.repo_ssl_verify: expected boolean, "
                f"got {value_type}"
            ),
        }

    return {
        "success": True,
        "ssl_verify": ssl_verify,
        "used_default": False,
        "details": (
            f"  build_image.repo_ssl_verify: {str(ssl_verify).lower()} "
            "(explicit)"
        ),
    }


def check_repo_ssl_verify_applied(host, arch: str = "x86_64") -> Dict[str, Any]:
    """Verify repo_ssl_verify is wired into the image build templates.

    This is a structural source-template check.  It confirms that the RHEL
    base and compute templates reference ``repo_ssl_verify`` and emit both
    ``sslverify`` and ``gpgcheck`` fields.  It does not inspect rendered or
    previously built artifacts.

    Args:
        host: Testinfra host connection.
        arch: Architecture to check (x86_64 or aarch64).

    Returns:
        Dict with 'success', 'ssl_verify', 'details'.
    """
    # Get the configured ssl_verify value
    ssl_result = check_repo_ssl_verify_config(host)
    if not ssl_result["success"]:
        return {
            "success": False,
            "ssl_verify": None,
            "used_default": False,
            "blocked_by_config": True,
            "results": [],
            "details": (
                "  Cannot determine repo_ssl_verify: "
                f"{ssl_result['details']}"
            ),
        }

    ssl_verify = ssl_result["ssl_verify"]
    used_default = ssl_result.get("used_default", False)
    expected_value = "1" if ssl_verify else "0"

    try:
        source_root = resolve_target_source_root()
    except ValueError as exc:
        return {
            "success": False,
            "ssl_verify": ssl_verify,
            "used_default": used_default,
            "blocked_by_config": False,
            "expected_value": expected_value,
            "results": [],
            "details": f"  Source path unavailable: {exc}",
        }

    # Inspect templates from the current checkout locally and clone_path
    # only when tests execute against a remote OIM server.
    template_dir = os.path.join(
        source_root,
        "src",
        "image_build_manager",
        "roles",
        "build_os_images",
        "templates",
        "images",
    )
    template_paths = [
        os.path.join(template_dir, "rhel-base-config.yaml.j2"),
        os.path.join(template_dir, "rhel-compute-config.yaml.j2"),
    ]

    results = []
    all_ok = True
    for tpl in template_paths:
        cmd = host.run(CMDS["cat_file"].format(path=tpl))
        if cmd.rc == 0 and cmd.stdout.strip():
            missing_refs = [
                ref for ref in (
                    "repo_ssl_verify", "sslverify", "gpgcheck",
                )
                if ref not in cmd.stdout
            ]
            has_ssl_ref = not missing_refs
            results.append({
                "template": os.path.basename(tpl),
                "has_ssl_ref": has_ssl_ref,
                "missing_refs": missing_refs,
            })
            if not has_ssl_ref:
                all_ok = False
        else:
            results.append({
                "template": os.path.basename(tpl),
                "has_ssl_ref": False,
                "missing_refs": [
                    "repo_ssl_verify", "sslverify", "gpgcheck",
                ],
            })
            all_ok = False

    lines = [
        (
            f"  repo_ssl_verify: {str(ssl_verify).lower()} "
            f"({'runtime default' if used_default else 'explicit'}; "
            f"expected sslverify={expected_value})"
        ),
    ]
    for r in results:
        status = "references repo_ssl_verify" if r["has_ssl_ref"] else "MISSING reference"
        lines.append(f"    {r['template']}: {status}")

    return {
        "success": all_ok,
        "ssl_verify": ssl_verify,
        "used_default": used_default,
        "blocked_by_config": False,
        "expected_value": expected_value,
        "results": results,
        "details": "\n".join(lines),
    }


# =============================================================================
# PRECHECK VERIFICATION
# =============================================================================

def check_target_connectivity(host) -> Dict[str, Any]:
    """Verify SSH connectivity to the target host.

    Runs a simple echo command to confirm the connection is alive.
    Uses retry to handle transient SSH failures.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    cmd = _retry_run(host, CMDS["echo_test"])
    if cmd.rc == 0 and "connectivity_ok" in cmd.stdout:
        return {
            "success": True,
            "details": "Target host is reachable via SSH",
            "error": None,
        }
    return {
        "success": False,
        "details": "",
        "error": (
            f"SSH connectivity test failed (rc={cmd.rc}). "
            "Check: oim_server_ip, SSH user/password in test_config.yml"
        ),
    }


def check_env_vars_present(host) -> Dict[str, Any]:
    """Verify all required omnia.env variables exist on target.

    Checks: OMNIA_DATA_PATH, OMNIA_PROJECT_NAME, SYSTEM_ADMIN_NIC_IPV4,
    SYSTEM_HOSTNAME, SYSTEM_DOMAIN_NAME.
    These env vars are set by ``omnia.sh --setup-venv`` and must be
    present before any playbook can run.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    required_vars = [
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
        "SYSTEM_ADMIN_NIC_IPV4",
        "SYSTEM_HOSTNAME",
        "SYSTEM_DOMAIN_NAME",
    ]
    results = []
    all_ok = True

    for var in required_vars:
        value = read_remote_env(host, var)
        found = bool(value)
        results.append({
            "variable": var,
            "found": found,
            "value": value if found else "(not set)",
        })
        if not found:
            all_ok = False

    lines = []
    for r in results:
        status = "present" if r["found"] else "MISSING"
        lines.append(f"  {r['variable']}: {status} ({r['value']})")

    return {
        "success": all_ok,
        "results": results,
        "details": "\n".join(lines),
        "error": None if all_ok else (
            "Required env vars missing. "
            "Run: omnia.sh --setup-venv on the target first."
        ),
    }


def check_hostname_domain(host) -> Dict[str, Any]:
    """Verify hostname and domain match configured env vars on target.

    Uses ``hostname -s`` (short hostname) and ``hostname -d`` (domain)
    to compare against SYSTEM_HOSTNAME and SYSTEM_DOMAIN_NAME.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    cfg_hostname = read_remote_env(host, "SYSTEM_HOSTNAME")
    cfg_domain = read_remote_env(host, "SYSTEM_DOMAIN_NAME")

    actual_hostname = _retry_run(
        host, CMDS["hostname_short"],
    ).stdout.strip()
    domain_result = _retry_run(
        host, CMDS["hostname_domain"],
    )
    actual_domain = domain_result.stdout.strip() if domain_result.rc == 0 else ""

    hostname_match = (actual_hostname == cfg_hostname)
    domain_match = (actual_domain == cfg_domain) if actual_domain else True

    results = {
        "configured_hostname": cfg_hostname or "(not set)",
        "actual_hostname": actual_hostname,
        "hostname_match": hostname_match,
        "configured_domain": cfg_domain or "(not set)",
        "actual_domain": actual_domain or "(unavailable)",
        "domain_match": domain_match,
    }

    all_ok = hostname_match
    lines = [
        f"  SYSTEM_HOSTNAME: {cfg_hostname} (actual: {actual_hostname}) "
        f"{'MATCH' if hostname_match else 'MISMATCH'}",
        f"  SYSTEM_DOMAIN_NAME: {cfg_domain} (actual: {actual_domain or '(unavailable)'}) "
        f"{'MATCH' if domain_match else 'MISMATCH'}",
        f"  FQDN: {cfg_hostname}.{cfg_domain}",
    ]

    error = None
    if not hostname_match:
        error = (
            f"Hostname mismatch: SYSTEM_HOSTNAME={cfg_hostname}, "
            f"actual hostname -s={actual_hostname}. "
            "Fix: hostnamectl set-hostname <name> or update omnia.env"
        )
    elif not domain_match:
        error = (
            f"Domain mismatch: SYSTEM_DOMAIN_NAME={cfg_domain}, "
            f"actual hostname -d={actual_domain}. "
            "Fix: update SYSTEM_DOMAIN_NAME in omnia.env or "
            f"hostnamectl set-hostname {cfg_hostname}.{cfg_domain}"
        )

    return {
        "success": all_ok,
        "results": results,
        "details": "\n".join(lines),
        "error": error,
    }


def check_admin_ip(host) -> Dict[str, Any]:
    """Verify SYSTEM_ADMIN_NIC_IPV4 is assigned to a local interface.

    Reads SYSTEM_ADMIN_NIC_IPV4 from the target and verifies the IP is
    present in the output of ``hostname -I``.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    cfg_ip = read_remote_env(host, "SYSTEM_ADMIN_NIC_IPV4")
    if not cfg_ip:
        return {
            "success": False,
            "details": "  SYSTEM_ADMIN_NIC_IPV4: (not set)",
            "error": (
                "SYSTEM_ADMIN_NIC_IPV4 is not set. "
                "Fix: set it in omnia.env and run omnia.sh --setup-venv"
            ),
        }

    ip_cmd = _retry_run(host, CMDS["hostname_ip"])
    all_ips = ip_cmd.stdout.strip().split() if ip_cmd.rc == 0 else []
    ip_assigned = cfg_ip in all_ips

    return {
        "success": ip_assigned,
        "configured_ip": cfg_ip,
        "assigned_ips": all_ips,
        "details": (
            f"  SYSTEM_ADMIN_NIC_IPV4: {cfg_ip} "
            f"({'assigned' if ip_assigned else 'NOT assigned'})"
        ),
        "error": None if ip_assigned else (
            f"SYSTEM_ADMIN_NIC_IPV4 ({cfg_ip}) is not assigned to any "
            f"interface. Available IPs: {', '.join(all_ips)}"
        ),
    }


def check_omnia_setup(host) -> Dict[str, Any]:
    """Verify omnia.sh setup has been completed on target.

    Checks that ``/etc/omnia/omnia.env`` and
    ``/etc/profile.d/omnia-env.sh`` exist on the target.
    These are created by ``omnia.sh --setup-venv``.

    Returns:
        Dict with 'success', 'details', 'error'.
    """
    env_file = "/etc/omnia/omnia.env"
    profile_file = "/etc/profile.d/omnia-env.sh"

    env_cmd = _retry_run(
        host, CMDS["file_exists"].format(path=env_file),
    )
    profile_cmd = _retry_run(
        host, CMDS["file_exists"].format(path=profile_file),
    )

    env_exists = env_cmd.rc == 0 and "exists" in env_cmd.stdout
    profile_exists = profile_cmd.rc == 0 and "exists" in profile_cmd.stdout

    all_ok = env_exists
    lines = [
        f"  {env_file}: {'present' if env_exists else 'MISSING'}",
        f"  {profile_file}: {'present' if profile_exists else 'MISSING'}",
    ]

    return {
        "success": all_ok,
        "env_file_exists": env_exists,
        "profile_exists": profile_exists,
        "details": "\n".join(lines),
        "error": None if all_ok else (
            "omnia.sh setup incomplete. "
            "Run: ./omnia.sh --setup-venv on the target."
        ),
    }
