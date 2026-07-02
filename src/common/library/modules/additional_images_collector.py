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
Ansible module to collect container images from additional_packages.json.
Returns a dict of role-specific images for crictl pull operations.
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.build_image.config import ROLE_SPECIFIC_KEYS, IMAGE_ROLE_KEYS
from ansible.module_utils.build_image.common_functions import (
    load_json_file,
    is_additional_packages_enabled,
    get_allowed_additional_subgroups
)

def extract_images_from_cluster(cluster_items):
    """
    Extract image entries (type: "image") from a cluster list.

    Args:
        cluster_items (list): List of package items.

    Returns:
        list: List of dicts with 'package' and either 'tag' or 'digest'.
              Each dict contains 'pull_ref' for the complete crictl pull reference.
    """
    if not cluster_items or not isinstance(cluster_items, list):
        return []

    images = []
    for item in cluster_items:
        if item.get('type') == 'image' and item.get('package'):
            package = item['package']
            image_entry = {'package': package}

            # Digest takes precedence over tag (more specific)
            if item.get('digest'):
                image_entry['digest'] = item['digest']
                image_entry['pull_ref'] = f"{package}@{item['digest']}"
            else:
                tag = item.get('tag', 'latest')
                image_entry['tag'] = tag
                image_entry['pull_ref'] = f"{package}:{tag}"

            images.append(image_entry)

    return images


def collect_additional_images(additional_json_path, software_config, module):
    """
    Collect container images from additional_packages.json.

    Global images (under additional_packages.cluster[]) go to all IMAGE_ROLE_KEYS.
    Role-specific images go only to their specific role.
    Only processes roles that are in allowed_subgroups from software_config.json.

    Args:
        additional_json_path (str): Path to additional_packages.json.
        software_config (dict): Parsed software_config.json content.
        module: Ansible module instance.

    Returns:
        dict: Role-keyed dict of image lists.
    """
    if not is_additional_packages_enabled(software_config):
        return {}

    data = load_json_file(additional_json_path, module)
    if not data:
        return {}

    allowed_subgroups = get_allowed_additional_subgroups(software_config)
    result = {}

    # Extract global images from additional_packages.cluster[]
    additional_packages = data.get('additional_packages', {})
    global_images = extract_images_from_cluster(additional_packages.get('cluster', []))

    # Initialize result dict for allowed IMAGE_ROLE_KEYS with global images
    for role in IMAGE_ROLE_KEYS:
        if role in allowed_subgroups:
            result[role] = list(global_images)

    # Add role-specific images for allowed subgroups
    for role in allowed_subgroups:
        if role in ROLE_SPECIFIC_KEYS and role in data:
            role_data = data.get(role, {})
            role_images = extract_images_from_cluster(role_data.get('cluster', []))

            if role in result:
                result[role].extend(role_images)
            elif role_images:
                result[role] = role_images

    # Deduplicate images in each role while preserving order (using pull_ref)
    for role in result:
        seen = set()
        unique_images = []
        for img in result[role]:
            if img['pull_ref'] not in seen:
                unique_images.append(img)
                seen.add(img['pull_ref'])
        result[role] = unique_images

    return result


def run_module():
    """
    Run the Ansible module.

    Collects container images from additional_packages.json,
    returns a dict keyed by role with image lists for crictl pull.
    """
    module_args = dict(
        additional_json_path=dict(type="str", required=True),
        software_config_path=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        additional_images_dict={}
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    additional_json_path = module.params["additional_json_path"]
    software_config_path = module.params["software_config_path"]

    # Load software_config.json
    software_config = load_json_file(software_config_path, module)

    # Collect images from additional_packages.json
    additional_images = collect_additional_images(
        additional_json_path, software_config, module
    )
    result["additional_images_dict"] = additional_images

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
