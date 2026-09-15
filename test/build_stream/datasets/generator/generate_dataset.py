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
"""Generate BuildStream datasets from canonical source YAML.

Source files remain authoritative. Profiles and CLI overrides are validated
patches, rendered in staging, then published as one complete dataset.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import os
import re
import shlex
import shutil
import sys
import tempfile
import uuid
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    select_autoescape,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

GENERATOR_VERSION = 2
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
TEMPLATES_DIR = GENERATOR_DIR / "templates"
DATASETS_DIR = GENERATOR_DIR.parent.resolve()
REPO_ROOT = GENERATOR_DIR.parents[3]
SOURCE_FILE = REPO_ROOT / "src/build_stream/input/build_stream_config.yml"
OUTPUT_FILE = "input/build_stream_config.yml"
DOCUMENT = "build_stream_config"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SENSITIVE = ("credential", "password", "secret", "token", "private_key")


class GeneratorError(Exception):
    """A user-correctable generator error."""


def _yaml(kind: str = "safe") -> YAML:
    instance = YAML(typ=kind)
    instance.allow_duplicate_keys = False
    if kind == "rt":
        instance.preserve_quotes = True
    return instance


def _load(path: Path, round_trip: bool = False) -> dict[str, Any]:
    if not path.is_file():
        raise GeneratorError(f"Required file not found: {path}")
    try:
        with path.open(encoding="utf-8") as stream:
            value = _yaml("rt" if round_trip else "safe").load(stream)
    except (OSError, UnicodeError, YAMLError) as exc:
        raise GeneratorError(f"Cannot load YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GeneratorError(f"YAML document must be a mapping: {path}")
    return value


def _dump(value: dict[str, Any]) -> str:
    writer = _yaml("rt")
    writer.default_flow_style = False
    writer.width = 120
    writer.indent(mapping=2, sequence=4, offset=2)
    stream = StringIO()
    writer.dump(value, stream)
    return stream.getvalue()


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in patch.items():
        result[key] = (
            _merge(result[key], value)
            if isinstance(result.get(key), dict) and isinstance(value, dict)
            else copy.deepcopy(value)
        )
    return result


def _safe_name(value: str, label: str) -> str:
    if not NAME_PATTERN.fullmatch(value) or value in {".", "..", "generator"}:
        raise GeneratorError(f"Invalid {label} '{value}'; use one safe directory name")
    return value


def _sensitive(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE)


def _validate_patch(source: dict[str, Any], patch: dict[str, Any], prefix: str = "") -> None:
    for key, value in patch.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if _sensitive(path):
            raise GeneratorError(f"Credential-like profile field is forbidden: {path}")
        if key not in source:
            raise GeneratorError(f"Profile patch path does not exist: {DOCUMENT}:{path}")
        if isinstance(value, dict):
            if not isinstance(source[key], dict):
                raise GeneratorError(f"Cannot merge a mapping into: {DOCUMENT}:{path}")
            _validate_patch(source[key], value, path)


def _profiles() -> list[str]:
    return sorted(path.stem for path in PROFILES_DIR.glob("*.yml"))


def _profile(name: str) -> dict[str, Any]:
    _safe_name(name, "profile name")
    defaults = _load(PROFILES_DIR / "defaults.yml")
    profile = defaults
    if name != "defaults":
        override = _load(PROFILES_DIR / f"{name}.yml")
        if "description" not in override:
            raise GeneratorError(f"Profile '{name}' must define its own description")
        profile = _merge(defaults, override)
    unknown = sorted(set(profile) - {"description", "patches"})
    if unknown:
        raise GeneratorError(f"Profile '{name}' has unsupported keys: {', '.join(unknown)}")
    if not isinstance(profile.get("description", ""), str):
        raise GeneratorError(f"Profile '{name}' description must be a string")
    patches = profile.get("patches", {})
    if not isinstance(patches, dict) or any(key != DOCUMENT for key in patches):
        raise GeneratorError(f"Profile '{name}' patches must contain only {DOCUMENT}")
    if not isinstance(patches.get(DOCUMENT, {}), dict):
        raise GeneratorError(f"Profile patch '{DOCUMENT}' must be a mapping")
    return profile


def _list_profiles() -> None:
    print("\nAvailable profiles:\n" + "-" * 80)
    for name in _profiles():
        print(f"  {name:16s} {_profile(name).get('description', '')}")
    print("\n  Inspect: ./generate_dataset.py profiles defaults")
    print("  Create:  ./generate_dataset.py create my_dataset --profile defaults\n")


def _show_profile(name: str) -> None:
    profile = _profile(name)
    print(f"\nProfile: {name}\n{'-' * 72}")
    print(f"  Description: {profile.get('description', '')}\n\nEffective patch:")
    print(_dump(profile.get("patches", {})).rstrip() or "{}")
    print(f"\n  ./generate_dataset.py create my_dataset --profile {name}\n")


def _assignment(text: str, option: str) -> tuple[str, Any]:
    if "=" not in text:
        raise GeneratorError(f"Invalid {option} value; expected KEY=VALUE")
    target, raw = text.split("=", 1)
    target = target.strip()
    if not target or _sensitive(target):
        raise GeneratorError(
            "Credentials cannot be stored in datasets; configure the encrypted "
            "BuildStream credential pair on the execution OIM"
        )
    try:
        return target, _yaml().load(raw.strip())
    except YAMLError as exc:
        raise GeneratorError(f"Invalid YAML value for {option} target '{target}'") from exc


def _path(raw: str) -> tuple[str, ...]:
    if raw.startswith("/"):
        return tuple(part.replace("~1", "/").replace("~0", "~") for part in raw[1:].split("/"))
    return tuple(part.strip() for part in raw.split("."))


def _set(document: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    if not path or not all(path):
        raise GeneratorError("Override path cannot be empty")
    current = document
    for segment in path[:-1]:
        if not isinstance(current.get(segment), dict):
            raise GeneratorError(f"Override path does not exist: {'.'.join(path)}")
        current = current[segment]
    if path[-1] not in current:
        raise GeneratorError(f"Override path does not exist: {'.'.join(path)}")
    current[path[-1]] = value


def _path_patch(path: tuple[str, ...], value: Any) -> dict[str, Any]:
    patch: Any = copy.deepcopy(value)
    for segment in reversed(path):
        patch = {segment: patch}
    return patch


def _overrides(
    document: dict[str, Any], patch: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    combined = copy.deepcopy(patch)
    for text in args.set_values:
        target, value = _assignment(text, "--set")
        if ":" not in target:
            raise GeneratorError("--set must use build_stream_config:field=VALUE")
        document_name, raw_path = target.split(":", 1)
        if document_name != DOCUMENT:
            raise GeneratorError(f"Unknown --set document: {document_name}")
        path = _path(raw_path)
        _set(document, path, value)
        combined = _merge(combined, _path_patch(path, value))
    for text in args.var:
        key, value = _assignment(text, "--var")
        if any(separator in key for separator in (".", "/", ":")):
            raise GeneratorError("--var accepts top-level fields only; use --set for paths")
        _set(document, (key,), value)
        combined = _merge(combined, {key: value})
    return combined


def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    source = _load(SOURCE_FILE, round_trip=True)
    provenance = {"path": str(SOURCE_FILE.relative_to(REPO_ROOT)), "sha256": _hash(SOURCE_FILE)}
    if args.from_src:
        return {"dataset": args.dataset_name, "profile": "from-src", "mode": "from-src",
                "document": source, "patches": {}, "provenance": provenance,
                "set_values": [], "legacy_values": []}
    name = args.profile_option or args.profile or "defaults"
    profile = _profile(name)
    patch = copy.deepcopy(profile.get("patches", {}).get(DOCUMENT, {}))
    _validate_patch(source, patch)
    document = _merge(source, patch)
    combined = _overrides(document, patch, args)
    return {"dataset": args.dataset_name, "profile": name, "mode": "profile",
            "document": document, "patches": {DOCUMENT: combined}, "provenance": provenance,
            "set_values": args.set_values, "legacy_values": args.var}


def _guidance(document: dict[str, Any]) -> list[str]:
    notes = [
        "REVIEW BEFORE USE: build_stream_host_ip must identify the execution OIM.",
        "REVIEW BEFORE USE: gitlab_host must identify the reachable GitLab server.",
        "Credentials are configured separately and are never generated or synchronized.",
    ]
    if not document.get("enable_build_stream", False):
        notes.insert(0, "BuildStream is disabled; domain tasks must be skipped.")
    return notes


def _render(plan: dict[str, Any], staging: Path) -> list[str]:
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    environment.filters["to_yaml"] = _dump
    try:
        content = environment.get_template("document.yml.j2").render(
            title="BuildStream configuration", source=plan["provenance"]["path"],
            guidance=_guidance(plan["document"]), document=plan["document"])
    except TemplateError as exc:
        raise GeneratorError(f"Template rendering failed: {exc}") from exc
    if plan["document"].get("enable_build_stream", False):
        for field in ("build_stream_host_ip", "gitlab_host"):
            if not plan["document"].get(field):
                content = re.sub(rf"^({field}:.*)$", r"\1  # REPLACE WITH REAL VALUE",
                                 content, flags=re.MULTILINE)
    output = staging / OUTPUT_FILE
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    plan["replacement_marker_count"] = content.count("REPLACE WITH REAL VALUE")
    manifest = {
        "schema_version": 2, "generator_version": GENERATOR_VERSION,
        "dataset": plan["dataset"], "profile": plan["profile"], "mode": plan["mode"],
        "replacement_marker_count": plan["replacement_marker_count"],
        "source_documents": {DOCUMENT: plan["provenance"]}, "patches": plan["patches"],
        "external_inputs": [
            "Encrypted BuildStream credential pair configured on the execution OIM"
        ],
        "artifacts": {OUTPUT_FILE: _hash(output)},
    }
    (staging / "dataset_manifest.yml").write_text("---\n" + _dump(manifest), encoding="utf-8")
    (staging / "README.md").write_text(_readme(plan), encoding="utf-8")
    return [OUTPUT_FILE, "dataset_manifest.yml", "README.md"]


def _regenerate(plan: dict[str, Any]) -> str:
    command = ["./generate_dataset.py", "create", plan["dataset"]]
    if plan["mode"] == "from-src":
        command.append("--from-src")
    else:
        command.extend(["--profile", plan["profile"]])
        for value in plan["set_values"]:
            command.extend(["--set", value])
        for value in plan["legacy_values"]:
            command.extend(["--var", value])
    command.append("--force")
    return shlex.join(command)


def _readme(plan: dict[str, Any]) -> str:
    return "\n".join([
        f"# Dataset: {plan['dataset']}", "",
        "Generated from canonical `src/build_stream/input/build_stream_config.yml`.", "",
        f"- Profile: `{plan['profile']}`", f"- Mode: `{plan['mode']}`",
        f"- Required value replacements: `{plan['replacement_marker_count']}`",
        "- Provenance and artifact hashes: `dataset_manifest.yml`", "",
        "## Files", "", f"- `{OUTPUT_FILE}`", "- `dataset_manifest.yml`", "- `README.md`", "",
        "## Customer edit checklist", "",
        *[f"- {item}" for item in _guidance(plan["document"])], "",
        "Credentials are never generated or synchronized. From `test/build_stream`",
        "on the execution OIM, run `./setup_env.sh --set-domain-creds`.", "",
        "## Regenerate", "", "```bash", "cd datasets/generator/", _regenerate(plan), "```", "",
        "## Use", "", f"Set `dataset: \"{plan['dataset']}\"` and",
        "`sync_build_stream_input: true` in `test_config.yml`.", "",
    ])


def _inventory(directory: Path) -> dict[str, tuple[str, str]]:
    entries = {}
    for path in directory.rglob("*"):
        relative = str(path.relative_to(directory))
        entries[relative] = (("symlink", "") if path.is_symlink() else
                             ("file", _hash(path)) if path.is_file() else
                             ("directory", "") if path.is_dir() else ("special", ""))
    return entries


@contextmanager
def _dataset_lock():
    """Serialize dataset comparisons and publication like the reference generator."""
    descriptor = None
    try:
        descriptor = os.open(DATASETS_DIR, os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise GeneratorError("Another dataset transaction is active; retry") from exc
    finally:
        if descriptor is not None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def _changes(expected: Path, actual: Path) -> list[str]:
    left, right = _inventory(expected), _inventory(actual)
    changes = [f"missing: {name}" for name in sorted(set(left) - set(right))]
    changes += [f"extra: {name}" for name in sorted(set(right) - set(left))]
    changes += [
        f"changed: {name}"
        for name in sorted(set(left) & set(right))
        if left[name] != right[name]
    ]
    return changes


def _publish(staging: Path, output: Path, force: bool) -> None:
    with _dataset_lock():
        if output.is_symlink() or (output.exists() and not output.is_dir()):
            raise GeneratorError(f"Unsafe dataset target: {output}")
        if output.exists() and not force:
            raise GeneratorError(f"Dataset '{output.name}' already exists; use --force")
        backup = DATASETS_DIR / f".{output.name}.backup-{uuid.uuid4().hex}"
        existed = output.exists()
        try:
            if existed:
                output.rename(backup)
            staging.rename(output)
        except (OSError, KeyboardInterrupt) as exc:
            if existed and backup.exists() and not output.exists():
                backup.rename(output)
            raise GeneratorError(f"Cannot publish dataset: {exc}") from exc
        if backup.exists():
            shutil.rmtree(backup)


def _generate(args: argparse.Namespace) -> None:
    plan = _prepare(args)
    output = DATASETS_DIR / args.dataset_name
    if output.parent != DATASETS_DIR:
        raise GeneratorError(f"Dataset path escapes dataset root: {output}")
    if output.exists() and not (args.force or args.dry_run or args.check):
        raise GeneratorError(f"Dataset '{args.dataset_name}' already exists; use --force")
    staging = Path(tempfile.mkdtemp(prefix=f".{args.dataset_name}.staging-", dir=DATASETS_DIR))
    try:
        staging.chmod(0o755)
        generated = _render(plan, staging)
        if args.dry_run:
            print(f"  [OK] Dry run passed: {len(generated)} files generated; nothing published")
        elif args.check:
            with _dataset_lock():
                if output.is_symlink() or not output.is_dir():
                    raise GeneratorError(f"Dataset does not exist safely: {output}")
                changes = _changes(staging, output)
            if changes:
                raise GeneratorError("Dataset is stale:\n  - " + "\n  - ".join(changes))
            print(f"  [OK] Dataset '{args.dataset_name}' is current")
        else:
            _publish(staging, output, args.force)
            print(f"  [OK] Dataset '{args.dataset_name}' published ({len(generated)} files)")
            print(f"  Use: set dataset: \"{args.dataset_name}\" and sync_build_stream_input: true")
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate BuildStream test datasets",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="""Examples:
  ./generate_dataset.py profiles
  ./generate_dataset.py profiles disabled
  ./generate_dataset.py create my_dataset --profile defaults
  ./generate_dataset.py create disabled_dataset --profile disabled
  ./generate_dataset.py create my_dataset --profile defaults --set build_stream_config:gitlab_host=10.10.10.20
  ./generate_dataset.py create source_snapshot --from-src
  ./generate_dataset.py create my_dataset --profile defaults --dry-run
  ./generate_dataset.py create my_dataset --profile defaults --check

Legacy syntax remains supported:
  ./generate_dataset.py my_dataset defaults
""")
    parser.add_argument("dataset_name", nargs="?")
    parser.add_argument("profile", nargs="?")
    parser.add_argument("--profile", dest="profile_option")
    parser.add_argument("--var", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument(
        "--set", dest="set_values", action="append", default=[],
        metavar="DOCUMENT:PATH=VALUE"
    )
    parser.add_argument("--list-profiles", "--profiles", action="store_true")
    parser.add_argument("--show-profile")
    parser.add_argument("--from-src", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    return parser


def _normalize(arguments: list[str]) -> list[str]:
    if not arguments:
        return arguments
    no_color = ["--no-color"] if "--no-color" in arguments else []
    remaining = [item for item in arguments if item != "--no-color"]
    if not remaining:
        return []
    if remaining[0] == "create":
        if len(remaining) < 2 or remaining[1].startswith("-"):
            raise GeneratorError("Usage: generate_dataset.py create DATASET [OPTIONS]")
        return [*no_color, *remaining[1:]]
    if remaining[0] == "profiles":
        if len(remaining) == 1:
            return [*no_color, "--list-profiles"]
        if len(remaining) == 2 and not remaining[1].startswith("-"):
            return [*no_color, "--show-profile", remaining[1]]
        raise GeneratorError("Usage: generate_dataset.py profiles [PROFILE]")
    return arguments


def _validate(args: argparse.Namespace) -> None:
    if args.list_profiles or args.show_profile:
        if any((args.dataset_name, args.profile, args.profile_option, args.var,
                args.set_values, args.from_src, args.force, args.dry_run, args.check)):
            raise GeneratorError("Profile display commands do not accept generation arguments")
        return
    if not args.dataset_name:
        raise GeneratorError("dataset name is required")
    _safe_name(args.dataset_name, "dataset name")
    if args.profile and args.profile_option:
        raise GeneratorError("Choose a profile positionally or with --profile, not both")
    if args.from_src and (args.profile or args.profile_option or args.var or args.set_values):
        raise GeneratorError("--from-src cannot be combined with profiles or overrides")
    if args.dry_run and args.check:
        raise GeneratorError("--dry-run and --check are mutually exclusive")
    if args.check and args.force:
        raise GeneratorError("--check and --force are mutually exclusive")


def main(arguments: list[str] | None = None) -> int:
    """Run the generator CLI and return its process exit code."""
    parser = _parser()
    try:
        raw = list(sys.argv[1:] if arguments is None else arguments)
        if not raw:
            parser.print_help()
            _list_profiles()
            return 0
        args = parser.parse_args(_normalize(raw))
        _validate(args)
        if args.list_profiles:
            _list_profiles()
        elif args.show_profile:
            _show_profile(args.show_profile)
        else:
            _generate(args)
        return 0
    except (GeneratorError, OSError) as exc:
        print(f"  [FAIL] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("  [WARN] Generation interrupted; staged output was cleaned up", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
