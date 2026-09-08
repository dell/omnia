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

#!/usr/bin/env python3

import argparse
import os
from pathlib import Path


def resolve_base_and_paths(base_dir_arg: str):
    base_dir = base_dir_arg
    if not os.path.exists(base_dir):
        repo_root = Path(__file__).resolve().parents[1]
        base_dir = str(repo_root)

    base_dir_path = Path(base_dir).resolve()

    # Support base_dir as either repo root (contains input/) or the input directory itself.
    is_input_dir = (
        (base_dir_path / 'software_config.json').exists()
        and (base_dir_path / 'config').exists()
    )

    if is_input_dir:
        input_dir = str(base_dir_path)
        repo_root = Path(__file__).resolve().parents[1]
    else:
        input_dir = str(base_dir_path / 'input')
        repo_root = base_dir_path

    return repo_root, Path(input_dir)


def generate_example_catalogs(base_dir: str):
    repo_root, input_dir_path = resolve_base_and_paths(base_dir)

    # Use catalogs from src/main/samples directory instead of removed examples/catalog
    samples_catalog_dir = repo_root / 'main' / 'samples'
    mapping_base = samples_catalog_dir  # Catalog files are directly in samples directory

    # DEPRECATED: Catalog example files moved to src/main/samples/
    # This script is kept for backward compatibility but now uses the samples directory
    if not samples_catalog_dir.exists():
        raise FileNotFoundError(
            f"Catalog samples directory not found: {samples_catalog_dir}\n"
            "The catalog files have been moved to src/main/samples/ directory. "
            "To use this script, ensure the samples directory exists with catalog files."
        )

    # Map output catalog files to their corresponding mapping folder names
    # Updated to use actual catalog files from src/main/samples/
    targets = {
        'catalog_rhel_10_0_aarch64.json': 'catalog_rhel_10_0_aarch64',
        'catalog_rhel_10_0_x86_64.json': 'catalog_rhel_10_0_x86_64',
        'catalog_rhel_10_0_x86_aarch64.json': 'catalog_rhel_10_0_x86_aarch64',
        'catalog_rhel_10_2_x86_aarch64.json': 'catalog_rhel_10_2_x86_aarch64',
        'catalog_rhel_x86_64.json': 'catalog_rhel_x86_64',
        'catalog_rhel.json': 'catalog_rhel',
    }

    # Ensure catalog_rhel.json is generated last
    generation_order = [
        'catalog_rhel_10_0_aarch64.json',
        'catalog_rhel_10_0_x86_64.json',
        'catalog_rhel_10_0_x86_aarch64.json',
        'catalog_rhel_10_2_x86_aarch64.json',
        'catalog_rhel_x86_64.json',
        'catalog_rhel.json',
    ]

    results = []

    for out_name in generation_order:
        # Catalog files are now directly in samples directory
        catalog_file = samples_catalog_dir / out_name
        if catalog_file.exists():
            print(f"\n==> Found catalog file: {catalog_file}")
            results.append((out_name, "found"))
        else:
            print(f"\n==> Catalog file not found: {catalog_file}")
            results.append((out_name, "not_found"))

    print("\n=== Summary ===")
    for name, status in results:
        print(f"{name}: {status}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='List available catalog files from src/main/samples/ directory.'
    )
    parser.add_argument(
        '--base-dir',
        default='/opt/omnia/input/project_default/',
        help='Project base directory containing input/ and build_stream/ folders, or the input/ directory itself.'
    )
    args = parser.parse_args()

    print("Catalog files are now located in src/main/samples/ directory.")
    print("This script lists the available catalog files instead of generating them.")
    generate_example_catalogs(args.base_dir)


if __name__ == '__main__':
    main()
