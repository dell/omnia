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
"""Generate image_build_manager datasets from canonical source YAML.

The product's ``src/image_build_manager`` files are the source of truth. Small
profiles and CLI overrides are applied as structured patches, then thin Jinja2
templates serialize the documents into a staging directory before atomic
publication.
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
_validate_repo_host = _cli.validate_repo_host

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
prepare_customer_documents = _rendering.prepare_customer_documents
render_documents = _rendering.render_documents
replace_documentation_repo_host = _rendering.replace_documentation_repo_host
serialize_yaml = _rendering.serialize_yaml

GENERATOR_VERSION = 5
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
DATASETS_DIR = GENERATOR_DIR.parent.resolve()
REPO_ROOT = GENERATOR_DIR.parents[3]
SRC_DOMAIN_DIR = REPO_ROOT / "src" / "image_build_manager"
SRC_INPUT_DIR = SRC_DOMAIN_DIR / "input"
SRC_REPO_OUTPUT_DIR = SRC_DOMAIN_DIR / "samples" / "repo_manager_output"

_PROFILE_KEYS = {"description", "repo_variant", "patches", "replacements"}
_DOCUMENT_NAMES = {"image_build_config", "package_groups", "repo_status"}
_BUILTIN_PROFILES = {
    "offline-catalog": {
        "source": "defaults",
        "repositories": "repo-manager",
        "packages": "catalog",
    },
    "offline-config": {
        "source": "config",
        "repositories": "repo-manager",
        "packages": "package_groups",
    },
    "internet-catalog": {
        "source": "internet",
        "repositories": "internet",
        "packages": "catalog",
    },
    "internet-config": {
        "source": "internet_config",
        "repositories": "internet",
        "packages": "package_groups",
    },
}
_PROFILE_ALIASES = {
    "standalone": "internet-config",
    "defaults": "offline-catalog",
    "config": "offline-config",
    "internet": "internet-catalog",
    "internet_config": "internet-config",
}
_EXTENSIBLE_PATCH_ROOTS = {
    ("package_groups", "functional_groups"),
    ("repo_status", "repositories"),
    ("repo_status", "registries"),
    ("repo_status", "file_repos"),
}
_SENSITIVE_PARTS = {
    "access_id", "access_key", "credential", "password", "secret", "token",
}
_DOMAIN_CREDENTIAL_GUIDANCE = (
    "from test/image_build_manager on the execution OIM run "
    "./setup_env.sh --set-domain-creds"
)

_IBM = "image_build_config"
_LEGACY_VAR_PATHS = {
    "repo_manager_output_path": (_IBM, ("repo_manager_output_path",)),
    "s3_provider": (_IBM, ("s3_configurations", "provider")),
    "s3_endpoint_url": (_IBM, ("s3_configurations", "endpoint_url")),
    "image_build_type": (_IBM, ("image_build_type",)),
    "build_image_max_parallel": (_IBM, ("build_image", "max_parallel")),
    "build_image_build_timeout": (_IBM, ("build_image", "build_timeout")),
    "build_image_force_rebuild": (_IBM, ("build_image", "force_rebuild")),
    "build_image_backup_s3_images": (_IBM, ("build_image", "backup_s3_images")),
    "repo_ssl_verify": (_IBM, ("build_image", "repo_ssl_verify")),
    "functional_groups_source": (_IBM, ("functional_groups_source",)),
    "aarch64_inventory_host_ip": (_IBM, ("aarch64_inventory_host_ip",)),
    "aarch64_ssh_user": (_IBM, ("aarch64_ssh_user",)),
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


def _profile_source_name(profile_name: str) -> str:
    """Resolve a friendly or legacy profile name to its YAML file stem."""
    friendly_name = _PROFILE_ALIASES.get(profile_name, profile_name)
    profile_details = _BUILTIN_PROFILES.get(friendly_name)
    if profile_details:
        return str(profile_details["source"])
    return profile_name


def _available_profile_names() -> list[str]:
    """Return friendly built-in profiles followed by custom profile names."""
    internal_names = {
        str(details["source"]) for details in _BUILTIN_PROFILES.values()
    }
    custom_names = sorted(
        path.stem
        for path in PROFILES_DIR.glob("*.yml")
        if path.stem not in internal_names
    )
    return [*_BUILTIN_PROFILES, *custom_names]


def _validate_profile(profile: dict[str, Any], profile_name: str) -> None:
    """Validate the profile control structure before applying patches."""
    unknown = sorted(set(profile) - _PROFILE_KEYS)
    if unknown:
        raise GeneratorError(
            f"Profile '{profile_name}' has unsupported keys: {', '.join(unknown)}"
        )
    if not isinstance(profile.get("description", ""), str):
        raise GeneratorError(f"Profile '{profile_name}' description must be a string")
    variant = profile.get("repo_variant", "offline")
    if not isinstance(variant, str) or variant not in {"offline", "internet"}:
        raise GeneratorError(
            f"Profile '{profile_name}' repo_variant must be offline or internet"
        )
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
    """Load defaults.yml, then deep-merge a named profile over it."""
    _validate_name(profile_name, "profile name")
    source_name = _profile_source_name(profile_name)
    defaults_path = PROFILES_DIR / "defaults.yml"
    defaults = _load_yaml(defaults_path, "defaults profile")
    profile = defaults
    if source_name != "defaults":
        profile_path = PROFILES_DIR / f"{source_name}.yml"
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
    """Display friendly profiles as a use-case-oriented selection table."""
    print("\nAvailable profiles:")
    print("-" * 104)
    print(f"  {'PROFILE':20s} {'REPOSITORIES':14s} {'PACKAGES':14s} DESCRIPTION")
    print(f"  {'-' * 20} {'-' * 14} {'-' * 14} {'-' * 48}")
    for name in _available_profile_names():
        profile = _load_profile(name)
        details = _BUILTIN_PROFILES.get(name, {})
        repositories = str(
            details.get("repositories", profile.get("repo_variant", "offline"))
        )
        packages = str(details.get("packages", _profile_package_source(profile)))
        description = str(details.get("description", profile.get("description", "")))
        display_name = _color(f"{name:20s}", _CYAN)
        print(f"  {display_name} {repositories:14s} {packages:14s} {description}")
    print()
    print("  Recommended: internet-config (alias: standalone)")
    print("  Inspect:     ./generate_dataset.py profiles internet-config")
    print(
        "  Create:      ./generate_dataset.py create my_dataset "
        "--profile internet-config"
    )
    print(
        "  Legacy names (defaults, config, internet, internet_config) "
        "remain supported."
    )
    print()


def _profile_package_source(profile: dict[str, Any]) -> str:
    """Return the effective functional-group package source for a profile."""
    image_patch = profile.get("patches", {}).get("image_build_config", {})
    return str(image_patch.get("functional_groups_source", "catalog"))


def _show_profile(profile_name: str) -> None:
    """Show one profile's behavior, patch, and ready-to-run command."""
    profile = _load_profile(profile_name)
    friendly_name = _PROFILE_ALIASES.get(profile_name, profile_name)
    details = _BUILTIN_PROFILES.get(friendly_name, {})
    repositories = str(
        details.get("repositories", profile.get("repo_variant", "offline"))
    )
    packages = str(details.get("packages", _profile_package_source(profile)))
    description = str(details.get("description", profile.get("description", "")))

    print(f"\nProfile: {friendly_name}")
    print("-" * 72)
    print(f"  Description:  {description}")
    print(f"  Repositories: {repositories}")
    print(f"  Packages:     {packages}")
    if profile_name != friendly_name:
        print(f"  Selected as:  {profile_name} (legacy alias)")
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
        f"  ./generate_dataset.py create my_dataset --profile {friendly_name}"
    )
    if repositories == "repo-manager":
        print(
            "  Add --repo-host REPO_MANAGER_HOST to replace every offline "
            "dummy URL in one step."
        )
    print()


def _source_paths(repo_variant: str) -> dict[str, Path]:
    """Resolve canonical document sources for a repo variant."""
    repo_filename = (
        "repo_status_internet.yml"
        if repo_variant == "internet"
        else "repo_status.yml"
    )
    return {
        "image_build_config": SRC_INPUT_DIR / "image_build_config.yml",
        "package_groups": SRC_INPUT_DIR / "package_groups.yml",
        "repo_status": SRC_REPO_OUTPUT_DIR / repo_filename,
    }


def _load_source_documents(
    repo_variant: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    """Load canonical source documents and collect their provenance."""
    documents: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, str]] = {}
    for document_name, source_path in _source_paths(repo_variant).items():
        documents[document_name] = _load_source_yaml(source_path, document_name)
        provenance[document_name] = {
            "path": _repo_relative(source_path),
            "sha256": sha256_file(source_path),
        }
    return prepare_customer_documents(documents, repo_variant), provenance


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
    if _is_sensitive_target(target):
        raise GeneratorError(
            "Credentials cannot be stored in profiles or CLI overrides; "
            f"{_DOMAIN_CREDENTIAL_GUIDANCE}"
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


def _is_sensitive_target(target: str) -> bool:
    """Return whether a CLI target appears to contain credential material."""
    normalized = target.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_PARTS)


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
            _reject_sensitive_patch_keys(value, display)
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
        if _is_sensitive_target(display):
            raise GeneratorError(
                "Credentials cannot be stored in profile patches; "
                f"{_DOMAIN_CREDENTIAL_GUIDANCE}"
            )
        if key not in source:
            if _is_extensible_patch_path(document_name, path):
                _reject_sensitive_patch_keys(value, display)
                continue
            raise GeneratorError(f"Profile patch path does not exist: {display}")
        if isinstance(value, dict):
            source_value = source[key]
            if not isinstance(source_value, dict):
                raise GeneratorError(
                    f"Profile patch cannot merge a mapping into: {display}"
                )
            _validate_patch_paths(source_value, value, document_name, path)


def _is_extensible_patch_path(
    document_name: str, path: tuple[str, ...]
) -> bool:
    """Return whether a patch may add a key below a controlled open mapping."""
    full_path = (document_name,) + path
    matching_root = next(
        (root for root in _EXTENSIBLE_PATCH_ROOTS if full_path[:len(root)] == root),
        None,
    )
    if matching_root is None:
        return False
    relative_path = full_path[len(matching_root):]
    if matching_root == ("package_groups", "functional_groups"):
        return len(relative_path) == 1 or (
            len(relative_path) == 2 and relative_path[-1] == "packages"
        )
    if matching_root == ("repo_status", "repositories"):
        return 1 <= len(relative_path) <= 3 or (
            len(relative_path) == 4
            and relative_path[-1] in {"url", "priority"}
        )
    if matching_root == ("repo_status", "registries"):
        return 1 <= len(relative_path) <= 2 or (
            len(relative_path) == 3
            and relative_path[-1]
            in {
                "ca_path", "client_cert_path", "client_key_path",
                "capath", "clientcertpath", "clientkeypath", "insecure",
            }
        )
    if matching_root == ("repo_status", "file_repos"):
        return 1 <= len(relative_path) <= 3
    return False


def _reject_sensitive_patch_keys(value: Any, display: str) -> None:
    """Reject credential-like keys nested inside a newly added mapping."""
    if not isinstance(value, dict):
        return
    for key, nested_value in value.items():
        nested_display = f"{display}.{key}"
        if _is_sensitive_target(nested_display):
            raise GeneratorError(
                "Credentials cannot be stored in profile patches; "
                f"{_DOMAIN_CREDENTIAL_GUIDANCE}"
            )
        _reject_sensitive_patch_keys(nested_value, nested_display)


def _apply_set_overrides(
    documents: dict[str, dict[str, Any]],
    combined_patches: dict[str, Any],
    assignments: list[str],
) -> None:
    """Apply dotted or JSON Pointer overrides to existing document fields."""
    for assignment in assignments:
        target, value = _parse_assignment(assignment, "--set")
        if ":" not in target:
            raise GeneratorError(
                "--set target must use DOCUMENT:dot.path=VALUE, for example "
                "image_build_config:build_image.repo_ssl_verify=false"
            )
        document_name, raw_path = target.split(":", 1)
        if raw_path.startswith("/"):
            path = tuple(
                part.replace("~1", "/").replace("~0", "~")
                for part in raw_path[1:].split("/")
            )
        else:
            path = tuple(part.strip() for part in raw_path.split("."))
        if document_name not in _DOCUMENT_NAMES or not all(path):
            raise GeneratorError(f"Invalid --set target: {target}")
        if _is_sensitive_target(target):
            raise GeneratorError(
                "Credentials cannot be stored in profiles or CLI overrides; "
                f"{_DOMAIN_CREDENTIAL_GUIDANCE}"
            )
        _set_existing_path(documents[document_name], path, value)
        _record_patch(combined_patches, document_name, path, value)
        _info(f"Applied override: {target}")


def _extract_repo_variant(
    assignments: list[str], current_variant: str
) -> tuple[str, list[tuple[str, Any]]]:
    """Parse legacy assignments and extract the repo_type selector."""
    parsed: list[tuple[str, Any]] = []
    repo_variant = current_variant
    for assignment in assignments:
        key, value = _parse_assignment(assignment, "--var")
        if key == "repo_type":
            if value not in {"offline", "internet"}:
                raise GeneratorError("--var repo_type must be offline or internet")
            repo_variant = value
            continue
        parsed.append((key, value))
    return repo_variant, parsed


def _apply_legacy_overrides(
    documents: dict[str, dict[str, Any]],
    combined_patches: dict[str, Any],
    assignments: list[tuple[str, Any]],
) -> None:
    """Apply supported flat --var aliases without exposing secret values."""
    for key, value in assignments:
        if _is_sensitive_target(key):
            raise GeneratorError(
                "Credentials cannot be stored in profiles or CLI overrides; "
                f"{_DOMAIN_CREDENTIAL_GUIDANCE}"
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
        repo_variant = args.repo_variant or "offline"
        documents, provenance = _load_source_documents(repo_variant)
        repo_host = None
        if args.repo_host:
            if repo_variant != "offline":
                raise GeneratorError("--repo-host is valid only for offline data")
            repo_host = _validate_repo_host(args.repo_host)
            replace_documentation_repo_host(documents, repo_host)
        return {
            "dataset": args.dataset_name,
            "profile": "from-src",
            "mode": "from-src",
            "repo_variant": repo_variant,
            "documents": documents,
            "patches": {},
            "replacements": {},
            "provenance": provenance,
            "set_values": [],
            "legacy_values": [],
            "repo_host": repo_host,
            "normalizations": document_normalizations(repo_variant, repo_host),
        }

    profile_name = args.profile_option or args.profile or "offline-catalog"
    profile = _load_profile(profile_name)
    profile_variant = str(profile.get("repo_variant", "offline"))
    repo_variant = args.repo_variant or profile_variant
    repo_variant, legacy_assignments = _extract_repo_variant(args.var, repo_variant)
    friendly_name = _PROFILE_ALIASES.get(profile_name, profile_name)
    if friendly_name in _BUILTIN_PROFILES and repo_variant != profile_variant:
        raise GeneratorError(
            f"Profile '{friendly_name}' requires repository variant "
            f"'{profile_variant}', not '{repo_variant}'. Choose the matching "
            "internet-* or offline-* profile instead."
        )
    documents, provenance = _load_source_documents(repo_variant)
    combined_patches = copy.deepcopy(profile.get("patches", {}))
    replacements = copy.deepcopy(profile.get("replacements", {}))
    _apply_profile_replacements(documents, replacements)
    _apply_profile_patches(documents, combined_patches)
    _apply_set_overrides(documents, combined_patches, args.set_values)
    _apply_legacy_overrides(documents, combined_patches, legacy_assignments)
    repo_host = None
    if args.repo_host:
        if repo_variant != "offline":
            raise GeneratorError("--repo-host is valid only for offline data")
        repo_host = _validate_repo_host(args.repo_host)
        replace_documentation_repo_host(documents, repo_host)
    return {
        "dataset": args.dataset_name,
        "profile": friendly_name,
        "mode": "profile",
        "repo_variant": repo_variant,
        "documents": documents,
        "patches": combined_patches,
        "replacements": replacements,
        "provenance": provenance,
        "set_values": args.set_values,
        "legacy_values": args.var,
        "repo_host": repo_host,
        "normalizations": document_normalizations(repo_variant, repo_host),
    }


def _stage_dataset(plan: dict[str, Any], staging_path: Path) -> list[str]:
    """Render and document a complete staged dataset."""
    plan["guidance"] = document_guidance(
        plan["documents"], plan["repo_variant"]
    )
    generated = render_documents(
        plan["documents"], plan["provenance"], plan["guidance"],
        plan["repo_variant"], staging_path
    )
    for output_name in generated:
        _ok(f"Generated: {output_name}")
    plan["replacement_marker_count"] = replacement_marker_count(
        staging_path, generated
    )
    plan["external_inputs"] = external_inputs(
        plan["repo_variant"], plan["documents"]
    )
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
    review = (
        "grep -R -n 'REPLACE WITH REAL VALUE' "
        f"{output_dir}/input/ {output_dir}/repo_manager_output/"
        if marker_count
        else "no required value replacements"
    )
    print(
        f"\n  Output:  {output_dir}\n"
        f"  Profile: {plan['profile']}\n"
        f'  Use:     set dataset: "{args.dataset_name}" in test_config.yml\n'
        f"  Review:  {review}\n"
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
        f"  Dataset Generator — {args.dataset_name} ({plan['profile']})\n"
        f"{'=' * 65}\n"
    )
    _info(
        f"Source mode: {plan['mode']}; "
        f"repository variant: {plan['repo_variant']}"
    )
    staging_path = Path(
        tempfile.mkdtemp(prefix=f".{args.dataset_name}.staging-", dir=DATASETS_DIR)
    )
    try:
        staging_path.chmod(0o755)
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
            "Generation interrupted; staged output was cleaned up. If the "
            "interrupt occurred during old-backup cleanup, inspect the output."
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
