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
SRC_INPUT_DIR = REPO_ROOT / "src" / "orchestrator" / "input"


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


def _copy_from_src(output_dir):
    """Copy dataset files directly from src/orchestrator/input/ directory."""
    if not SRC_INPUT_DIR.exists():
        _fail(f"src/ input directory not found: {SRC_INPUT_DIR}")

    # Copy input files
    input_dir = output_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for src_file in SRC_INPUT_DIR.glob("*.yml"):
        dest = input_dir / src_file.name
        shutil.copy2(src_file, dest)
        _ok(f"Copied: input/{src_file.name}")

    copied = [str(p.relative_to(output_dir)) for p in sorted(output_dir.rglob("*.yml"))]
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
  %(prog)s my_ds defaults
  %(prog)s my_custom defaults --var pxe_mapping_file_path=/path/to/mapping.csv
  %(prog)s my_ds --from-src
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
        help="Profile name: defaults, or a custom profile",
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
    profile_name = args.profile or "from-src"
    output_dir = DATASETS_DIR / dataset_name

    print()
    print("=================================================================")
    print(f"  Dataset Generator — {dataset_name} ({profile_name})")
    print("=================================================================")
    print()

    if output_dir.exists() and not args.force:
        _fail(
            f"Dataset '{dataset_name}' already exists at {output_dir}. "
            "Use --force to overwrite."
        )

    if args.from_src:
        _info("Copying from src/orchestrator/input/")
        rendered = _copy_from_src(output_dir)
        variables = {}
        profile_name = "from-src"
    else:
        variables = _resolve_variables(profile_name, args.var)
        _ok(f"Profile: {profile_name}")
        rendered = _render_templates(variables, output_dir)

    _generate_readme(dataset_name, profile_name, variables, rendered, output_dir)

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
