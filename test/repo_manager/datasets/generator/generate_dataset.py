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

"""Generate complete, reproducible Repo Manager test datasets.

Templates and canonical source inputs remain authoritative. Generation occurs
in a temporary directory and is published only after every artifact has been
rendered, hashed, and documented.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    select_autoescape,
)


GENERATOR_VERSION = 2
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
TEMPLATES_DIR = GENERATOR_DIR / "templates"
DATASETS_DIR = GENERATOR_DIR.parent.resolve()
REPO_ROOT = GENERATOR_DIR.parents[3]
SRC_INPUT_DIR = REPO_ROOT / "src" / "repo_manager" / "input"
SOURCE_INPUT_FILES = (
    "repo_manager_config.yml",
    "repo_manager_endpoint_config.yml",
)
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SENSITIVE_KEY_PARTS = {
    "access_id",
    "access_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
}

_GREEN = "\033[0;32m"
_RED = "\033[0;31m"
_BLUE = "\033[0;34m"
_NC = "\033[0m"


class GeneratorError(Exception):
    """A user-correctable dataset generation error."""


class _IndentedSafeDumper(yaml.SafeDumper):
    """Emit block sequences indented beneath their mapping keys."""

    def increase_indent(
        self, flow: bool = False, indentless: bool = False
    ) -> None:
        """Disable PyYAML's indentless block-sequence output style."""
        del indentless
        super().increase_indent(flow, indentless=False)


def _info(message: str) -> None:
    """Print an informational message."""
    print(f"  {_BLUE}[...]{_NC} {message}")


def _ok(message: str) -> None:
    """Print a success message."""
    print(f"  {_GREEN}[OK]{_NC}  {message}")


def _error(message: str) -> None:
    """Print an error message."""
    print(f"  {_RED}[ERROR]{_NC} {message}", file=sys.stderr)


def _validate_name(value: str, label: str) -> str:
    """Validate one portable name used to construct a local path."""
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValueError(
            f"{label} must start with an alphanumeric character and contain "
            "only letters, numbers, dots, underscores, or hyphens"
        )
    if value in {".", "..", "generator"}:
        raise ValueError(f"{label} cannot be {value!r}")
    return value


def _dataset_path(dataset_name: str) -> Path:
    """Resolve a dataset name while guaranteeing root containment."""
    dataset_name = _validate_name(dataset_name, "dataset name")
    datasets_root = DATASETS_DIR.resolve()
    candidate = (datasets_root / dataset_name).resolve(strict=False)
    if candidate.parent != datasets_root:
        raise ValueError("dataset path must remain directly under datasets/")
    return candidate


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    parts = set(re.split(r"[._-]+", normalized))
    return bool(parts & _SENSITIVE_KEY_PARTS) or any(
        part in normalized for part in _SENSITIVE_KEY_PARTS
    )


def _validate_override_key(key: str, variables: Dict[str, Any]) -> str:
    """Allow only declared, non-secret profile variables on the command line."""
    if not isinstance(key, str) or not _SAFE_NAME.fullmatch(key):
        raise ValueError(f"invalid variable override key: {key}")
    if _sensitive_key(key):
        raise ValueError(f"sensitive variable override is not permitted: {key}")
    if key not in variables:
        raise ValueError(f"unknown variable override: {key}")
    return key


def _load_mapping(path: Path, label: str) -> Dict[str, Any]:
    """Load one required YAML mapping with a contextual error."""
    if not path.is_file() or path.is_symlink():
        raise GeneratorError(f"Required {label} file not found safely: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise GeneratorError(f"Unable to parse {label} YAML '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise GeneratorError(f"{label} YAML must contain a mapping: {path}")
    return value


def _reject_sensitive_profile_keys(value: Dict[str, Any], prefix: str = "") -> None:
    """Prevent profile data from becoming a credential side channel."""
    for key, nested in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if _sensitive_key(path):
            raise GeneratorError(f"Credential-like profile field is forbidden: {path}")
        if isinstance(nested, dict):
            _reject_sensitive_profile_keys(nested, path)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge one profile mapping into another."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_profile(profile_name: str) -> Dict[str, Any]:
    """Load defaults and the selected profile override."""
    profile_name = _validate_name(profile_name, "profile name")
    defaults = _load_mapping(PROFILES_DIR / "defaults.yml", "default profile")
    variables = defaults
    if profile_name != "defaults":
        override = _load_mapping(
            PROFILES_DIR / f"{profile_name}.yml", "profile"
        )
        variables = _deep_merge(defaults, override)
    _reject_sensitive_profile_keys(variables)
    return variables


def _parse_overrides(
    variables: Dict[str, Any], raw_overrides: Iterable[str]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Apply validated CLI overrides and return their manifest representation."""
    effective = variables.copy()
    recorded: Dict[str, Any] = {}
    for raw_override in raw_overrides:
        if "=" not in raw_override:
            raise GeneratorError(
                f"Invalid variable override {raw_override!r}; expected KEY=VALUE"
            )
        key, raw_value = raw_override.split("=", 1)
        try:
            _validate_override_key(key, effective)
            value = yaml.safe_load(raw_value)
        except (ValueError, yaml.YAMLError) as exc:
            raise GeneratorError(str(exc)) from exc
        effective[key] = value
        recorded[key] = value
    return effective, recorded


def _render_templates(
    variables: Dict[str, Any], dataset_dir: Path
) -> List[str]:
    """Render every Jinja template and return generated relative paths."""
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(
            enabled_extensions=("html", "htm", "xml"),
            default_for_string=False,
            default=False,
        ),
        keep_trailing_newline=True,
    )
    generated: List[str] = []
    for template_path in sorted(TEMPLATES_DIR.rglob("*.j2")):
        relative_template = template_path.relative_to(TEMPLATES_DIR)
        relative_output = relative_template.with_suffix("")
        output_path = dataset_dir / relative_output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            rendered = environment.get_template(
                str(relative_template)
            ).render(**variables)
        except TemplateError as exc:
            raise GeneratorError(
                f"Template error in {relative_template}: {exc}"
            ) from exc
        output_path.write_text(
            rendered if rendered.endswith("\n") else rendered + "\n",
            encoding="utf-8",
        )
        generated.append(str(relative_output))
        _info(f"Rendered: {relative_output}")
    if not generated:
        raise GeneratorError(f"No templates found below {TEMPLATES_DIR}")
    return generated


def _copy_from_src(dataset_dir: Path) -> List[str]:
    """Copy only public Repo Manager inputs from the canonical source tree."""
    if not SRC_INPUT_DIR.is_dir() or SRC_INPUT_DIR.is_symlink():
        raise GeneratorError(f"Source input directory not found safely: {SRC_INPUT_DIR}")
    input_dir = dataset_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    generated: List[str] = []
    for filename in SOURCE_INPUT_FILES:
        source = SRC_INPUT_DIR / filename
        if not source.is_file() or source.is_symlink():
            raise GeneratorError(f"Required source input file not found safely: {source}")
        destination = input_dir / filename
        shutil.copy2(source, destination)
        relative = str(destination.relative_to(dataset_dir))
        generated.append(relative)
        _info(f"Copied: {filename}")
    return generated


def _hash(path: Path) -> str:
    """Return a SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_source(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _source_documents(profile_name: str, from_src: bool) -> Dict[str, Dict[str, str]]:
    """Build deterministic source provenance for the dataset manifest."""
    paths: List[Path]
    if from_src:
        paths = [SRC_INPUT_DIR / name for name in SOURCE_INPUT_FILES]
    else:
        paths = sorted(TEMPLATES_DIR.rglob("*.j2"))
        paths.append(PROFILES_DIR / "defaults.yml")
        if profile_name != "defaults":
            paths.append(PROFILES_DIR / f"{profile_name}.yml")
    return {
        _relative_source(path): {"sha256": _hash(path)}
        for path in sorted(set(paths))
    }


def _generate_manifest(
    dataset_name: str,
    profile_name: str,
    mode: str,
    overrides: Dict[str, Any],
    generated: Iterable[str],
    dataset_dir: Path,
) -> None:
    """Write deterministic provenance and artifact hashes."""
    artifacts = {
        relative: _hash(dataset_dir / relative)
        for relative in sorted(generated)
    }
    manifest = {
        "schema_version": 1,
        "generator_version": GENERATOR_VERSION,
        "dataset": dataset_name,
        "profile": profile_name,
        "mode": mode,
        "source_documents": _source_documents(
            profile_name, mode == "from-src"
        ),
        "overrides": overrides,
        "external_inputs": [
            "Encrypted Repo Manager credentials configured on the execution OIM"
        ],
        "artifacts": artifacts,
    }
    content = yaml.dump(
        manifest,
        Dumper=_IndentedSafeDumper,
        sort_keys=True,
        default_flow_style=False,
    )
    (dataset_dir / "dataset_manifest.yml").write_text(
        "---\n" + content, encoding="utf-8"
    )
    _info("Generated: dataset_manifest.yml")


def _generate_readme(
    dataset_name: str,
    profile_name: str,
    dataset_dir: Path,
    mode: str = "profile",
) -> None:
    """Generate deterministic dataset usage and regeneration guidance."""
    if mode == "from-src":
        regenerate = (
            f"python generate_dataset.py {dataset_name} --from-src --force"
        )
    else:
        regenerate = (
            f"python generate_dataset.py {dataset_name} {profile_name} --force"
        )
    content = f"""# Dataset: {dataset_name}

Generated by `datasets/generator/generate_dataset.py` using profile **{profile_name}**.

- Mode: `{mode}`
- Provenance and artifact hashes: `dataset_manifest.yml`
- Credentials: configured separately on the execution OIM and never generated

## Files

```text
{dataset_name}/
  input/
    repo_manager_config.yml
    repo_manager_endpoint_config.yml
  dataset_manifest.yml
  README.md
```

## Regenerate

```bash
cd datasets/generator/
{regenerate}
```

## Use

Set `dataset: "{dataset_name}"` and `sync_repo_manager_input: true` in
`test_config.yml`, or select the same values in `test_run_config.yml`.
"""
    (dataset_dir / "README.md").write_text(content, encoding="utf-8")
    _info("Generated: README.md")


def _inventory(directory: Path) -> Dict[str, Tuple[str, str]]:
    """Return deterministic entry types and hashes for drift comparison."""
    entries: Dict[str, Tuple[str, str]] = {}
    for path in directory.rglob("*"):
        relative = str(path.relative_to(directory))
        if path.is_symlink():
            entries[relative] = ("symlink", "")
        elif path.is_file():
            entries[relative] = ("file", _hash(path))
        elif path.is_dir():
            entries[relative] = ("directory", "")
        else:
            entries[relative] = ("special", "")
    return entries


def _directory_changes(expected: Path, actual: Path) -> List[str]:
    """Describe missing, extra, or changed dataset entries."""
    left = _inventory(expected)
    right = _inventory(actual)
    changes = [f"missing: {name}" for name in sorted(set(left) - set(right))]
    changes.extend(f"extra: {name}" for name in sorted(set(right) - set(left)))
    changes.extend(
        f"changed: {name}"
        for name in sorted(set(left) & set(right))
        if left[name] != right[name]
    )
    return changes


def _publish(staging: Path, output: Path, force: bool) -> None:
    """Atomically replace a dataset while retaining rollback state."""
    datasets_root = DATASETS_DIR.resolve()
    if output.parent != datasets_root:
        raise GeneratorError(f"Dataset path escapes dataset root: {output}")
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise GeneratorError(f"Unsafe dataset target: {output}")
    if output.exists() and not force:
        raise GeneratorError(f"Dataset '{output.name}' already exists; use --force")

    backup = datasets_root / f".{output.name}.backup-{uuid.uuid4().hex}"
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


def _build_staging(args: argparse.Namespace, staging: Path) -> List[str]:
    """Render one complete dataset into a staging directory."""
    if args.from_src:
        profile_name = "from-src"
        mode = "from-src"
        overrides: Dict[str, Any] = {}
        generated = _copy_from_src(staging)
    else:
        profile_name = args.profile or "defaults"
        mode = "profile"
        variables = _load_profile(profile_name)
        variables, overrides = _parse_overrides(variables, args.var)
        generated = _render_templates(variables, staging)

    _generate_manifest(
        args.dataset_name,
        profile_name,
        mode,
        overrides,
        generated,
        staging,
    )
    _generate_readme(args.dataset_name, profile_name, staging, mode)
    return [*generated, "dataset_manifest.yml", "README.md"]


def _generate(args: argparse.Namespace) -> None:
    """Generate, compare, preview, or atomically publish one dataset."""
    output = _dataset_path(args.dataset_name)
    if output.exists() and not (args.force or args.dry_run or args.check):
        raise GeneratorError(
            f"Dataset '{args.dataset_name}' already exists; use --force, "
            "--check, or --dry-run"
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{args.dataset_name}.staging-", dir=DATASETS_DIR
        )
    )
    try:
        staging.chmod(0o755)
        generated = _build_staging(args, staging)
        if args.dry_run:
            _ok(
                f"Dry run passed: {len(generated)} files generated; "
                "nothing published"
            )
            return
        if args.check:
            if output.is_symlink() or not output.is_dir():
                raise GeneratorError(f"Dataset does not exist safely: {output}")
            changes = _directory_changes(staging, output)
            if changes:
                raise GeneratorError(
                    "Dataset is stale:\n  - " + "\n  - ".join(changes)
                )
            _ok(f"Dataset '{args.dataset_name}' is current")
            return
        _publish(staging, output, args.force)
        _ok(
            f"Dataset '{args.dataset_name}' published "
            f"({len(generated)} files)"
        )
        print(
            f'  Use: set dataset: "{args.dataset_name}" and '
            "sync_repo_manager_input: true"
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _list_profiles() -> None:
    """List every supported profile."""
    print("Available profiles:")
    for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
        print(f"  - {profile_file.stem}")


def _show_profile(profile_name: str) -> None:
    """Display the effective non-secret variables for one profile."""
    variables = _load_profile(profile_name)
    print(yaml.safe_dump(variables, sort_keys=True, default_flow_style=False))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate reproducible Repo Manager FVT datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  ./generate_dataset.py profiles
  ./generate_dataset.py profiles defaults
  ./generate_dataset.py create my_dataset --profile defaults
  ./generate_dataset.py my_dataset rhel10 --dry-run
  ./generate_dataset.py my_dataset defaults --check
  ./generate_dataset.py source_snapshot --from-src
""",
    )
    parser.add_argument("dataset_name", nargs="?")
    parser.add_argument("profile", nargs="?")
    parser.add_argument("--profile", dest="profile_option")
    parser.add_argument("--var", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--from-src", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--show-profile")
    return parser


def _normalize(arguments: List[str]) -> List[str]:
    """Support shared create/profiles commands and the legacy positional CLI."""
    if not arguments:
        return arguments
    if arguments[0] == "create":
        if len(arguments) < 2 or arguments[1].startswith("-"):
            raise GeneratorError(
                "Usage: generate_dataset.py create DATASET [OPTIONS]"
            )
        return arguments[1:]
    if arguments[0] == "profiles":
        if len(arguments) == 1:
            return ["--list-profiles"]
        if len(arguments) == 2 and not arguments[1].startswith("-"):
            return ["--show-profile", arguments[1]]
        raise GeneratorError("Usage: generate_dataset.py profiles [PROFILE]")
    return arguments


def _validate_args(args: argparse.Namespace) -> None:
    """Reject ambiguous or unsafe CLI combinations before staging."""
    if args.list_profiles or args.show_profile:
        if any(
            (
                args.dataset_name,
                args.profile,
                args.profile_option,
                args.var,
                args.from_src,
                args.force,
                args.dry_run,
                args.check,
            )
        ):
            raise GeneratorError(
                "Profile display commands do not accept generation arguments"
            )
        return
    if not args.dataset_name:
        raise GeneratorError("dataset name is required")
    _validate_name(args.dataset_name, "dataset name")
    if args.profile and args.profile_option:
        raise GeneratorError(
            "Choose a profile positionally or with --profile, not both"
        )
    args.profile = args.profile_option or args.profile
    if args.from_src and (args.profile or args.var):
        raise GeneratorError(
            "--from-src cannot be combined with profiles or overrides"
        )
    if not args.from_src and not args.profile:
        args.profile = "defaults"
    if args.profile:
        _validate_name(args.profile, "profile name")
    if args.dry_run and args.check:
        raise GeneratorError("--dry-run and --check are mutually exclusive")
    if args.check and args.force:
        raise GeneratorError("--check and --force are mutually exclusive")


def main(arguments: List[str] | None = None) -> int:
    """Run the generator CLI and return its process exit code."""
    parser = _parser()
    try:
        raw = list(sys.argv[1:] if arguments is None else arguments)
        if not raw:
            parser.print_help()
            _list_profiles()
            return 0
        args = parser.parse_args(_normalize(raw))
        _validate_args(args)
        if args.list_profiles:
            _list_profiles()
        elif args.show_profile:
            _show_profile(args.show_profile)
        else:
            _generate(args)
        return 0
    except (GeneratorError, ValueError, OSError) as exc:
        _error(str(exc))
        return 1
    except KeyboardInterrupt:
        _error("Generation interrupted; staged output was cleaned up")
        return 130


if __name__ == "__main__":
    sys.exit(main())
