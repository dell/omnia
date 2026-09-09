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
    python generate_dataset.py my_custom defaults --var pulp_server_port=2226
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
# src/ paths (4 levels up from generator/ → test/repo_manager/datasets/generator → repo root)
REPO_ROOT = GENERATOR_DIR.parents[3]
SRC_INPUT_DIR = REPO_ROOT / "src" / "repo_manager" / "input"


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


def _error(msg):
    """Print an error message."""
    print(f"  {_RED}[ERROR]{_NC} {msg}")


def _load_profile(profile_name):
    """Load and merge profile YAML files.
    
    Args:
        profile_name: Name of the profile to load (without .yml extension)
        
    Returns:
        dict: Merged profile variables
    """
    # Always load defaults first
    defaults_path = PROFILES_DIR / "defaults.yml"
    if not defaults_path.exists():
        _error(f"Default profile not found: {defaults_path}")
        sys.exit(1)
    
    with open(defaults_path) as f:
        variables = yaml.safe_load(f) or {}
    
    # Load profile-specific overrides if not defaults
    if profile_name != "defaults":
        profile_path = PROFILES_DIR / f"{profile_name}.yml"
        if not profile_path.exists():
            _error(f"Profile not found: {profile_path}")
            sys.exit(1)
        
        with open(profile_path) as f:
            profile_vars = yaml.safe_load(f) or {}
        
        # Deep merge profile into defaults
        variables = _deep_merge(variables, profile_vars)
    
    return variables


def _deep_merge(base, override):
    """Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Override dictionary
        
    Returns:
        dict: Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _render_templates(variables, dataset_dir):
    """Render all Jinja2 templates to the dataset directory.
    
    Args:
        variables: Template variables
        dataset_dir: Target dataset directory
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        autoescape=select_autoescape(['j2']),
    )
    
    # Render all templates in the templates directory
    for template_path in TEMPLATES_DIR.rglob("*.j2"):
        # Calculate relative path from templates dir
        rel_path = template_path.relative_to(TEMPLATES_DIR)
        # Remove .j2 extension
        output_path = dataset_dir / rel_path.with_suffix('')
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get template relative path for Jinja2
        template_rel_path = str(rel_path)
        template = env.get_template(template_rel_path)
        
        try:
            rendered = template.render(**variables)
            with open(output_path, 'w') as f:
                f.write(rendered)
            _info(f"Rendered: {rel_path.with_suffix('')}")
        except TemplateError as e:
            _error(f"Template error in {rel_path}: {e}")
            sys.exit(1)


def _copy_from_src(dataset_dir):
    """Copy input files directly from src/repo_manager/input/.
    
    Args:
        dataset_dir: Target dataset directory
    """
    if not SRC_INPUT_DIR.exists():
        _error(f"Source input directory not found: {SRC_INPUT_DIR}")
        sys.exit(1)
    
    input_dir = dataset_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    for src_file in SRC_INPUT_DIR.glob("*.yml"):
        dest_file = input_dir / src_file.name
        shutil.copy2(src_file, dest_file)
        _info(f"Copied: {src_file.name}")


def _generate_readme(dataset_name, profile_name, dataset_dir):
    """Generate a README.md for the dataset.
    
    Args:
        dataset_name: Name of the dataset
        profile_name: Name of the profile used
        dataset_dir: Dataset directory
    """
    readme_content = f"""# Dataset: {dataset_name}

Generated by `datasets/generator/generate_dataset.py` using profile **{profile_name}**.

---

## Profile

| Parameter | Value |
|-----------|-------|
| Profile | `{profile_name}` |
| Generated | Auto-generated from templates |

## Generated Files

```
{dataset_name}/
  input/
    repo_manager_config.yml
    repo_manager_endpoint_config.yml
```

## Regenerate

```bash
cd datasets/generator/
python generate_dataset.py {dataset_name} {profile_name} --force
```
"""
    
    readme_path = dataset_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    _info(f"Generated: README.md")


def _list_profiles():
    """List all available profiles."""
    print("Available profiles:")
    for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
        profile_name = profile_file.stem
        print(f"  - {profile_name}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test datasets for repo_manager FVT"
    )
    parser.add_argument(
        "dataset_name",
        nargs="?",
        help="Name of the dataset to generate"
    )
    parser.add_argument(
        "profile",
        nargs="?",
        help="Profile name (e.g., defaults, rhel10, minimal)"
    )
    parser.add_argument(
        "--var",
        action="append",
        help="Variable override (KEY=VALUE, repeatable)"
    )
    parser.add_argument(
        "--from-src",
        action="store_true",
        help="Copy files directly from src/repo_manager/input/ instead of rendering templates"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing dataset directory"
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available profiles and exit"
    )
    
    args = parser.parse_args()
    
    # Handle --list-profiles
    if args.list_profiles:
        _list_profiles()
        return 0
    
    # Validate required arguments
    if not args.dataset_name:
        parser.error("dataset_name is required (unless using --list-profiles)")
    
    if not args.from_src and not args.profile:
        parser.error("profile is required (unless using --from-src)")
    
    dataset_dir = DATASETS_DIR / args.dataset_name
    
    # Check if dataset already exists
    if dataset_dir.exists() and not args.force:
        _error(f"Dataset already exists: {dataset_dir}")
        _error("Use --force to overwrite")
        return 1
    
    # Remove existing dataset if --force
    if dataset_dir.exists() and args.force:
        _info(f"Removing existing dataset: {args.dataset_name}")
        shutil.rmtree(dataset_dir)
    
    # Create dataset directory
    dataset_dir.mkdir(parents=True, exist_ok=True)
    _info(f"Creating dataset: {args.dataset_name}")
    
    if args.from_src:
        # Copy from source
        _copy_from_src(dataset_dir)
        _generate_readme(args.dataset_name, "from-src", dataset_dir)
    else:
        # Load profile variables
        _info(f"Loading profile: {args.profile}")
        variables = _load_profile(args.profile)
        
        # Apply CLI variable overrides
        if args.var:
            _info("Applying variable overrides")
            for var_override in args.var:
                if "=" not in var_override:
                    _error(f"Invalid variable override: {var_override}")
                    return 1
                key, value = var_override.split("=", 1)
                # Try to parse as YAML for proper type handling
                try:
                    parsed_value = yaml.safe_load(value)
                except yaml.YAMLError:
                    parsed_value = value
                variables[key] = parsed_value
                _info(f"  {key} = {parsed_value}")
        
        # Render templates
        _info("Rendering templates")
        _render_templates(variables, dataset_dir)
        
        # Generate README
        _generate_readme(args.dataset_name, args.profile, dataset_dir)
    
    _ok(f"Dataset generated successfully: {dataset_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())