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

from ..vars.execute_vars import (
    CMDS,
    RAW_ARGUMENT_CMDS,
)
from ..vars.common_vars import ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME

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


def path_exists(host: Any, path: str) -> bool:
    """Return whether a path exists on the OIM."""
    return run_cmd(host, "path_exists", path=path).rc == 0


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
