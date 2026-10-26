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
from datetime import datetime, timezone
from typing import Any, Dict, List

from omnia_auto import read_remote_env

from .command_func import repository_path
from .db_func import image_group
from .probe_func import run_cmd
from ..vars.common_vars import (
    CATALOG_BACKUP_SUFFIX,
    CATALOG_DEFAULT_FILE,
    CATALOG_IDENTIFIER_KEY,
    CATALOG_MAX_VERSION_ATTEMPTS,
    CATALOG_SAMPLES_DIR,
    CATALOG_SECTION,
    CATALOG_VARIANTS_DIR,
    CATALOG_VERSION_KEY,
    CATALOG_VERSION_RE,
    ENV_CATALOG_FILE_PATH,
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


def _sha256(host: Any, path: str) -> str:
    """Return the SHA-256 of a file on the OIM (empty when unreadable)."""
    result = run_cmd(host, "sha256_file", path=path)
    return result.stdout.split()[0] if result.rc == 0 and result.stdout else ""


def place_catalog(host: Any, selection: str) -> Dict[str, Any]:
    """Install the selected catalog (number or full path) at CATALOG_FILE_PATH.

    Returns:
        Dict with keys: success, source, target, backup, changed, sha256,
        identifier, version, error.
    """
    outcome = {"success": False, "source": "", "target": "", "backup": "",
               "changed": False, "sha256": "", "identifier": "", "version": "",
               "error": ""}
    source = resolve_catalog_source(host, selection)
    target = catalog_target(host)
    if not source["success"] or not target["success"]:
        outcome["error"] = source["error"] or target["error"]
        return outcome
    outcome.update(source=source["path"], target=target["path"])

    parsed = read_catalog(host, source["path"])
    if not parsed["success"]:
        outcome["error"] = parsed["error"]
        return outcome
    outcome.update(identifier=parsed["identifier"], version=parsed["version"])

    source_sha = _sha256(host, source["path"])
    current_sha = _sha256(host, target["path"]) if _exists(host, target["path"]) else ""
    if current_sha and current_sha != source_sha:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target["path"] + CATALOG_BACKUP_SUFFIX.format(timestamp=timestamp)
        if run_cmd(host, "copy_preserve", source=target["path"], target=backup).rc != 0:
            outcome["error"] = f"cannot back up {target['path']} to {backup}"
            return outcome
        outcome["backup"] = backup
    if current_sha != source_sha:
        if run_cmd(host, "install_file", source=source["path"], target=target["path"]).rc:
            outcome["error"] = f"cannot install {source['path']} at {target['path']}"
            return outcome
        outcome["changed"] = True

    outcome["sha256"] = _sha256(host, target["path"])
    outcome["success"] = bool(outcome["sha256"]) and outcome["sha256"] == source_sha
    if not outcome["success"]:
        outcome["error"] = f"{target['path']} does not match {source['path']} after install"
    return outcome


def bump_minor(version: str) -> str:
    """Return the next minor version (``1.4`` -> ``1.5``; ``x`` -> ``x.1``)."""
    match = CATALOG_VERSION_RE.fullmatch(version or "")
    if not match:
        return f"{version or '1'}.1"
    return f"{match.group(1)}.{int(match.group(2)) + 1}"


def next_catalog_version(host: Any, identifier: str, current: str) -> str:
    """Return the next minor version not yet used by an image group.

    A version is unused when no image group ``<identifier>-v<version>``
    exists; BuildStream rejects duplicate image groups.
    """
    candidate = bump_minor(current)
    for _ in range(CATALOG_MAX_VERSION_ATTEMPTS):
        if image_group(host, f"{identifier}-v{candidate}") is None:
            return candidate
        candidate = bump_minor(candidate)
    raise RuntimeError(f"no unused catalog version found after {current}")


def render_catalog(catalog: Dict[str, Any], version: str) -> str:
    """Serialize ``catalog`` with ``version`` set (2-space JSON + newline)."""
    updated = json.loads(json.dumps(catalog))
    updated[CATALOG_SECTION][CATALOG_VERSION_KEY] = version
    return json.dumps(updated, indent=2) + "\n"
