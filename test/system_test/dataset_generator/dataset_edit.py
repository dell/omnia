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

"""Low-level editors: comment-preserving YAML, env files and the PXE mapping CSV.

Every editor changes only the keys it is given and records each change, so the
rest of a file (defaults, comments, ordering, quoting) stays exactly as shipped.
"""

import csv
import io
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

Change = Tuple[str, str, str, str]  # (file, key, old, new)


class EditError(Exception):
    """A value cannot be written because the target file has no matching place."""


def new_yaml() -> YAML:
    """Return a round-trip YAML codec matching the shipped input style."""
    codec = YAML()
    codec.preserve_quotes = True
    codec.width = 4096
    codec.indent(mapping=2, sequence=4, offset=2)
    return codec


def split_header(text: str) -> Tuple[str, str]:
    """Split a YAML file into its header (licence comments up to ``---``) and the body.

    ruamel drops comments that precede the document start marker, so the header
    is carried over verbatim instead.
    """
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.strip() == "---":
            end = index + 1
            while end < len(lines) and not lines[end].strip():
                end += 1
            return "\n".join(lines[:end]) + "\n", "\n".join(lines[end:])
        if line.strip() and not line.lstrip().startswith("#"):
            break
    return "", text


def load_yaml(text: str) -> Any:
    """Parse YAML text keeping comments."""
    return new_yaml().load(text)


def dump_yaml(document: Any) -> str:
    """Serialize a round-trip document back to text."""
    stream = io.StringIO()
    new_yaml().dump(document, stream)
    return stream.getvalue()


def quoted(value: Any) -> Any:
    """Return strings double-quoted (the style of the input files); other types as is."""
    return DoubleQuotedScalarString(value) if isinstance(value, str) else value


def flow_list(values: Iterable[Any]) -> CommentedSeq:
    """Return a one-line ``[a, b]`` list."""
    seq = CommentedSeq(quoted(item) for item in values)
    seq.fa.set_flow_style()
    return seq


def has_value(value: Any) -> bool:
    """Return whether a user value counts as given (not "", None or an empty list)."""
    return value not in ("", None, [], {})


def clearable(current: Any) -> bool:
    """Return whether a blank user value clears ``current`` (non-empty text or plain list)."""
    if isinstance(current, str):
        return current != ""
    if isinstance(current, list):
        return bool(current) and not any(isinstance(item, (dict, list)) for item in current)
    return False


def set_value(mapping: Any, key: str, value: Any, changes: List[Change],
              label: str, where: str) -> None:
    """Set ``mapping[key]`` (quoted) when it differs and record the change.

    A blank value ("" / None / []) clears a text or a list of plain values, so
    a value removed from user_inputs.yml is removed from the file too. It
    never touches a boolean, a number, a block or a list of items.
    """
    old = mapping.get(key)
    if not has_value(value) and not isinstance(value, bool):
        if not clearable(old):
            return
        value = [] if isinstance(old, list) else ""
    new = list(value) if isinstance(value, (list, tuple)) else value
    if (list(old) if isinstance(old, list) else old) == new and not (
            isinstance(old, str) and old != new):
        return
    if isinstance(value, (list, tuple)):
        mapping[key] = flow_list(value)
    else:
        mapping[key] = quoted(value)
    changes.append((label, f"{where}.{key}", str(old), str(value)))


def item_with_key(sequence: Iterable[Any], key: str) -> Optional[CommentedMap]:
    """Return the first mapping of a list that has ``key`` (for ``- admin_network:`` items)."""
    for item in sequence:
        if isinstance(item, dict) and key in item:
            return item
    return None


def item_named(sequence: Iterable[Any], name: str) -> Optional[CommentedMap]:
    """Return the first mapping of a list whose ``name`` equals ``name``."""
    for item in sequence:
        if isinstance(item, dict) and str(item.get("name")) == name:
            return item
    return None


def edit_env(text: str, values: Dict[str, str], changes: List[Change], label: str) -> str:
    """Replace ``KEY=value`` lines of an env file; keys that are missing are appended.

    A blank value clears an existing line (``KEY=``) and adds nothing.
    """
    lines = text.split("\n")
    for key, value in values.items():
        value = "" if value is None else value
        pattern = re.compile(rf"^(\s*){re.escape(key)}=(.*)$")
        for index, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                if match.group(2).strip() != value:
                    lines[index] = f"{match.group(1)}{key}={value}"
                    changes.append((label, key, match.group(2).strip(), value))
                break
        else:
            if not value:
                continue
            while lines and lines[-1] == "":
                lines.pop()
            lines.extend(["", f"{key}={value}", ""])
            changes.append((label, key, "(absent)", value))
    return "\n".join(lines)


def csv_header(text: str) -> List[str]:
    """Return the column names of a CSV text (first non-empty line)."""
    for line in text.splitlines():
        if line.strip():
            return next(csv.reader([line]))
    raise EditError("the source CSV has no header line")


def render_csv(header: List[str], rows: List[Dict[str, str]]) -> str:
    """Render a CSV with ``header`` and one line per row (missing columns stay empty)."""
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([str(row.get(column, "") or "") for column in header])
    return stream.getvalue()
