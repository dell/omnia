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

"""Dependency-free GitLab mode inputs and validators (hosted / external).

Pure functions over the parsed ``build_stream_config.yml`` and
``test_config.yml``: they need neither the OIM nor the ``omnia_auto`` plugin,
so the BuildStream unit job can run them.
"""

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .vars.execute_vars import (
    EXTERNAL_CA_MAX_MODE,
    GITLAB_DEFAULT_BRANCH,
    GITLAB_DEFAULT_PROJECT_NAME,
    GITLAB_DEFAULT_VISIBILITY,
    GITLAB_EXTERNAL_CONFIG_KEYS,
    GITLAB_MODE_HOSTED,
    GITLAB_MODE_KEY,
    GITLAB_MODES,
)

Probe = Tuple[str, str, bool]

DEFAULT_TOKEN_MIN_DAYS_REMAINING = 30
GITLAB_BLOCK_KEYS = {"expected_mode", "token_min_days_remaining"}

# Same syntax rules as plugins/module_utils/external_gitlab/url_checks.py.
_URL_RE = re.compile(
    r"^https://[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?$"
)
_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)*$")
_IPV4_RE = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def gitlab_mode_of(config: Dict[str, Any]) -> str:
    """Return the ``gitlab_mode`` of a parsed build_stream_config.yml ("" when unset)."""
    return str((config or {}).get(GITLAB_MODE_KEY) or "").strip().lower()


def external_settings(config: Dict[str, Any]) -> Dict[str, str]:
    """Return the external GitLab settings of a parsed input file, defaults applied.

    Returns:
        Dict with keys: url (no trailing slash), namespace, name, project_path
        (``<namespace>/<name>``), ca_path ("" = system trust store), branch,
        visibility.
    """
    keys = GITLAB_EXTERNAL_CONFIG_KEYS

    def text(name: str, default: str = "") -> str:
        value = (config or {}).get(keys[name])
        return str(value).strip() if value not in (None, "") else default

    namespace = text("namespace").strip("/")
    name = text("name", GITLAB_DEFAULT_PROJECT_NAME)
    return {
        "url": text("url").rstrip("/"),
        "namespace": namespace,
        "name": name,
        "project_path": f"{namespace}/{name}" if namespace else name,
        "ca_path": text("ca"),
        "branch": text("branch", GITLAB_DEFAULT_BRANCH),
        "visibility": text("visibility", GITLAB_DEFAULT_VISIBILITY),
    }


def is_valid_external_url(value: str) -> bool:
    """Return whether ``value`` is an HTTPS URL with a valid host and port."""
    if not _URL_RE.match(value or ""):
        return False
    port = re.search(r"^https://[^/:]+:([0-9]+)", value)
    return not port or 1 <= int(port.group(1)) <= 65535


def is_valid_namespace(value: str) -> bool:
    """Return whether ``value`` is a GitLab group path such as ``infra/omnia-builds``."""
    return bool(_NAMESPACE_RE.match(value or ""))


def gitlab_major_version(version: str) -> Optional[int]:
    """Return the major number of ``17.4.1-ee`` (None when unparsable)."""
    try:
        return int(str(version).split(".", maxsplit=1)[0])
    except ValueError:
        return None


def days_until(expires_at: str, today: Optional[date] = None) -> Optional[int]:
    """Return the whole days from ``today`` to a ``YYYY-MM-DD`` date (None when unset)."""
    if not expires_at:
        return None
    try:
        expiry = datetime.strptime(str(expires_at)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (expiry - (today or datetime.now(timezone.utc).date())).days


def mode_is_ca_safe(mode: str) -> bool:
    """Return whether an octal mode is 0644 or stricter with no execute bit."""
    try:
        value = int(mode, 8)
    except ValueError:
        return False
    return value & ~EXTERNAL_CA_MAX_MODE == 0 and value & 0o111 == 0


def mode_input_probes(mode: str, config: Dict[str, Any], expected_mode: str = "") -> List[Probe]:
    """Return the probes that validate the inputs ``mode`` needs.

    Hosted needs an IPv4 ``gitlab_host``; external needs an HTTPS
    ``gitlab_external_url``, a group path and, when set, a CA path.
    ``expected_mode`` ("" = any) must equal ``mode``.
    """
    keys = GITLAB_EXTERNAL_CONFIG_KEYS
    probes: List[Probe] = [("gitlab_mode", mode, True)]
    if expected_mode:
        probes.append(("Expected mode (test_config.yml gitlab.expected_mode)", expected_mode,
                       expected_mode == mode))
    if mode == GITLAB_MODE_HOSTED:
        host_value = str(config.get(keys["hosted_host"]) or "")
        probes.append((keys["hosted_host"], host_value or "MISSING",
                       bool(_IPV4_RE.match(host_value))))
        ignored = [keys[name] for name in ("url", "namespace")
                   if str(config.get(keys[name]) or "").strip()]
        if ignored:
            probes.append(("External-only inputs set", f"{', '.join(ignored)} (ignored)", True))
        return probes
    settings = external_settings(config)
    probes.append((keys["url"], settings["url"] or "MISSING",
                   is_valid_external_url(settings["url"])))
    probes.append((keys["namespace"], settings["namespace"] or "MISSING",
                   is_valid_namespace(settings["namespace"])))
    probes.append((keys["ca"], settings["ca_path"] or "not set (system trust store)", True))
    if str(config.get(keys["hosted_host"]) or "").strip():
        probes.append((keys["hosted_host"], "set, ignored in external mode", True))
    return probes


def validate_gitlab_block(gitlab: Optional[Dict[str, Any]]) -> None:
    """Validate the test_config.yml ``gitlab`` block.

    Raises:
        ValueError: On an unknown key, an unsupported ``expected_mode`` or an
            invalid ``token_min_days_remaining``.
    """
    gitlab = {} if gitlab is None else gitlab
    if not isinstance(gitlab, dict):
        raise ValueError("gitlab must be a mapping")
    unknown = set(gitlab) - GITLAB_BLOCK_KEYS
    if unknown:
        raise ValueError(f"gitlab has unsupported keys: {', '.join(sorted(unknown))}; "
                         f"supported: {', '.join(sorted(GITLAB_BLOCK_KEYS))}")
    mode = str(gitlab.get("expected_mode") or "").strip()
    if mode and mode not in GITLAB_MODES:
        raise ValueError(
            f"gitlab.expected_mode must be empty or one of {', '.join(GITLAB_MODES)}: {mode!r}"
        )
    days = gitlab.get("token_min_days_remaining", DEFAULT_TOKEN_MIN_DAYS_REMAINING)
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ValueError("gitlab.token_min_days_remaining must be an integer >= 0")


def gitlab_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the gitlab block with defaults applied.

    Returns:
        Dict with keys: expected_mode ("" = take the mode from the input file;
        ``hosted`` or ``external`` fails the run when the input file selects the
        other mode) and token_min_days_remaining (external mode: the personal
        access token must be valid for at least this many days; 0 = only an
        expired token fails).
    """
    gitlab = config.get("gitlab") or {}
    return {
        "expected_mode": str(gitlab.get("expected_mode") or "").strip(),
        "token_min_days_remaining": gitlab.get("token_min_days_remaining",
                                               DEFAULT_TOKEN_MIN_DAYS_REMAINING),
    }
