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
# pylint: disable=too-many-locals
"""
Human-readable changelog rendering for the catalog diff engine (`differ.py`).

Produces two artifacts from a `differ.diff_catalogs()` result, both derived
from the same underlying diff and never merged into it:
    1. A plain-English changelog (Markdown-flavored text).
    2. A rich HTML report (Jinja2), when the `jinja2` package is available.

Also implements the two deterministic, offline compatibility/dependency
warnings this Story's scope supports (master reference file A.8):
    - CON-004: Kubernetes RPM/image/repo version pins must agree.
    - CON-007: Removing a group that another selected role still
      references affects both roles.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

_KUBE_COMPONENT_PATTERNS = {
    "kubeadm": re.compile(r"kubeadm", re.IGNORECASE),
    "kubelet": re.compile(r"kubelet", re.IGNORECASE),
    "kubectl": re.compile(r"kubectl", re.IGNORECASE),
    "cri-o": re.compile(r"cri[-_]o", re.IGNORECASE),
}
_VERSION_RE = re.compile(r"(\d+\.\d+)\.\d+")

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
TEMPLATE_NAME = "changelog_report.html.j2"


def _append_change(bucket: dict, op: dict, key: str, old_value, new_value) -> None:
    """Append one op's effect to a summary bucket's added/removed/changed list."""
    if op["op"] == "add":
        bucket["added"].append({"key": key, "value": new_value})
    elif op["op"] == "remove":
        bucket["removed"].append({"key": key, "value": old_value})
    else:
        bucket["changed"].append({"key": key, "old": old_value, "new": new_value})


def summarize(current_body: dict, future_body: dict, forward_diff: list) -> dict:
    """Build a human-readable summary of a forward diff, resolving raw op paths
    back to named packages/groups/functional-layers and catalog fields.

    Args:
        current_body: The current catalog's body (value under 'catalog').
        future_body: The future catalog's body (value under 'catalog').
        forward_diff: The op-list from `differ.build_ops(current, future)`.

    Returns:
        dict with 'catalog_fields' (list) and 'packages'/'groups'/
        'functionallayer' (each an {'added', 'removed', 'changed'} dict).
    """
    current_packages = current_body.get("packages", {})
    future_packages = future_body.get("packages", {})
    current_groups = current_body.get("groups", {})
    future_groups = future_body.get("groups", {})
    current_layers = {layer["name"]: layer for layer in current_body.get("functionallayer", [])}
    future_layers = {layer["name"]: layer for layer in future_body.get("functionallayer", [])}

    summary = {
        "catalog_fields": [],
        "packages": {"added": [], "removed": [], "changed": []},
        "groups": {"added": [], "removed": [], "changed": []},
        "functionallayer": {"added": [], "removed": [], "changed": []},
    }

    for op in forward_diff:
        path = op["path"]
        if path[:2] == ["catalog", "packages"]:
            key = path[2]
            _append_change(summary["packages"], op, key,
                            current_packages.get(key), future_packages.get(key))
        elif path[:2] == ["catalog", "groups"]:
            key = path[2]
            _append_change(summary["groups"], op, key,
                            current_groups.get(key), future_groups.get(key))
        elif path[:2] == ["catalog", "functionallayer_by_name"]:
            key = path[2]
            _append_change(summary["functionallayer"], op, key,
                            current_layers.get(key), future_layers.get(key))
        elif len(path) == 2 and path[1] != "functionallayer_order":
            field = path[1]
            summary["catalog_fields"].append({
                "field": field,
                "old": current_body.get(field),
                "new": op.get("value"),
            })

    return summary


def _extract_minor_version(text: str):
    """Return the first 'X.Y' minor-version substring found in text, or None."""
    if not text:
        return None
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _find_kube_components(catalog_body: dict) -> dict:
    """Locate the CON-004 kube-core components (kubeadm/kubelet/kubectl/cri-o)
    in a catalog's packages, each with its resolved minor version.
    """
    found = {}
    for key, pkg in catalog_body.get("packages", {}).items():
        name = pkg.get("name", "") or ""
        haystack = f"{key} {name}"
        for label, pattern in _KUBE_COMPONENT_PATTERNS.items():
            if label in found:
                continue
            if pattern.search(haystack):
                minor = _extract_minor_version(name) or _extract_minor_version(key)
                if minor:
                    found[label] = {"key": key, "name": name, "minor_version": minor}
    return found


def check_con004(future_body: dict, forward_diff: list) -> list:
    """CON-004 (master reference file A.8, blocking): Kubernetes RPM/image/repo
    version pins must agree. Only surfaces when the diff actually touched one
    of the affected packages and the future catalog's pins now disagree.

    Args:
        future_body: The future catalog's body.
        forward_diff: The op-list from `differ.build_ops(current, future)`.

    Returns:
        A list with at most one warning dict, or an empty list.
    """
    touched_keys = {
        op["path"][2] for op in forward_diff if op["path"][:2] == ["catalog", "packages"]
    }
    future_components = _find_kube_components(future_body)
    if len(future_components) < 2:
        return []

    minors = {component["minor_version"] for component in future_components.values()}
    if len(minors) <= 1:
        return []

    touched = any(component["key"] in touched_keys for component in future_components.values())
    if not touched:
        return []

    detail = ", ".join(
        f"{label} {component['name']} ({component['minor_version']})"
        for label, component in sorted(future_components.items())
    )
    return [{
        "constraint_id": "CON-004",
        "severity": "blocking",
        "message": (
            f"Kubernetes component version pins disagree after this change: {detail}. "
            "Master reference file A.8 CON-004 requires the kubeadm/kubelet/kubectl "
            "RPM and cri-o pins to share the same minor version."
        ),
    }]


def check_con007(current_body: dict, future_body: dict) -> list:
    """CON-007 (master reference file A.8, warning): removing a group from one
    functional layer's components while another functional layer still
    references it affects both roles, not just the edited one.

    Args:
        current_body: The current catalog's body.
        future_body: The future catalog's body.

    Returns:
        A list of warning dicts (one per affected group/layer pairing).
    """
    warnings = []
    current_layers = {
        layer["name"]: set(layer.get("components", []))
        for layer in current_body.get("functionallayer", [])
    }
    future_layers = {
        layer["name"]: set(layer.get("components", []))
        for layer in future_body.get("functionallayer", [])
    }

    for layer_name, old_components in current_layers.items():
        new_components = future_layers.get(layer_name, set())
        for group in old_components - new_components:
            still_referenced_by = sorted(
                other_name for other_name, other_components in future_layers.items()
                if other_name != layer_name and group in other_components
            )
            if still_referenced_by:
                warnings.append({
                    "constraint_id": "CON-007",
                    "severity": "warning",
                    "message": (
                        f"Group '{group}' was removed from functional layer '{layer_name}', "
                        f"but is still referenced by {', '.join(still_referenced_by)} -- "
                        "removing it here does not remove it from those layers."
                    ),
                })
    return warnings


def collect_warnings(current_body: dict, future_body: dict, forward_diff: list) -> list:
    """Run all implemented compatibility/dependency checks and combine results.

    Args:
        current_body: The current catalog's body.
        future_body: The future catalog's body.
        forward_diff: The op-list from `differ.build_ops(current, future)`.

    Returns:
        Combined list of warning dicts from every implemented check.
    """
    warnings = []
    warnings.extend(check_con004(future_body, forward_diff))
    warnings.extend(check_con007(current_body, future_body))
    return warnings


def _base_os_notes(summary: dict) -> list:
    """Extract base-OS group changes (os/os_version) from a groups summary."""
    notes = []
    for item in summary["groups"]["changed"]:
        old_group, new_group = item["old"] or {}, item["new"] or {}
        if old_group.get("type") != "base_os" and new_group.get("type") != "base_os":
            continue
        old_os = f"{old_group.get('os', '')} {old_group.get('os_version', '')}".strip()
        new_os = f"{new_group.get('os', '')} {new_group.get('os_version', '')}".strip()
        if old_os != new_os:
            notes.append(f"Base OS group '{item['key']}': {old_os} -> {new_os}")
    return notes


def _architecture_notes(summary: dict) -> list:
    """Extract architecture-support changes from a packages summary."""
    def archs_of(pkg):
        archs = set()
        for source in (pkg or {}).get("sources", []) or []:
            arch = source.get("architecture")
            if arch:
                archs.add(arch)
        return archs

    notes = []
    for item in summary["packages"]["changed"]:
        old_archs, new_archs = archs_of(item["old"]), archs_of(item["new"])
        if old_archs != new_archs:
            notes.append(
                f"Package '{item['key']}' architecture support: "
                f"{sorted(old_archs)} -> {sorted(new_archs)}"
            )
    return notes


def _source_versions(pkg: dict) -> list:
    """Flatten every source's 'version' list into one sorted, de-duplicated list."""
    versions = set()
    for source in pkg.get("sources", []) or []:
        versions.update(source.get("version") or [])
    return sorted(versions)


def _package_label(pkg) -> str:
    """Best-effort human label for a package value (name + version/tag, plus the
    source-level version list when the package has no top-level version/tag of
    its own -- otherwise an unchanged os-version-only source bump would render
    as an identical-looking 'before'/'after' pair).
    """
    if not pkg:
        return "<unknown>"
    name = pkg.get("name", "")
    version = pkg.get("version") or pkg.get("tag") or ""
    if version:
        return f"{name} ({version})"
    source_versions = _source_versions(pkg)
    return f"{name} [{', '.join(source_versions)}]" if source_versions else name


def _render_package_section(pkg: dict) -> list:
    """Render the '## Packages' section's lines from a packages summary bucket."""
    lines = [f"## Packages ({len(pkg['added'])} added, {len(pkg['removed'])} removed, "
             f"{len(pkg['changed'])} changed)"]
    for item in pkg["added"]:
        lines.append(f"- + {item['key']}: {_package_label(item['value'])}")
    for item in pkg["removed"]:
        lines.append(f"- - {item['key']}: {_package_label(item['value'])}")
    for item in pkg["changed"]:
        lines.append(f"- ~ {item['key']}: {_package_label(item['old'])} -> "
                     f"{_package_label(item['new'])}")
    lines.append("")
    return lines


def _render_keyed_section(title: str, bucket: dict) -> list:
    """Render a '## <title>' section's lines from a key-only summary bucket
    (groups or functional layers, which have no per-item label beyond their key).
    """
    lines = [f"## {title} ({len(bucket['added'])} added, {len(bucket['removed'])} removed, "
             f"{len(bucket['changed'])} changed)"]
    for item in bucket["added"]:
        lines.append(f"- + {item['key']}")
    for item in bucket["removed"]:
        lines.append(f"- - {item['key']}")
    for item in bucket["changed"]:
        lines.append(f"- ~ {item['key']}")
    lines.append("")
    return lines


def _render_impact_section(summary: dict) -> list:
    """Render the base-OS/architecture/catalog-metadata impact section's lines."""
    base_os_notes = _base_os_notes(summary)
    arch_notes = _architecture_notes(summary)
    if not (base_os_notes or arch_notes or summary["catalog_fields"]):
        return []
    lines = ["## Base OS, Architecture, and Catalog Metadata Impact"]
    for note in base_os_notes + arch_notes:
        lines.append(f"- {note}")
    for item in summary["catalog_fields"]:
        lines.append(f"- {item['field']}: {item['old']} -> {item['new']}")
    lines.append("")
    return lines


def _render_warnings_section(warnings: list) -> list:
    """Render the compatibility/dependency warnings section's lines."""
    lines = ["## Compatibility / Dependency Warnings"]
    if not warnings:
        lines.append("- None detected.")
        return lines
    for warning in warnings:
        lines.append(f"- [{warning['severity'].upper()}] {warning['constraint_id']}: "
                     f"{warning['message']}")
    return lines


def render_changelog_text(current_name: str, future_name: str, schema_version: dict,
                           summary: dict, warnings: list) -> str:
    """Render the plain-English changelog (Markdown-flavored text).

    Args:
        current_name: Display name/identifier for the current catalog.
        future_name: Display name/identifier for the future catalog.
        schema_version: {'current': ..., 'future': ...} labels from diff_catalogs.
        summary: The dict from `summarize()`.
        warnings: The list from `collect_warnings()`.

    Returns:
        The changelog as a single Markdown-flavored text string.
    """
    lines = [f"# Changelog: {current_name} -> {future_name}", "",
             f"Schema version: {schema_version['current']} -> {schema_version['future']}", ""]
    lines.extend(_render_package_section(summary["packages"]))
    lines.extend(_render_keyed_section("Groups", summary["groups"]))
    lines.extend(_render_keyed_section("Functional Layers", summary["functionallayer"]))
    lines.extend(_render_impact_section(summary))
    lines.extend(_render_warnings_section(warnings))
    return "\n".join(lines)


def render_html(current_name: str, future_name: str, schema_version: dict,
                 summary: dict, warnings: list):
    """Render the rich HTML changelog report via Jinja2.

    Args:
        current_name: Display name/identifier for the current catalog.
        future_name: Display name/identifier for the future catalog.
        schema_version: {'current': ..., 'future': ...} labels from diff_catalogs.
        summary: The dict from `summarize()`.
        warnings: The list from `collect_warnings()`.

    Returns:
        The rendered HTML as a string, or None if `jinja2` is not installed
        (the plain-text changelog remains the guaranteed artifact either way).
    """
    try:
        import jinja2
    except ImportError:
        logger.warning("jinja2 not installed, skipping HTML report generation")
        return None

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    return template.render(
        current_name=current_name,
        future_name=future_name,
        schema_version=schema_version,
        summary=summary,
        warnings=warnings,
        base_os_notes=_base_os_notes(summary),
        architecture_notes=_architecture_notes(summary),
        package_label=_package_label,
    )
