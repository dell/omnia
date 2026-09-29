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

import copy
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
_KUBE_IMAGE_PATTERNS = {
    "kube-apiserver": re.compile(r"kube-apiserver$", re.IGNORECASE),
    "kube-controller-manager": re.compile(r"kube-controller-manager$", re.IGNORECASE),
    "kube-scheduler": re.compile(r"kube-scheduler$", re.IGNORECASE),
    "kube-proxy": re.compile(r"kube-proxy$", re.IGNORECASE),
}
_VERSION_RE = re.compile(r"(\d+\.\d+)\.\d+")
_REPONAME_KUBE_VERSION_RE = re.compile(r"kubernetes-v(\d+)-(\d+)", re.IGNORECASE)
_LAYER_VERSION_TOKEN_RE = re.compile(r"rhel_(\d+_\d+)_")

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


def detect_os_version_cutover(current_body: dict, future_body: dict):
    """Detect whether this diff is a wholesale base-OS-version cutover: every
    functional layer in the current catalog was renamed to its counterpart in
    the future catalog by substituting a single 'MAJOR_MINOR' version token
    (e.g. '10_0' -> '10_2'), with each renamed layer's component set
    otherwise unchanged, and no layer name is shared between the two catalogs.

    This is the situation the diff-changelog Story's worked example already
    describes in prose (a same-content catalog re-cut for a new OS version,
    where per-OS-version layer naming makes every group in the old layer set
    look "removed" relative to the new one). Detecting it lets the renderer
    consolidate what would otherwise be dozens of near-identical per-package
    and per-group lines into one explanatory note.

    Args:
        current_body: The current catalog's body (value under 'catalog').
        future_body: The future catalog's body (value under 'catalog').

    Returns:
        A dict {'old_version', 'new_version', 'renamed_layers'} (dotted
        version strings and a sorted list of (old_name, new_name) pairs) if
        the whole-catalog cutover pattern is detected, else None.
    """
    current_layers = {
        layer["name"]: set(layer.get("components", []))
        for layer in current_body.get("functionallayer", [])
    }
    future_layers = {
        layer["name"]: set(layer.get("components", []))
        for layer in future_body.get("functionallayer", [])
    }
    if not current_layers or not future_layers:
        return None
    if set(current_layers) & set(future_layers):
        return None  # some layer name persisted unchanged -- not a full cutover

    old_tokens = {tok for name in current_layers for tok in _LAYER_VERSION_TOKEN_RE.findall(name)}
    new_tokens = {tok for name in future_layers for tok in _LAYER_VERSION_TOKEN_RE.findall(name)}
    if len(old_tokens) != 1 or len(new_tokens) != 1:
        return None
    old_token, new_token = old_tokens.pop(), new_tokens.pop()
    if old_token == new_token:
        return None

    renamed_layers = []
    for name, components in current_layers.items():
        mapped = name.replace(old_token, new_token)
        if mapped not in future_layers or components != future_layers[mapped]:
            return None
        renamed_layers.append((name, mapped))

    return {
        "old_version": old_token.replace("_", "."),
        "new_version": new_token.replace("_", "."),
        "renamed_layers": sorted(renamed_layers),
    }


def _extract_minor_version(text: str):
    """Return the first 'X.Y' minor-version substring found in text, or None."""
    if not text:
        return None
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _find_kube_components(catalog_body: dict) -> dict:
    """Locate every CON-004 kube-core version pin in a catalog's packages,
    each with its resolved minor version -- across all three pin kinds the
    master reference file's A.8 CON-004 constraint actually covers:

    - **RPM** components (kubeadm/kubelet/kubectl/cri-o): minor version from
      the package's own name/key (e.g. 'kubelet-1.35.1').
    - **Container image** components (kube-apiserver/kube-controller-manager/
      kube-scheduler/kube-proxy): minor version from the image package's own
      `tag` field, not its key -- a `packagetype: image` entry's key is the
      image reference (e.g. 'registry.k8s.io/kube-apiserver'), which never
      changes when only the tag is bumped or rolled back.
    - **Repository identifier** components: any source whose `reponame`
      itself encodes a Kubernetes minor version (e.g. 'kubernetes-v1-35').
      This is tracked as its own component, separate from the RPM/image
      component sharing that repository, so a reponame that drifts out of
      sync with the package's own name/tag (e.g. the RPM still reads
      'kubelet-1.35.1' but its `reponame` moved to 'kubernetes-v1-34') is
      itself detected as a version-pin disagreement, not silently ignored.
    """
    found = {}
    for key, pkg in catalog_body.get("packages", {}).items():
        name = pkg.get("name", "") or ""
        tag = pkg.get("tag", "") or ""
        haystack = f"{key} {name}"
        packagetype = pkg.get("packagetype")

        if packagetype == "image":
            for label, pattern in _KUBE_IMAGE_PATTERNS.items():
                if label not in found and pattern.search(key):
                    minor = _extract_minor_version(tag)
                    if minor:
                        found[label] = {"key": key, "name": f"{name}:{tag}",
                                        "minor_version": minor}
        else:
            for label, pattern in _KUBE_COMPONENT_PATTERNS.items():
                if label not in found and pattern.search(haystack):
                    minor = _extract_minor_version(name) or _extract_minor_version(key)
                    if minor:
                        found[label] = {"key": key, "name": name, "minor_version": minor}

        for source in pkg.get("sources", []) or []:
            reponame = source.get("reponame") or ""
            match = _REPONAME_KUBE_VERSION_RE.search(reponame)
            if not match:
                continue
            label = f"repository '{reponame}'"
            if label not in found:
                found[label] = {"key": key, "name": reponame,
                                 "minor_version": f"{match.group(1)}.{match.group(2)}"}
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


def check_con007(current_body: dict, future_body: dict, cutover: dict = None) -> list:
    """CON-007 (master reference file A.8, warning): removing a group from one
    functional layer's components while another functional layer still
    references it affects both roles, not just the edited one.

    When `cutover` (from `detect_os_version_cutover`) is supplied and every
    individual finding below is fully explained by that whole-catalog
    OS-version rename (i.e. the only functional layer still referencing the
    "removed" group is that layer's own renamed counterpart), the per-group
    findings are consolidated into a single informational note instead of one
    warning per group -- otherwise a same-content OS-version cutover renders
    as dozens of near-duplicate CON-007 lines that all say the same thing.

    Args:
        current_body: The current catalog's body.
        future_body: The future catalog's body.
        cutover: Optional result of `detect_os_version_cutover(current_body,
            future_body)`, used only to consolidate presentation -- it never
            suppresses a finding that isn't fully explained by the rename.

    Returns:
        A list of warning dicts (one per affected group/layer pairing, or a
        single consolidated dict when `cutover` explains every finding).
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
    rename_map = dict(cutover["renamed_layers"]) if cutover else {}

    # A group's removal is fully explained by the rename (not a real
    # structural change) when the *set* of layers referencing it, translated
    # through the rename map, is identical before and after -- i.e. it was
    # already shared across exactly the layers that got renamed, and nothing
    # else changed about who references it.
    all_groups = {g for comps in current_layers.values() for g in comps}
    all_groups |= {g for comps in future_layers.values() for g in comps}
    cutover_explained_groups = set()
    if cutover:
        for group in all_groups:
            old_refs = {name for name, comps in current_layers.items() if group in comps}
            new_refs = {name for name, comps in future_layers.items() if group in comps}
            translated_old_refs = {rename_map.get(name, name) for name in old_refs}
            if old_refs and translated_old_refs == new_refs:
                cutover_explained_groups.add(group)

    for layer_name, old_components in current_layers.items():
        new_components = future_layers.get(layer_name, set())
        for group in old_components - new_components:
            if group in cutover_explained_groups:
                continue
            still_referenced_by = sorted(
                other_name for other_name, other_components in future_layers.items()
                if other_name != layer_name and group in other_components
            )
            if not still_referenced_by:
                continue
            warnings.append({
                "constraint_id": "CON-007",
                "severity": "warning",
                "message": (
                    f"Group '{group}' was removed from functional layer '{layer_name}', "
                    f"but is still referenced by {', '.join(still_referenced_by)} -- "
                    "removing it here does not remove it from those layers."
                ),
            })

    if cutover_explained_groups:
        example = sorted(cutover_explained_groups)[0]
        warnings.insert(0, {
            "constraint_id": "CON-007",
            "severity": "info",
            "message": (
                f"Base-OS-version cutover ({cutover['old_version']} -> "
                f"{cutover['new_version']}): {len(cutover_explained_groups)} group(s) "
                f"across {len(cutover['renamed_layers'])} functional layer(s) appear "
                f"'removed' only because each layer was renamed to its "
                f"{cutover['new_version']} equivalent, and every layer that referenced "
                f"the group before still does after the rename (e.g. group "
                f"'{example}'). This is not an orphaned-group warning -- see the Base "
                "OS, Architecture, and Catalog Metadata Impact section for the full "
                "old -> new layer-name mapping. Affected groups: "
                f"{', '.join(sorted(cutover_explained_groups))}."
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
    cutover = detect_os_version_cutover(current_body, future_body)
    warnings = []
    warnings.extend(check_con004(future_body, forward_diff))
    warnings.extend(check_con007(current_body, future_body, cutover))
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


def _without_source_versions(pkg: dict) -> dict:
    """Deep-copy a package value with every source's 'version' list stripped,
    so two packages that differ only in their OS-version pin compare equal.
    """
    clone = copy.deepcopy(pkg)
    for source in clone.get("sources", []) or []:
        source.pop("version", None)
    return clone


def _is_pure_version_bump(old_pkg: dict, new_pkg: dict, cutover: dict) -> bool:
    """True when a changed package's only difference is its source(s)' version
    list moving from the cutover's old version to its new version -- the same
    per-package "diff" that a whole-catalog OS-version re-cut produces,
    whether or not the package also carries its own unrelated top-level
    `version`/`tag` (e.g. a container image tag), which is compared as-is.
    """
    if not cutover or not old_pkg or not new_pkg:
        return False
    if not (set(_source_versions(old_pkg)) == {cutover["old_version"]}
            and set(_source_versions(new_pkg)) == {cutover["new_version"]}):
        return False
    return _without_source_versions(old_pkg) == _without_source_versions(new_pkg)


def _split_package_changes(changed: list, cutover: dict) -> tuple:
    """Split a packages summary's 'changed' list into (pure_version_bumps,
    other_changes), using `_is_pure_version_bump` against `cutover`.
    """
    if not cutover:
        return [], changed
    bumps, other = [], []
    for item in changed:
        (bumps if _is_pure_version_bump(item["old"], item["new"], cutover) else other).append(item)
    return bumps, other


def _render_package_section(pkg: dict, cutover: dict = None) -> list:
    """Render the '## Packages' section's lines from a packages summary bucket.

    When `cutover` is supplied, packages whose only change is the version-list
    bump the cutover already explains are collapsed into a single summary
    line instead of one near-identical bullet per package.
    """
    bumps, other_changed = _split_package_changes(pkg["changed"], cutover)
    lines = [f"## Packages ({len(pkg['added'])} added, {len(pkg['removed'])} removed, "
             f"{len(pkg['changed'])} changed)"]
    for item in pkg["added"]:
        lines.append(f"- + {item['key']}: {_package_label(item['value'])}")
    for item in pkg["removed"]:
        lines.append(f"- - {item['key']}: {_package_label(item['value'])}")
    if bumps:
        lines.append(
            f"- ~ {len(bumps)} package(s) version-bumped {cutover['old_version']} -> "
            f"{cutover['new_version']} only (no other change) as part of the base-OS-"
            f"version cutover: {', '.join(item['key'] for item in bumps[:5])}"
            + (f", and {len(bumps) - 5} more" if len(bumps) > 5 else "")
        )
    for item in other_changed:
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


def _render_impact_section(summary: dict, cutover: dict = None) -> list:
    """Render the base-OS/architecture/catalog-metadata impact section's lines."""
    base_os_notes = _base_os_notes(summary)
    arch_notes = _architecture_notes(summary)
    if not (base_os_notes or arch_notes or summary["catalog_fields"] or cutover):
        return []
    lines = ["## Base OS, Architecture, and Catalog Metadata Impact"]
    if cutover:
        lines.append(
            f"- Base-OS-version cutover: {cutover['old_version']} -> "
            f"{cutover['new_version']} ({len(cutover['renamed_layers'])} functional "
            "layer(s) renamed, components unchanged):"
        )
        for old_name, new_name in cutover["renamed_layers"]:
            lines.append(f"  - {old_name} -> {new_name}")
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


def render_changelog_text(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        current_name: str, future_name: str, schema_version: dict,
        summary: dict, warnings: list, cutover: dict = None) -> str:
    """Render the plain-English changelog (Markdown-flavored text).

    Args:
        current_name: Display name/identifier for the current catalog.
        future_name: Display name/identifier for the future catalog.
        schema_version: {'current': ..., 'future': ...} labels from diff_catalogs.
        summary: The dict from `summarize()`.
        warnings: The list from `collect_warnings()`.
        cutover: Optional result of `detect_os_version_cutover()`, used to
            consolidate pure OS-version-bump package lines and to render the
            old -> new functional-layer-name mapping.

    Returns:
        The changelog as a single Markdown-flavored text string.
    """
    lines = [f"# Changelog: {current_name} -> {future_name}", "",
             f"Schema version: {schema_version['current']} -> {schema_version['future']}", ""]
    lines.extend(_render_package_section(summary["packages"], cutover))
    lines.extend(_render_keyed_section("Groups", summary["groups"]))
    lines.extend(_render_keyed_section("Functional Layers", summary["functionallayer"]))
    lines.extend(_render_impact_section(summary, cutover))
    lines.extend(_render_warnings_section(warnings))
    return "\n".join(lines)


def render_html(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        current_name: str, future_name: str, schema_version: dict,
        summary: dict, warnings: list, cutover: dict = None):
    """Render the rich HTML changelog report via Jinja2.

    Args:
        current_name: Display name/identifier for the current catalog.
        future_name: Display name/identifier for the future catalog.
        schema_version: {'current': ..., 'future': ...} labels from diff_catalogs.
        summary: The dict from `summarize()`.
        warnings: The list from `collect_warnings()`.
        cutover: Optional result of `detect_os_version_cutover()`.

    Returns:
        The rendered HTML as a string, or None if `jinja2` is not installed
        (the plain-text changelog remains the guaranteed artifact either way).
    """
    try:
        import jinja2
    except ImportError:
        logger.warning("jinja2 not installed, skipping HTML report generation")
        return None

    bumps, other_changed = _split_package_changes(summary["packages"]["changed"], cutover)

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
        cutover=cutover,
        version_bump_packages=bumps,
        other_changed_packages=other_changed,
    )
