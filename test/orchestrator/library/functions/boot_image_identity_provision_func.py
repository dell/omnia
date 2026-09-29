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

"""Boot image identity and architecture verification.

Verifies that the Boot Service configurations deployed by provision match
the kernel, initrd, and rootfs paths declared in ``build_status.yml`` and
that each functional group is listed under the correct architecture key.

The matching strategy mirrors the Orchestrator's ``validate_image.yml``:

1. Exact name match between Boot Service configuration name and the
   ``functional_group`` field in ``build_status.yml``.
2. Prefix + architecture suffix match when the PXE mapping name does not
   include the OS version segment (e.g. ``slurm_node_x86_64`` matches
   ``slurm_node_rhel_10_0_x86_64``).
3. Strip ``_first`` fallback for the primary Kubernetes control plane
   (``service_kube_control_plane_first_*`` reuses the non-``_first`` image).
"""

import posixpath
from collections.abc import Mapping
from typing import Any

from omnia_auto import resolve_domain_data_path

from ..vars.precheck_vars import (
    ENV_IMAGE_BUILD_MANAGER_DATA_PATH,
    ENV_OMNIA_DATA_PATH,
)
from ._pxeboot_helpers import (
    fg_prefix_without_os,
    parse_fg_identity,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import (
    api_json,
    exception_result,
    group_header,
    load_context,
    metadata_name,
    resource_list,
    result,
)
from .project_func import (
    resolve_target_input_project_path,
    resolve_target_project_name,
)


# -------------------------------------------------------------------
# build_status.yml resolution (mirrors precheck_func._dependency_paths)
# -------------------------------------------------------------------

def _build_status_path(host) -> str:
    """Resolve the build_status.yml path on the target."""
    input_dir = resolve_target_input_project_path(host)
    config = read_yaml_mapping(
        host, posixpath.join(input_dir, "orchestrator_config.yml")
    )
    explicit = config.get("image_build_manager_output_path")
    if isinstance(explicit, str) and explicit.strip():
        path = explicit.strip()
        if not posixpath.isabs(path):
            raise ValueError(
                f"image_build_manager_output_path must be absolute: {path}"
            )
        return path
    root = resolve_domain_data_path(
        host,
        "image_build_manager",
        ENV_OMNIA_DATA_PATH,
        domain_data_path_var=ENV_IMAGE_BUILD_MANAGER_DATA_PATH,
    )
    return posixpath.join(
        root, "output", resolve_target_project_name(host), "build_status.yml"
    )


# -------------------------------------------------------------------
# build_status parsing — preserves architecture keys
# -------------------------------------------------------------------

def _parse_build_status_images(
    build_status: Mapping[str, Any],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Parse ``functional_group_images`` returning entries and arch mapping.

    Returns:
        entries: ``[{group, kernel, initrd, image}, ...]``
        arch_map: ``{functional_group_name -> architecture_key}``
    """
    raw_images = build_status.get("functional_group_images", []) or []
    if not isinstance(raw_images, list):
        raise TypeError("functional_group_images must be a list")
    entries: list[dict[str, str]] = []
    arch_map: dict[str, str] = {}
    for block in raw_images:
        if not isinstance(block, dict):
            raise TypeError("functional_group_images entries must be mappings")
        # Flat format: {functional_group: "...", kernel: "...", ...}
        if "functional_group" in block:
            entry = _extract_entry(block)
            entries.append(entry)
            # No architecture key available in flat format.
            continue
        # Nested format: {x86_64: [...], aarch64: [...]}
        for arch_key, arch_entries in block.items():
            if not isinstance(arch_entries, list):
                raise TypeError(
                    f"architecture image entries under '{arch_key}' must be lists"
                )
            for candidate in arch_entries:
                entry = _extract_entry(candidate)
                entries.append(entry)
                arch_map[entry["group"]] = str(arch_key)
    if not entries:
        raise ValueError("build_status.yml contains no boot image entries")
    return entries, arch_map


def _extract_entry(candidate: Any) -> dict[str, str]:
    """Validate and extract one functional-group image entry."""
    if not isinstance(candidate, dict):
        raise TypeError("functional-group image entry must be a mapping")
    group = str(candidate.get("functional_group") or "").strip()
    if not group:
        raise ValueError("functional-group image entry has no name")
    kernel = str(candidate.get("kernel") or "").strip()
    initrd = str(candidate.get("initrd") or "").strip()
    image = str(candidate.get("image") or "").strip()
    if not kernel:
        raise ValueError(f"{group} has no kernel path")
    if not initrd:
        raise ValueError(f"{group} has no initrd path")
    return {"group": group, "kernel": kernel, "initrd": initrd, "image": image}


# -------------------------------------------------------------------
# Matching — same strategy as validate_image.yml
# -------------------------------------------------------------------

def _match_build_entry(
    fg_name: str,
    entries: list[dict[str, str]],
) -> dict[str, str] | None:
    """Find the build_status entry for a functional group.

    Matching order (mirrors ``validate_image.yml``):
    1. Exact name match.
    2. Prefix + arch suffix match (handles FGs without OS version).
    3. Strip ``_first`` and retry prefix + arch (primary KCP fallback).
    """
    # 1. Exact match.
    for entry in entries:
        if entry["group"] == fg_name:
            return entry

    # Parse the FG we're looking for.
    arch, _os, _ver = parse_fg_identity(fg_name)
    if not arch:
        return None
    fg_prefix = fg_prefix_without_os(fg_name)

    # 2. Prefix + arch match.
    for entry in entries:
        entry_prefix = fg_prefix_without_os(entry["group"])
        entry_arch, _eos, _ever = parse_fg_identity(entry["group"])
        if entry_prefix == fg_prefix and entry_arch == arch:
            return entry

    # 3. Strip _first and retry (primary Kubernetes control plane).
    if "_first_" in fg_prefix or fg_prefix.endswith("_first"):
        base_prefix = fg_prefix.replace("_first_", "_", 1)
        if base_prefix == fg_prefix:
            base_prefix = fg_prefix.rsplit("_first", 1)[0]
        for entry in entries:
            entry_prefix = fg_prefix_without_os(entry["group"])
            entry_arch, _eos, _ever = parse_fg_identity(entry["group"])
            if entry_prefix == base_prefix and entry_arch == arch:
                return entry

    return None


# -------------------------------------------------------------------
# Public check functions
# -------------------------------------------------------------------

def check_boot_image_identity(host) -> dict[str, Any]:
    """Verify Boot Service kernel/initrd paths match build_status.yml."""
    try:
        context = load_context(host)
        build_path = _build_status_path(host)
        build_status = read_yaml_mapping(host, build_path)

        if build_status.get("overall_status") != "success":
            return result(
                False,
                "Boot image identity verification",
                [("build_status.yml", build_path)],
                "build_status.yml overall_status is not 'success'",
            )

        entries, _arch_map = _parse_build_status_images(build_status)
        configurations = resource_list(api_json(host, "boot_configurations"))

        fields: list[tuple[str, object]] = [
            ("build_status.yml", build_path),
            ("Image entries", len(entries)),
            ("Boot configurations", len(configurations)),
        ]
        failures: list[str] = []

        for fg_name, rows in context["rows_by_fg"].items():
            group_header(fields, fg_name)

            # Find matching build_status entry.
            expected = _match_build_entry(fg_name, entries)
            if expected is None:
                failures.append(
                    f"{fg_name}: no matching entry in build_status.yml"
                )
                fields.append(("  Build status entry", "MISSING"))
                continue
            fields.append(
                ("  Build status entry", expected["group"])
            )

            # Find the Boot Service configuration.
            matches = [
                item for item in configurations
                if metadata_name(item) == fg_name
            ]
            if len(matches) != 1:
                failures.append(
                    f"{fg_name}: Boot Service configuration "
                    f"count={len(matches)}, expected 1"
                )
                fields.append(
                    ("  Boot configuration", f"count={len(matches)}")
                )
                continue

            spec = matches[0].get("spec")
            if not isinstance(spec, dict):
                failures.append(f"{fg_name}: Boot Service spec is missing")
                fields.append(("  Boot configuration", "spec missing"))
                continue

            # Compare kernel and initrd paths.
            actual_kernel = str(spec.get("kernel") or "").strip()
            actual_initrd = str(spec.get("initrd") or "").strip()
            expected_kernel = expected["kernel"]
            expected_initrd = expected["initrd"]

            kernel_ok = actual_kernel == expected_kernel
            initrd_ok = actual_initrd == expected_initrd

            fields.append((
                "  Kernel",
                "matched" if kernel_ok else f"MISMATCH: expected={expected_kernel}",
            ))
            fields.append((
                "  Initrd",
                "matched" if initrd_ok else f"MISMATCH: expected={expected_initrd}",
            ))

            if not kernel_ok:
                failures.append(
                    f"{fg_name}: kernel mismatch "
                    f"(expected={expected_kernel}, actual={actual_kernel})"
                )
            if not initrd_ok:
                failures.append(
                    f"{fg_name}: initrd mismatch "
                    f"(expected={expected_initrd}, actual={actual_initrd})"
                )

        return result(
            not failures,
            "Boot image identity verified per functional group",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result(
            "Boot image identity could not be validated", exc
        )


def check_boot_image_architecture(host) -> dict[str, Any]:
    """Verify build_status.yml architecture keys match functional group names."""
    try:
        context = load_context(host)
        build_path = _build_status_path(host)
        build_status = read_yaml_mapping(host, build_path)

        if build_status.get("overall_status") != "success":
            return result(
                False,
                "Boot image architecture verification",
                [("build_status.yml", build_path)],
                "build_status.yml overall_status is not 'success'",
            )

        entries, arch_map = _parse_build_status_images(build_status)

        fields: list[tuple[str, object]] = [
            ("build_status.yml", build_path),
            ("Image entries", len(entries)),
            ("Architecture keys mapped", len(arch_map)),
        ]
        failures: list[str] = []

        # 1. Verify architecture key consistency within build_status.yml.
        for entry in entries:
            group = entry["group"]
            name_arch, _os, _ver = parse_fg_identity(group)
            declared_arch = arch_map.get(group)

            if declared_arch and name_arch:
                if declared_arch != name_arch:
                    failures.append(
                        f"{group}: listed under '{declared_arch}' but "
                        f"name suffix is '{name_arch}'"
                    )
                    fields.append((
                        f"  [{group}]",
                        f"MISMATCH: key={declared_arch}, suffix={name_arch}",
                    ))
                else:
                    fields.append((
                        f"  [{group}]",
                        f"consistent ({declared_arch})",
                    ))
            elif declared_arch:
                fields.append((
                    f"  [{group}]",
                    f"arch key={declared_arch}, no arch suffix in name",
                ))
            elif name_arch:
                fields.append((
                    f"  [{group}]",
                    f"flat format, name suffix={name_arch}",
                ))

        # 2. Verify every provisioned FG has a build_status entry.
        for fg_name in context["rows_by_fg"]:
            matched = _match_build_entry(fg_name, entries)
            if matched is None:
                failures.append(
                    f"{fg_name}: provisioned but has no entry in "
                    "build_status.yml"
                )
                fields.append((
                    f"  [{fg_name}]",
                    "MISSING from build_status.yml",
                ))
            else:
                # Verify the matched entry's arch matches the FG's arch.
                fg_arch, _os, _ver = parse_fg_identity(fg_name)
                entry_arch, _eos, _ever = parse_fg_identity(matched["group"])
                if fg_arch and entry_arch and fg_arch != entry_arch:
                    failures.append(
                        f"{fg_name}: architecture '{fg_arch}' but "
                        f"matched build entry '{matched['group']}' has "
                        f"architecture '{entry_arch}'"
                    )
                    fields.append((
                        f"  [{fg_name}]",
                        f"ARCH MISMATCH: fg={fg_arch}, "
                        f"build={entry_arch}",
                    ))

        return result(
            not failures,
            "Boot image architecture consistency verified",
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return exception_result(
            "Boot image architecture could not be validated", exc
        )
