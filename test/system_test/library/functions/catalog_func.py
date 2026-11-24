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

"""catalog_build theme: the catalog plan and the SVT actions of a catalog stage.

* ``write_plan`` (./setup_env.sh --configure): resolve the catalogs of the theme
  block (``all`` = ./omnia.sh --list-catalogs order), mark the ones with an
  aarch64 layer as skipped unless include_aarch64, and freeze the plan in
  catalog_vars.CATALOG_PLAN_FILE. The stages and tests are generated from it
  (catalog_vars.py) and run like every other theme: svt/test_svt.py.
* ``run_action`` (the first test of a catalog stage): put back the shared
  runtime inputs, apply catalog_overrides/<catalog>/<domain>/<file>, write the
  global settings (repo_config, caching_policy, repo_policies, force_rebuild,
  functional_groups_source: catalog), then ./omnia.sh --select-catalog.
* ``stop_leftovers`` (after a failed exec): the ansible-playbook workers run in
  their own session, so a playbook killed at the FVT timeout can leave them (and
  a dnf download) running; they are stopped before the next test.

Nothing is skipped for content an earlier catalog brought: repo_manager syncs
only what is new; image_build_manager rebuilds every image (force_rebuild true,
the default) or reuses a matching one (false).
"""

import json
import os
import shutil
import signal
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml
from ruamel.yaml.comments import CommentedMap

from dataset_generator.dataset_edit import Change, dump_yaml, load_yaml, set_value, split_header

from .catalog_settings import describe_settings
from .omnia_func import domain_input_dir, omnia_env
from .run_func import load_run
from .setup_func import bundled_catalogs, resolve_catalog, row, select_catalog
from ..messages.svt_msgs import CATALOG_MSGS
from ..vars.catalog_vars import (
    ACTION_SELECT,
    ACTION_SKIP,
    CATALOG_PLAN_FILE,
    CATALOG_STAGE_PREFIX,
    CATALOG_STEP_DOMAINS,
    CATALOG_STEP_PLAYBOOKS,
    load_plan,
)
from ..vars.common_vars import INPUTS_FILE, MODULE_ROOT, REPO_ROOT

Emit = Callable[[str], None]

SAMPLES_DIR = os.path.join(REPO_ROOT, "src", "main", "samples")
DEFAULT_CATALOG = "default"
DEFAULT_CATALOG_FILE = os.path.join(SAMPLES_DIR, "catalog_rhel.json")
OVERRIDES_DIR = os.path.join(MODULE_ROOT, "catalog_overrides")
BASELINE_DIR = "baseline_inputs"
REPO_INPUT = ("repo_manager", "repo_manager_config.yml")
IMAGE_INPUT = ("image_build_manager", "image_build_config.yml")
NESTED_REPO_SECTIONS = ("user_repos", "additional_repos")
AARCH64_HOST_KEY = ("image_build_manager", "image_build_config", "aarch64_inventory_host_ip")
PROC_DIR = "/proc"


# ------------------------------------------------------------------- plan
def catalog_file(name: str) -> str:
    """Return the bundled catalog file of a --list-catalogs name."""
    if name == DEFAULT_CATALOG:
        return DEFAULT_CATALOG_FILE
    return os.path.join(SAMPLES_DIR, "catalogs", name)


def aarch64_layers(path: str) -> List[str]:
    """Return the functional layers of a catalog built for aarch64."""
    with open(path, "r", encoding="utf-8") as stream:
        catalog = json.load(stream).get("catalog", {})
    return [str(layer.get("name", "")) for layer in catalog.get("functionallayer", [])
            if isinstance(layer, dict) and "aarch64" in str(layer.get("name", ""))]


def _aarch64_host() -> str:
    try:
        with open(INPUTS_FILE, "r", encoding="utf-8") as stream:
            node: Any = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError):
        return ""
    for key in AARCH64_HOST_KEY:
        node = node.get(key) if isinstance(node, dict) else None
    return "" if node is None else str(node).strip()


def _selected_names(settings: Dict[str, Any]) -> List[str]:
    """Return the --list-catalogs names to run, in run order."""
    listed, error = bundled_catalogs()
    if error:
        raise ValueError(error)
    if settings["catalogs"] == "all":
        return [listed[number] for number in sorted(listed, key=int)]
    names = []
    for selection in settings["catalogs"]:
        name, problem = resolve_catalog(selection)
        if problem:
            raise ValueError(CATALOG_MSGS["unknown_catalog"].format(selection=selection))
        names.append(name)
    return names


def plan(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return one entry per catalog: stage, index, catalog, run (bool), reason.

    Raises:
        ValueError: --list-catalogs fails, a catalog is unknown or missing, or
            include_aarch64 is true without an aarch64 build host.
    """
    if settings["include_aarch64"] and not _aarch64_host():
        raise ValueError(CATALOG_MSGS["aarch64_host_missing"])
    entries = []
    for index, name in enumerate(_selected_names(settings), 1):
        path = catalog_file(name)
        if not os.path.isfile(path):
            raise ValueError(CATALOG_MSGS["catalog_file_missing"].format(path=path))
        layers = aarch64_layers(path)
        skip = bool(layers) and not settings["include_aarch64"]
        entries.append({"stage": f"{CATALOG_STAGE_PREFIX}{index:02d}", "index": index,
                        "catalog": name, "run": not skip,
                        "reason": CATALOG_MSGS["skip_aarch64"].format(
                            layers=", ".join(layers)) if skip else ""})
    return entries


def plan_lines(settings: Dict[str, Any], entries: List[Dict[str, Any]]) -> List[str]:
    """Return the plan as printed by --configure."""
    lines = [CATALOG_MSGS["plan_header"].format(
        count=len(entries), run=sum(1 for entry in entries if entry["run"]),
        path=CATALOG_PLAN_FILE)]
    lines.extend(CATALOG_MSGS["plan_line"].format(
        stage=entry["stage"], mark="run" if entry["run"] else "skip", catalog=entry["catalog"],
        reason=f"  ({entry['reason']})" if entry["reason"] else "") for entry in entries)
    lines.append(CATALOG_MSGS["steps_header"].format(
        steps=", ".join(f"{domain} {tag}" for domain, tag in settings["steps"])))
    lines.append(CATALOG_MSGS["settings"].format(settings=describe_settings(settings)))
    return lines


def write_plan(settings: Dict[str, Any], run_id: str, emit: Emit,
               path: str = CATALOG_PLAN_FILE) -> Tuple[List[Dict[str, Any]], str]:
    """Resolve and store the plan of run ``run_id``; return (report rows, error)."""
    try:
        entries = plan(settings)
    except ValueError as exc:
        return [row("catalog plan", "FAILED", error=str(exc))], str(exc)
    lines = plan_lines(settings, entries)
    for line in lines:
        emit(line)
    os.makedirs(os.path.dirname(path), mode=0o750, exist_ok=True)
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8") as stream:
        json.dump({"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"), "settings": {**settings, "steps": [list(step) for step in
                                                                    settings["steps"]]},
            "entries": entries}, stream, indent=2)
    os.replace(temp, path)
    return [row("catalog plan", "PASSED", details="\n".join(lines))], ""


# ------------------------------------------------------------ runtime inputs
def _runtime_dir(domain: str) -> str:
    return domain_input_dir(omnia_env(), domain)


def _is_credential(name: str) -> bool:
    return name.startswith(".") or "credential" in name


def _override_files(catalog: str) -> List[tuple]:
    """Return (domain, file name, source) of every override of ``catalog``."""
    files = []
    for domain in CATALOG_STEP_DOMAINS:
        folder = os.path.join(OVERRIDES_DIR, catalog, domain)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            source = os.path.join(folder, name)
            if os.path.isfile(source) and not os.path.islink(source) and not _is_credential(name):
                files.append((domain, name, source))
    return files


def restore_and_override(run_folder: str, catalog: str, emit: Emit) -> List[str]:
    """Put back every shared input an earlier override replaced, then apply ``catalog``'s.

    The shared copy of a file is kept in <run folder>/baseline_inputs/ the
    first time an override replaces it. Returns what was done.
    """
    done = []
    baseline = os.path.join(run_folder, BASELINE_DIR)
    for domain in CATALOG_STEP_DOMAINS:
        saved = os.path.join(baseline, domain)
        for name in sorted(os.listdir(saved)) if os.path.isdir(saved) else []:
            shutil.copy2(os.path.join(saved, name), os.path.join(_runtime_dir(domain), name))
    for domain, name, source in _override_files(catalog):
        target = os.path.join(_runtime_dir(domain), name)
        keep = os.path.join(baseline, domain, name)
        if not os.path.exists(keep) and os.path.isfile(target):
            os.makedirs(os.path.dirname(keep), mode=0o750, exist_ok=True)
            shutil.copy2(target, keep)
        shutil.copy2(source, target)
        emit(CATALOG_MSGS["override_applied"].format(source=source, target=target))
        done.append(f"override {domain}/{name}")
    return done


def _edit_yaml(path: str, edit: Callable[[Any, List[Change]], None]) -> List[Change]:
    """Apply ``edit`` to a YAML input file, keeping its comments; write only on change."""
    if not os.path.isfile(path):
        raise ValueError(CATALOG_MSGS["no_runtime_input"].format(path=path))
    with open(path, "r", encoding="utf-8") as stream:
        header, body = split_header(stream.read())
    document = load_yaml(body)
    changes: List[Change] = []
    edit(document, changes)
    if changes:
        temp = f"{path}.svt-tmp"
        with open(temp, "w", encoding="utf-8") as stream:
            stream.write(header + dump_yaml(document))
        os.replace(temp, path)
    return changes


def _key_of(mapping: Any, key: str) -> Optional[Any]:
    """Return the key of ``mapping`` equal to ``key`` as text ("10.2" == 10.2)."""
    return next((existing for existing in mapping if str(existing) == key), None) \
        if isinstance(mapping, dict) else None


def _repo_entry(document: Any, key: str, path: str) -> Any:
    """Return the mapping of repository ``<version>/<arch>/<repo>`` (created when null)."""
    version, arch, name = key.split("/")
    repositories = document.get("repositories") if isinstance(document, dict) else None
    arches = repositories.get(_key_of(repositories, version)) \
        if _key_of(repositories, version) is not None else None
    repos = arches.get(arch) if isinstance(arches, dict) else None
    holders = [repos] + [repos.get(section) for section in NESTED_REPO_SECTIONS] \
        if isinstance(repos, dict) else []
    for holder in holders:
        if isinstance(holder, dict) and name in holder:
            if not isinstance(holder[name], dict):
                holder[name] = CommentedMap()
            return holder[name]
    raise ValueError(CATALOG_MSGS["repo_missing"].format(key=key, path=path))


def write_settings(settings: Dict[str, Any]) -> List[Change]:
    """Write the global settings into the runtime repo_manager and image inputs."""
    repo_path = os.path.join(_runtime_dir(REPO_INPUT[0]), REPO_INPUT[1])
    image_path = os.path.join(_runtime_dir(IMAGE_INPUT[0]), IMAGE_INPUT[1])

    def repo(document: Any, changes: List[Change]) -> None:
        set_value(document, "repo_config", settings["repo_config"], changes, repo_path, "top")
        set_value(document, "caching_policy", settings["caching_policy"], changes, repo_path,
                  "top")
        for key, entry in settings["repo_policies"].items():
            target = _repo_entry(document, key, repo_path)
            for field, value in entry.items():
                set_value(target, field, value, changes, repo_path, key)

    def image(document: Any, changes: List[Change]) -> None:
        build = document.get("build_image")
        if not isinstance(build, dict):
            build = document["build_image"] = CommentedMap()
        set_value(build, "force_rebuild", settings["force_rebuild"], changes, image_path,
                  "build_image")
        set_value(document, "functional_groups_source", "catalog", changes, image_path, "top")

    return _edit_yaml(repo_path, repo) + _edit_yaml(image_path, image)


# ------------------------------------------------------------------ actions
def _outcome(success: bool, started: float, command: str, output: str, step: tuple,
             **extra: Any) -> Dict[str, Any]:
    """Return an action result shaped like fvt_func.run_fvt_step's."""
    return {"success": success, "rc": 0 if success else 1, "duration": time.monotonic() - started,
            "command": command, "output": output, "results": [], "step": " ".join(step[1]),
            "fvt": {"suite": "test/system_test", "domain": "svt", "tag": step[1][0],
                    "action": "", "options": " ".join(step[1][1:])}, **extra}


def _select(case: Dict[str, Any], emit: Emit) -> Dict[str, Any]:
    started = time.monotonic()
    settings = load_plan().get("settings") or {}
    run_folder = load_run().get("report_path", "")
    rows: List[Dict[str, Any]] = []
    notes: List[str] = []
    error = ""
    try:
        notes.extend(restore_and_override(run_folder, case["catalog"], emit))
        changes = write_settings(settings)
        notes.append(f"{len(changes)} setting(s) written: {describe_settings(settings)}")
        emit(CATALOG_MSGS["inputs_written"].format(details=notes[-1]))
        error = select_catalog(case["catalog"], emit, rows)
    except (OSError, ValueError, KeyError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    selected = rows[0] if rows else {}
    output = "\n".join([*notes, str(selected.get("output") or ""), error]).strip()
    return _outcome(not error, started, str(selected.get("command") or
                                            f"./omnia.sh --select-catalog {case['catalog']}"),
                    output, case["step"], error=error)


def run_action(case: Dict[str, Any], emit: Emit = print) -> Dict[str, Any]:
    """Run the SVT action of a catalog test case; return a run_fvt_step-shaped result.

    A skipped catalog returns ``skipped`` (the reason) instead of running anything.
    """
    if case.get("action") == ACTION_SKIP:
        return _outcome(True, time.monotonic(), "", case.get("reason", ""), case["step"],
                        skipped=case.get("reason", ""))
    if case.get("action") == ACTION_SELECT:
        return _select(case, emit)
    raise ValueError(f"unknown SVT action {case.get('action')!r}")


# -------------------------------------------------------- leftover processes
def _processes(proc: str = PROC_DIR) -> Dict[int, Tuple[int, List[str]]]:
    """Return {pid: (ppid, argv)} of every readable process under /proc."""
    found: Dict[int, Tuple[int, List[str]]] = {}
    for name in os.listdir(proc):
        if not name.isdigit():
            continue
        try:
            with open(os.path.join(proc, name, "stat"), "r", encoding="utf-8") as stream:
                ppid = int(stream.read().rsplit(")", 1)[1].split()[1])
            with open(os.path.join(proc, name, "cmdline"), "rb") as stream:
                argv = [part.decode("utf-8", "replace")
                        for part in stream.read().split(b"\0") if part]
        except (OSError, IndexError, ValueError):
            continue
        found[int(name)] = (ppid, argv)
    return found


def leftover_playbooks(domain: str, processes: Dict[int, Tuple[int, List[str]]]) -> List[int]:
    """Return orphaned ``ansible-playbook <domain playbook>`` processes and their descendants.

    Orphaned = reparented to init (ppid 1): its FVT step already ended.
    """
    playbook = CATALOG_STEP_PLAYBOOKS.get(domain)
    roots = [pid for pid, (ppid, argv) in processes.items()
             if ppid == 1 and playbook in argv
             and any(os.path.basename(arg) == "ansible-playbook" for arg in argv)]
    tree = set(roots)
    grown = True
    while grown:
        grown = False
        for pid, (ppid, _) in processes.items():
            if ppid in tree and pid not in tree:
                tree.add(pid)
                grown = True
    return sorted(tree)


def stop_leftovers(domain: str, emit: Emit, grace: float = 10.0) -> List[int]:
    """Stop what a failed step of ``domain`` left running (SIGTERM, then SIGKILL)."""
    pids = leftover_playbooks(domain, _processes())
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        deadline = time.monotonic() + (grace if sig == signal.SIGTERM else 0)
        while time.monotonic() < deadline and any(os.path.exists(f"{PROC_DIR}/{pid}")
                                                  for pid in pids):
            time.sleep(0.5)
    if pids:
        emit(CATALOG_MSGS["leftovers_stopped"].format(
            domain=domain, pids=", ".join(str(pid) for pid in pids)))
    return pids
