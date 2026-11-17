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

PowerVault (powervault_config of storage_config.yml, a comment in the shipped file): the user
gives ip (a list or comma separated), iscsi_initiator and volume_id; POWERVAULT_DEFAULTS fills the
other keys. The item is merged like any list item (the key is created when the file has none).
Without an ip the item is ignored and a block of an earlier run is removed; with an ip and no
iscsi_initiator or volume_id the run stops and names the empty ones.

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
from typing import Any, Dict, List, Optional

from ruamel.yaml.comments import CommentedMap, CommentedSeq

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
REMOVE_WHEN_EMPTY = ("ib_addr_mode", "powervault_config")
# Keys the shipped file only has as a comment: created (an empty list that the items are
# merged into) when user_inputs.yml gives a value, removed again when it is emptied.
CREATE_WHEN_GIVEN = ("powervault_config",)
# The user's values of a PowerVault. Without ip the item is ignored (no PowerVault); with an ip
# the other two are required.
POWERVAULT_REQUIRED = ("ip", "iscsi_initiator", "volume_id")
# The other keys of a PowerVault item: the Slurm control node's /mnt/slurm with the MariaDB and
# Slurm spool directories bound per host. A key given in user_inputs.yml overrides its default.
POWERVAULT_DEFAULTS = {
    "port": 3260,
    "mount_point": "/mnt/slurm",
    "fs_type": "xfs",
    "mnt_opts": "defaults,_netdev,noatime",
    "node_key": "local_hostname",
    "node_mount_point": ["/var/lib/mysql", "/var/spool/slurm"],
    "functional_group_prefix": ["slurm_control_node"],
    "permissions": {"owner": "slurm", "group": "slurm", "mode": "0750"},
}
POWERVAULT_OPTIONAL = ("name", "dump_freq", "fsck_pass", "mount_params")
# Path keys of omnia_config that may use $NAME / ${NAME} of omnia.env (the project folder differs
# per installation); they are written as absolute paths, which the product requires.
ENV_PATH_KEYS = ("csi_powerscale_driver_secret_file_path", "csi_powerscale_driver_values_file_path")
ENV_DEFAULTS = {"OMNIA_DATA_PATH": "/opt/omnia", "OMNIA_PROJECT_NAME": "project_default"}
_ENV_REF = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
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
        if file_key is None and key in CREATE_WHEN_GIVEN and has_value(value):
            node[key] = CommentedSeq()
            file_key = key
        elif file_key is None and key in REMOVE_WHEN_EMPTY and not has_value(value):
            continue
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
            old = f"{len(current)} item(s)" if isinstance(current, list) else str(current)
            changes.append((label, here, old, "(removed)"))
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


def parse_env(text: str) -> Dict[str, str]:
    """Return the KEY=value lines of an omnia.env text (references to earlier keys resolved).

    ORCHESTRATOR_DATA_PATH and the other domain paths are commented out in the shipped file; the
    orchestrator's is then OMNIA_DATA_PATH/orchestrator.
    """
    env = dict(ENV_DEFAULTS)
    for line in text.splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            value = match.group(2).split(" #", 1)[0].strip().strip("\"'")
            env[match.group(1)] = _ENV_REF.sub(
                lambda ref: env.get(ref.group(1) or ref.group(2), ref.group(0)), value)
    env.setdefault("ORCHESTRATOR_DATA_PATH", f"{env['OMNIA_DATA_PATH']}/orchestrator")
    return env


def _expand_env_paths(node: Any, env: Dict[str, str], label: str) -> Any:
    """Return ``node`` with $NAME / ${NAME} of omnia.env expanded in the ENV_PATH_KEYS values."""
    if isinstance(node, list):
        return [_expand_env_paths(item, env, label) for item in node]
    if not isinstance(node, dict):
        return node
    result = {}
    for key, value in node.items():
        if key in ENV_PATH_KEYS and isinstance(value, str) and "$" in value:
            unknown = sorted({ref.group(1) or ref.group(2) for ref in _ENV_REF.finditer(value)}
                             - set(env))
            if unknown:
                raise EditError(f"{label}: {key}: {', '.join(unknown)} is not in omnia.env "
                                f"(known: {', '.join(sorted(env))})")
            value = _ENV_REF.sub(lambda ref: env[ref.group(1) or ref.group(2)], value)
        result[key] = _expand_env_paths(value, env, label)
    return result


def render_target(text: str, target: Dict[str, Any], inputs: Dict[str, Any],
                  changes: List[Change], env: Optional[Dict[str, str]] = None) -> str:
    """Return the new content of one target file (``env``: the omnia.env this run writes)."""
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
        section = _powervault_given(section, label)
    if env and isinstance(section, dict):
        section = _expand_env_paths(section, env, label)
    return RENDERERS[target["format"]](text, section or {}, changes, label)


def _powervault_item(item: Dict[str, Any], number: int, label: str) -> Dict[str, Any]:
    """Return the storage_config item of one PowerVault: the user's three values on top of
    POWERVAULT_DEFAULTS (keys given in user_inputs.yml override the defaults)."""
    given = {key: value for key, value in item.items() if has_value(value)}
    unknown = sorted(set(given) - set(POWERVAULT_REQUIRED) - set(POWERVAULT_DEFAULTS)
                     - set(POWERVAULT_OPTIONAL))
    if unknown:
        raise EditError(f"{label}: powervault_config item {number}: unknown key(s) "
                        f"{', '.join(unknown)} (allowed: "
                        f"{', '.join((*POWERVAULT_REQUIRED, *POWERVAULT_DEFAULTS))})")
    empty = [key for key in POWERVAULT_REQUIRED if not has_value(item.get(key))]
    if empty:
        raise EditError(f"{label}: powervault_config item {number} has an ip, so it also needs "
                        f"{', '.join(empty)} (leave ip empty for no PowerVault)")
    ip = given["ip"]
    addresses = [part.strip() for part in ip.split(",") if part.strip()] if isinstance(ip, str) \
        else list(ip)
    rest = {**POWERVAULT_DEFAULTS, **{key: value for key, value in given.items()
                                      if key not in ("name", *POWERVAULT_REQUIRED)}}
    return {"name": str(given.get("name") or f"powervault{number}"), "ip": addresses,
            "port": rest.pop("port"), "iscsi_initiator": given["iscsi_initiator"],
            "volume_id": given["volume_id"], **rest}


def _powervault_given(section: Any, label: str) -> Any:
    """Return the storage_config section with the PowerVault items that have an ip, complete.

    An item without an ip is ignored (so ``powervault_config`` is removed or never created).
    """
    if not isinstance(section, dict) or "powervault_config" not in section:
        return section
    items = []
    for number, item in enumerate(section["powervault_config"] or [], 1):
        if not isinstance(item, dict):
            raise EditError(f"{label}: powervault_config item {number} must be a mapping")
        if has_value(item.get("ip")):
            items.append(_powervault_item(item, number, label))
    return {**section, "powervault_config": items}


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
