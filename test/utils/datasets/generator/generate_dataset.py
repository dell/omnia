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
Utils Domain — Dataset Generator.

Generates test datasets from Jinja2 templates and YAML variable profiles.

Usage:
    python generate_dataset.py <name> <profile>
    python generate_dataset.py <name> --from-src

Examples:
    python generate_dataset.py data_set_01 defaults
    python generate_dataset.py data_set_02 --from-src
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


SCRIPT_DIR = Path(__file__).parent.resolve()
DATASETS_DIR = SCRIPT_DIR.parent
PROFILES_DIR = SCRIPT_DIR / "profiles"
TEMPLATES_DIR = SCRIPT_DIR / "templates"

# Monorepo paths
TEST_DIR = DATASETS_DIR.parent
MONOREPO_ROOT = TEST_DIR.parent.parent
SRC_INPUT_DIR = MONOREPO_ROOT / "src" / "utils" / "input"


def load_profile(profile_name: str) -> dict:
    """Load a variable profile from YAML.

    Always loads defaults.yml first, then merges the specified profile.

    Args:
        profile_name: Name of the profile (without .yml extension).

    Returns:
        dict: Merged variable dictionary.
    """
    # Load defaults first
    defaults_path = PROFILES_DIR / "defaults.yml"
    if not defaults_path.exists():
        print(f"ERROR: defaults.yml not found at {defaults_path}")
        sys.exit(1)

    with open(defaults_path, "r") as f:
        variables = yaml.safe_load(f) or {}

    # Merge profile if not "defaults"
    if profile_name != "defaults":
        profile_path = PROFILES_DIR / f"{profile_name}.yml"
        if not profile_path.exists():
            print(f"ERROR: Profile not found: {profile_path}")
            sys.exit(1)

        with open(profile_path, "r") as f:
            profile_vars = yaml.safe_load(f) or {}
            variables.update(profile_vars)

    return variables


def render_templates(output_dir: Path, variables: dict) -> None:
    """Render all Jinja2 templates to the output directory.

    Args:
        output_dir: Target directory for rendered files.
        variables: Variable dictionary for template rendering.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=select_autoescape(['html', 'xml']),  # nosec B701
    )

    for template_path in TEMPLATES_DIR.rglob("*.j2"):
        # Get relative path from templates dir
        rel_path = template_path.relative_to(TEMPLATES_DIR)
        # Remove .j2 extension
        output_path = output_dir / str(rel_path)[:-3]

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Render template
        template = env.get_template(str(rel_path))
        content = template.render(**variables)

        with open(output_path, "w") as f:
            f.write(content)

        print(f"  Created: {output_path.relative_to(DATASETS_DIR)}")


def copy_from_src(output_dir: Path) -> None:
    """Copy input files from src/utils/input/ to the dataset.

    Args:
        output_dir: Target directory for copied files.
    """
    input_dir = output_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    if not SRC_INPUT_DIR.exists():
        print(f"ERROR: Source input directory not found: {SRC_INPUT_DIR}")
        sys.exit(1)

    for src_file in SRC_INPUT_DIR.iterdir():
        if src_file.is_file():
            dest_file = input_dir / src_file.name
            shutil.copy2(src_file, dest_file)
            print(f"  Copied: {dest_file.relative_to(DATASETS_DIR)}")


def generate_readme(output_dir: Path, profile_name: str, variables: dict) -> None:
    """Generate README.md for the dataset.

    Args:
        output_dir: Target directory.
        profile_name: Name of the profile used.
        variables: Variable dictionary.
    """
    readme_content = f"""# Dataset: {output_dir.name}

Generated: {datetime.now().isoformat()}
Profile: {profile_name}

## Variables

```yaml
{yaml.dump(variables, default_flow_style=False)}
```

## Files

"""
    for file_path in sorted(output_dir.rglob("*")):
        if file_path.is_file() and file_path.name != "README.md":
            readme_content += f"- {file_path.relative_to(output_dir)}\n"

    readme_path = output_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)

    print(f"  Created: {readme_path.relative_to(DATASETS_DIR)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test datasets for utils domain."
    )
    parser.add_argument(
        "name",
        help="Dataset name (e.g., data_set_01)",
    )
    parser.add_argument(
        "profile",
        nargs="?",
        default="defaults",
        help="Profile name (default: defaults)",
    )
    parser.add_argument(
        "--from-src",
        action="store_true",
        help="Copy from src/utils/input/ instead of rendering templates",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Override variable: --var key=value",
    )

    args = parser.parse_args()

    output_dir = DATASETS_DIR / args.name

    if output_dir.exists():
        print(f"ERROR: Dataset already exists: {output_dir}")
        print("Remove it first or choose a different name.")
        sys.exit(1)

    print(f"Generating dataset: {args.name}")

    if args.from_src:
        print("Mode: Copy from src/")
        output_dir.mkdir(parents=True, exist_ok=True)
        copy_from_src(output_dir)
        generate_readme(output_dir, "from-src", {"source": str(SRC_INPUT_DIR)})
    else:
        print(f"Mode: Template rendering (profile: {args.profile})")
        variables = load_profile(args.profile)

        # Apply CLI overrides
        for var_override in args.var:
            if "=" in var_override:
                key, value = var_override.split("=", 1)
                variables[key] = value

        output_dir.mkdir(parents=True, exist_ok=True)
        render_templates(output_dir, variables)
        generate_readme(output_dir, args.profile, variables)

    print(f"\nDataset created: {output_dir}")


if __name__ == "__main__":
    main()
