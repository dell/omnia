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

import os

# =============================================================================
# SETTINGS STORE
# =============================================================================

_settings: dict = {
    "ssh_opts": (
        "-o StrictHostKeyChecking=no "
        "-o UserKnownHostsFile=/dev/null "
        "-o LogLevel=ERROR"
    ),
    "ssh_options_list": [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=10",
    ],
    "default_verbosity": 1,
    "default_timeout": 7200,
    "line_width": 160,
    "runner_logger_name": "playbook_runner",
}


# =============================================================================
# PUBLIC API
# =============================================================================

def configure(**kwargs) -> None:
    """Set or override package settings.

    Accepts any keyword argument.  Standard keys are listed in the
    example below; additional keys are stored and retrievable via
    ``get_setting()``.

    Example::

        omnia_auto.configure(
            module_root="/root/my-module/test",
            config_file="test_config.yml",
            credentials_file="test_creds.yml",
            credentials_key=".test_creds.key",
            ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
            ssh_options_list=["-o", "StrictHostKeyChecking=no", ...],
            default_verbosity=1,
            default_timeout=7200,
            line_width=160,
            runner_logger_name="playbook_runner",
        )
    """
    for key, value in kwargs.items():
        if key == "module_root" and value:
            _settings[key] = os.path.abspath(value)
        else:
            _settings[key] = value


def get_setting(key: str, default=None):
    """Get a configured setting value.

    Args:
        key: Setting name.
        default: Fallback if the key has not been configured.

    Returns:
        The stored value, or *default*.
    """
    val = _settings.get(key)
    return val if val is not None else default


def init_module_root(path: str) -> None:
    """Convenience wrapper — sets ``module_root``."""
    _settings["module_root"] = os.path.abspath(path)


def get_module_root() -> str:
    """Get the module root directory.

    Resolution order:
      1. Value set via ``init_module_root()`` / ``configure()``
      2. ``OMNIA_TEST_ROOT`` environment variable

    Raises:
        RuntimeError: If module_root was never configured.
    """
    root = _settings.get("module_root")
    if root:
        return root
    env = os.environ.get("OMNIA_TEST_ROOT")
    if env:
        _settings["module_root"] = os.path.abspath(env)
        return _settings["module_root"]
    raise RuntimeError(
        "module_root not configured. "
        "Call omnia_auto.configure(module_root=...) first."
    )
