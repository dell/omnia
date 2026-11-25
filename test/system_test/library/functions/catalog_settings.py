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

"""The catalog_build theme block of catalog_build_test_config.yml: check and normalize it.

Pure validation (no command runs, nothing is written), so config_func can load
it with the rest of the theme's settings. The runtime is catalog_func.py.
"""

import ast
import os
import re
from typing import Any, Dict, List, Tuple

from ..messages.svt_msgs import CATALOG_MSGS
from ..vars.common_vars import TEST_ROOT
from ..vars.catalog_vars import (
    CATALOG_CLEANUP_BETWEEN,
    CATALOG_DEFAULTS,
    CATALOG_REPO_CONFIGS,
    CATALOG_REPO_POLICIES,
    CATALOG_STEP_DOMAINS,
)

REPO_POLICY_KEY_RE = re.compile(r"^(\d+\.\d+)/(x86_64|aarch64)/([A-Za-z0-9_.-]+)$")
CATALOG_NAME_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
BOOL_KEYS = ("include_aarch64", "caching_policy", "force_rebuild", "continue_on_failure")


class CatalogSettingsError(ValueError):
    """The catalog_build block is invalid; the message says what to fix."""


def domain_fvt_tags(domain: str) -> List[str]:
    """Return FVT_TAGS of test/<domain>/library/vars/domain_vars.py ([] when unreadable).

    Read with ast, so the suite's own imports are never executed here.
    """
    path = os.path.join(TEST_ROOT, domain, "library", "vars", "domain_vars.py")
    try:
        with open(path, "r", encoding="utf-8") as stream:
            tree = ast.parse(stream.read())
    except (OSError, SyntaxError):
        return []
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
        if getattr(target, "id", None) == "FVT_TAGS" and node.value is not None:
            try:
                return [str(tag) for tag in ast.literal_eval(node.value)]
            except ValueError:
                return []
    return []


def _error(path: str, key: str, problem: str) -> CatalogSettingsError:
    return CatalogSettingsError(CATALOG_MSGS["invalid"].format(path=path, key=key, problem=problem))


def _catalogs(value: Any, path: str) -> Any:
    if value == "all":
        return "all"
    if not isinstance(value, list) or not value:
        raise _error(path, "catalogs", 'use "all" or a non-empty list of catalog names/numbers')
    catalogs = []
    for item in value:
        text = str(item).strip()
        if not text or not CATALOG_NAME_RE.fullmatch(text) or ".." in text.split("/"):
            raise _error(path, "catalogs", f"invalid catalog {item!r}")
        catalogs.append(text)
    if len(set(catalogs)) != len(catalogs):
        raise _error(path, "catalogs", "a catalog is listed twice")
    return catalogs


def _repo_policies(value: Any, path: str) -> Dict[str, Dict[str, Any]]:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise _error(path, "repo_policies", "must be a mapping")
    policies = {}
    for key, entry in value.items():
        where = f"repo_policies.{key}"
        if not REPO_POLICY_KEY_RE.fullmatch(str(key)):
            raise _error(path, where, 'key must be "<version>/<arch>/<repo>", e.g. '
                                      '"10.2/x86_64/epel"')
        if not isinstance(entry, dict) or not entry or set(entry) - {"policy", "caching"}:
            raise _error(path, where, "give policy and/or caching only")
        if "policy" in entry and entry["policy"] not in CATALOG_REPO_POLICIES:
            raise _error(path, where, f"policy must be one of {', '.join(CATALOG_REPO_POLICIES)}")
        if "caching" in entry and not isinstance(entry["caching"], bool):
            raise _error(path, where, "caching must be true or false")
        policies[str(key)] = dict(entry)
    return policies


def _steps(value: Any, path: str) -> Tuple[Tuple[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise _error(path, "steps", "must be a non-empty list of [domain, tag]")
    steps = []
    tags = {domain: domain_fvt_tags(domain) for domain in CATALOG_STEP_DOMAINS}
    for item in value:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or not all(isinstance(part, str) for part in item)):
            raise _error(path, "steps", f"{item!r} must be [domain, tag]")
        domain, tag = item
        if domain not in CATALOG_STEP_DOMAINS:
            raise _error(path, "steps", f"domain {domain!r} must be one of "
                                        f"{', '.join(CATALOG_STEP_DOMAINS)}")
        if tag not in tags[domain]:
            raise _error(path, "steps", f"{domain} has no FVT tag {tag!r} "
                                        f"(known: {', '.join(tags[domain]) or 'none found'})")
        steps.append((domain, tag))
    return tuple(steps)


def load_catalog_settings(block: Any, path: str) -> Dict[str, Any]:
    """Return the checked catalog_build block with every default filled in.

    Raises:
        CatalogSettingsError: An unknown key or an invalid value.
    """
    block = block or {}
    if not isinstance(block, dict):
        raise _error(path, "catalog_build", "must be a mapping")
    unknown = sorted(set(block) - set(CATALOG_DEFAULTS))
    if unknown:
        raise _error(path, ", ".join(unknown),
                     f"unknown key (known: {', '.join(CATALOG_DEFAULTS)})")
    settings = {**CATALOG_DEFAULTS, **block}
    for key in BOOL_KEYS:
        if not isinstance(settings[key], bool):
            raise _error(path, key, "must be true or false (without quotes)")
    if settings["repo_config"] not in CATALOG_REPO_CONFIGS:
        raise _error(path, "repo_config", f"must be one of {', '.join(CATALOG_REPO_CONFIGS)}")
    if settings["cleanup_between"] not in CATALOG_CLEANUP_BETWEEN:
        raise _error(path, "cleanup_between",
                     f"must be one of {', '.join(CATALOG_CLEANUP_BETWEEN)}")
    settings["catalogs"] = _catalogs(settings["catalogs"], path)
    settings["repo_policies"] = _repo_policies(settings["repo_policies"], path)
    steps = settings["steps"]
    settings["steps"] = steps if isinstance(steps, tuple) else _steps(steps, path)
    return settings


def describe_settings(settings: Dict[str, Any]) -> str:
    """Return the global sweep settings as one line (report and logs)."""
    overrides = ", ".join(f"{key}={value}" for key, value in settings["repo_policies"].items())
    return (f"repo_config={settings['repo_config']}, caching_policy={settings['caching_policy']}"
            f"{f', repo_policies: {overrides}' if overrides else ''}, "
            f"force_rebuild={settings['force_rebuild']}, "
            f"include_aarch64={settings['include_aarch64']}, "
            f"continue_on_failure={settings['continue_on_failure']}, "
            f"cleanup_between={settings['cleanup_between']}")
