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

"""
Dataset Generator — Renders Jinja2 templates into test dataset directories.

Replaces duplicated YAML files across datasets with a single set of Jinja2
templates and YAML variable profiles. Only the values that change between
datasets are stored in profile files; everything else comes from defaults.yml.

Usage:
    python generate_dataset.py <dataset_name> <profile>
    python generate_dataset.py <dataset_name> <profile> [--var KEY=VALUE ...]
    python generate_dataset.py <dataset_name> --from-src
    python generate_dataset.py --list-profiles
    python generate_dataset.py --help

Examples:
    python generate_dataset.py my_ds defaults
    python generate_dataset.py my_custom defaults --var pxe_mapping_file_path=/path/to/mapping.csv
    python generate_dataset.py my_ds --from-src
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    select_autoescape,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILES_DIR = GENERATOR_DIR / "profiles"
TEMPLATES_DIR = GENERATOR_DIR / "templates"
DATASETS_DIR = GENERATOR_DIR.parent
# src/ paths (4 levels up from generator/ → test/orchestrator/datasets/generator → repo root)
REPO_ROOT = GENERATOR_DIR.parents[3]
SRC_DOMAIN_DIR = REPO_ROOT / "src" / "orchestrator"
SRC_INPUT_DIR = SRC_DOMAIN_DIR / "input"
SRC_REPO_OUTPUT_DIR = SRC_DOMAIN_DIR / "samples" / "repo_manager_output"
SRC_IMAGE_BUILD_OUTPUT_DIR = SRC_DOMAIN_DIR / "samples" / "image_build_manager_output"


# ---------------------------------------------------------------------------
# Console output helpers
# ---------------------------------------------------------------------------
_GREEN = "\033[0;32m"
_RED = "\033[0;31m"
_BLUE = "\033[0;34m"
_CYAN = "\033[0;36m"
_NC = "\033[0m"


def _info(msg):
    """Print an informational message."""
    print(f"  {_BLUE}[...]{_NC} {msg}")


def _ok(msg):
    """Print a success message."""
    print(f"  {_GREEN}[OK]{_NC}  {msg}")


def _warn(msg):
    """Print a warning message."""
    print(f"  {_CYAN}[WARN]{_NC} {msg}")


def _fail(msg):
    """Print an error message and exit."""
    print(f"  {_RED}[FAIL]{_NC} {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------
def _load_yaml(path):
    """Load a YAML file and return as dict."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _merge_dicts(base, override):
    """Deep-merge *override* into *base*. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _directory_changes(staging_path: Path, output_dir: Path) -> list[str]:
    """Compare staging and output directories, return list of changed files."""
    changes = []
    staging_files = {f.relative_to(staging_path): f for f in staging_path.rglob("*") if f.is_file()}
    output_files = {f.relative_to(output_dir): f for f in output_dir.rglob("*") if f.is_file()}

    # Check for new or modified files
    for rel_path, staging_file in staging_files.items():
        if rel_path not in output_files:
            changes.append(f"new: {rel_path}")
        else:
            output_file = output_files[rel_path]
            if staging_file.stat().st_size != output_file.stat().st_size:
                changes.append(f"modified: {rel_path}")
            elif staging_file.read_bytes() != output_file.read_bytes():
                changes.append(f"modified: {rel_path}")

    # Check for deleted files
    for rel_path in output_files:
        if rel_path not in staging_files:
            changes.append(f"deleted: {rel_path}")

    return changes


def _parse_cli_var(var_str):
    """Parse ``KEY=VALUE`` into *(key, value)* with YAML type inference."""
    if "=" not in var_str:
        _fail(f"Invalid --var format: '{var_str}'. Expected KEY=VALUE.")
    key, raw = var_str.split("=", 1)
    key = key.strip()
    raw = raw.strip()
    try:
        return key, yaml.safe_load(raw)
    except yaml.YAMLError:
        return key, raw


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------
def _available_profiles():
    """Return a sorted list of (name, data) for non-default profiles."""
    profiles = []
    for yml in sorted(PROFILES_DIR.glob("*.yml")):
        if yml.name == "defaults.yml":
            continue
        profiles.append((yml.stem, _load_yaml(yml)))
    return profiles


def _list_profiles():
    """Print available profiles to stdout."""
    print("\nAvailable profiles:")
    print("-" * 50)
    print(f"  {_CYAN}{'defaults':20s}{_NC} (base profile — used when no override needed)")
    for name, data in _available_profiles():
        dcgm = data.get("dcgm_enabled", "—")
        print(f"  {_CYAN}{name:20s}{_NC} dcgm_enabled={dcgm}")
    print()


def _resolve_variables(profile_name, cli_vars):
    """Load defaults → merge profile → apply CLI overrides."""
    defaults_path = PROFILES_DIR / "defaults.yml"
    if not defaults_path.exists():
        _fail(f"defaults.yml not found at {defaults_path}")

    variables = _load_yaml(defaults_path)

    # "defaults" is a virtual profile — no separate file needed
    if profile_name != "defaults":
        profile_path = PROFILES_DIR / f"{profile_name}.yml"
        if not profile_path.exists():
            available = ", ".join(
                name for name, _ in _available_profiles()
            )
            _fail(
                f"Profile '{profile_name}' not found. "
                f"Available: defaults, {available}"
            )
        variables = _merge_dicts(variables, _load_yaml(profile_path))

    for var_str in cli_vars:
        key, value = _parse_cli_var(var_str)
        variables[key] = value
        _info(f"Override: {key} = {value}")

    return variables


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def _render_templates(variables, output_dir):
    """Render all Jinja2 templates into *output_dir*. Returns file list."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default_for_string=False, default=False),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )

    rendered = []
    for tpl_path in sorted(TEMPLATES_DIR.rglob("*.j2")):
        rel = tpl_path.relative_to(TEMPLATES_DIR)
        out_name = str(rel).removesuffix(".j2")

        template = env.get_template(str(rel))
        try:
            content = template.render(**variables)
        except TemplateError as exc:
            _fail(f"Template render error in {rel}: {exc}")

        out_path = output_dir / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        rendered.append(out_name)
        _ok(f"Generated: {out_name}")

    # Create repo_manager_output directory if it doesn't exist
    repo_output_dir = output_dir / "repo_manager_output"
    repo_output_dir.mkdir(parents=True, exist_ok=True)
    rendered.append("repo_manager_output/")
    _ok("Created: repo_manager_output/")

    return rendered


def _copy_from_src(output_dir, profile_data=None):
    """Copy dataset files directly from src/orchestrator/ directory."""
    if not SRC_INPUT_DIR.exists():
        _fail(f"src/ input directory not found: {SRC_INPUT_DIR}")

    # Determine file filter from profile
    include_input_files = None
    include_samples = None
    
    if profile_data and "include_files" in profile_data:
        include_config = profile_data["include_files"]
        include_input_files = include_config.get("input", [])
        include_samples = include_config.get("samples", [])
        _info(f"Using profile file filter: {len(include_input_files)} input files, {len(include_samples)} sample dirs")
    else:
        _info("No profile filter - copying all files")

    # Copy input files (both .yml and .csv)
    input_dir = output_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    if include_input_files:
        # Filter based on profile
        for filename in include_input_files:
            src_file = SRC_INPUT_DIR / filename
            if src_file.exists():
                dest = input_dir / filename
                shutil.copy2(src_file, dest)
                _ok(f"Copied: input/{filename}")
            else:
                _warn(f"File not found: {filename}")
    else:
        # Copy all files
        for src_file in SRC_INPUT_DIR.glob("*.yml"):
            dest = input_dir / src_file.name
            shutil.copy2(src_file, dest)
            _ok(f"Copied: input/{src_file.name}")
        
        for src_file in SRC_INPUT_DIR.glob("*.csv"):
            dest = input_dir / src_file.name
            shutil.copy2(src_file, dest)
            _ok(f"Copied: input/{src_file.name}")

    # Copy sample directories based on profile
    if include_samples:
        for sample_dir in include_samples:
            src_sample = SRC_DOMAIN_DIR / "samples" / sample_dir
            if src_sample.exists():
                dest_sample = output_dir / sample_dir
                if dest_sample.exists():
                    shutil.rmtree(dest_sample)
                shutil.copytree(src_sample, dest_sample)
                _ok(f"Copied: {sample_dir}/")
            else:
                _warn(f"Sample directory not found: {sample_dir}")
    else:
        # Copy all sample directories
        if SRC_REPO_OUTPUT_DIR.exists():
            repo_output_dir = output_dir / "repo_manager_output"
            if repo_output_dir.exists():
                shutil.rmtree(repo_output_dir)
            shutil.copytree(SRC_REPO_OUTPUT_DIR, repo_output_dir)
            _ok(f"Copied: repo_manager_output/")
        else:
            _warn(f"repo_manager_output not found: {SRC_REPO_OUTPUT_DIR}")

        if SRC_IMAGE_BUILD_OUTPUT_DIR.exists():
            image_build_output_dir = output_dir / "image_build_manager_output"
            if image_build_output_dir.exists():
                shutil.rmtree(image_build_output_dir)
            shutil.copytree(SRC_IMAGE_BUILD_OUTPUT_DIR, image_build_output_dir)
            _ok(f"Copied: image_build_manager_output/")
        else:
            _warn(f"image_build_manager_output not found: {SRC_IMAGE_BUILD_OUTPUT_DIR}")

    copied = [str(p.relative_to(output_dir)) for p in sorted(output_dir.rglob("*")) if p.is_file()]
    return copied


def _generate_readme(dataset_name, profile_name, variables, rendered, output_dir):
    """Write a README.md summarising the generated dataset."""
    lines = [
        f"# Dataset: {dataset_name}",
        "",
        f"Generated by `datasets/generator/generate_dataset.py` "
        f"using profile **{profile_name}**.",
        "",
        "---",
        "",
        "## Profile",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Profile | `{profile_name}` |",
        f"| pxe_mapping_file_path | `{variables.get('pxe_mapping_file_path', '')}` |",
        f"| language | `{variables.get('language', '')}` |",
        f"| dns_enabled | `{variables.get('dns_enabled', '')}` |",
        f"| dcgm_enabled | `{variables.get('dcgm_enabled', '')}` |",
        "",
        "## Generated Files",
        "",
        "```",
        f"{dataset_name}/",
    ]
    for fname in sorted(rendered):
        lines.append(f"  {fname}")
    lines += [
        "```",
        "",
        "## Regenerate",
        "",
        "```bash",
        "cd datasets/generator/",
        f"python generate_dataset.py {dataset_name} {profile_name} --force",
        "```",
        "",
    ]

    readme_path = output_dir / "README.md"
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    _ok("Generated: README.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Entry point for the dataset generator CLI."""
    parser = argparse.ArgumentParser(
        description="Generate test dataset from Jinja2 templates and profiles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_k8s_dataset k8s_only --from-src
  %(prog)s my_slurm_dataset slurm_only --from-src
  %(prog)s my_combined_dataset k8s_and_slurm --from-src
  %(prog)s my_k8s_dataset k8s_only --check
  %(prog)s my_slurm_dataset slurm_only --dry-run
  %(prog)s my_dataset defaults --var pxe_mapping_file_path=/path/to/mapping.csv
  %(prog)s --list-profiles
""",
    )
    parser.add_argument(
        "dataset_name",
        nargs="?",
        help="Name of the dataset directory to create",
    )
    parser.add_argument(
        "profile",
        nargs="?",
        help="Profile name: defaults, k8s_only, slurm_only, k8s_and_slurm, or a custom profile",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a template variable (repeatable)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available profiles and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing dataset directory",
    )
    parser.add_argument(
        "--from-src",
        action="store_true",
        help="Copy files directly from src/ instead of rendering templates",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if dataset is current (compare with staged output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate staging output without publishing to datasets/",
    )

    args = parser.parse_args()

    if args.list_profiles:
        _list_profiles()
        return

    if not args.dataset_name:
        parser.print_help()
        sys.exit(1)

    if not args.from_src and not args.profile:
        parser.error("profile is required unless --from-src is used")

    dataset_name = args.dataset_name
    profile_name = args.profile or "defaults"
    output_dir = DATASETS_DIR / dataset_name

    print()
    print("=================================================================")
    print(f"  Dataset Generator — {dataset_name} ({profile_name})")
    print("=================================================================")
    print()

    if output_dir.exists() and not args.force and not args.check and not args.dry_run:
        _fail(
            f"Dataset '{dataset_name}' already exists at {output_dir}. "
            "Use --force to overwrite, --check to compare, or --dry-run to test."
        )

    # Use staging directory for atomic operations
    staging_path = Path(
        tempfile.mkdtemp(prefix=f".{dataset_name}.staging-", dir=DATASETS_DIR)
    )
    try:
        staging_path.chmod(0o755)

        if args.from_src:
            _info("Copying from src/orchestrator/")
            # Use profile for filtering if provided and not defaults
            if profile_name and profile_name != "defaults":
                profile_data = _load_yaml(PROFILES_DIR / f"{profile_name}.yml")
                _info(f"Using profile filter: {profile_name}")
            else:
                profile_data = None
                _info("No profile filter - copying all files")
            rendered = _copy_from_src(staging_path, profile_data)
            variables = {}
        else:
            variables = _resolve_variables(profile_name, args.var)
            _ok(f"Profile: {profile_name}")
            rendered = _render_templates(variables, staging_path)

        _generate_readme(dataset_name, profile_name, variables, rendered, staging_path)

        # Handle --check mode
        if args.check:
            if not output_dir.is_dir() or output_dir.is_symlink():
                _fail(f"Dataset does not exist safely: {output_dir}")
            changes = _directory_changes(staging_path, output_dir)
            if changes:
                _fail(
                    "Dataset is stale:\n  - " + "\n  - ".join(changes)
                )
            _ok(f"Dataset '{dataset_name}' is current")
            return

        # Handle --dry-run mode
        if args.dry_run:
            _ok(f"Dry run passed: {len(rendered)} files generated; nothing published")
            print(f"\n  Staging output: {staging_path}")
            return

        # Publish to final location
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(staging_path, output_dir)

    finally:
        if staging_path.exists():
            try:
                shutil.rmtree(staging_path)
            except OSError as exc:
                _warn(f"Could not remove staging directory {staging_path}: {exc}")

    print()
    print(f"{_GREEN}========================================={_NC}")
    print(f"{_GREEN}  Dataset '{dataset_name}' generated "
          f"({len(rendered)} files){_NC}")
    print(f"{_GREEN}========================================={_NC}")
    print()
    print(f"  Output:  {output_dir}")
    print(f"  Profile: {profile_name}")
    print()
    print("  To use this dataset:")
    print(f'    Edit test_config.yml → dataset: "{dataset_name}"')
    print()


if __name__ == "__main__":
    main()
