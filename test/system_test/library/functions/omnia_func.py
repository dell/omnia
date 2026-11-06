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

"""Checks of the Omnia setup on this OIM: omnia.env, data folders, venv and credentials.

Shared by ./setup_env.sh (before credentials are written) and the
initialization stage of ./run_validation.sh. Every function returns the
problems found as text that says how to fix them; nothing is changed.
"""

import os
from typing import Dict, List

from .fvt_func import read_env_file
from ..messages.svt_msgs import SETUP_MSGS
from ..vars.common_vars import (
    DOMAIN_DATA_KEY,
    DOMAIN_INPUT_DIR,
    OMNIA_ACTIVATE_SCRIPT,
    OMNIA_DATA_KEY,
    OMNIA_ENV_FILE,
    OMNIA_PROJECT_KEY,
    OMNIA_VENV_KEY,
    VAULT_HEADER,
    VIRTUAL_ENV_KEY,
)
from ..vars.theme_vars import CREDENTIAL_FILES, THEMES


def omnia_env() -> Dict[str, str]:
    """Return the installed omnia.env values ({} before omnia.sh -s)."""
    return read_env_file(OMNIA_ENV_FILE)


def activate_hint(env: Dict[str, str]) -> str:
    """Return the command that activates the Omnia venv."""
    data = env.get(OMNIA_DATA_KEY) or "<OMNIA_DATA_PATH>"
    return f"source {os.path.join(data, OMNIA_ACTIVATE_SCRIPT)}"


def domain_input_dir(env: Dict[str, str], domain: str) -> str:
    """Return <domain data>/input/<project>.

    The domain data root is <DOMAIN>_DATA_PATH, else <OMNIA_DATA_PATH>/<domain>.
    """
    root = (env.get(DOMAIN_DATA_KEY.format(domain=domain.upper()))
            or os.path.join(env.get(OMNIA_DATA_KEY, ""), domain))
    return os.path.join(root, DOMAIN_INPUT_DIR.format(project=env.get(OMNIA_PROJECT_KEY, "")))


def setup_problems(theme: str) -> List[str]:
    """Return why the Omnia setup (omnia.sh -s) is missing or incomplete ([] when ready)."""
    if not os.path.isfile(OMNIA_ENV_FILE):
        return [SETUP_MSGS["no_omnia_env"].format(path=OMNIA_ENV_FILE)]
    env = omnia_env()
    problems = [SETUP_MSGS["env_key_missing"].format(key=key, path=OMNIA_ENV_FILE)
                for key in (OMNIA_DATA_KEY, OMNIA_PROJECT_KEY, OMNIA_VENV_KEY)
                if not env.get(key)]
    if problems:
        return problems
    for path in (env[OMNIA_DATA_KEY], os.path.join(env[OMNIA_VENV_KEY], "bin", "python")):
        if not os.path.exists(path):
            problems.append(SETUP_MSGS["setup_path_missing"].format(path=path))
    for domain in THEMES[theme]["credential_domains"]:
        path = domain_input_dir(env, domain)
        if not os.path.isdir(path):
            problems.append(SETUP_MSGS["setup_path_missing"].format(path=path))
    return problems


def venv_problem() -> str:
    """Return why the active virtualenv is not the Omnia venv ("" when it is)."""
    env = omnia_env()
    venv = env.get(OMNIA_VENV_KEY, "")
    active = os.environ.get(VIRTUAL_ENV_KEY, "")
    if venv and active and os.path.realpath(active) == os.path.realpath(venv):
        return ""
    return SETUP_MSGS["venv_not_active"].format(
        venv=venv or "<OMNIA_VENV_PATH>", active=active or "none", hint=activate_hint(env))


def credential_path(env: Dict[str, str], domain: str) -> str:
    """Return the credential store of ``domain``."""
    return os.path.join(domain_input_dir(env, domain), CREDENTIAL_FILES[domain])


def _is_vault_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as stream:
            return stream.read(len(VAULT_HEADER)) == VAULT_HEADER
    except OSError:
        return False


def missing_credentials(theme: str) -> List[str]:
    """Return the domains of ``theme`` whose credential store is missing or not encrypted."""
    env = omnia_env()
    return [domain for domain in THEMES[theme]["credential_domains"]
            if not _is_vault_file(credential_path(env, domain))]
