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
omnia-auto — Central Configuration.

Provides ``configure()`` and ``get_setting()`` for package-wide
settings management.

Usage::

    import omnia_auto
    omnia_auto.configure(
        module_root      = os.path.dirname(__file__),
        config_file      = "test_config.yml",
        credentials_file = "test_creds.yml",
        credentials_key  = ".test_creds.key",
        default_timeout  = 3600,
    )
"""

from contextlib import contextmanager
from contextvars import ContextVar
import os
import shlex
from typing import Any, Dict, Iterator, Optional

# =============================================================================
# SETTINGS STORE
# =============================================================================

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "ssh_opts": (
        "-o StrictHostKeyChecking=accept-new "
        "-o LogLevel=ERROR"
    ),
    "ssh_options_list": [
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "LogLevel=ERROR",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=10",
    ],
    "default_verbosity": 1,
    "default_timeout": 7200,
    "line_width": 160,
    "runner_logger_name": "playbook_runner",
}

_SUPPORTED_SETTINGS = frozenset({
    *_DEFAULT_SETTINGS,
    "module_root",
    "repository_root",
    "config_file",
    "credentials_file",
    "credentials_key",
    "env_file",
    "venv_env_var",
})
_SETTINGS: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "omnia_auto_settings", default=None,
)


def _current_settings() -> Dict[str, Any]:
    """Return this execution context's mutable settings copy."""
    current = _SETTINGS.get()
    if current is None:
        current = dict(_DEFAULT_SETTINGS)
        current["ssh_options_list"] = list(
            _DEFAULT_SETTINGS["ssh_options_list"]
        )
        _SETTINGS.set(current)
    return current


def _validate_setting(key: str, value: Any) -> Any:
    """Validate one public configuration value."""
    if key not in _SUPPORTED_SETTINGS:
        raise TypeError(f"Unsupported omnia_auto setting: {key}")
    if key in {"module_root", "repository_root"}:
        if not isinstance(value, (str, os.PathLike)) or not value:
            raise ValueError(f"{key} must be a non-empty path")
        return os.path.abspath(os.fspath(value))
    if key in {
        "config_file", "credentials_file", "credentials_key", "env_file",
        "venv_env_var", "runner_logger_name",
    } and (not isinstance(value, str) or not value):
        raise ValueError(f"{key} must be a non-empty string")
    if key == "ssh_opts":
        return _join_ssh_options(value)
    if key == "ssh_options_list" and (
        not isinstance(value, (list, tuple))
        or not all(isinstance(item, str) for item in value)
    ):
        raise ValueError("ssh_options_list must contain only strings")
    if key == "ssh_options_list":
        return _parse_ssh_options(value)
    if key in {"default_timeout", "line_width"} and (
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
    ):
        raise ValueError(f"{key} must be a positive integer")
    if key == "default_verbosity" and (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value not in range(5)
    ):
        raise ValueError("default_verbosity must be an integer from 0 to 4")
    return value


def _join_ssh_options(value: Any) -> str:
    """Return validated SSH options in their stable text representation."""
    return shlex.join(_parse_ssh_options(value))


def _parse_ssh_options(value: Any) -> list[str]:
    """Load the SSH validator lazily to avoid package initialization cycles."""
    # Importing functions at module load time executes functions/__init__.py,
    # which imports this configuration module. The helper remains internal to
    # functions while configuration can still initialize independently.
    from ..functions._ssh_options import parse_ssh_options

    return parse_ssh_options(value)


# =============================================================================
# PUBLIC API
# =============================================================================

def configure(**kwargs) -> None:
    """Set or override package settings.

    Unknown names and invalid values are rejected so configuration typos fail
    during setup rather than changing execution behavior later.

    Example::

        omnia_auto.configure(
            module_root="/root/my-module/test",
            config_file="test_config.yml",
            credentials_file="test_creds.yml",
            credentials_key=".test_creds.key",
            ssh_opts="-o StrictHostKeyChecking=accept-new",
            ssh_options_list=["-o", "StrictHostKeyChecking=accept-new", ...],
            default_verbosity=1,
            default_timeout=7200,
            line_width=160,
            runner_logger_name="playbook_runner",
        )
    """
    updated = dict(_current_settings())
    for key, value in kwargs.items():
        updated[key] = _validate_setting(key, value)
    _SETTINGS.set(updated)


def get_setting(key: str, default=None):
    """Get a configured setting value.

    Args:
        key: Setting name.
        default: Fallback if the key has not been configured.

    Returns:
        The stored value, or *default*.
    """
    if key not in _SUPPORTED_SETTINGS:
        raise KeyError(f"Unsupported omnia_auto setting: {key}")
    val = _current_settings().get(key)
    resolved = val if val is not None else default
    if isinstance(resolved, list):
        return list(resolved)
    if isinstance(resolved, dict):
        return dict(resolved)
    return resolved


def init_module_root(path: str) -> None:
    """Convenience wrapper — sets ``module_root``."""
    configure(module_root=path)


def get_module_root() -> str:
    """Get the module root directory.

    Resolution order:
      1. Value set via ``init_module_root()`` / ``configure()``
      2. ``OMNIA_TEST_ROOT`` environment variable

    Raises:
        RuntimeError: If module_root was never configured.
    """
    settings = _current_settings()
    root = settings.get("module_root")
    if root:
        return root
    env = os.environ.get("OMNIA_TEST_ROOT")
    if env:
        configure(module_root=env)
        return get_setting("module_root")
    raise RuntimeError(
        "module_root not configured. "
        "Call omnia_auto.configure(module_root=...) first."
    )


@contextmanager
def configured(**kwargs) -> Iterator[None]:
    """Temporarily apply settings within the current execution context."""
    updated = dict(_current_settings())
    for key, value in kwargs.items():
        updated[key] = _validate_setting(key, value)
    token = _SETTINGS.set(updated)
    try:
        yield
    finally:
        _SETTINGS.reset(token)


def reset_configuration() -> None:
    """Reset settings in the current execution context to defaults."""
    _SETTINGS.set(None)
