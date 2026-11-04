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
Build Stream — Shared OIM Probes.

Every probe returns ``(label, state, ok)``. ``summarize_probes`` turns a
list of probes into a verification result whose fields carry a check or
cross mark per item, so every test prints each checked item.
``result_fields`` renders the older single-check result dictionaries the
same way.
"""

import shlex
from typing import Any, Dict, List, Tuple

from omnia_auto import (
    Symbols,
    read_remote_env,
    resolve_domain_data_path,
    run_on_host,
)

from library.vars.common_vars import (
    CMDS,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    RESULT_FAILED_ITEM_PREFIXES,
    RESULT_HIDDEN_KEYS,
)

Probe = Tuple[str, str, bool]


def run_cmd(host: Any, cmd_key: str, **params: Any) -> Any:
    """Run ``CMDS[cmd_key]`` on the OIM with every value shell-quoted.

    Returns:
        The Testinfra command result (rc, stdout, stderr).
    """
    quoted = {name: shlex.quote(str(value)) for name, value in params.items()}
    return run_on_host(host, CMDS[cmd_key].format(**quoted))


def domain_data_path(host: Any, domain: str) -> str:
    """Return ``<DOMAIN>_DATA_PATH`` when set, else ``OMNIA_DATA_PATH/<domain>``."""
    return resolve_domain_data_path(
        host, domain, ENV_OMNIA_DATA_PATH, f"{domain.upper()}_DATA_PATH",
    )


def domain_input_path(host: Any, domain: str) -> str:
    """Return the domain input directory for the active project."""
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    return f"{domain_data_path(host, domain)}/input/{project}"


def domain_output_path(host: Any, domain: str) -> str:
    """Return the domain output directory for the active project."""
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    return f"{domain_data_path(host, domain)}/output/{project}"


def _render_value(value: Any) -> Any:
    """Render a result value as a short report string."""
    if isinstance(value, dict):
        return ", ".join(f"{name}={item}" for name, item in value.items()) or "none"
    if isinstance(value, (list, tuple)):
        return "; ".join(str(_render_value(item)) for item in value) or "none"
    return value


def env_var_set(host: Any, name: str) -> Probe:
    """omnia.env sets ``name`` to a non-empty value."""
    try:
        return f"omnia.env {name}", read_remote_env(host, name), True
    except ValueError:
        return f"omnia.env {name}", "NOT SET", False


def file_present(host: Any, path: str) -> Probe:
    """A regular file exists on the OIM."""
    present = run_cmd(host, "file_exists", path=path).rc == 0
    return f"File {path}", "present" if present else "MISSING", present


def unit_active(host: Any, unit: str) -> Probe:
    """systemd reports the unit active."""
    state = run_cmd(host, "systemctl_is_active", service=unit).stdout.strip() or "unknown"
    ok = state == "active"
    return f"Unit {unit}", state if ok else f"NOT ACTIVE ({state})", ok


def container_running(host: Any, name: str) -> Probe:
    """The container runs and its healthcheck (when defined) passes."""
    result = run_cmd(host, "podman_container_state", container=name)
    running, _, health = result.stdout.strip().partition(" ")
    if result.rc != 0 or running != "true":
        return f"Container {name}", f"NOT RUNNING ({running or 'absent'})", False
    if health and health != "healthy":
        return f"Container {name}", f"running, UNHEALTHY ({health})", False
    return f"Container {name}", f"running ({health})" if health else "running", True


def volume_present(host: Any, name: str) -> Probe:
    """The podman volume exists."""
    present = run_cmd(host, "podman_volume_exists", volume=name).rc == 0
    return f"Volume {name}", "present" if present else "MISSING", present


def port_listening(host: Any, port: int) -> Tuple[bool, str]:
    """Return (inspected, listening-state) for a TCP port."""
    result = run_cmd(host, "port_listening", port=int(port))
    if result.rc != 0:
        return False, f"inspection failed (rc={result.rc})"
    return True, "listening" if result.stdout.strip() else "closed"


def port_open(host: Any, port: int) -> Probe:
    """A process listens on the TCP port."""
    inspected, state = port_listening(host, port)
    ok = inspected and state == "listening"
    return f"TCP port {port}", state if ok or not inspected else "NOT LISTENING", ok


def port_closed(host: Any, port: int) -> Probe:
    """Nothing listens on the TCP port."""
    inspected, state = port_listening(host, port)
    ok = inspected and state == "closed"
    return f"TCP port {port}", state if ok or not inspected else "STILL LISTENING", ok


def summarize_probes(name: str, probes: List[Probe]) -> Dict[str, Any]:
    """Aggregate probes into a verification result.

    Returns:
        Dict with keys: name, success, fields (label/state pairs), failures,
        error (failed probes joined into one line).
    """
    fields = [(f"{Symbols.CHECK if ok else Symbols.CROSS} {label}", state)
              for label, state, ok in probes]
    failures = [f"{label}: {state}" for label, state, ok in probes if not ok]
    return {"name": name, "success": not failures, "fields": fields,
            "failures": failures, "error": "; ".join(failures)}


def failure_summary(result: Dict[str, Any]) -> str:
    """Return the failed probes of a result as one readable line."""
    return "; ".join(result.get("failures", [])) or result.get("error") or "no failure details"


def result_fields(result: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Return report fields for a result dictionary.

    Probe results already carry ``fields``. Single-check results are
    rendered from their keys: details first (one line each), every list item
    on its own line (marked with a cross for ``still_*``, ``missing`` and
    ``*errors`` keys, otherwise a check), dicts flattened to ``key=value``
    pairs; success and error are left out.
    """
    if "fields" in result:
        return list(result["fields"])
    fields = [("Details", line) for line in str(result.get("details") or "").splitlines()]
    for key, value in result.items():
        if key in RESULT_HIDDEN_KEYS or value in ("", None):
            continue
        label = key.replace("_", " ").capitalize()
        if isinstance(value, (list, tuple)) and value:
            ok = not key.startswith(RESULT_FAILED_ITEM_PREFIXES) and not key.endswith("errors")
            mark = Symbols.CHECK if ok else Symbols.CROSS
            fields.extend((f"{mark} {label}", _render_value(item)) for item in value)
        else:
            fields.append((label, _render_value(value)))
    return fields
