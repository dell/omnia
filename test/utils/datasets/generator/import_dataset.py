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
Utils Domain — Dataset Importer.

Imports external test datasets into the datasets directory and updates
test_config.yml to use the imported dataset.

Usage:
    python import_dataset.py <source_path> <dataset_name>
    python import_dataset.py /path/to/external/data my_dataset

Examples:
    python import_dataset.py /opt/test_data/collect_data collect_external
    python import_dataset.py ~/test_data/basic_collect basic_collect
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).parent.resolve()
DATASETS_DIR = SCRIPT_DIR.parent
TEST_DIR = DATASETS_DIR.parent
TEST_CONFIG_FILE = TEST_DIR / "test_config.yml"


def validate_source_path(source_path: Path) -> None:
    """Validate the source dataset path.

    Args:
        source_path: Path to the source dataset directory.

    Raises:
        ValueError: If the source path is invalid.
    """
    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    
    if not source_path.is_dir():
        raise ValueError(f"Source path is not a directory: {source_path}")
    
    # Check for required input directory
    input_dir = source_path / "input"
    if not input_dir.exists():
        raise ValueError(f"Source dataset must contain an 'input' directory: {source_path}")
    
    # Check for at least one required file
    required_files = ["collect_pxe.yml", "install_os_config.yml"]
    found_files = [f for f in required_files if (input_dir / f).exists()]
    
    if not found_files:
        raise ValueError(
            f"Source dataset input directory must contain at least one of: {required_files}"
        )


def import_dataset(source_path: Path, dataset_name: str, force: bool = False) -> Path:
    """Import an external dataset into the datasets directory.

    Args:
        source_path: Path to the source dataset directory.
        dataset_name: Name for the imported dataset.
        force: Overwrite existing dataset if True.

    Returns:
        Path: Path to the imported dataset.

    Raises:
        ValueError: If validation fails or dataset already exists.
    """
    # Validate source
    validate_source_path(source_path)
    
    # Validate dataset name
    if not dataset_name or dataset_name in {".", "..", "generator"}:
        raise ValueError(f"Invalid dataset name: {dataset_name}")
    
    if "/" in dataset_name or "\\" in dataset_name:
        raise ValueError(f"Dataset name cannot contain path separators: {dataset_name}")
    
    # Check if dataset already exists
    target_dir = DATASETS_DIR / dataset_name
    if target_dir.exists():
        if not force:
            raise ValueError(
                f"Dataset already exists: {dataset_name}. "
                f"Use --force to overwrite."
            )
        print(f"Removing existing dataset: {target_dir}")
        shutil.rmtree(target_dir)
    
    # Create target directory
    print(f"Importing dataset: {dataset_name}")
    print(f"Source: {source_path}")
    print(f"Target: {target_dir}")
    
    # Copy the entire dataset
    shutil.copytree(source_path, target_dir)
    
    print(f"✓ Dataset imported successfully")
    return target_dir


def update_test_config(dataset_name: str) -> None:
    """Update test_config.yml to use the imported dataset.

    Args:
        dataset_name: Name of the dataset to use.
    """
    if not TEST_CONFIG_FILE.exists():
        raise ValueError(f"Test config file not found: {TEST_CONFIG_FILE}")
    
    # Read current config
    with open(TEST_CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f) or {}
    
    # Update dataset field
    old_dataset = config.get("dataset", "")
    config["dataset"] = dataset_name
    
    # Write updated config
    with open(TEST_CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    if old_dataset:
        print(f"✓ Updated test_config.yml: {old_dataset} → {dataset_name}")
    else:
        print(f"✓ Updated test_config.yml: dataset → {dataset_name}")


def generate_import_readme(target_dir: Path, source_path: Path, dataset_name: str) -> None:
    """Generate README.md for the imported dataset.

    Args:
        target_dir: Target directory of the imported dataset.
        source_path: Original source path.
        dataset_name: Name of the dataset.
    """
    readme_content = f"""# Dataset: {dataset_name}

Imported from: {source_path}

## Import Details

This dataset was imported from an external location using the dataset importer.

## Files

"""
    for file_path in sorted(target_dir.rglob("*")):
        if file_path.is_file() and file_path.name != "README.md":
            readme_content += f"- {file_path.relative_to(target_dir)}\n"
    
    readme_path = target_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    print(f"✓ Created: {readme_path.relative_to(DATASETS_DIR)}")


def main():
    parser = argparse.ArgumentParser(
        description="Import external test datasets into the datasets directory."
    )
    parser.add_argument(
        "source_path",
        help="Path to the external dataset directory to import",
    )
    parser.add_argument(
        "dataset_name",
        help="Name for the imported dataset in the datasets directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing dataset if it already exists",
    )
    parser.add_argument(
        "--no-config-update",
        action="store_true",
        help="Skip updating test_config.yml to use the imported dataset",
    )

    args = parser.parse_args()

    # Resolve paths
    source_path = Path(args.source_path).expanduser().resolve()
    dataset_name = args.dataset_name

    try:
        # Import the dataset
        target_dir = import_dataset(source_path, dataset_name, args.force)
        
        # Generate README
        generate_import_readme(target_dir, source_path, dataset_name)
        
        # Update test config unless skipped
        if not args.no_config_update:
            update_test_config(dataset_name)
        
        print(f"\n✅ Import complete: {dataset_name}")
        print(f"   Location: {target_dir}")
        print(f"   Ready to use in tests")
        
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
