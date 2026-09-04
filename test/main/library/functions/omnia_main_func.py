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
Omnia Main — Verification Functions

Functions that verify the state of omnia.sh setup, environment
installation, venv creation, domain initialization, and CLI behavior.

All functions return a dict with keys: success, details, error.
"""

import os
import time
from typing import Any, Dict, List

from omnia_auto import load_test_config, run_on_host, is_local_execution

from ..vars.common_vars import (
    CMDS,
    REPO_ROOT,
    OMNIA_SH_PATH,
    OMNIA_CLI_PATH,
    OMNIA_RELEASE,
    SYSTEM_ENV_FILE,
    PROFILE_DROP_IN,
    BASE_DIRS,
    DOMAINS_WITH_INIT,
    OPTIONAL_ENV_VARS,
    OMNIA_CLI_HELP_SECTIONS,
)


# =============================================================================
# CLONE PATH RESOLUTION
# =============================================================================

def _resolve_clone_path() -> str:
    """Resolve the clone path for omnia.sh commands.

    Matches the IBM pattern used in ``omnia_auto.run_playbook``:
    - **Local mode**: Returns the local repo root (computed from the
      source tree).  ``clone_path`` in test_config.yml is ignored
      because it refers to a path on the *remote* server.
    - **Remote mode**: Returns ``clone_path`` from test_config.yml
      (the path where the project is synced on the target server).

    Returns:
        Absolute path to use as ``clone_path`` in shell commands.
    """
    if is_local_execution():
        return REPO_ROOT
    config = load_test_config()
    clone_path = config.get("clone_path", "")
    if not clone_path:
        raise ValueError(
            "'clone_path' must be set in test_config.yml "
            "for remote execution (oim_server_ip is set)"
        )
    return clone_path


# =============================================================================
# VENV DETECTION
# =============================================================================

def is_running_from_omnia_venv() -> bool:
    """Check if tests are running from the omnia production venv.

    Compares the active VIRTUAL_ENV against the configured venv_path
    (default: /opt/omnia/venv).  When they match, destructive operations
    like --setup-venv and --cleanup must be skipped because they would
    destroy the interpreter that is currently executing the test suite.

    Uses both os.path.realpath and normpath to handle symlinks and
    trailing slashes consistently.

    Returns:
        True if the active venv IS the omnia production venv.
        False if running from test/main/.venv or no venv is active.
    """
    active_venv = os.environ.get("VIRTUAL_ENV", "")
    if not active_venv:
        return False
    config = load_test_config()
    omnia_venv = config.get("venv_path", "/opt/omnia/venv")

    # Normalize both paths: resolve symlinks AND strip trailing slashes
    active_norm = os.path.normpath(os.path.realpath(active_venv))
    omnia_norm = os.path.normpath(os.path.realpath(omnia_venv))

    # Also check if active venv starts with the omnia venv path
    # (handles cases like /opt/omnia/venv vs /opt/omnia/venv/)
    return active_norm == omnia_norm or active_norm.startswith(omnia_norm + os.sep)


# =============================================================================
# OMNIA.SH EXECUTION
# =============================================================================

def run_omnia_cmd(host, cmd_key: str, **kwargs) -> Dict[str, Any]:
    """Run an omnia.sh command on the target host.

    Uses ``_resolve_clone_path()`` so that local mode resolves paths
    from the source tree and remote mode uses ``clone_path`` from config.

    Args:
        host: Testinfra host connection.
        cmd_key: Key into the CMDS dict.
        **kwargs: Format parameters for the command template.

    Returns:
        Dict with keys: success, rc, output, duration, error.
    """
    kwargs.setdefault("clone_path", _resolve_clone_path())
    kwargs.setdefault("omnia_sh", OMNIA_SH_PATH)

    cmd = CMDS[cmd_key].format(**kwargs)
    start = time.time()
    result = run_on_host(host, cmd)
    duration = time.time() - start

    return {
        "success": result.rc == 0,
        "rc": result.rc,
        "output": result.stdout.strip(),
        "duration": duration,
        "error": result.stderr.strip() if result.rc != 0 else "",
    }


def run_omnia_cmd_expect_error(
    host, cmd_key: str, **kwargs
) -> Dict[str, Any]:
    """Run an omnia.sh command expecting a non-zero exit code.

    Uses ``_resolve_clone_path()`` so that local mode resolves paths
    from the source tree and remote mode uses ``clone_path`` from config.

    Args:
        host: Testinfra host connection.
        cmd_key: Key into the CMDS dict.
        **kwargs: Format parameters for the command template.

    Returns:
        Dict with keys: success (True if rc!=0), rc, output, error.
    """
    kwargs.setdefault("clone_path", _resolve_clone_path())
    kwargs.setdefault("omnia_sh", OMNIA_SH_PATH)

    cmd = CMDS[cmd_key].format(**kwargs)
    result = run_on_host(host, cmd)

    return {
        "success": result.rc != 0,
        "rc": result.rc,
        "output": result.stdout.strip(),
        "error": result.stderr.strip(),
    }


# =============================================================================
# ENVIRONMENT VALIDATION (source-level)
# =============================================================================

def check_env_source_validation(host) -> Dict[str, Any]:
    """Verify validate_env_source rejects a bad env file.

    Creates a temp copy of omnia.env with SYSTEM_ADMIN_NIC_IPV4
    blanked out, then calls validate_env_source on it.
    Expects a non-zero exit code.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, rc.
    """
    clone_path = _resolve_clone_path()

    omnia_sh = f"{clone_path}/{OMNIA_SH_PATH}"
    omnia_env = f"{clone_path}/src/main/omnia.env"

    # Create a temp env file with empty SYSTEM_ADMIN_NIC_IPV4,
    # then source omnia.sh functions and call validate_env_source
    cmd = (
        f"bash -c '"
        f"tmp=$(mktemp); "
        f"sed \"s/^SYSTEM_ADMIN_NIC_IPV4=.*/SYSTEM_ADMIN_NIC_IPV4=/\" "
        f"{omnia_env} > \"$tmp\"; "
        f"source <(grep -A100 \"^validate_env_source()\" {omnia_sh}"
        f" | head -30); "
        f"validate_env_source \"$tmp\"; "
        f"rc=$?; rm -f \"$tmp\"; exit $rc"
        f"' 2>&1"
    )
    result = run_on_host(host, cmd)

    # validate_env_source should exit 1 for a blank IP
    rejected = result.rc != 0

    if rejected:
        return {
            "success": True,
            "details": (
                "validate_env_source correctly rejected "
                "empty SYSTEM_ADMIN_NIC_IPV4"
            ),
            "error": "",
            "rc": result.rc,
        }
    return {
        "success": False,
        "details": "",
        "error": (
            "validate_env_source accepted empty "
            "SYSTEM_ADMIN_NIC_IPV4 (should have failed)"
        ),
        "rc": result.rc,
    }


# =============================================================================
# ENVIRONMENT VERIFICATION
# =============================================================================

def check_env_file_installed(host) -> Dict[str, Any]:
    """Verify omnia.env is installed at /etc/omnia/omnia.env.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = CMDS["file_exists"].format(path=SYSTEM_ENV_FILE)
    result = run_on_host(host, cmd)

    if "exists" in result.stdout:
        return {
            "success": True,
            "details": SYSTEM_ENV_FILE,
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"{SYSTEM_ENV_FILE} not found",
    }


def check_profile_drop_in(host) -> Dict[str, Any]:
    """Verify /etc/profile.d/omnia-env.sh exists.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = CMDS["file_exists"].format(path=PROFILE_DROP_IN)
    result = run_on_host(host, cmd)

    if "exists" in result.stdout:
        return {
            "success": True,
            "details": PROFILE_DROP_IN,
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"{PROFILE_DROP_IN} not found",
    }


def check_env_vars_loaded(host) -> Dict[str, Any]:
    """Verify environment variables are set after sourcing profile.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing.
    """
    missing: List[str] = []
    loaded: List[str] = []

    for var_name in OPTIONAL_ENV_VARS:
        cmd = CMDS["source_profile_and_check"].format(
            profile_file=PROFILE_DROP_IN,
            var_name=var_name,
        )
        result = run_on_host(host, cmd)
        value = result.stdout.strip()
        if value:
            loaded.append(f"{var_name}={value}")
        else:
            missing.append(var_name)

    if not missing:
        return {
            "success": True,
            "details": f"{len(loaded)} vars loaded",
            "error": "",
            "missing": [],
        }
    return {
        "success": False,
        "details": f"{len(loaded)} loaded, {len(missing)} missing",
        "error": f"Missing: {', '.join(missing)}",
        "missing": missing,
    }


# =============================================================================
# VENV VERIFICATION
# =============================================================================

def check_venv_created(host) -> Dict[str, Any]:
    """Verify Python venv exists at OMNIA_VENV_PATH.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    activate = f"{venv_path}/bin/activate"
    cmd = CMDS["file_exists"].format(path=activate)
    result = run_on_host(host, cmd)

    if "exists" in result.stdout:
        return {
            "success": True,
            "details": venv_path,
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"Venv not found at {venv_path}",
    }


def check_ansible_available(host) -> Dict[str, Any]:
    """Verify ansible is available in the venv.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    cmd = CMDS["venv_ansible_version"].format(venv_path=venv_path)
    result = run_on_host(host, cmd)

    if result.rc == 0 and result.stdout.strip():
        version = result.stdout.strip().split("\n")[0]
        return {
            "success": True,
            "details": version,
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": "Ansible not found in venv",
    }


# =============================================================================
# DIRECTORY VERIFICATION
# =============================================================================

def check_base_dirs_created(host) -> Dict[str, Any]:
    """Verify base directories created by omnia.sh --setup-venv.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing.
    """
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )

    missing: List[str] = []
    present: List[str] = []

    for dir_tmpl in BASE_DIRS:
        dir_path = dir_tmpl.format(data_path=data_path)
        cmd = CMDS["dir_exists"].format(path=dir_path)
        result = run_on_host(host, cmd)
        if "exists" in result.stdout:
            present.append(dir_path)
        else:
            missing.append(dir_path)

    if not missing:
        return {
            "success": True,
            "details": f"{len(present)} directories present",
            "error": "",
            "missing": [],
        }
    return {
        "success": False,
        "details": f"{len(present)} present, {len(missing)} missing",
        "error": f"Missing: {', '.join(missing)}",
        "missing": missing,
    }


def check_activate_helper(host) -> Dict[str, Any]:
    """Verify activate-omnia.sh helper script exists.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    helper_path = f"{data_path}/activate-omnia.sh"

    cmd = CMDS["file_exists"].format(path=helper_path)
    result = run_on_host(host, cmd)

    if "exists" in result.stdout:
        return {
            "success": True,
            "details": helper_path,
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"activate-omnia.sh not found at {helper_path}",
    }


# =============================================================================
# DOMAIN INIT VERIFICATION
# =============================================================================

def check_domain_log_dirs(
    host, domains: List[str] = None
) -> Dict[str, Any]:
    """Verify domain log directories created under /var/log/omnia/.

    Args:
        host: Testinfra host connection.
        domains: Optional list of domains to check.
                 Defaults to DOMAINS_WITH_INIT (all domains).

    Returns:
        Dict with keys: success, details, error, missing, found.
    """
    missing: List[str] = []
    present: List[str] = []

    check_domains = domains if domains is not None else DOMAINS_WITH_INIT
    for domain in check_domains:
        cmd = CMDS["domain_log_dir_exists"].format(domain=domain)
        result = run_on_host(host, cmd)
        log_dir = f"/var/log/omnia/{domain}"
        if "exists" in result.stdout:
            present.append(log_dir)
        else:
            missing.append(log_dir)

    if not missing:
        return {
            "success": True,
            "details": f"{len(present)} log directories present",
            "error": "",
            "missing": [],
            "found": present,
        }
    return {
        "success": False,
        "details": f"{len(present)} present, {len(missing)} missing",
        "error": f"Missing: {', '.join(missing)}",
        "missing": missing,
        "found": present,
    }


def check_domain_input_staged(
    host, domain: str
) -> Dict[str, Any]:
    """Verify domain input files staged to data path.

    Args:
        host: Testinfra host connection.
        domain: Domain name to check.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    cmd = CMDS["domain_input_file_count"].format(
        data_path=data_path,
        domain=domain,
        project=project,
    )
    result = run_on_host(host, cmd)
    count = result.stdout.strip()

    try:
        file_count = int(count)
    except ValueError:
        file_count = 0

    if file_count > 0:
        return {
            "success": True,
            "details": f"{file_count} file(s) for {domain}",
            "error": "",
            "file_count": file_count,
        }
    return {
        "success": False,
        "details": "",
        "error": f"No input files staged for {domain}",
        "file_count": 0,
    }


def check_domain_output_dirs(
    host,
) -> Dict[str, Any]:
    """Verify domain output directories created by domain-init.sh.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing.
    """
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    project = config.get(
        "project_name", "project_default"
    )

    missing: List[str] = []
    present: List[str] = []

    for domain in DOMAINS_WITH_INIT:
        cmd = CMDS["domain_output_dir_exists"].format(
            data_path=data_path,
            domain=domain,
            project=project,
        )
        result = run_on_host(host, cmd)
        output_dir = (
            f"{data_path}/{domain}/output/{project}"
        )
        if "exists" in result.stdout:
            present.append(output_dir)
        else:
            missing.append(output_dir)

    if not missing:
        return {
            "success": True,
            "details": (
                f"{len(present)} output directories present"
            ),
            "error": "",
            "missing": [],
        }
    return {
        "success": False,
        "details": (
            f"{len(present)} present, "
            f"{len(missing)} missing"
        ),
        "error": f"Missing: {', '.join(missing)}",
        "missing": missing,
    }


# =============================================================================
# CLI VERIFICATION
# =============================================================================

def check_help_output(host) -> Dict[str, Any]:
    """Verify omnia.sh --help returns expected sections.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing_sections.
    """
    result = run_omnia_cmd(host, "omnia_sh_help")
    output = result["output"]

    expected_sections = [
        "USAGE:",
        "SETUP COMMANDS",
        "EXECUTION COMMANDS:",
        "OPTIONS:",
        "DOMAINS:",
        "EXAMPLES:",
    ]

    missing = [
        s for s in expected_sections if s not in output
    ]

    if not missing:
        return {
            "success": True,
            "details": f"All {len(expected_sections)} sections present",
            "error": "",
            "missing_sections": [],
        }
    return {
        "success": False,
        "details": output[:200],
        "error": f"Missing: {', '.join(missing)}",
        "missing_sections": missing,
    }


def check_error_contains(
    output: str, expected: str
) -> bool:
    """Check if command output contains an expected string.

    Args:
        output: Command output text.
        expected: Expected substring.

    Returns:
        True if expected string found in output.
    """
    return expected.lower() in output.lower()


# =============================================================================
# VENV CONTENT VERIFICATION
# =============================================================================

def check_pip_packages(host) -> Dict[str, Any]:
    """Verify expected pip packages installed in venv.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing.
    """
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    cmd = CMDS["venv_pip_list"].format(venv_path=venv_path)
    result = run_on_host(host, cmd)
    output = result.stdout.lower()

    expected_packages = [
        "ansible-core",
    ]

    missing: List[str] = []
    found: List[str] = []

    for pkg in expected_packages:
        if pkg.lower() in output:
            found.append(pkg)
        else:
            missing.append(pkg)

    if not missing:
        return {
            "success": True,
            "details": ", ".join(found),
            "error": "",
            "missing": [],
        }
    return {
        "success": False,
        "details": f"{len(found)} found, {len(missing)} missing",
        "error": f"Missing: {', '.join(missing)}",
        "missing": missing,
    }


def check_galaxy_collections(host) -> Dict[str, Any]:
    """Verify Galaxy collections installed in venv.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config = load_test_config()
    venv_path = config.get("venv_path", "/opt/omnia/venv")

    cmd = CMDS["venv_galaxy_list"].format(venv_path=venv_path)
    result = run_on_host(host, cmd)
    output = result.stdout.strip()

    # Count collection lines (format: namespace.name  version)
    lines = [
        ln for ln in output.split("\n")
        if ln.strip() and "." in ln.split()[0]
        if not ln.startswith("#")
    ]

    if lines:
        return {
            "success": True,
            "details": f"{len(lines)} collection(s)",
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": "No Galaxy collections found",
    }


# =============================================================================
# OMNIA-CLI VERIFICATION
# =============================================================================

def run_omnia_cli_cmd(
    host, cmd_key: str, **kwargs
) -> Dict[str, Any]:
    """Run an omnia-cli command on the target host.

    Uses ``_resolve_clone_path()`` so that local mode resolves paths
    from the source tree and remote mode uses ``clone_path`` from config.

    Args:
        host: Testinfra host connection.
        cmd_key: Key into the CMDS dict.
        **kwargs: Format parameters for the command template.

    Returns:
        Dict with keys: success, rc, output, error.
    """
    kwargs.setdefault("clone_path", _resolve_clone_path())
    kwargs.setdefault("omnia_cli", OMNIA_CLI_PATH)

    cmd = CMDS[cmd_key].format(**kwargs)
    result = run_on_host(host, cmd)

    return {
        "success": result.rc == 0,
        "rc": result.rc,
        "output": result.stdout.strip(),
        "error": result.stderr.strip() if result.rc != 0 else "",
    }


def run_omnia_cli_expect_error(
    host, cmd_key: str, **kwargs
) -> Dict[str, Any]:
    """Run an omnia-cli command expecting a non-zero exit code.

    Uses ``_resolve_clone_path()`` so that local mode resolves paths
    from the source tree and remote mode uses ``clone_path`` from config.

    Args:
        host: Testinfra host connection.
        cmd_key: Key into the CMDS dict.
        **kwargs: Format parameters for the command template.

    Returns:
        Dict with keys: success (True if rc!=0), rc, output, error.
    """
    kwargs.setdefault("clone_path", _resolve_clone_path())
    kwargs.setdefault("omnia_cli", OMNIA_CLI_PATH)

    cmd = CMDS[cmd_key].format(**kwargs)
    result = run_on_host(host, cmd)

    return {
        "success": result.rc != 0,
        "rc": result.rc,
        "output": result.stdout.strip(),
        "error": result.stderr.strip(),
    }


def check_cli_help_output(host) -> Dict[str, Any]:
    """Verify omnia-cli help returns expected sections.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error, missing_sections.
    """
    result = run_omnia_cli_cmd(host, "omnia_cli_help")
    output = result["output"]

    missing = [
        s for s in OMNIA_CLI_HELP_SECTIONS if s not in output
    ]

    if not missing:
        return {
            "success": True,
            "details": (
                f"All {len(OMNIA_CLI_HELP_SECTIONS)} sections"
            ),
            "error": "",
            "missing_sections": [],
        }
    return {
        "success": False,
        "details": output[:200],
        "error": f"Missing: {', '.join(missing)}",
        "missing_sections": missing,
    }


def check_cli_version_output(host) -> Dict[str, Any]:
    """Verify omnia-cli version shows release info.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    result = run_omnia_cli_cmd(host, "omnia_cli_version")
    output = result["output"]

    if OMNIA_RELEASE in output:
        return {
            "success": True,
            "details": OMNIA_RELEASE,
            "error": "",
        }
    return {
        "success": False,
        "details": output[:200],
        "error": f"Release '{OMNIA_RELEASE}' not found",
    }
