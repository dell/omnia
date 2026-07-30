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

"""Playbook Path Registry — single source of truth for playbook locations.

Reads playbook_paths.yml at module load time and exposes a lookup function.
When domain segregation is complete, only the YAML file needs updating —
no Python code changes required.

Usage:
    from core.common.playbook_registry import get_playbook_path

    path = get_playbook_path("provision.yml")
    # Returns "/omnia/provision/provision.yml"
"""

import os
from pathlib import Path
from typing import Optional

from api.logging_utils import log_secure_info

_PLAYBOOK_PATHS_FILE = Path(os.getenv(
    "PLAYBOOK_PATHS_CONFIG",
    str(Path(__file__).resolve().parent.parent.parent / "playbook_paths.yml"),
))


def _load_mapping(config_path: Path) -> dict:
    """Load playbook name→path mapping from YAML config.

    Returns an empty dict on any error, which makes every lookup fail
    safely (no playbook can be resolved).
    """
    try:
        import yaml  # pylint: disable=import-outside-toplevel
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict) and isinstance(data.get("playbook_paths"), dict):
            return dict(data["playbook_paths"])
        log_secure_info("error", "playbook_paths.yml: missing 'playbook_paths' key")
        return {}
    except FileNotFoundError:
        log_secure_info("error", "playbook_paths.yml not found",
                        str(config_path)[:8])
        return {}
    except Exception:  # pylint: disable=broad-except
        log_secure_info("error", "Failed to load playbook_paths.yml",
                        exc_info=True)
        return {}


_REGISTRY: dict = _load_mapping(_PLAYBOOK_PATHS_FILE)


def get_playbook_path(playbook_name: str) -> Optional[str]:
    """Resolve a playbook filename to its absolute container path.

    Args:
        playbook_name: Filename only (e.g. ``"provision.yml"``).

    Returns:
        Absolute path string if found, ``None`` otherwise.
    """
    return _REGISTRY.get(playbook_name)


def get_all_playbook_names() -> list:
    """Return the list of all registered playbook names."""
    return list(_REGISTRY.keys())
