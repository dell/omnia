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

"""Build the new input files and publish them.

Two destinations:
  * in place  - the files of ``src/<domain>/input`` and ``src/main/omnia.env`` are
    rewritten (only when their content changes, atomically);
  * explicit path - the complete input tree (every ``input`` file of the profile's
    domains plus omnia.env) is created under ``--output-dir``, with the same
    ``<domain>/input/...`` layout. Files already there are never overwritten
    blindly: identical files stay, different ones are moved into
    ``<output-dir>/.backup/<UTC timestamp>/`` first.
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .dataset_edit import Change
from .dataset_merge import render_target

BACKUP_DIR = ".backup"
CREDENTIAL_FILE = "credential"
# System directories an output folder must not be (the generator writes and moves files).
BROAD_ROOTS = {"/"} | {f"/{name}" for name in (
    "bin", "boot", "dev", "etc", "home", "lib", "lib64", "opt", "proc", "root", "run",
    "sbin", "srv", "sys", "tmp", "usr", "var")}
Outputs = Dict[str, bytes]  # relative output path -> file content


def build_outputs(repo_root: Path, profile: Dict[str, Any], inputs: Dict[str, Any],
                  complete: bool) -> Tuple[Outputs, List[Change]]:
    """Return the new content of every file to write, and the list of value changes.

    ``complete`` adds the untouched files of the profile's input directories
    (never credential files), so an output folder receives the whole input set.
    """
    outputs: Outputs = {}
    changes: List[Change] = []
    if complete:
        for directory in profile.get("input_dirs", []):
            base = repo_root / directory
            for path in sorted(base.rglob("*")):
                if (path.is_file() and not path.name.startswith(".")
                        and CREDENTIAL_FILE not in path.name):
                    outputs[_output_name(directory, path, base)] = path.read_bytes()
    for target in profile["targets"]:
        source = repo_root / target["file"]
        text = render_target(source.read_text(encoding="utf-8"), target, inputs, changes)
        outputs[target["out"]] = text.encode("utf-8")
    return outputs, changes


def check_output_dir(output_dir: Path, repo_root: Path) -> None:
    """Reject broad system roots and the repository source tree as an output folder."""
    if str(output_dir) in BROAD_ROOTS:
        raise ValueError(f"{output_dir} is a system directory; give a dedicated folder "
                         f"such as {output_dir.as_posix().rstrip('/')}/omnia_inputs")
    src = (repo_root / "src").resolve()
    if output_dir == src or src in output_dir.parents:
        raise ValueError(f"{output_dir} is inside {src}; run without a folder to update src")


def _output_name(directory: str, path: Path, base: Path) -> str:
    """Return the ``<domain>/input/<file>`` name of an input file."""
    domain = Path(directory).parts[-2] if Path(directory).name == "input" else Path(directory).name
    return f"{domain}/input/{path.relative_to(base).as_posix()}"


def _write_atomic(path: Path, content: bytes) -> None:
    """Write ``content`` to ``path`` through a temp file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    handle, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def publish_in_place(repo_root: Path, profile: Dict[str, Any], outputs: Outputs,
                     dry_run: bool) -> List[Tuple[str, str]]:
    """Rewrite the profile's target files in the source tree.

    Returns:
        (path, action) pairs; action is ``updated`` or ``unchanged``.
    """
    report = []
    for target in profile["targets"]:
        path = repo_root / target["file"]
        content = outputs[target["out"]]
        changed = path.read_bytes() != content
        if changed and not dry_run:
            _write_atomic(path, content)
        report.append((target["file"], "updated" if changed else "unchanged"))
    return report


def publish_to_directory(output_dir: Path, outputs: Outputs,
                         dry_run: bool) -> List[Tuple[str, str]]:
    """Create the whole input tree under ``output_dir``; move different existing files aside.

    Returns:
        (relative path, action) pairs; action is ``created``, ``unchanged`` or
        ``replaced (old file moved to .backup/<stamp>/...)``.
    """
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(f"{output_dir} exists and is not a directory")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = []
    for name, content in sorted(outputs.items()):
        path = output_dir / name
        if not path.exists():
            action = "created"
        elif path.read_bytes() == content:
            report.append((name, "unchanged"))
            continue
        else:
            backup = output_dir / BACKUP_DIR / stamp / name
            action = f"replaced (old file moved to {BACKUP_DIR}/{stamp}/{name})"
            if not dry_run:
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, backup)
        if not dry_run:
            _write_atomic(path, content)
        report.append((name, action))
    return report
