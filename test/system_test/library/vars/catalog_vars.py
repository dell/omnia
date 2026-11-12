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

"""catalog_build theme data: settings defaults and the stages and tests of its plan.

``./setup_env.sh --theme catalog_build --configure`` resolves the catalog list
of catalog_build_test_config.yml (``./omnia.sh --list-catalogs``) and writes
the plan to CATALOG_PLAN_FILE. The theme is then data like any other theme:
one stage per catalog (catalog_01, catalog_02 ...) with its stage_info, and
one TEST_CASES entry per step, generated here from the plan. A changed
catalog_build_test_config.yml needs a new --configure (the run guard), so the
plan always belongs to the current run.

Each catalog stage runs, in order: ``select`` (catalog_overrides/, the global
settings, ./omnia.sh --select-catalog: an SVT action, not an FVT step), then
``<tag> exec`` and ``<tag> verify`` of every configured step, then the
cleanup_between steps (they run even after a failure).
"""

import json
import os
from typing import Any, Dict, List, Tuple

from .common_vars import REPORT_ROOT

FvtStep = Tuple[str, Tuple[str, ...]]

CATALOG_THEME = "catalog_build"
CATALOG_PLAN_FILE = os.path.join(REPORT_ROOT, "catalog_build_plan.json")
CATALOG_STAGE_PREFIX = "catalog_"
# Test IDs: SVT_CATALOG_BUILD_<catalog NN><step NN>; order: base + catalog * 100 + step.
CATALOG_ID_FORMAT = "SVT_CATALOG_BUILD_{index:02d}{step:02d}"
CATALOG_ORDER_BASE = 2000

# Domains whose FVT steps a catalog runs, and the playbook each one runs (after a
# failed exec its orphaned ansible-playbook workers are stopped, catalog_func).
CATALOG_STEP_DOMAINS = ("repo_manager", "image_build_manager")
CATALOG_STEP_PLAYBOOKS: Dict[str, str] = {
    "repo_manager": "repo_manager.yml",
    "image_build_manager": "image_build_manager.yml",
}
CATALOG_DEFAULT_STEPS: Tuple[Tuple[str, str], ...] = (
    ("repo_manager", "precheck"),
    ("repo_manager", "prepare"),
    ("repo_manager", "execute"),
    ("repo_manager", "status"),
    ("image_build_manager", "precheck"),
    ("image_build_manager", "validate"),
    ("image_build_manager", "prepare"),
    ("image_build_manager", "build"),
)
CATALOG_REPO_CONFIGS = ("always", "partial")
CATALOG_REPO_POLICIES = ("always", "partial", "never")
# cleanup_between -> FVT steps after every catalog. repo_manager has no whole-catalog
# repository cleanup (cleanup_repos takes one exact repository), so "repos" removes the
# repo_manager deployment; the next catalog prepares it again.
CATALOG_CLEANUP_BETWEEN: Dict[str, Tuple[FvtStep, ...]] = {
    "none": (),
    "images": (("image_build_manager", ("cleanup_images", "test")),),
    "repos": (("repo_manager", ("cleanup", "test", "--marker", "destructive")),),
    "full": (("image_build_manager", ("cleanup_images", "test")),
             ("image_build_manager", ("cleanup", "test")),
             ("repo_manager", ("cleanup", "test", "--marker", "destructive"))),
}
# Every key of the catalog_build block of catalog_build_test_config.yml, with its default.
CATALOG_DEFAULTS: Dict[str, Any] = {
    "catalogs": "all",
    "include_aarch64": False,
    "repo_config": "partial",
    "caching_policy": True,
    "repo_policies": {},
    "force_rebuild": True,
    "continue_on_failure": True,
    "cleanup_between": "none",
    "steps": CATALOG_DEFAULT_STEPS,
}
# SVT actions of a catalog stage (catalog_func.run_action).
ACTION_SELECT = "catalog_select"
ACTION_SKIP = "catalog_skip"


def load_plan(path: str = CATALOG_PLAN_FILE) -> Dict[str, Any]:
    """Return the plan written by --configure ({} when none or unreadable)."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            plan = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return plan if isinstance(plan, dict) and isinstance(plan.get("entries"), list) else {}


def catalog_stages(plan: Dict[str, Any]) -> Tuple[str, ...]:
    """Return the stage of every catalog of the plan, in run order."""
    return tuple(entry["stage"] for entry in plan.get("entries") or [])


def catalog_soft_stages(plan: Dict[str, Any]) -> Tuple[str, ...]:
    """Return the catalog stages whose failure does not stop the next (continue_on_failure)."""
    settings = plan.get("settings") or {}
    return catalog_stages(plan) if settings.get("continue_on_failure", True) else ()


def catalog_stage_info(plan: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """Return (title, description) of every catalog stage (report and pipeline)."""
    info = {}
    for entry in plan.get("entries") or []:
        title = f"Catalog {entry['index']}: {entry['catalog']}"
        description = entry["reason"] or (
            "./omnia.sh --select-catalog, then the repo_manager and image_build_manager FVT "
            "steps (exec, verify)")
        info[entry["stage"]] = (title, description)
    return info


def _case(entry: Dict[str, Any], number: int, name: str, title: str,
          **fields: Any) -> Tuple[str, Dict[str, Any]]:
    key = f"{CATALOG_THEME}_{entry['stage'][len(CATALOG_STAGE_PREFIX):]}_{name}"
    return key, {"id": CATALOG_ID_FORMAT.format(index=entry["index"], step=number),
                 "order": CATALOG_ORDER_BASE + entry["index"] * 100 + number,
                 "stage": entry["stage"], "title": f"{entry['catalog']}: {title}", **fields}


def _catalog_cases(entry: Dict[str, Any], settings: Dict[str, Any]) -> List[Tuple[str, Dict]]:
    if not entry["run"]:
        return [_case(entry, 0, "skip", "skipped", action=ACTION_SKIP, reason=entry["reason"],
                      step=("svt", ("skip", entry["catalog"])))]
    cases = [_case(entry, 0, "select",
                   "select (catalog_overrides, global settings, ./omnia.sh --select-catalog)",
                   action=ACTION_SELECT, catalog=entry["catalog"],
                   step=("svt", ("select", entry["catalog"])))]
    number = 0
    for domain, tag in settings.get("steps") or CATALOG_DEFAULT_STEPS:
        for action in ("exec", "verify"):
            number += 1
            cases.append(_case(entry, number, f"{domain}_{tag}_{action}",
                               f"{domain} {tag} {action}", step=(domain, (tag, action)),
                               stop_leftovers=action == "exec"))
    for domain, arguments in CATALOG_CLEANUP_BETWEEN.get(settings.get("cleanup_between"), ()):
        number += 1
        cases.append(_case(entry, number, f"cleanup_{domain}_{arguments[0]}",
                           f"cleanup_between: {domain} {arguments[0]}",
                           step=(domain, tuple(arguments)), always=True))
    return cases


def catalog_test_cases(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return the TEST_CASES entries of every catalog of the plan."""
    settings = plan.get("settings") or {}
    return dict(case for entry in plan.get("entries") or []
                for case in _catalog_cases(entry, settings))


CATALOG_PLAN = load_plan()
