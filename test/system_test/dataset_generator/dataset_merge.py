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

"""Write one user_inputs.yml section into one shipped input file.

The section mirrors the file (same keys, same nesting), so a single generic
merge serves every YAML file:

* mapping  -> walk into the key of the same name (an unknown key is an error,
  which catches typos);
* list of mappings -> match each item by ``name``, ``cluster_name``, ``address``
  (ntp_servers) or ``subnet`` (additional_subnets) or, for ``- admin_network:``
  style items, by their single key; a new item is appended;
* scalar or list of scalars -> written when given, typed like the file value; an empty
  value removes a key of REMOVE_WHEN_EMPTY (ib_addr_mode) instead of writing "".

An empty value ("" / []) clears the text or plain list in the file, so a value
removed from user_inputs.yml is removed there too; it never changes a boolean,
a number, a block or a list of items, and it never adds a new list item.

Mount switch (vast_storage, nfs_slurm, nfs_k8s): without a source for the mount in
user_inputs.yml, the whole shipped mount in storage_config.yml is commented out with a
reversible marker, and the user's item for it is not merged (it would add a mount without a
source); giving a source later restores it. omnia_config.yml is never changed: a reference
to a mount that is off (vast_storage_name, or the nfs_storage_name of the Slurm or the
Kubernetes cluster) is reported by the orchestrator validation ("storage_config.yml does not
define referenced storage").
"""

import csv
import re
from typing import Any, Dict, List

from ruamel.yaml.comments import CommentedMap

from .dataset_edit import (
    Change,
    EditError,
    csv_header,
    dump_yaml,
    edit_env,
    has_value,
    load_yaml,
    quoted,
    render_csv,
    set_value,
    split_header,
)

IDENTITY_KEYS = ("name", "cluster_name", "address", "subnet")
# Keys the product reads as "feature on" when they exist, whatever their value, and whose
# schema rejects an empty value: an empty value in user_inputs.yml removes them from the file.
# ib_addr_mode: with it the orchestrator runs the IPoIB pipeline for the rows that have an
# IB_NIC_NAME; without it the pipeline is skipped (a cluster without InfiniBand).
REMOVE_WHEN_EMPTY = ("ib_addr_mode",)
# Mounts that are switched off in storage_config.yml when user_inputs.yml gives no source:
# (mount name, label of the marker, title).
SWITCHES = (
    ("vast_storage", "vast", "VAST"),
    ("nfs_slurm", "nfs_slurm", "nfs_slurm"),
    ("nfs_k8s", "nfs_k8s", "nfs_k8s"),
)


def typed(value: Any, current: Any) -> Any:
    """Return ``value`` converted to the type the file already uses for the key."""
    if not has_value(value):
        return value
    if isinstance(current, bool) and isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    if isinstance(current, int) and not isinstance(current, bool) and str(value).isdigit():
        return int(value)
    if isinstance(current, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return value


def _file_key(mapping: Any, key: Any) -> Any:
    """Return the key of ``mapping`` equal to ``key`` as text ("10.2" == 10.2), or None."""
    for existing in mapping:
        if str(existing) == str(key):
            return existing
    return None


def _identity(item: Dict[str, Any]) -> tuple:
    """Return how a user list item is matched: ("name", value) or ("key", single key)."""
    for key in IDENTITY_KEYS:
        if has_value(item.get(key)):
            return key, str(item[key])
    if len(item) == 1:
        return "key", next(iter(item))
    raise EditError(f"list item {dict(item)} needs a name or cluster_name")


def merge_yaml(node: Any, wanted: Dict[str, Any], changes: List[Change], label: str,
               where: str = "") -> None:
    """Merge the user mapping ``wanted`` into the file mapping ``node`` in place."""
    for key, value in wanted.items():
        here = f"{where}.{key}" if where else str(key)
        file_key = _file_key(node, key)
        if file_key is None:
            raise EditError(f"{label}: '{here}' is not a key of this file (check the spelling)")
        current = node[file_key]
        if isinstance(value, dict):
            if not isinstance(current, dict):
                raise EditError(f"{label}: '{here}' is a single value in this file, not a block")
            merge_yaml(current, value, changes, label, here)
        elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            if not isinstance(current, list):
                raise EditError(f"{label}: '{here}' is not a list in this file")
            merge_list(current, value, changes, label, here)
        elif key in REMOVE_WHEN_EMPTY and not has_value(value):
            del node[file_key]
            changes.append((label, here, str(current), "(removed)"))
        else:
            set_value(node, file_key, typed(value, current), changes, label, where)


def merge_list(items: List[Any], wanted: List[Dict[str, Any]], changes: List[Change],
               label: str, where: str) -> None:
    """Merge user list items into the file list, matching items by identity."""
    for entry in wanted:
        kind, ident = _identity(entry)
        if kind == "key":
            match = next((i for i in items if isinstance(i, dict) and ident in i), None)
            if match is None:
                raise EditError(f"{label}: '{where}' has no '{ident}' item")
            merge_yaml(match[ident], entry[ident] or {}, changes, label, f"{where}[{ident}]")
            continue
        rest = {k: v for k, v in entry.items() if k != kind}
        match = next((i for i in items if isinstance(i, dict) and str(i.get(kind)) == ident), None)
        if match is not None:
            merge_yaml(match, rest, changes, label, f"{where}[{ident}]")
        elif any(has_value(v) for v in rest.values()):
            item = CommentedMap([(kind, quoted(ident))])
            item.update((k, quoted(v)) for k, v in rest.items() if has_value(v))
            items.append(item)
            changes.append((label, f"{where}[{ident}]", "(absent)", "added"))


def mount_requested(inputs: Dict[str, Any], mount: str) -> bool:
    """Return whether user_inputs.yml gives a source for the ``mount`` of storage_config."""
    mounts = (((inputs.get("orchestrator") or {}).get("storage_config") or {})
              .get("mounts") or [])
    return any(isinstance(m, dict) and str(m.get("name")) == mount
               and has_value(m.get("source")) for m in mounts)


def _mount_block(lines: List[str], mount: str) -> List[int]:
    """Return the line numbers of the ``mount`` item of storage_config (empty if absent)."""
    for number, line in enumerate(lines):
        match = re.match(rf"^(\s*)- name:\s*[\"']?{mount}[\"']?\s*(#.*)?$", line)
        if match:
            indent = len(match.group(1))
            block = [number]
            for following in range(number + 1, len(lines)):
                text = lines[following]
                if text.strip() and len(text) - len(text.lstrip()) <= indent:
                    break
                block.append(following)
            while block and not lines[block[-1]].strip():
                block.pop()
            return block
    return []


def switch_mount(text: str, switch: tuple, enable: bool, changes: List[Change],
                 label: str) -> str:
    """Comment the lines of a storage_config mount out (enable=False) or restore them."""
    mount, marker, title = switch
    prefix = f"# [{marker} off] "
    note = (f"{prefix.rstrip()} {title} is off: user_inputs.yml gives no {mount} source; "
            f"fill it and rerun the generator to turn {title} on.")
    lines = text.split("\n")
    if enable:
        if not any(line.lstrip().startswith(prefix.strip()) for line in lines):
            return text
        restored = [line.replace(prefix, "", 1) for line in lines if line.strip() != note]
        changes.append((label, title, "off", "on"))
        return "\n".join(restored)
    block = _mount_block(lines, mount)
    if not block:
        return text
    indent = lines[block[0]][:len(lines[block[0]]) - len(lines[block[0]].lstrip())]
    for number in block:
        lines[number] = f"{prefix}{lines[number]}" if lines[number].strip() else lines[number]
    lines.insert(block[0], f"{indent}{note}")
    changes.append((label, title, "on", "off"))
    return "\n".join(lines)


MOUNTS_PREFIX = "# [mounts off] "
MOUNTS_NOTE = (f"{MOUNTS_PREFIX.rstrip()} no mount is configured: every mount has no source in "
               "user_inputs.yml; fill one and rerun the generator.")


def _mounts_have_items(lines: List[str]) -> bool:
    """Return whether the ``mounts:`` block of storage_config has an item that is not commented."""
    start = next((n for n, line in enumerate(lines) if re.match(r"^mounts\s*:\s*$", line)), None)
    if start is None:
        return False
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith((" ", "#")):
            break
        if re.match(r"^\s+- name:", line):
            return True
    return False


def switch_mounts_key(text: str, keep: bool, changes: List[Change], label: str) -> str:
    """Comment the ``mounts:`` key out when no mount is left (an empty ``mounts:`` is null,
    which the schema rejects), and restore it when a mount is back."""
    lines = text.split("\n")
    if keep or _mounts_have_items(lines):
        if not any(line.startswith(MOUNTS_PREFIX.strip()) for line in lines):
            return text
        restored = [line.replace(MOUNTS_PREFIX, "", 1) for line in lines if line != MOUNTS_NOTE]
        changes.append((label, "mounts", "off", "on"))
        return "\n".join(restored)
    for number, line in enumerate(lines):
        if re.match(r"^mounts\s*:\s*$", line):
            lines[number] = f"{MOUNTS_PREFIX}{line}"
            lines.insert(number, MOUNTS_NOTE)
            changes.append((label, "mounts", "on", "off"))
            return "\n".join(lines)
    return text


def render_yaml(text: str, section: Dict[str, Any], changes: List[Change], label: str) -> str:
    """Merge ``section`` into a YAML file; return the original text when nothing changed."""
    head, body = split_header(text)
    document = load_yaml(body)
    before = len(changes)
    merge_yaml(document, section, changes, label)
    return head + dump_yaml(document) if len(changes) > before else text


def render_env(text: str, section: Dict[str, Any], changes: List[Change], label: str) -> str:
    """Write ``KEY: value`` pairs into ``KEY=value`` lines of an env file."""
    values = {key: "" if value is None else str(value) for key, value in section.items()}
    return edit_env(text, values, changes, label)


def render_csv_rows(text: str, section: Dict[str, Any], changes: List[Change], label: str) -> str:
    """Keep the CSV header, replace every data row with ``row1``, ``row2``, ... ."""
    rows = [str(v) for k, v in sorted(section.items(), key=lambda kv: _row_number(kv[0]))
            if has_value(v)]
    if not rows:
        return text
    header = csv_header(text)
    parsed = []
    for number, row in enumerate(rows, 1):
        cells = [cell.strip() for cell in next(csv.reader([row]))]
        if len(cells) > len(header):
            raise EditError(f"{label}: row{number} has {len(cells)} columns, the header "
                            f"has {len(header)}")
        parsed.append(dict(zip(header, cells)))
    rendered = render_csv(header, parsed)
    if rendered != text:
        old_rows = max(len([line for line in text.splitlines() if line.strip()]) - 1, 0)
        changes.append((label, "rows", str(old_rows), str(len(rows))))
    return rendered


def _row_number(key: Any) -> int:
    """Return N of ``rowN`` so row10 sorts after row9."""
    match = re.fullmatch(r"row(\d+)", str(key))
    if not match:
        raise EditError(f"pxe_mapping_file: '{key}' must be named row1, row2, ...")
    return int(match.group(1))


RENDERERS = {"yaml": render_yaml, "env": render_env, "csv": render_csv_rows}


def render_target(text: str, target: Dict[str, Any], inputs: Dict[str, Any],
                  changes: List[Change]) -> str:
    """Return the new content of one target file."""
    section = inputs
    for key in target["section"].split("."):
        section = (section or {}).get(key) if isinstance(section, dict) else None
    label = target["file"]
    if target.get("switch") == "mount":
        off = []
        for switch in SWITCHES:
            enable = mount_requested(inputs, switch[0])
            text = switch_mount(text, switch, enable, changes, label)
            if not enable:
                off.append(switch[0])
        if off:
            section = _without_mounts(section, off)
        user_mounts = isinstance(section, dict) and bool(section.get("mounts"))
        text = switch_mounts_key(text, user_mounts, changes, label)
    return RENDERERS[target["format"]](text, section or {}, changes, label)


def _without_mounts(section: Any, names: List[str]) -> Any:
    """Return the storage_config section without the mounts called ``names``.

    A switched-off mount is commented out in the file; merging the user's item for it
    afterwards would append a new, incomplete one (no source).
    """
    if not isinstance(section, dict) or not isinstance(section.get("mounts"), list):
        return section
    mounts = [m for m in section["mounts"]
              if not (isinstance(m, dict) and str(m.get("name")) in names)]
    rest = {k: v for k, v in section.items() if k != "mounts"}
    return {**rest, "mounts": mounts} if mounts else rest
