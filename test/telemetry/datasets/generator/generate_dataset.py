#!/usr/bin/env python3
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
"""Generate telemetry datasets from canonical source YAML.

The product's ``src/telemetry/input`` files are the source of truth. Small
profiles and CLI overrides are applied as structured patches, then the
shared Jinja2 template serializes the documents into a staging directory
before atomic publication.
"""

from argparse import Namespace
import copy
from importlib import import_module
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError as RuamelYAMLError


def _load_component(name: str):
    """Load a sibling module for both package import and direct execution."""
    package_name = __package__
    if not package_name:
        datasets_dir = str(Path(__file__).resolve().parent.parent)
        if datasets_dir not in sys.path:
            sys.path.insert(0, datasets_dir)
        package_name = Path(__file__).resolve().parent.name
    return import_module(f"{package_name}.{name}")


_cli = _load_component("dataset_cli")
_handoff = _load_component("dataset_handoff")
_publication = _load_component("dataset_publication")
_rendering = _load_component("dataset_rendering")

DatasetCliError = _cli.DatasetCliError
_create_parser = _cli.create_parser
_normalize_cli_args = _cli.normalize_cli_args
_validate_mode_arguments = _cli.validate_mode_arguments
_validate_name = _cli.validate_name

artifact_hashes = _handoff.artifact_hashes
external_inputs = _handoff.external_inputs
regeneration_command = _handoff.regeneration_command
replacement_marker_count = _handoff.replacement_marker_count
write_manifest = _handoff.write_manifest
write_readme = _handoff.write_readme

DatasetPublicationError = _publication.DatasetPublicationError
dataset_lock = _publication.dataset_lock
directory_changes = _publication.directory_changes
publish_dataset = _publication.publish_dataset
sha256_file = _publication.sha256_file

DatasetRenderingError = _rendering.DatasetRenderingError
document_guidance = _rendering.document_guidance
document_normalizations = _rendering.document_normalizations
is_sensitive_target = _rendering.is_sensitive_target
prepare_customer_documents = _rendering.prepare_customer_documents
render_documents = _rendering.render_documents
serialize_yaml = _rendering.serialize_yaml

GENERATOR_VERSION = 1
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
DATASETS_DIR = GENERATOR_DIR.parent.resolve()
REPO_ROOT = GENERATOR_DIR.parents[3]
SRC_INPUT_DIR = REPO_ROOT / "src" / "telemetry" / "input"

_PROFILE_KEYS = {"description", "patches", "replacements"}
_DOCUMENT_NAMES = {"telemetry_config", "telemetry_storage_config", "telemetry_packages"}
_SOURCE_FILES = {
    "telemetry_config": "telemetry_config.yml",
    "telemetry_storage_config": "telemetry_storage_config.yml",
    "telemetry_packages": "telemetry_packages.yml",
}

_SENSITIVE_PARTS = {
    "access_id", "access_key", "credential", "password", "secret", "token",
}

# Legacy --var aliases: flat key -> (document, dotted path)
_LEGACY_VAR_PATHS: dict[str, tuple[str, tuple[str, ...]]] = {
    "kube_vip": ("telemetry_config", ("cluster_inventory",)),
    "idrac_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "idrac", "metrics_enabled"),
    ),
    "ldms_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "ldms", "metrics_enabled"),
    ),
    "powerscale_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "powerscale", "metrics_enabled"),
    ),
    "ufm_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "ufm", "metrics_enabled"),
    ),
    "vast_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "vast", "metrics_enabled"),
    ),
    "ome_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sources", "ome", "metrics_enabled"),
    ),
    "victoria_metrics_enabled": (
        "telemetry_config",
        ("telemetry_sinks", "victoria_metrics", "persistence_size"),
    ),
    "victoria_logs_enabled": (
        "telemetry_config",
        ("telemetry_sinks", "victoria_logs", "storage_size"),
    ),
    "kafka_enabled": (
        "telemetry_config",
        ("telemetry_sinks", "kafka", "persistence_size"),
    ),
    "install_mode": (
        "telemetry_packages",
        ("install_mode",),
    ),
}

_GREEN = "\033[0;32m"
_RED = "\033[0;31m"
_BLUE = "\033[0;34m"
_CYAN = "\033[0;36m"
_NC = "\033[0m"


class GeneratorError(Exception):
    """Raised for a user-correctable dataset generation error."""


def _color(value: str, code: str) -> str:
    """Apply ANSI color when console color is enabled."""
    if os.environ.get("NO_COLOR"):
        return value
    return f"{code}{value}{_NC}"


def _info(message: str) -> None:
    """Print an informational message."""
    print(f"  {_color('[...]', _BLUE)} {message}")


def _ok(message: str) -> None:
    """Print a success message."""
    print(f"  {_color('[OK]', _GREEN)}  {message}")


def _warn(message: str) -> None:
    """Print a warning message."""
    print(f"  {_color('[WARN]', _CYAN)} {message}")


def _load_yaml(path: Path, label: str | None = None) -> dict[str, Any]:
    """Load a YAML mapping with a concise, contextual error."""
    display = label or str(path)
    if not path.is_file():
        raise GeneratorError(f"Required file not found: {path}")
    loader = YAML(typ="safe")
    loader.allow_duplicate_keys = False
    try:
        with path.open(encoding="utf-8") as stream:
            data = loader.load(stream)
    except (OSError, UnicodeError, RuamelYAMLError) as exc:
        raise GeneratorError(f"Cannot load {display}: {exc}") from exc
    if not isinstance(data, dict):
        raise GeneratorError(f"{display} must contain a YAML mapping")
    return data


def _load_source_yaml(path: Path, label: str) -> dict[str, Any]:
    """Round-trip load product YAML so its customer guidance is retained."""
    if not path.is_file():
        raise GeneratorError(f"Required file not found: {path}")
    loader = YAML(typ="rt")
    loader.preserve_quotes = True
    loader.allow_duplicate_keys = False
    try:
        with path.open(encoding="utf-8") as stream:
            data = loader.load(stream)
    except (OSError, UnicodeError, RuamelYAMLError) as exc:
        raise GeneratorError(f"Cannot load {label}: {exc}") from exc
    if not isinstance(data, dict):
        raise GeneratorError(f"{label} must contain a YAML mapping")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a recursive mapping merge; lists and scalar values replace."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _repo_relative(path: Path) -> str:
    """Return a portable repository-relative path when possible."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _available_profile_names() -> list[str]:
    """Return sorted profile names from profiles/ directory."""
    return sorted(
        path.stem
        for path in PROFILES_DIR.glob("*.yml")
    )


def _validate_profile(profile: dict[str, Any], profile_name: str) -> None:
    """Validate the profile control structure before applying patches."""
    unknown = sorted(set(profile) - _PROFILE_KEYS)
    if unknown:
        raise GeneratorError(
            f"Profile '{profile_name}' has unsupported keys: {', '.join(unknown)}"
        )
    if not isinstance(profile.get("description", ""), str):
        raise GeneratorError(f"Profile '{profile_name}' description must be a string")
    patches = profile.get("patches", {})
    if not isinstance(patches, dict):
        raise GeneratorError(f"Profile '{profile_name}' patches must be a mapping")
    unknown_documents = sorted(set(patches) - _DOCUMENT_NAMES)
    if unknown_documents:
        raise GeneratorError(
            f"Profile '{profile_name}' patches unknown documents: "
            f"{', '.join(unknown_documents)}"
        )
    for document_name, patch in patches.items():
        if not isinstance(patch, dict):
            raise GeneratorError(
                f"Profile patch '{document_name}' must be a mapping"
            )
    replacements = profile.get("replacements", {})
    if not isinstance(replacements, dict):
        raise GeneratorError(
            f"Profile '{profile_name}' replacements must be a mapping"
        )
    unknown_documents = sorted(set(replacements) - _DOCUMENT_NAMES)
    if unknown_documents:
        raise GeneratorError(
            f"Profile '{profile_name}' replacements unknown documents: "
            f"{', '.join(unknown_documents)}"
        )
    if any(not isinstance(value, dict) for value in replacements.values()):
        raise GeneratorError(
            f"Profile '{profile_name}' document replacements must be mappings"
        )


def _load_profile(profile_name: str) -> dict[str, Any]:
    """Load shared profile YAML, applying defaults first."""
    _validate_name(profile_name, "profile name")
    defaults_path = PROFILES_DIR / "defaults.yml"
    defaults = _load_yaml(defaults_path, "defaults profile")
    profile = defaults
    if profile_name != "defaults":
        profile_path = PROFILES_DIR / f"{profile_name}.yml"
        if not profile_path.is_file():
            available = ", ".join(_available_profile_names()) or "none"
            raise GeneratorError(
                f"Profile '{profile_name}' not found. Available: {available}"
            )
        profile_override = _load_yaml(profile_path, profile_name)
        if "description" not in profile_override:
            raise GeneratorError(
                f"Profile '{profile_name}' must define its own description"
            )
        profile = _deep_merge(defaults, profile_override)
    _validate_profile(profile, profile_name)
    return profile


def _list_profiles() -> None:
    """Display available profiles with their descriptions."""
    print("\nAvailable profiles:")
    print("-" * 80)
    print(f"  {'PROFILE':24s} DESCRIPTION")
    print(f"  {'-' * 24} {'-' * 52}")
    for name in _available_profile_names():
        profile = _load_profile(name)
        description = str(profile.get("description", ""))
        display_name = _color(f"{name:24s}", _CYAN)
        print(f"  {display_name} {description}")
    print()
    recommended = "defaults"
    print(f"  Recommended: {recommended} (canonical source defaults)")
    print(f"  Inspect:     ./generate_dataset.py profiles {recommended}")
    print(
        "  Create:      ./generate_dataset.py create my_dataset "
        f"--profile {recommended}"
    )
    print()


def _show_profile(profile_name: str) -> None:
    """Show one profile's behavior, patch, and ready-to-run command."""
    profile = _load_profile(profile_name)
    description = str(profile.get("description", ""))

    print(f"\nProfile: {profile_name}")
    print("-" * 72)
    print(f"  Description: {description}")
    print("\nEffective patch:")
    patches = profile.get("patches", {})
    if patches:
        print(yaml.safe_dump(patches, sort_keys=False).rstrip())
    else:
        print("{}")
    replacements = profile.get("replacements", {})
    if replacements:
        print("\nWhole-field replacements:")
        print(yaml.safe_dump(replacements, sort_keys=False).rstrip())
    print("\nCreate a dataset:")
    print(
        f"  ./generate_dataset.py create my_dataset --profile {profile_name}"
    )
    print()


def _source_paths() -> dict[str, Path]:
    """Resolve canonical document sources."""
    return {
        document_name: SRC_INPUT_DIR / filename
        for document_name, filename in _SOURCE_FILES.items()
    }


def _load_source_documents() -> tuple[
    dict[str, dict[str, Any]], dict[str, dict[str, str]]
]:
    """Load canonical source documents and collect their provenance."""
    documents: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, str]] = {}
    for document_name, source_path in _source_paths().items():
        documents[document_name] = _load_source_yaml(source_path, document_name)
        provenance[document_name] = {
            "path": _repo_relative(source_path),
            "sha256": sha256_file(source_path),
        }
    return prepare_customer_documents(documents), provenance


def _parse_assignment(assignment: str, option: str) -> tuple[str, Any]:
    """Parse one CLI KEY=VALUE assignment using YAML scalar inference."""
    if "=" not in assignment:
        raise GeneratorError(
            f"Invalid {option} value. Expected KEY=VALUE."
        )
    target, raw_value = assignment.split("=", 1)
    target = target.strip()
    if not target:
        raise GeneratorError(f"Invalid {option} value: key cannot be empty")
    if is_sensitive_target(target):
        raise GeneratorError(
            "Credentials cannot be stored in profiles or CLI overrides"
        )
    loader = YAML(typ="safe")
    loader.allow_duplicate_keys = False
    try:
        value = loader.load(raw_value.strip())
    except RuamelYAMLError as exc:
        raise GeneratorError(
            f"Invalid YAML value for {option} key '{target}'"
        ) from exc
    return target, value


def _set_existing_path(
    document: dict[str, Any], path: tuple[str, ...], value: Any
) -> None:
    """Set an existing mapping path, rejecting typos and list traversal."""
    current: dict[str, Any] = document
    for segment in path[:-1]:
        next_value = current.get(segment)
        if not isinstance(next_value, dict):
            dotted = ".".join(path)
            raise GeneratorError(f"Override path does not exist: {dotted}")
        current = next_value
    final = path[-1]
    if final not in current:
        dotted = ".".join(path)
        raise GeneratorError(f"Override path does not exist: {dotted}")
    current[final] = value


def _patch_for_path(path: tuple[str, ...], value: Any) -> dict[str, Any]:
    """Build a nested patch mapping for one document path."""
    patch: Any = copy.deepcopy(value)
    for segment in reversed(path):
        patch = {segment: patch}
    return patch


def _record_patch(
    patches: dict[str, Any], document_name: str, path: tuple[str, ...], value: Any
) -> None:
    """Record a CLI override in the combined reproducibility patch."""
    existing = patches.get(document_name, {})
    patches[document_name] = _deep_merge(
        existing, _patch_for_path(path, value)
    )


def _apply_profile_patches(
    documents: dict[str, dict[str, Any]], patches: dict[str, Any]
) -> None:
    """Apply structured profile patches to canonical source documents."""
    for document_name, patch in patches.items():
        _validate_patch_paths(documents[document_name], patch, document_name)
        documents[document_name] = _deep_merge(documents[document_name], patch)


def _apply_profile_replacements(
    documents: dict[str, dict[str, Any]], replacements: dict[str, Any]
) -> None:
    """Replace explicitly selected top-level fields without inherited data."""
    for document_name, document_replacements in replacements.items():
        for field, value in document_replacements.items():
            display = f"{document_name}:{field}"
            if field not in documents[document_name]:
                raise GeneratorError(
                    f"Profile replacement field does not exist: {display}"
                )
            documents[document_name][field] = copy.deepcopy(value)


def _validate_patch_paths(
    source: dict[str, Any],
    patch: dict[str, Any],
    document_name: str,
    parent: tuple[str, ...] = (),
) -> None:
    """Reject profile patch paths that are absent from the source document."""
    for key, value in patch.items():
        path = parent + (str(key),)
        display = f"{document_name}:{'.'.join(path)}"
        if is_sensitive_target(display):
            raise GeneratorError(
                "Credentials cannot be stored in profile patches"
            )
        if key not in source:
            raise GeneratorError(f"Profile patch path does not exist: {display}")
        if isinstance(value, dict):
            source_value = source[key]
            if not isinstance(source_value, dict):
                raise GeneratorError(
                    f"Profile patch cannot merge a mapping into: {display}"
                )
            _validate_patch_paths(source_value, value, document_name, path)


def _apply_set_overrides(
    documents: dict[str, dict[str, Any]],
    combined_patches: dict[str, Any],
    assignments: list[str],
) -> None:
    """Apply dotted overrides to existing document fields."""
    for assignment in assignments:
        target, value = _parse_assignment(assignment, "--set")
        if ":" not in target:
            raise GeneratorError(
                "--set target must use DOCUMENT:dot.path=VALUE, for example "
                "telemetry_config:telemetry_sources.idrac.metrics_enabled=false"
            )
        document_name, raw_path = target.split(":", 1)
        path = tuple(part.strip() for part in raw_path.split("."))
        if document_name not in _DOCUMENT_NAMES or not all(path):
            raise GeneratorError(f"Invalid --set target: {target}")
        if is_sensitive_target(target):
            raise GeneratorError(
                "Credentials cannot be stored in profiles or CLI overrides"
            )
        _set_existing_path(documents[document_name], path, value)
        _record_patch(combined_patches, document_name, path, value)
        _info(f"Applied override: {target}")


def _apply_legacy_overrides(
    documents: dict[str, dict[str, Any]],
    combined_patches: dict[str, Any],
    assignments: list[str],
) -> None:
    """Apply supported flat --var aliases without exposing secret values."""
    for assignment in assignments:
        key, value = _parse_assignment(assignment, "--var")
        if is_sensitive_target(key):
            raise GeneratorError(
                "Credentials cannot be stored in profiles or CLI overrides"
            )
        destination = _LEGACY_VAR_PATHS.get(key)
        if destination is None:
            supported = ", ".join(sorted(_LEGACY_VAR_PATHS))
            raise GeneratorError(
                f"Unknown --var key '{key}'. Supported legacy keys: {supported}. "
                "Use --set DOCUMENT:dot.path=VALUE for nested fields."
            )
        document_name, path = destination
        _set_existing_path(documents[document_name], path, value)
        _record_patch(combined_patches, document_name, path, value)
        _info(f"Applied legacy override: {key}")


def _prepare_documents(args: Namespace) -> dict[str, Any]:
    """Resolve mode/profile, load sources, and apply all requested patches."""
    if args.from_src:
        documents, provenance = _load_source_documents()
        return {
            "dataset": args.dataset_name,
            "profile": "from-src",
            "mode": "from-src",
            "documents": documents,
            "patches": {},
            "replacements": {},
            "provenance": provenance,
            "set_values": [],
            "legacy_values": [],
            "normalizations": document_normalizations(),
        }

    profile_name = (
        args.profile_option
        or args.profile
        or "defaults"
    )
    profile = _load_profile(profile_name)
    documents, provenance = _load_source_documents()
    combined_patches = copy.deepcopy(profile.get("patches", {}))
    replacements = copy.deepcopy(profile.get("replacements", {}))
    _apply_profile_replacements(documents, replacements)
    _apply_profile_patches(documents, combined_patches)
    _apply_set_overrides(documents, combined_patches, args.set_values)
    _apply_legacy_overrides(documents, combined_patches, args.var)
    return {
        "dataset": args.dataset_name,
        "profile": profile_name,
        "mode": "profile",
        "documents": documents,
        "patches": combined_patches,
        "replacements": replacements,
        "provenance": provenance,
        "set_values": args.set_values,
        "legacy_values": args.var,
        "normalizations": document_normalizations(),
    }


def _stage_dataset(plan: dict[str, Any], staging_path: Path) -> list[str]:
    """Render and document a complete staged dataset."""
    plan["guidance"] = document_guidance(plan["documents"])
    generated = render_documents(
        plan["documents"], plan["provenance"], plan["guidance"],
        staging_path,
    )
    for output_name in generated:
        _ok(f"Generated: {output_name}")
    plan["replacement_marker_count"] = replacement_marker_count(
        staging_path, generated
    )
    plan["external_inputs"] = external_inputs(plan["documents"])
    manifest_name = write_manifest(
        staging_path, artifact_hashes(staging_path, generated), plan,
        GENERATOR_VERSION, serialize_yaml,
    )
    _ok(f"Generated: {manifest_name}")
    generated.append(manifest_name)
    readme_name = write_readme(
        staging_path, plan, generated, regeneration_command(plan)
    )
    _ok(f"Generated: {readme_name}")
    generated.append(readme_name)
    return generated


def _complete_generation(
    args: Namespace,
    plan: dict[str, Any],
    staging_path: Path,
    output_dir: Path,
    generated: list[str],
) -> None:
    """Handle dry-run, drift-check, or publication for staged output."""
    marker_count = plan["replacement_marker_count"]
    if args.dry_run:
        _ok(f"Dry run passed: {len(generated)} files generated; nothing published")
        if marker_count:
            _warn(f"Review {marker_count} replacement markers before execution")
        return
    if args.check:
        with dataset_lock(DATASETS_DIR):
            if not output_dir.is_dir() or output_dir.is_symlink():
                raise GeneratorError(f"Dataset does not exist safely: {output_dir}")
            changes = directory_changes(staging_path, output_dir)
        if changes:
            raise GeneratorError(
                "Dataset is stale:\n  - " + "\n  - ".join(changes)
            )
        _ok(f"Dataset '{args.dataset_name}' is current")
        return

    publish_dataset(staging_path, output_dir, DATASETS_DIR, args.force)
    _ok(f"Dataset '{args.dataset_name}' published ({len(generated)} files)")
    if marker_count:
        _warn(f"Review {marker_count} replacement markers before execution")
    print(
        f"\n  Output:  {output_dir}\n"
        f"  Profile: {plan['profile']}\n"
        f'  Use:     set dataset: "{args.dataset_name}" in test_config.yml\n'
    )


def _generate(args: Namespace) -> None:
    """Build, compare, or publish one dataset."""
    plan = _prepare_documents(args)
    output_dir = DATASETS_DIR / args.dataset_name
    if output_dir.parent != DATASETS_DIR:
        raise GeneratorError(f"Dataset path escapes datasets directory: {output_dir}")
    if output_dir.is_symlink():
        raise GeneratorError(f"Refusing to use dataset symlink: {output_dir}")
    if output_dir.exists() and not (args.force or args.dry_run or args.check):
        raise GeneratorError(
            f"Dataset '{args.dataset_name}' already exists. Use --force to replace it."
        )

    print(
        f"\n{'=' * 65}\n"
        f"  Telemetry Dataset Generator - {args.dataset_name} ({plan['profile']})\n"
        f"{'=' * 65}\n"
    )
    _info(f"Source mode: {plan['mode']}")
    staging_path = Path(
        tempfile.mkdtemp(prefix=f".{args.dataset_name}.staging-", dir=DATASETS_DIR)
    )
    try:
        generated = _stage_dataset(plan, staging_path)
        _complete_generation(args, plan, staging_path, output_dir, generated)
    finally:
        if staging_path.exists():
            try:
                shutil.rmtree(staging_path)
            except OSError as exc:
                _warn(f"Could not remove staging directory {staging_path}: {exc}")


def main(arguments: list[str] | None = None) -> int:
    """Run the dataset generator CLI and return a process exit code."""
    parser = _create_parser()
    try:
        raw_arguments = list(
            sys.argv[1:] if arguments is None else arguments
        )
        if "--no-color" in raw_arguments:
            os.environ["NO_COLOR"] = "1"
        normalized_arguments = _normalize_cli_args(raw_arguments)
        if not normalized_arguments:
            parser.print_help()
            _list_profiles()
            return 0
        args = parser.parse_args(normalized_arguments)
        _validate_mode_arguments(args)
        if args.list_profiles:
            _list_profiles()
            return 0
        if args.show_profile:
            _show_profile(args.show_profile)
            return 0
        _generate(args)
        return 0
    except (
        GeneratorError, DatasetCliError, DatasetRenderingError,
        DatasetPublicationError, OSError,
    ) as exc:
        sys.stdout.flush()
        print(f"  {_color('[FAIL]', _RED)} {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        _warn(
            "Generation interrupted; staged output was cleaned up."
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
