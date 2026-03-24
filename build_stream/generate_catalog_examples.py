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
import json
import os
import shutil
from pathlib import Path

# Import sibling module generate_catalog.py in the same folder
# When executed as a script (python build_stream/generate_catalog_examples.py),
# sys.path[0] will be this folder, so a plain import works.
import generate_catalog as gen


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


def copy_mapping_to_input(mapping_dir: Path, input_dir: Path):
    src_sw = mapping_dir / 'software_config.json'
    src_pxe = mapping_dir / 'pxe_mapping_file.csv'

    if not src_sw.exists() or not src_pxe.exists():
        raise FileNotFoundError(f"Mapping set missing files in {mapping_dir}")

    dst_sw = input_dir / 'software_config.json'
    dst_pxe = input_dir / 'pxe_mapping_file.csv'

    shutil.copyfile(src_sw, dst_sw)
    shutil.copyfile(src_pxe, dst_pxe)


def generate_example_catalogs(base_dir: str):
    repo_root, input_dir_path = resolve_base_and_paths(base_dir)

    examples_catalog_dir = repo_root / 'examples' / 'catalog'
    mapping_base = examples_catalog_dir / 'mapping_file_software_config'

    # Map output catalog files to their corresponding mapping folder names
    targets = {
        'catalog_rhel_aarch64_with_slurm_only.json': 'catalog_rhel_aarch64_with_slurm_only_json',
        'catalog_rhel_x86_64_with_slurm_only.json': 'catalog_rhel_x86_64_with_slurm_only_json',
        'catalog_rhel.json': 'catalog_rhel_json',
    }

    # Ensure catalog_rhel.json is generated last
    generation_order = [
        'catalog_rhel_aarch64_with_slurm_only.json',
        'catalog_rhel_x86_64_with_slurm_only.json',
        'catalog_rhel.json',
    ]

    # Paths used by the generator
    input_config_dir = str(input_dir_path / 'config')
    software_config_file = str(input_dir_path / 'software_config.json')
    pxe_mapping_csv = str(input_dir_path / 'pxe_mapping_file.csv')

    results = []

    for out_name in generation_order:
        mapping_folder = targets[out_name]
        mapping_dir = mapping_base / mapping_folder
        print(f"\n==> Preparing mapping for {out_name} from {mapping_dir}")
        copy_mapping_to_input(mapping_dir, input_dir_path)

        print(
            f"Generating catalog using software_config={software_config_file} "
            f"and pxe_mapping={pxe_mapping_csv}"
        )
        catalog_obj = gen.generate_catalog(input_config_dir, software_config_file, pxe_mapping_csv)

        out_path = examples_catalog_dir / out_name
        print(f"Writing generated catalog to {out_path}")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(catalog_obj, f, indent=2)

        results.append({
            'output': str(out_path),
            'functional_packages': len(catalog_obj['Catalog']['FunctionalPackages']),
            'os_packages': len(catalog_obj['Catalog']['OSPackages']),
            'infra_packages': len(catalog_obj['Catalog']['InfrastructurePackages']),
            'functional_layers': len(catalog_obj['Catalog']['FunctionalLayer']),
        })

    print("\nSummary:")
    for r in results:
        print(
            f"  - {r['output']} => functional={r['functional_packages']}, "
            f"os={r['os_packages']}, infra={r['infra_packages']}, layers={r['functional_layers']}"
        )


def main():
    parser = argparse.ArgumentParser(
        description='Generate example catalogs by copying mapping/software_config into input/ and rendering catalogs.'
    )
    parser.add_argument(
        '--base-dir',
        default='/opt/omnia/input/project_default/',
        help='Project base directory containing input/ and build_stream/ folders, or the input/ directory itself.'
    )
    args = parser.parse_args()

    generate_example_catalogs(args.base_dir)


if __name__ == '__main__':
    main()
