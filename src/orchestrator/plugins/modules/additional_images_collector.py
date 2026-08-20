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

# pylint: disable=import-error,no-name-in-module
#!/usr/bin/python

"""
Ansible module to collect container images from the catalog.
Returns a dict of role-specific images for crictl pull operations.

Extracts packages with packagetype 'image' from the catalog's
functional layers, groups, and package definitions.
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.build_image.common_functions import load_json_file


def collect_images_from_catalog(catalog_data):
    """
    Collect container images directly from catalog package definitions.

    Walks the catalog's functional layers -> groups -> components -> packages
    and collects entries where packagetype == 'image'.  Each image is mapped
    to the role derived from the functional layer name.

    Args:
        catalog_data (dict): Parsed catalog JSON content.

    Returns:
        dict: Role-keyed dict of image lists.
    """
    if not catalog_data:
        return {}

    catalog = catalog_data.get('catalog', {})
    packages = catalog.get('packages', {})
    groups = catalog.get('groups', {})
    functionallayers = catalog.get('functionallayer', [])

    # Build a map of component names to image entries
    image_packages = {}
    for pkg_key, pkg_data in packages.items():
        if isinstance(pkg_data, dict) and pkg_data.get('packagetype') == 'image':
            name = pkg_data.get('name', '')
            if name:
                tag = pkg_data.get('tag', 'latest')
                digest = pkg_data.get('digest', '')
                entry = {'package': name}
                if digest:
                    entry['digest'] = digest
                    entry['pull_ref'] = f"{name}@{digest}"
                else:
                    entry['tag'] = tag
                    entry['pull_ref'] = f"{name}:{tag}"
                image_packages[pkg_key] = entry

    if not image_packages:
        return {}

    # Map functional layers to roles and collect their images
    os_markers = {'rhel', 'rocky', 'ubuntu', 'sles', 'centos'}
    result = {}

    for fl in functionallayers:
        fl_name = fl.get('name', '')
        fl_components = fl.get('components', [])

        # Derive role name by stripping OS/arch suffix
        parts = fl_name.split('_')
        role_parts = []
        for part in parts:
            if part.lower() in os_markers:
                break
            role_parts.append(part)
        role_name = '_'.join(role_parts) if role_parts else fl_name

        # Collect image packages from all groups in this functional layer
        role_images = []
        for group_ref in fl_components:
            group_data = groups.get(group_ref, {})
            group_components = group_data.get('components', [])
            for comp in group_components:
                if comp in image_packages:
                    role_images.append(image_packages[comp])

        if role_images:
            if role_name in result:
                result[role_name].extend(role_images)
            else:
                result[role_name] = list(role_images)

    # Deduplicate images per role
    for role in result:
        seen = set()
        unique = []
        for img in result[role]:
            if img['pull_ref'] not in seen:
                unique.append(img)
                seen.add(img['pull_ref'])
        result[role] = unique

    return result


def run_module():
    """
    Run the Ansible module.

    Collects container images from the catalog and returns a dict
    keyed by role with image lists for crictl pull.
    """
    module_args = dict(
        catalog_file_path=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        additional_images_dict={}
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    catalog_file_path = module.params["catalog_file_path"]

    # Load catalog file
    catalog_data = load_json_file(catalog_file_path, module)
    if not catalog_data:
        module.fail_json(msg=f"Failed to load catalog file: {catalog_file_path}")

    # Collect images from catalog
    result["additional_images_dict"] = collect_images_from_catalog(catalog_data)

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
