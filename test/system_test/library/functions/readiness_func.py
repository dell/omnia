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

"""Readiness of the OIM for the SVT stages: the setup record and what ``./run_validation.sh`` needs.

``./setup_env.sh`` writes reports/setup/setup.json; these functions read it, compare it with the
inputs and the installed Omnia, and say what must be done again. The stage runner uses them to
refuse a stage on an OIM that is not ready.
"""

import hashlib
import json
import os
from typing import Any, Dict, List, Tuple

from .config_func import theme_config_path
from .fvt_func import domain_dir
from .omnia_func import credential_path, missing_credentials, omnia_env, setup_problems
from ..messages.svt_msgs import CATALOG_MSGS, SETUP_MSGS
from ..vars.catalog_vars import CATALOG_PLAN_FILE, load_plan
from ..vars.common_vars import (
    DEFAULT_THEME,
    FVT_REQUIREMENTS,
    FVT_SETUP,
    INPUTS_FILE,
    OMNIA_AUTO_WHEEL,
    OMNIA_VENV_KEY,
    REQUIREMENTS_MARKER,
    RUN_STATE,
    SETUP_RECORD,
    SETUP_REPORT_DIR,
)
from ..vars.theme_vars import THEMES

Check = Tuple[str, bool, str]


def sha256(path: str) -> str:
    """Return the SHA-256 of a file ("" when it is absent)."""
    try:
        with open(path, "rb") as stream:
            return hashlib.sha256(stream.read()).hexdigest()
    except OSError:
        return ""


def read_json(path: str) -> Dict[str, Any]:
    """Return the JSON mapping in ``path`` ({} when missing or not a mapping)."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_setup_record() -> Dict[str, Any]:
    """Return reports/setup/setup.json ({} before the first step)."""
    return read_json(os.path.join(SETUP_REPORT_DIR, SETUP_RECORD))


def omnia_venv_path() -> str:
    """Return OMNIA_VENV_PATH of the installed omnia.env ("" before omnia.sh -s)."""
    return omnia_env().get(OMNIA_VENV_KEY, "")


def requirements_checksum(domain: str) -> str:
    """Return one checksum of what a suite's setup_env.sh installs."""
    suite = domain_dir(domain)
    parts = [sha256(os.path.join(suite, FVT_REQUIREMENTS)), sha256(os.path.join(suite, FVT_SETUP)),
             sha256(OMNIA_AUTO_WHEEL)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def outdated_requirements(theme: str, venv: str) -> List[str]:
    """Return the theme suites whose test requirements are not (or no longer) in ``venv``."""
    marker = read_json(os.path.join(venv, REQUIREMENTS_MARKER)) if venv else {}
    return [domain for domain in THEMES[theme]["fvt_domains"]
            if marker.get(domain) != requirements_checksum(domain)]


def configure_problem(record: Dict[str, Any]) -> str:
    """Return why the inputs must be configured (again) ("" when current)."""
    configured = record.get("configure") or {}
    if configured.get("status") != "passed":
        return SETUP_MSGS["configure_first"]
    if configured.get("inputs_sha256") != sha256(INPUTS_FILE):
        return SETUP_MSGS["inputs_changed"].format(path=INPUTS_FILE)
    theme_config = theme_config_path(configured.get("theme") or DEFAULT_THEME)
    if configured.get("test_config_sha256") != sha256(theme_config):
        return SETUP_MSGS["inputs_changed"].format(path=theme_config)
    return ""


def _install_outdated(installed: Dict[str, Any], configured: Dict[str, Any]) -> bool:
    """Return whether the last configure changed what the last install installed.

    Compared: the generated src inputs (not user_inputs.yml itself) and the
    selected catalog. Records of an older SVT without the generated checksum
    fall back to the user_inputs.yml checksum.
    """
    if installed.get("generated_sha256") and configured.get("generated_sha256"):
        return (installed["generated_sha256"] != configured["generated_sha256"]
                or installed.get("catalog_selected", "") != configured.get("catalog", ""))
    return installed.get("inputs_sha256") != configured.get("inputs_sha256")


def catalog_plan_problem(path: str = CATALOG_PLAN_FILE, run_file: str = RUN_STATE) -> str:
    """Return why the catalog plan does not belong to the current run ("" when it does)."""
    run_id = read_json(run_file).get("run_id", "")
    plan = load_plan(path)
    if not plan:
        return CATALOG_MSGS["plan_missing"].format(run_id=run_id, path=path)
    if plan.get("run_id") != run_id:
        return CATALOG_MSGS["plan_other_run"].format(path=path, plan_run=plan.get("run_id"),
                                                     run_id=run_id)
    return ""


def readiness_checks(theme: str) -> List[Check]:
    """Return (label, ok, how to fix) for everything ./run_validation.sh needs."""
    record = load_setup_record()
    checks: List[Check] = []
    problem = configure_problem(record)
    checks.append((f"Inputs configured (user_inputs.yml, {theme}_test_config.yml)",
                   not problem, problem))
    setup = setup_problems(theme)
    checks.append(("Omnia installed (omnia.sh -s: omnia.env, data path, venv, domain inputs)",
                   not setup, "; ".join(setup)))
    installed = record.get("install") or {}
    if installed.get("status") == "failed":
        detail = SETUP_MSGS["install_failed"].format(
            error=(installed.get("error") or "").splitlines()[0] if installed.get("error") else "")
    elif installed.get("status") != "passed":
        detail = SETUP_MSGS["install_first"]
    elif _install_outdated(installed, record.get("configure") or {}):
        detail = SETUP_MSGS["install_again"]
    else:
        detail = ""
    checks.append(("Installed after the last configure", not detail, detail))
    if THEMES[theme].get("catalog_plan"):
        detail = catalog_plan_problem()
        checks.append(("Catalog plan of this run (configure)", not detail, detail))
    if setup:
        checks.append(("Test requirements in the Omnia venv", False, SETUP_MSGS["install_first"]))
        checks.append(("Domain credentials", False, SETUP_MSGS["creds_after_install"]))
        return checks
    outdated = outdated_requirements(theme, omnia_venv_path())
    detail = (SETUP_MSGS["requirements_outdated"].format(domains=", ".join(outdated))
              if outdated else "")
    label = f"Test requirements in the Omnia venv ({len(THEMES[theme]['fvt_domains'])} suites)"
    checks.append((label, not outdated, detail))
    missing = missing_credentials(theme)
    env = omnia_env()
    for domain in THEMES[theme]["credential_domains"]:
        detail = SETUP_MSGS["creds_missing"].format(
            domain=domain, path=credential_path(env, domain)) if domain in missing else ""
        checks.append((f"Credentials: {domain}", not detail, detail))
    return checks


def readiness_problems(theme: str) -> List[str]:
    """Return how to fix everything that blocks the SVT stages ([] when ready)."""
    return [detail for _, ok, detail in readiness_checks(theme) if not ok]
