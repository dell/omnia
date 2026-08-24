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
Paths in the YAML are relative to OMNIA_SRC_PATH (the ``omnia/src/``
directory).  The registry resolves them to absolute paths at load time.

Resolution order for OMNIA_SRC_PATH:
  1. ``OMNIA_SRC_PATH`` environment variable (if set and non-empty).
  2. Auto-detected from this file's location in the source tree:
     ``<this_file>/../../../../..`` → ``omnia/src/``.

Usage:
    from core.common.playbook_registry import get_playbook_path

    path = get_playbook_path("repo_manager.yml")
    # Returns "/home/user/omnia/src/repo_manager/playbooks/repo_manager.yml"
"""

import os
from pathlib import Path
from typing import Optional

from api.logging_utils import log_secure_info

_PLAYBOOK_PATHS_FILE = Path(os.getenv(
    "PLAYBOOK_PATHS_CONFIG",
    str(Path(__file__).resolve().parent.parent.parent / "playbook_paths.yaml"),
))

# Auto-detect: this file is at src/build_stream/app/core/common/playbook_registry.py
# so .parent x5 gives src/
_AUTO_DETECTED_SRC_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
)


def _get_omnia_src_path() -> str:
    """Return the Omnia source tree root (``omnia/src/``).

    Reads ``OMNIA_SRC_PATH`` from the environment.  Falls back to
    auto-detection from this file's location in the source tree.
    """
    return os.environ.get("OMNIA_SRC_PATH") or _AUTO_DETECTED_SRC_PATH


def _resolve_path(relative_path: str) -> str:
    """Resolve a relative playbook path to an absolute path.

    If the path is already absolute it is returned as-is (backward compat).
    Otherwise it is joined with OMNIA_SRC_PATH.
    """
    if os.path.isabs(relative_path):
        return relative_path
    return str(Path(_get_omnia_src_path()) / relative_path)


def _load_mapping(config_path: Path) -> dict:
    """Load playbook name→path mapping from YAML config.

    Relative paths are resolved against OMNIA_SRC_PATH.
    Returns an empty dict on any error, which makes every lookup fail
    safely (no playbook can be resolved).
    """
    try:
        import yaml  # pylint: disable=import-outside-toplevel
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict) and isinstance(data.get("playbook_paths"), dict):
            raw = data["playbook_paths"]
            return {name: _resolve_path(p) for name, p in raw.items()}
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
    """Resolve a playbook filename to its absolute path on the host.

    Args:
        playbook_name: Filename only (e.g. ``"repo_manager.yml"``).

    Returns:
        Absolute path string if found, ``None`` otherwise.
    """
    return _REGISTRY.get(playbook_name)


def get_all_playbook_names() -> list:
    """Return the list of all registered playbook names."""
    return list(_REGISTRY.keys())
