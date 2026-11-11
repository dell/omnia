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

"""Load user_inputs.yml safely and check it before anything is written.

Checks, all fail-closed with a message naming the key:
* the file parses (YAML / indentation errors report line and column);
* no credential-like key or vault value (test_automation.md section 11:
  datasets never carry secrets);
* every mandatory key of the profile is filled. Optional keys may stay empty.
"""

import csv
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import yaml

from .dataset_edit import has_value

CREDENTIAL_KEY = re.compile(r"(^|_)(password|passwd|pwd|secret|token|api_?key|private_?key)$",
                            re.IGNORECASE)
VAULT_MARKER = "$ANSIBLE_VAULT"
DNS_HOSTNAME = re.compile(r"^nid(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})$")
PXE_HOSTNAME_COLUMN = 4


class InputError(Exception):
    """user_inputs.yml cannot be used; the message says what to fix."""


def load_inputs(path: Path) -> Dict[str, Any]:
    """Return the parsed user_inputs.yml, or raise InputError."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise InputError(f"{path}: YAML/indentation error{where}: "
                         f"{getattr(exc, 'problem', exc)}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path}: expected the module blocks main, repo_manager, ...")
    return data


def _walk(node: Any, where: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield (dotted path, value) for every key of a nested structure."""
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{where}.{key}" if where else str(key)
            yield here, value
            yield from _walk(value, here)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{where}[{index}]")


def credential_problems(inputs: Dict[str, Any]) -> List[str]:
    """Return keys that look like credentials or values that are vault payloads."""
    problems = []
    for where, value in _walk(inputs):
        if CREDENTIAL_KEY.search(where.rsplit(".", 1)[-1]):
            problems.append(f"{where}: credentials do not belong in user_inputs.yml")
        if isinstance(value, str) and value.lstrip().startswith(VAULT_MARKER):
            problems.append(f"{where}: vault payloads do not belong in user_inputs.yml")
    return problems


def dns_problems(inputs: Dict[str, Any]) -> List[str]:
    """Return the PXE rows whose hostname is not a nid name while dns_enabled is true.

    The orchestrator (pxe_mapping_validator) requires nid001-nid999 hostnames when
    dns_enabled is true, which is also the shipped default when the key is left empty.
    """
    orchestrator = inputs.get("orchestrator") or {}
    flag = (orchestrator.get("orchestrator_config") or {}).get("dns_enabled")
    if flag is False or str(flag).strip().lower() in ("false", "no", "0"):
        return []
    problems = []
    for key, row in (orchestrator.get("pxe_mapping_file") or {}).items():
        cells = next(csv.reader([str(row)]), [])
        name = cells[PXE_HOSTNAME_COLUMN].strip() if len(cells) > PXE_HOSTNAME_COLUMN else ""
        if name and not DNS_HOSTNAME.match(name):
            problems.append(f"orchestrator.pxe_mapping_file.{key}: hostname {name!r} must be "
                            "nid001-nid999 while orchestrator.orchestrator_config.dns_enabled "
                            "is true (set it to false, or rename the node)")
    return problems


def resolve(inputs: Dict[str, Any], path: str) -> Any:
    """Return the value at ``a.b[x].c``; ``[x]`` selects the list item keyed or named x."""
    node: Any = inputs
    for part in path.split("."):
        match = re.fullmatch(r"([^\[]+)(?:\[([^\]]+)\])?", part)
        key, select = match.group(1), match.group(2)
        node = node.get(key) if isinstance(node, dict) else None
        if select is not None:
            items = node if isinstance(node, list) else []
            node = next((i[select] for i in items if isinstance(i, dict) and select in i),
                        next((i for i in items if isinstance(i, dict) and select in
                              (str(i.get("name")), str(i.get("cluster_name")))), None))
    return node


def missing_mandatory(inputs: Dict[str, Any], mandatory: List[str]) -> List[str]:
    """Return the mandatory paths whose value is empty or absent."""
    return [path for path in mandatory if not has_value(resolve(inputs, path))]


def check_inputs(inputs: Dict[str, Any], mandatory: List[str], path: Path) -> None:
    """Raise InputError listing every credential problem and empty mandatory key."""
    problems = credential_problems(inputs)
    problems += [f"{key}: MANDATORY, fill it" for key in missing_mandatory(inputs, mandatory)]
    problems += dns_problems(inputs)
    if problems:
        raise InputError(f"{path}: {len(problems)} problem(s):\n  - " + "\n  - ".join(problems))
