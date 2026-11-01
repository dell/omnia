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

"""Shared OIM command runner and state probes.

``run_cmd`` is the only way this suite executes a ``CMDS`` template: every
placeholder value is shell-quoted. Probes return ``(field_label, state_text,
ok)`` so verifiers can build report fields and failure lists uniformly;
``summarize`` prefixes every field with a check (ok) or cross (not ok).
Inspection errors are reported as failures rather than being mistaken for an
absent resource.
"""

import shlex
from typing import Any, Dict, List, Optional, Tuple

from omnia_auto import Symbols, read_remote_env, resolve_domain_data_path, run_on_host

from ..vars.common_vars import (
    CMDS,
    DOMAIN_CREDENTIAL_FILES,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    RAW_ARGUMENT_CMDS,
)

Probe = Tuple[str, str, bool]


def render_cmd(cmd_key: str, **params: Any) -> str:
    """Return ``CMDS[cmd_key]`` with every value shell-quoted.

    For templates listed in RAW_ARGUMENT_CMDS the ``arguments`` value is an
    already-quoted argument string and is inserted verbatim.
    """
    quoted = {
        name: (value if name == "arguments" and cmd_key in RAW_ARGUMENT_CMDS
               else shlex.quote(str(value)))
        for name, value in params.items()
    }
    return CMDS[cmd_key].format(**quoted)


def run_cmd(host: Any, cmd_key: str, **params: Any) -> Any:
    """Run ``CMDS[cmd_key]`` on the OIM (see ``render_cmd``).

    Returns:
        The Testinfra command result (rc, stdout, stderr).
    """
    return run_on_host(host, render_cmd(cmd_key, **params))


def data_path(host: Any) -> str:
    """Return OMNIA_DATA_PATH on the OIM.

    Raises:
        ValueError: When omnia.env does not set it (no fallback is used).
    """
    return read_remote_env(host, ENV_OMNIA_DATA_PATH).rstrip("/")


def project_name(host: Any) -> str:
    """Return OMNIA_PROJECT_NAME on the OIM.

    Raises:
        ValueError: When omnia.env does not set it (no fallback is used).
    """
    return read_remote_env(host, ENV_OMNIA_PROJECT_NAME)


def domain_data_path(host: Any, domain: str) -> str:
    """Return a non-empty ``<DOMAIN>_DATA_PATH``, else ``<OMNIA_DATA_PATH>/<domain>``."""
    try:
        return resolve_domain_data_path(
            host, domain, ENV_OMNIA_DATA_PATH, f"{domain.upper()}_DATA_PATH"
        )
    except ValueError:
        return f"{data_path(host)}/{domain}"


def domain_input_path(host: Any, domain: str) -> str:
    """Return the domain input directory for the active project."""
    return f"{domain_data_path(host, domain)}/input/{project_name(host)}"


def env_var_set(host: Any, name: str) -> Probe:
    """Check that omnia.env sets ``name`` to a non-empty value."""
    try:
        value = read_remote_env(host, name)
    except ValueError:
        return f"omnia.env {name}", "NOT SET", False
    return f"omnia.env {name}", value, True


def file_present(host: Any, path: str) -> Probe:
    """Check that a regular file exists on the OIM."""
    present = run_cmd(host, "file_exists", path=path).rc == 0
    return f"File {path}", "present" if present else "MISSING", present


def credential_store_probes(host: Any, domain: str) -> List[Probe]:
    """Check that a domain credential store and its vault key exist.

    A missing store makes the domain playbook prompt for credentials, which
    blocks an unattended run.
    """
    input_dir = domain_input_path(host, domain)
    return [file_present(host, f"{input_dir}/{name}")
            for name in DOMAIN_CREDENTIAL_FILES[domain]]


def container_absent(host: Any, name: str) -> Probe:
    """Podman exits 0 when the container exists and 1 when it does not."""
    result = run_cmd(host, "podman_container_exists", name=name)
    if result.rc == 1:
        return f"Container {name}", "removed", True
    if result.rc == 0:
        return f"Container {name}", "STILL EXISTS", False
    return f"Container {name}", f"inspection failed (rc={result.rc})", False


def container_running(host: Any, name: str) -> Probe:
    """A container is healthy when it runs and its healthcheck (if any) passes."""
    result = run_cmd(host, "podman_container_running", name=name)
    running, _, health = result.stdout.strip().partition(" ")
    if result.rc != 0 or running != "true":
        return f"Container {name}", f"NOT RUNNING ({running or 'absent'})", False
    if health and health != "healthy":
        return f"Container {name}", f"running, UNHEALTHY ({health})", False
    return f"Container {name}", f"running ({health})" if health else "running", True


def volume_present(host: Any, name: str) -> Probe:
    """A podman volume exists (podman exits 0 when it does)."""
    present = run_cmd(host, "podman_volume_exists", name=name).rc == 0
    return f"Volume {name}", "present" if present else "MISSING", present


def unit_inactive(host: Any, unit: str) -> Probe:
    """A unit is cleaned when it is not active."""
    state = run_cmd(host, "systemctl_is_active", unit=unit).stdout.strip() or "unknown"
    ok = state not in {"active", "activating"}
    return f"Unit {unit}", state if ok else f"STILL {state}", ok


def unit_active(host: Any, unit: str) -> Probe:
    """A unit is healthy when systemd reports it active."""
    state = run_cmd(host, "systemctl_is_active", unit=unit).stdout.strip() or "unknown"
    return f"Unit {unit}", state if state == "active" else f"NOT ACTIVE ({state})", (
        state == "active"
    )


def port_closed(host: Any, port: int) -> Probe:
    """A TCP port is closed when nothing listens on it."""
    result = run_cmd(host, "port_listening", port=int(port))
    if result.rc != 0:
        return f"TCP port {port}", f"inspection failed (rc={result.rc})", False
    listening = bool(result.stdout.strip())
    return f"TCP port {port}", "STILL LISTENING" if listening else "closed", not listening


def port_open(host: Any, port: int) -> Probe:
    """A TCP port is open when a process listens on it."""
    result = run_cmd(host, "port_listening", port=int(port))
    if result.rc != 0:
        return f"TCP port {port}", f"inspection failed (rc={result.rc})", False
    listening = bool(result.stdout.strip())
    return f"TCP port {port}", "listening" if listening else "NOT LISTENING", listening


def path_exists(host: Any, path: str) -> bool:
    """Return whether a path exists on the OIM."""
    return run_cmd(host, "path_exists", path=path).rc == 0


def capture_baseline(host: Any, paths: List[str]) -> Dict[str, bool]:
    """Record which to-be-preserved paths exist before cleanup runs."""
    return {path: path_exists(host, path) for path in paths}


def path_removed(host: Any, path: str) -> Probe:
    """Check that cleanup removed a path."""
    exists = path_exists(host, path)
    return f"Removed {path}", "STILL EXISTS" if exists else "removed", not exists


def path_preserved(host: Any, path: str, baseline: Dict[str, bool]) -> Probe:
    """Check that cleanup kept a path that existed before it ran."""
    if not baseline.get(path, False):
        return f"Preserved {path}", "absent before cleanup", True
    exists = path_exists(host, path)
    return f"Preserved {path}", "present" if exists else "DELETED", exists


def removed_or_preserved(host: Any, paths: List[str], remove: bool,
                         baseline: Dict[str, bool]) -> List[Probe]:
    """Return removal probes when ``remove`` is true, else preservation probes."""
    return [
        path_removed(host, path) if remove else path_preserved(host, path, baseline)
        for path in paths
    ]


def summarize(name: str, probes: List[Probe],
              extra_fields: Optional[List[Tuple[str, Any]]] = None) -> Dict[str, Any]:
    """Aggregate probes into a verifier result.

    Returns:
        Dict with keys: name, success, fields (label/state pairs), failures.
    """
    fields = list(extra_fields or [])
    fields.extend((f"{Symbols.CHECK if ok else Symbols.CROSS} {label}", state)
                  for label, state, ok in probes)
    failures = [f"{label}: {state}" for label, state, ok in probes if not ok]
    return {
        "name": name,
        "success": not failures,
        "fields": fields,
        "failures": failures,
    }
