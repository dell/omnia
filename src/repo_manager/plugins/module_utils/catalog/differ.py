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
"""
Catalog Diff/Patch Engine: deterministic, reversible diff between two
Schema 2.0 catalogs (lowercase 'catalog' root key only).

This is a plain dict/set comparison, not a model-generated diff, so the
reversibility invariant (current + forward_diff == future, future +
reverse_diff == current) can be verified exactly rather than hoped for.
"""

from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any

CATALOG_SCALAR_FIELDS = ("name", "version", "schema_version", "identifier", "description")


class CatalogFormatError(Exception):
    """Raised when a catalog is not a supported Schema 2.0 catalog for diffing."""


def _require_schema_2(catalog: dict, label: str) -> dict:
    """Validate a catalog is Schema 2.0 (lowercase 'catalog' root) and return its body.

    Args:
        catalog: The raw catalog dict as loaded from JSON.
        label: Human label ('current' or 'future') for the error message.

    Returns:
        The catalog body (the value under the 'catalog' key).

    Raises:
        CatalogFormatError: If the catalog uses the legacy Schema 1.0
            PascalCase 'Catalog' root key, or has no recognizable root key.
    """
    if "catalog" in catalog:
        return catalog["catalog"]
    if "Catalog" in catalog:
        raise CatalogFormatError(
            f"The {label} catalog uses the legacy Schema 1.0 format (PascalCase "
            f"'Catalog' root key). Run 'catalog_manager.py transform' to convert it "
            f"to Schema 2.0 first -- this diff engine only supports the current "
            f"lowercase-root schema."
        )
    raise CatalogFormatError(f"The {label} catalog is missing a 'catalog' root key.")


def schema_version_label(catalog_body: dict) -> str:
    """Return a human-readable label for a catalog's internal schema_version field.

    Args:
        catalog_body: The catalog body (value under the 'catalog' key).

    Returns:
        The schema_version as a string, or a note that it is unspecified
        (older catalogs built before the field existed omit it).
    """
    version = catalog_body.get("schema_version")
    return str(version) if version is not None else "unspecified (pre-schema_version catalog)"


def _index_functional_layer(layers: list) -> dict:
    """Index a functionallayer list by its 'name' field, preserving order."""
    indexed = {}
    for layer in layers:
        indexed[layer["name"]] = layer
    return indexed


def _component_ops(old_value: dict, new_value: dict, path: list):
    """Return ordered list edits, or None when whole-object replacement is needed."""
    if not isinstance(old_value, dict) or not isinstance(new_value, dict):
        return None
    old_items, new_items = old_value.get("components"), new_value.get("components")
    if not isinstance(old_items, list) or not isinstance(new_items, list):
        return None
    if not all(isinstance(item, str) for item in old_items + new_items):
        return None
    if ({key: value for key, value in old_value.items() if key != "components"}
            != {key: value for key, value in new_value.items() if key != "components"}):
        return None

    ops = []
    # Walk right-to-left so earlier indices remain valid after each edit.
    matcher = SequenceMatcher(a=old_items, b=new_items, autojunk=False)
    for tag, start, end, new_start, new_end in reversed(matcher.get_opcodes()):
        if tag == "equal":
            continue
        for index in range(end - 1, start - 1, -1):
            ops.append({"op": "remove_component", "path": path + ["components"],
                        "index": index, "value": old_items[index]})
        for offset, value in enumerate(new_items[new_start:new_end]):
            ops.append({"op": "insert_component", "path": path + ["components"],
                        "index": start + offset, "value": value})
    return ops


def _build_map_ops(old_map: dict, new_map: dict, path_prefix: list) -> list:
    """Build forward ops (old -> new) for a single dict-keyed collection.

    Args:
        old_map: The collection's state in the source catalog.
        new_map: The collection's state in the target catalog.
        path_prefix: Path segments identifying this collection, e.g.
            ["catalog", "packages"].

    Returns:
        Whole-object add/remove/set operations, or indexed component operations
        for component-only changes in groups and functional layers.
    """
    ops = []
    for key, old_val in old_map.items():
        if key not in new_map:
            ops.append({"op": "remove", "path": path_prefix + [key]})
        elif old_val != new_map[key]:
            component_ops = None
            if path_prefix[1] in ("groups", "functionallayer_by_name"):
                component_ops = _component_ops(old_val, new_map[key], path_prefix + [key])
            if component_ops is not None:
                ops.extend(component_ops)
            else:
                ops.append({"op": "set", "path": path_prefix + [key],
                            "value": deepcopy(new_map[key])})
    for key, new_val in new_map.items():
        if key not in old_map:
            ops.append({"op": "add", "path": path_prefix + [key], "value": deepcopy(new_val)})
    return ops


def build_ops(old_catalog: dict, new_catalog: dict) -> list:
    """Build a deterministic, self-contained op-list diff from old to new.

    Args:
        old_catalog: The source catalog (root key 'catalog').
        new_catalog: The target catalog (root key 'catalog').

    Returns:
        A list of ops (see `_build_map_ops`) that, applied via `apply_patch`
        to old_catalog, reproduces new_catalog exactly. Calling this again
        with the arguments swapped produces the exact inverse op-list.

    Raises:
        CatalogFormatError: If either catalog isn't a supported Schema 2.0 catalog.
    """
    old_cat = _require_schema_2(old_catalog, "source")
    new_cat = _require_schema_2(new_catalog, "target")

    ops = []

    for field in CATALOG_SCALAR_FIELDS:
        old_val = old_cat.get(field)
        new_val = new_cat.get(field)
        if old_val == new_val:
            continue
        if field not in new_cat:
            ops.append({"op": "remove", "path": ["catalog", field]})
        else:
            ops.append({"op": "set", "path": ["catalog", field], "value": deepcopy(new_val)})

    ops.extend(_build_map_ops(old_cat.get("packages", {}), new_cat.get("packages", {}),
                               ["catalog", "packages"]))
    ops.extend(_build_map_ops(old_cat.get("groups", {}), new_cat.get("groups", {}),
                               ["catalog", "groups"]))

    old_layers = _index_functional_layer(old_cat.get("functionallayer", []))
    new_layers = _index_functional_layer(new_cat.get("functionallayer", []))
    ops.extend(_build_map_ops(old_layers, new_layers, ["catalog", "functionallayer_by_name"]))

    old_order = list(old_layers.keys())
    new_order = list(new_layers.keys())
    if old_order != new_order:
        ops.append({"op": "set", "path": ["catalog", "functionallayer_order"],
                    "value": deepcopy(new_order)})

    return ops


def _apply_component_op(cat: dict, layers_by_name: dict, op: dict) -> None:
    """Apply one checked list edit; reject invalid indices and stale removals."""
    path = op.get("path")
    if not isinstance(path, list) or len(path) != 4:
        raise CatalogFormatError("Invalid component operation path")
    if (path[0] != "catalog" or path[1] not in ("groups", "functionallayer_by_name")
            or not isinstance(path[2], str) or path[3] != "components"):
        raise CatalogFormatError("Invalid component operation path")
    collection = layers_by_name if path[1] == "functionallayer_by_name" else cat.get("groups", {})
    entry = collection.get(path[2])
    items = entry.get("components") if isinstance(entry, dict) else None
    index, value = op.get("index"), op.get("value")
    valid_index = isinstance(index, int) and not isinstance(index, bool)
    if (not isinstance(items, list) or not valid_index
            or not isinstance(value, str) or index < 0 or index > len(items)):
        raise CatalogFormatError("Invalid component operation target, index or value")
    if op["op"] == "remove_component":
        if index == len(items) or items[index] != value:
            raise CatalogFormatError("Component removal does not match the source at its index")
        items.pop(index)
    else:
        items.insert(index, value)


def apply_patch(source_catalog: dict, ops: list) -> dict:
    """Apply a self-contained op-list (from `build_ops`) to a catalog.

    Args:
        source_catalog: The catalog to apply the ops to (not mutated).
        ops: An op-list as produced by `build_ops`.

    Returns:
        A new catalog dict with the ops applied.

    Raises:
        CatalogFormatError: If source_catalog isn't a supported Schema 2.0 catalog.
    """
    result = deepcopy(source_catalog)
    cat = _require_schema_2(result, "source")

    layers_by_name = _index_functional_layer(cat.get("functionallayer", []))
    order = list(layers_by_name.keys())

    for op in ops:
        if op["op"] in ("insert_component", "remove_component"):
            _apply_component_op(cat, layers_by_name, op)
            continue
        if op["op"] not in ("add", "remove", "set"):
            raise CatalogFormatError("Unknown patch operation")
        path = op["path"]
        if path[:2] == ["catalog", "functionallayer_by_name"]:
            name = path[2]
            if op["op"] == "remove":
                layers_by_name.pop(name, None)
            else:
                layers_by_name[name] = deepcopy(op["value"])
        elif path == ["catalog", "functionallayer_order"]:
            order = deepcopy(op["value"])
        elif path[1] in ("packages", "groups"):
            container = cat.setdefault(path[1], {})
            key = path[2]
            if op["op"] == "remove":
                container.pop(key, None)
            else:
                container[key] = deepcopy(op["value"])
        elif len(path) == 2:
            field = path[1]
            if op["op"] == "remove":
                cat.pop(field, None)
            else:
                cat[field] = deepcopy(op["value"])

    cat["functionallayer"] = [layers_by_name[name] for name in order if name in layers_by_name]
    return result


class ReversibilityError(Exception):
    """Raised when a computed forward/reverse diff pair fails to reconstruct exactly."""


def diff_catalogs(current_catalog: dict, future_catalog: dict) -> dict:
    """Compute and verify a reversible forward/reverse diff between two catalogs.

    Args:
        current_catalog: The 'current_catalog' (root key 'catalog').
        future_catalog: The 'future_catalog' (root key 'catalog').

    Returns:
        dict with keys:
            'forward_diff': ops turning current_catalog into future_catalog.
            'reverse_diff': ops turning future_catalog into current_catalog.
            'schema_version': {'current': ..., 'future': ...} informational labels.

    Raises:
        CatalogFormatError: If either catalog isn't a supported Schema 2.0 catalog.
        ReversibilityError: If the computed diffs do not reconstruct exactly
            (should not happen for two well-formed Schema 2.0 catalogs; kept
            as a hard safety check rather than a silent best-effort result).
    """
    forward_diff = build_ops(current_catalog, future_catalog)
    reverse_diff = build_ops(future_catalog, current_catalog)

    reconstructed_future = apply_patch(current_catalog, forward_diff)
    if reconstructed_future != future_catalog:
        raise ReversibilityError(
            "current_catalog + forward_diff did not reproduce future_catalog exactly."
        )

    reconstructed_current = apply_patch(future_catalog, reverse_diff)
    if reconstructed_current != current_catalog:
        raise ReversibilityError(
            "future_catalog + reverse_diff did not reproduce current_catalog exactly."
        )

    current_body = _require_schema_2(current_catalog, "current")
    future_body = _require_schema_2(future_catalog, "future")

    return {
        "forward_diff": forward_diff,
        "reverse_diff": reverse_diff,
        "schema_version": {
            "current": schema_version_label(current_body),
            "future": schema_version_label(future_body),
        },
    }


def _describe_op(op: dict) -> dict[str, Any]:
    """Return a shallow copy of an op suitable for JSON serialization."""
    return dict(op)


def serialize_ops(ops: list) -> list:
    """Return a JSON-serializable copy of an op-list.

    Args:
        ops: An op-list as produced by `build_ops`.

    Returns:
        A list of plain dicts (defensive copy; ops are already JSON-safe,
        this exists so callers don't need to know that).
    """
    return [_describe_op(op) for op in ops]
