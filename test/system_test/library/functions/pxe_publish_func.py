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

"""Local SVT actions on the discovery PXE mapping file the orchestrator reads.

Discovery writes ``bmc_pxe_mapping_file_<ts>.csv`` and points the symlink
``bmc_pxe_mapping_file.csv`` at the newest one. These actions never edit an
existing file and never touch OME: they publish a new timestamped file with
one row removed and repoint the symlink, so the timestamp contract holds.

When ``use_discovery_mapping=true`` in the theme's test_config, the
``pxe_use_discovery_mapping`` action copies the latest timestamped
``bmc_pxe_mapping_file_<ts>.csv`` from the discovery output to the
orchestrator's ``pxe_mapping_file.csv`` input, replacing the static file
that the dataset generator wrote.
"""

import csv
import datetime
import glob
import io
import os
import shutil
import time
from typing import Any, Callable, Dict, List, Tuple

import yaml

from .fvt_func import read_env_file, step_info
from ..vars.common_vars import MODULE_ROOT
from ..vars.theme_vars import FvtStep

PXE_MAPPING_SYMLINK = "bmc_pxe_mapping_file.csv"
PXE_MAPPING_PREFIX = "bmc_pxe_mapping_file_"
ORCHESTRATOR_PXE_FILE = "pxe_mapping_file.csv"
GROUP_COLUMN = "FUNCTIONAL_GROUP_NAME"
HOST_COLUMN = "HOSTNAME"


def output_dir() -> str:
    """Return the discovery output folder of the installed Omnia (OMNIA_DATA_PATH/discovery)."""
    env = read_env_file()
    data = env.get("DISCOVERY_DATA_PATH") or os.path.join(env.get("OMNIA_DATA_PATH", ""),
                                                          "discovery")
    return os.path.join(data, "output", env.get("OMNIA_PROJECT_NAME", "project_default"))


def _read(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, "r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _write_csv(path: str, header: List[str], rows: List[Dict[str, str]]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    with open(path, "w", encoding="utf-8", newline="") as stream:
        stream.write(buffer.getvalue())


def _publish(folder: str, header: List[str], rows: List[Dict[str, str]]) -> str:
    """Write rows as a new timestamped mapping file and repoint the symlink to it."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    name = f"{PXE_MAPPING_PREFIX}{stamp}.csv"
    while os.path.exists(os.path.join(folder, name)):
        time.sleep(1)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        name = f"{PXE_MAPPING_PREFIX}{stamp}.csv"
    _write_csv(os.path.join(folder, name), header, rows)
    temp = os.path.join(folder, f".{PXE_MAPPING_SYMLINK}.svt")
    if os.path.lexists(temp):
        os.unlink(temp)
    os.symlink(name, temp)
    os.replace(temp, os.path.join(folder, PXE_MAPPING_SYMLINK))
    return name


def _newest(folder: str) -> str:
    """Return the file name the symlink points to."""
    link = os.path.join(folder, PXE_MAPPING_SYMLINK)
    if not os.path.islink(link):
        raise ValueError(f"{link} is not a symlink: run discovery first")
    return os.readlink(link)


def remove_last_node(group: str) -> Dict[str, Any]:
    """Publish the newest mapping without the last row (highest hostname) of ``group``.

    Returns:
        Dict with keys: success, removed (hostname), file (new file), source, output, error.
    """
    folder = output_dir()
    source = _newest(folder)
    header, rows = _read(os.path.join(folder, source))
    matches = sorted((row for row in rows if row.get(GROUP_COLUMN) == group),
                     key=lambda row: row.get(HOST_COLUMN, ""))
    if not matches:
        return {"success": False, "removed": "", "file": "", "source": source,
                "output": f"no row of group {group} in {source}",
                "error": f"no row of functional group {group} in {source}"}
    removed = matches[-1]
    kept = [row for row in rows if row is not removed]
    published = _publish(folder, header, kept)
    _, check = _read(os.path.join(folder, _newest(folder)))
    ok = (_newest(folder) == published and len(check) == len(rows) - 1
          and removed not in check and check == kept)
    text = (f"published {published} without {removed.get(HOST_COLUMN)} ({group}); "
            f"{len(check)} of {len(rows)} rows kept, symlink -> {published}")
    return {"success": ok, "removed": removed.get(HOST_COLUMN, ""), "file": published,
            "source": source, "output": text,
            "error": "" if ok else "the published file does not hold the expected rows"}


def orchestrator_input_dir() -> str:
    """Return the orchestrator input folder (OMNIA_DATA_PATH/orchestrator/input/<project>)."""
    env = read_env_file()
    data = env.get("ORCHESTRATOR_DATA_PATH") or os.path.join(env.get("OMNIA_DATA_PATH", ""),
                                                              "orchestrator")
    return os.path.join(data, "input", env.get("OMNIA_PROJECT_NAME", "project_default"))


def _latest_timestamped_file(folder: str) -> str:
    """Return the name of the latest ``bmc_pxe_mapping_file_<ts>.csv`` in ``folder``.

    Raises ValueError when no timestamped file exists.
    """
    files = sorted(name for name in os.listdir(folder)
                   if name.startswith(PXE_MAPPING_PREFIX) and name.endswith(".csv")
                   and name != PXE_MAPPING_SYMLINK)
    if not files:
        raise ValueError(f"no timestamped {PXE_MAPPING_PREFIX}*.csv in {folder}")
    return files[-1]


def _is_discovery_enabled() -> bool:
    """Return whether ``use_discovery_mapping`` is true in any ``*_test_config.yml``.

    Reads every ``<theme>_test_config.yml`` next to the SVT runner and returns
    True when any of them sets ``use_discovery_mapping: true``.  The default is
    False.
    """
    for path in sorted(glob.glob(os.path.join(MODULE_ROOT, "*_test_config.yml"))):
        try:
            with open(path, "r", encoding="utf-8") as stream:
                data = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict) and data.get("use_discovery_mapping") is True:
            return True
    return False


def use_discovery_mapping() -> Dict[str, Any]:
    """Copy the latest discovery ``bmc_pxe_mapping_file_<ts>.csv`` to the orchestrator input.

    When ``use_discovery_mapping=false`` (the default) in the theme's test_config, this is
    a successful no-op: the existing ``pxe_mapping_file.csv`` stays unchanged.

    When ``use_discovery_mapping=true``, replaces ``pxe_mapping_file.csv`` in the
    orchestrator input folder with the contents of the latest timestamped
    discovery output file.

    Returns:
        Dict with keys: success, source, target, output, error.
    """
    if not _is_discovery_enabled():
        return {"success": True, "source": "", "target": "",
                "output": "use_discovery_mapping=false (default): using existing "
                          "pxe_mapping_file.csv, no action taken",
                "error": ""}
    disc_folder = output_dir()
    orch_folder = orchestrator_input_dir()
    try:
        source_name = _latest_timestamped_file(disc_folder)
    except ValueError as exc:
        return {"success": False, "source": "", "target": "",
                "output": str(exc), "error": str(exc)}
    source_path = os.path.join(disc_folder, source_name)
    target_path = os.path.join(orch_folder, ORCHESTRATOR_PXE_FILE)
    if not os.path.isdir(orch_folder):
        return {"success": False, "source": source_path, "target": target_path,
                "output": f"orchestrator input folder {orch_folder} does not exist",
                "error": f"orchestrator input folder {orch_folder} does not exist"}
    shutil.copy2(source_path, target_path)
    # Verify the copy
    source_header, source_rows = _read(source_path)
    target_header, target_rows = _read(target_path)
    ok = source_header == target_header and len(source_rows) == len(target_rows)
    text = (f"use_discovery_mapping=true: copied {source_name} ({len(source_rows)} rows) from "
            f"{disc_folder} to {target_path}")
    return {"success": ok, "source": source_path, "target": target_path,
            "output": text,
            "error": "" if ok else "the copied file does not match the source"}


def check_newest_has_group(group: str) -> Dict[str, Any]:
    """Check the symlink points to the newest mapping and that group has rows in it.

    Returns:
        Dict with keys: success, output, error.
    """
    folder = output_dir()
    newest = _newest(folder)
    files = sorted(name for name in os.listdir(folder) if name.startswith(PXE_MAPPING_PREFIX))
    _, rows = _read(os.path.join(folder, newest))
    count = sum(1 for row in rows if row.get(GROUP_COLUMN) == group)
    ok = bool(files) and files[-1] == newest and count > 0
    return {"success": ok, "output": f"symlink -> {newest}; {count} row(s) of {group}",
            "error": "" if ok else "symlink is not the newest mapping or the group has no row"}


LOCAL_DOMAIN = "svt"
LOCAL_ACTIONS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "pxe_remove_last_node": remove_last_node,
    "pxe_check_group": check_newest_has_group,
    "pxe_use_discovery_mapping": use_discovery_mapping,
}


def run_local_step(step: FvtStep) -> Dict[str, Any]:
    """Run a local SVT action (domain ``svt``) in the shape of an FVT step result."""
    started = time.monotonic()
    action, *arguments = step[1]
    command = f"svt {action} {' '.join(arguments)}".rstrip()
    try:
        result = LOCAL_ACTIONS[action](*arguments)
    except (OSError, ValueError, csv.Error) as exc:
        result = {"success": False, "output": "", "error": f"{type(exc).__name__}: {exc}"}
    success = bool(result.get("success"))
    return {"success": success, "rc": 0 if success else 1,
            "duration": time.monotonic() - started, "command": command,
            "output": result.get("output", "") or result.get("error", ""),
            "step": command, "fvt": step_info(step), "results": []}
