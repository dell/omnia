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
Credential management constants for omnia-auto.

Generic framework constants only — no domain-specific file names,
field definitions, or paths.  Each domain's ``setup_env.sh`` defines
its own file names and field lists and passes them to the credential
CLI at runtime.

Environment variables used:
    OMNIA_DATA_PATH      — Root data directory (default ``/opt/omnia``).
    OMNIA_PROJECT_NAME   — Active project (default ``project_default``).
"""

import os

# =============================================================================
# ENV VAR NAMES  (keys — never hardcode the *values*)
# =============================================================================

ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_OMNIA_PROJECT_NAME = "OMNIA_PROJECT_NAME"
ENV_OMNIA_VENV_PATH = "OMNIA_VENV_PATH"

# Defaults used when env vars are unset (match omnia.env defaults)
DEFAULT_DATA_PATH = "/opt/omnia"
DEFAULT_PROJECT_NAME = "project_default"

# =============================================================================
# VAULT SETTINGS
# =============================================================================

VAULT_KEY_LENGTH = 32
VAULT_FILE_MODE = 0o600
VAULT_HEADER = "$ANSIBLE_VAULT"
VAULT_TIMEOUT = 30

# =============================================================================
# PATH BUILDERS
# =============================================================================


def get_data_path() -> str:
    """Return OMNIA_DATA_PATH from environment.

    Returns:
        The value of ``OMNIA_DATA_PATH`` or the default.
    """
    return os.environ.get(ENV_OMNIA_DATA_PATH, DEFAULT_DATA_PATH)


def get_project_name() -> str:
    """Return OMNIA_PROJECT_NAME from environment.

    Returns:
        The value of ``OMNIA_PROJECT_NAME`` or the default.
    """
    return os.environ.get(ENV_OMNIA_PROJECT_NAME, DEFAULT_PROJECT_NAME)


def get_domain_input_path(domain: str) -> str:
    """Build ``<data_path>/<domain>/input/<project>/``.

    Args:
        domain: Domain name (e.g. ``telemetry``).

    Returns:
        Absolute path to the domain's input directory.
    """
    return os.path.join(
        get_data_path(), domain, "input", get_project_name(),
    )
