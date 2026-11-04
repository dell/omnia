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

"""Catalog selection, placement at CATALOG_FILE_PATH and version bumping.

Placement mirrors ``./omnia.sh --select-catalog``: the selected catalog (a
``--list-catalogs`` number or a full path) is validated, the active catalog is
backed up when it differs, and the catalog is installed at the path omnia.env
assigns to CATALOG_FILE_PATH.
"""

import json
import posixpath
from typing import Any, Dict, List, Optional, Tuple

from omnia_auto import read_remote_env

from . import db_func, gitlab_api_func
from .command_func import repository_path
from .execute_probe_func import run_cmd
from ..vars.execute_vars import (
    CATALOG_DEFAULT_FILE,
    CATALOG_IDENTIFIER_KEY,
    CATALOG_MAX_VERSION_ATTEMPTS,
    CATALOG_SAMPLES_DIR,
    CATALOG_SECTION,
    CATALOG_VARIANTS_DIR,
    CATALOG_VERSION_KEY,
    CATALOG_VERSION_RE,
    ENV_CATALOG_FILE_PATH,
    GITLAB_CADENCE_CATALOG_FILE,
    GITLAB_CATALOG_FILE,
    OMNIA_ENV_FILE,
)


def _exists(host: Any, path: str) -> bool:
    """Return whether a regular file exists on the OIM."""
    return run_cmd(host, "file_exists", path=path).rc == 0


def bundled_catalogs(host: Any) -> List[str]:
    """Return the bundled catalogs in ``./omnia.sh --list-catalogs`` order.

    Number 1 is samples/catalog_rhel.json (when present), followed by every
    JSON file under samples/catalogs sorted on the OIM, as omnia.sh does.
    """
    default = posixpath.join(repository_path(CATALOG_SAMPLES_DIR), CATALOG_DEFAULT_FILE)
    variants = run_cmd(host, "list_catalog_variants",
                       directory=repository_path(CATALOG_VARIANTS_DIR)).stdout
    return ([default] if _exists(host, default) else []) + [
        line.strip() for line in variants.splitlines() if line.strip()]


def resolve_catalog_source(host: Any, selection: str) -> Dict[str, Any]:
    """Resolve installation.catalog (number or full path) to a file on the OIM.

    Returns:
        Dict with keys: success, path, error.
    """
    if selection.isdigit():
        catalogs = bundled_catalogs(host)
        number = int(selection)
        if not 1 <= number <= len(catalogs):
            return {"success": False, "path": "",
                    "error": f"catalog number {number} is not in 1-{len(catalogs)} "
                             "(see ./omnia.sh --list-catalogs)"}
        return {"success": True, "path": catalogs[number - 1], "error": ""}
    if not _exists(host, selection):
        return {"success": False, "path": "", "error": f"catalog file {selection} not found"}
    return {"success": True, "path": selection, "error": ""}


def catalog_target(host: Any) -> Dict[str, Any]:
    """Return CATALOG_FILE_PATH as resolved by sourcing omnia.env on the OIM.

    Returns:
        Dict with keys: success, path, error.
    """
    path = read_remote_env(host, ENV_CATALOG_FILE_PATH, env_file=OMNIA_ENV_FILE,
                           required=False) or ""
    if not posixpath.isabs(path) or not path.endswith(".json"):
        return {"success": False, "path": path,
                "error": f"{ENV_CATALOG_FILE_PATH} must be an absolute .json path "
                         f"in {OMNIA_ENV_FILE} (got {path!r})"}
    return {"success": True, "path": path, "error": ""}


def read_catalog(host: Any, path: str) -> Dict[str, Any]:
    """Read and parse a catalog JSON file on the OIM.

    Returns:
        Dict with keys: success, catalog (dict), identifier, version, error.
    """
    result = run_cmd(host, "cat_file", path=path)
    if result.rc != 0:
        return {"success": False, "catalog": {}, "identifier": "", "version": "",
                "error": f"cannot read {path} (rc={result.rc})"}
    return parse_catalog(result.stdout, path)


def parse_catalog(content: str, label: str) -> Dict[str, Any]:
    """Parse catalog JSON text and extract its identifier and version."""
    try:
        catalog = json.loads(content)
        section = catalog[CATALOG_SECTION]
        return {"success": True, "catalog": catalog,
                "identifier": str(section.get(CATALOG_IDENTIFIER_KEY, "")),
                "version": str(section.get(CATALOG_VERSION_KEY, "")), "error": ""}
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        return {"success": False, "catalog": {}, "identifier": "", "version": "",
                "error": f"{label} is not a valid catalog: {exc}"}


def selected_catalog(host: Any, selection: str) -> Dict[str, Any]:
    """Read the catalog chosen by installation.catalog (number or full path).

    This is the catalog the build and cadence tests commit to GitLab, so a
    run never commits whatever catalog happens to be active on the OIM.

    Returns:
        Dict with keys: success, path, catalog, identifier, version, error.
    """
    source = resolve_catalog_source(host, selection)
    if not source["success"]:
        return {"success": False, "path": "", "catalog": {}, "identifier": "",
                "version": "", "error": f"installation.catalog {selection}: {source['error']}"}
    parsed = read_catalog(host, source["path"])
    return {**parsed, "path": source["path"]}


def bump_minor(version: str) -> str:
    """Return the next minor version (``1.4`` -> ``1.5``; ``x`` -> ``x.1``)."""
    match = CATALOG_VERSION_RE.fullmatch(version or "")
    if not match:
        return f"{version or '1'}.1"
    return f"{match.group(1)}.{int(match.group(2)) + 1}"


def previous_minor(version: str) -> str:
    """Return the minor version before ``version`` (``1.5`` -> ``1.4``)."""
    major, minor = _version_key(version) or (1, 1)
    return f"{major}.{max(minor - 1, 0)}"


def _version_key(version: str) -> Optional[Tuple[int, int]]:
    """Return ``(major, minor)`` for a ``X.Y`` version (None otherwise)."""
    match = CATALOG_VERSION_RE.fullmatch((version or "").strip())
    return (int(match.group(1)), int(match.group(2))) if match else None


def highest_version(*versions: str) -> str:
    """Return the highest ``X.Y`` version among ``versions`` (first one if none parse)."""
    valid = [v.strip() for v in versions if _version_key(v)]
    return max(valid, key=_version_key) if valid else (versions[0] if versions else "")


def next_catalog_version(host: Any, identifier: str, *known: str) -> Dict[str, str]:
    """Return the next minor version above every version already in use.

    The base is the highest of ``known`` (local catalog, GitLab
    catalog_rhel.json) and every catalog version recorded in image_groups
    for ``identifier``, so a version that was already committed (even by a
    failed build) is never reused. Candidates whose image group
    ``<identifier>-v<version>`` exists are skipped; BuildStream rejects
    duplicate image groups.

    Returns:
        Dict with keys: base, version, db_highest.
    """
    recorded = db_func.catalog_versions(host, identifier)
    db_highest = highest_version(*recorded) if recorded else ""
    base = highest_version(*known, *recorded)
    candidate = bump_minor(base)
    for _ in range(CATALOG_MAX_VERSION_ATTEMPTS):
        if db_func.image_group(host, f"{identifier}-v{candidate}") is None:
            return {"base": base, "version": candidate, "db_highest": db_highest}
        candidate = bump_minor(candidate)
    raise RuntimeError(f"no unused catalog version found after {base}")


def plan_catalog_version(host: Any, context: Dict[str, Any],
                         selected: Dict[str, Any]) -> Dict[str, Any]:
    """Pick the next unused version for the selected catalog.

    Versions already in use for the same catalog identifier are collected
    from the selected file, both GitLab catalogs (catalog_rhel.json and
    cadence_catalog_rhel.json), the active catalog at CATALOG_FILE_PATH and
    image_groups. Versions of other identifiers are ignored.

    Returns:
        Dict with keys: base, version, db_highest, seen (readable summary).
    """
    identifier = selected["identifier"]
    seen = {"selected": selected["version"]}
    for label, name in (("GitLab", GITLAB_CATALOG_FILE),
                        ("GitLab cadence", GITLAB_CADENCE_CATALOG_FILE)):
        remote = gitlab_api_func.get_file(context, name)
        parsed = parse_catalog(remote["content"], name) if remote["success"] else {}
        if parsed.get("identifier") == identifier:
            seen[label] = parsed["version"]
    target = catalog_target(host)
    active = read_catalog(host, target["path"]) if target["success"] else {}
    if active.get("identifier") == identifier:
        seen["active"] = active["version"]
    bump = next_catalog_version(host, identifier, *seen.values())
    seen["image_groups"] = bump["db_highest"]
    return {**bump, "seen": ", ".join(f"{k} {v or '-'}" for k, v in seen.items())}


def render_catalog(catalog: Dict[str, Any], version: str) -> str:
    """Serialize ``catalog`` with ``version`` set (2-space JSON + newline)."""
    updated = json.loads(json.dumps(catalog))
    updated[CATALOG_SECTION][CATALOG_VERSION_KEY] = version
    return json.dumps(updated, indent=2) + "\n"
