#!/usr/bin/python

"""
Ansible module: Generate cluster functional_groups.yaml based on a CSV mapping file.
Always overwrites the YAML file with new data.
"""

import os
import re
import csv
from collections import OrderedDict
import yaml
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: generate_functional_groups
short_description: Generate functional groups from PXE mapping CSV
description:
  - Reads a PXE mapping CSV file and generates a functional_groups YAML configuration file.
  - Classification rules are read from a YAML file instead of hardcoded dicts.
options:
  mapping_file_path:
    description: Path to the PXE mapping CSV file.
    required: true
    type: str
  functional_groups_file_path:
    description: Path to write the functional groups YAML output.
    required: true
    type: str
  omnia_config_path:
    description: Path to the omnia_config.yml file.
    required: true
    type: str
  classification_file_path:
    description: Path to functional_group_classification.yml. When provided, classification rules are read from this file instead of hardcoded dicts.
    required: false
    type: str
    default: null
'''

EXAMPLES = r'''
- name: Generate functional groups from mapping file
  generate_functional_groups:
    mapping_file_path: >-
      {{ omnia_data_path }}/orchestrator/input/{{ project_name }}/pxe_mapping_file.csv
    functional_groups_file_path: >-
      {{ omnia_data_path }}/.data/functional_groups_config.yml
    omnia_config_path: >-
      {{ omnia_data_path }}/orchestrator/input/{{ project_name }}/omnia_config.yml
    classification_file_path: "{{ role_path }}/../../vars/functional_group_classification.yml"
  register: fg_result
'''

RETURN = r'''
functional_groups:
  description: Dictionary of generated functional groups with their node assignments.
  type: dict
  returned: success
categories:
  description: Dictionary of category-to-functional-group mappings.
  type: dict
  returned: success
msg:
  description: Status message.
  type: str
  returned: always
'''

# Legacy hardcoded maps — used as fallback when classification_file_path is not provided.
FUNCTIONAL_GROUP_LAYER_MAP = {
    "service_kube_control_plane_first_x86_64": "management",
    "service_kube_control_plane_x86_64": "management",
    "service_kube_node_x86_64": "management",
    "login_node_x86_64": "management",
    "login_node_aarch64": "management",
    "login_compiler_node_x86_64": "management",
    "login_compiler_node_aarch64": "management",
    "slurm_control_node_x86_64": "management",
    "slurm_node_x86_64": "compute",
    "slurm_node_aarch64": "compute",
    "os_x86_64": "compute",
    "os_aarch64": "compute",
}

DESCRIPTION_MAP = {
    "os": "Minimal OS Node",
    "slurm_control_node": "Slurm Head",
    "slurm_node": "Slurm Worker",
    "login_node": "Login Node",
    "login_compiler_node": "Login Compiler Node",
    "service_kube_control_plane_first": "Kubernetes Control Plane (Primary)",
    "service_kube_control_plane": "Kubernetes Control Plane",
    "service_kube_node": "Kubernetes Worker Node"
}


def load_classification(classification_file_path, module):
    """Load functional group classification rules from YAML file."""
    if not os.path.exists(classification_file_path):
        module.fail_json(msg=f"Classification file not found: {classification_file_path}")
    try:
        with open(classification_file_path, encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return data.get('functional_group_categories', {})
    except Exception as e:
        module.fail_json(msg=f"Failed to load classification file: {str(e)}")


def classify_functional_group(fg_name, categories):
    """Classify a functional group name using pattern-based rules.

    Returns (category_name, layer, description) for the first matching category.
    Unknown FGs fall through to the 'custom' catch-all category.
    """
    for cat_name, cat_config in categories.items():
        patterns = cat_config.get('patterns', [])
        for pattern in patterns:
            if re.match(pattern, fg_name):
                # Determine layer
                layer = cat_config.get('default_layer', 'compute')
                for substring, mapped_layer in cat_config.get('layer_rules', {}).items():
                    if substring in fg_name:
                        layer = mapped_layer
                        break

                # Determine description — match longest prefix first
                desc_map = cat_config.get('description_map', {})
                description = cat_config.get('default_description', fg_name)
                # Sort by key length descending so longer (more specific) prefixes match first
                for prefix in sorted(desc_map.keys(), key=len, reverse=True):
                    if fg_name.startswith(prefix):
                        description = desc_map[prefix]
                        break

                return cat_name, layer, description

    return 'custom', 'compute', 'User-Defined Functional Group'


def get_layer_for_fg(fg_name, categories):
    """Return the layer for a functional group using classification rules."""
    _, layer, _ = classify_functional_group(fg_name, categories)
    return layer


def get_description_for_fg(fg_name, categories):
    """Return the description for a functional group using classification rules."""
    _, _, description = classify_functional_group(fg_name, categories)
    return description

def load_omnia_config(omnia_config_path, module):
    """Load omnia_config.yml and return (kube_name, slurm_name)."""
    if not os.path.exists(omnia_config_path):
        module.fail_json(msg=f"omnia_config.yml not found: {omnia_config_path}")

    try:
        with open(omnia_config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        kube_name = None
        k8s_clusters = config.get("service_k8s_cluster", [])
        if isinstance(k8s_clusters, list) and k8s_clusters:
            for cluster in k8s_clusters:
                if cluster.get("deployment") is True:
                    kube_name = cluster.get("cluster_name")
                    break
            if kube_name is None:
                kube_name = k8s_clusters[0].get("cluster_name")

        slurm_name = None
        slurm_clusters = config.get("slurm_cluster", [])
        if isinstance(slurm_clusters, list) and slurm_clusters:
            slurm_name = slurm_clusters[0].get("cluster_name")

        return kube_name, slurm_name

    except Exception as e:
        error_msg = f"Failed to load omnia_config.yml: {str(e)}"
        module.fail_json(msg=error_msg)


def parse_csv(filename, module, categories=None):
    """Parse CSV file and extract groups and functional groups.

    When categories is provided, all FGs are accepted (classified via patterns).
    When categories is None, only FGs in the legacy FUNCTIONAL_GROUP_LAYER_MAP are accepted.
    """
    groups = {}
    functional_groups = {}
    kube_control_seen = False

    try:
        with open(filename, newline="", encoding="utf-8") as f:
            cleaned_lines = [line.strip() for line in f if line.strip()]
            header = cleaned_lines[0].split(",")
            expected_columns = len(header)
            valid_lines = [
                line for line in cleaned_lines if len(line.split(",")) == expected_columns
            ]

            reader = csv.DictReader(valid_lines)

            for row in reader:
                func_group = row["FUNCTIONAL_GROUP_NAME"].strip()
                group_name = row["GROUP_NAME"].strip()
                parent = row.get("PARENT_SERVICE_TAG", "").strip() or ""

                if func_group == "service_kube_control_plane_x86_64" and not kube_control_seen:
                    func_group = "service_kube_control_plane_first_x86_64"
                    kube_control_seen = True

                groups[group_name] = {"parent": parent}

                if categories is not None:
                    # Data-driven: accept all FGs (they will be classified by pattern)
                    functional_groups.setdefault(func_group, set()).add(group_name)
                else:
                    # Legacy: only accept FGs in the hardcoded map
                    if func_group in FUNCTIONAL_GROUP_LAYER_MAP:
                        functional_groups.setdefault(func_group, set()).add(group_name)

        return groups, functional_groups

    except Exception as e:
        error_msg = f"Error parsing CSV file: {str(e)}"
        module.fail_json(msg=error_msg)

def build_yaml(new_groups, new_func_groups, kube_cluster_name, slurm_cluster_name,
               categories=None):
    """Build YAML structure with groups and functional groups.

    When categories is provided, layer and description are resolved via
    pattern-based classification. Otherwise, the legacy hardcoded maps are used.
    """
    data = OrderedDict({"groups": OrderedDict(), "functional_groups": []})

    # Add groups
    for grp, details in new_groups.items():
        data["groups"][grp] = details

    # Add functional groups
    for func_group, group_list in new_func_groups.items():
        if categories is not None:
            category, layer, description = classify_functional_group(func_group, categories)
        else:
            layer = FUNCTIONAL_GROUP_LAYER_MAP.get(func_group, "compute")
            desc_key = next((k for k in DESCRIPTION_MAP if func_group.startswith(k)), func_group)
            description = DESCRIPTION_MAP.get(desc_key, func_group)
            category = None

        fg_lower = func_group.lower()
        # get appropriate cluster name
        cluster_name = (
            kube_cluster_name
            if "kube" in fg_lower
            else slurm_cluster_name or "slurm_cluster"
        )

        entry = OrderedDict({
            "name": func_group,
            "cluster_name": cluster_name,
            "group": sorted(list(group_list)),
            "_comment": [
                f"{description} functional_groups:",
                f"This functional_group is used to configure the nodes for {description}. "
                f"It belongs to the {layer} layer.",
                f"The nodes included in this functional_group will have the necessary tools "
                f"and configurations to run {description}.",
                f"The nodes in this functional_group can be used to run {description}."
            ]
        })
        if category is not None:
            entry["category"] = category
            entry["layer"] = layer
        data["functional_groups"].append(entry)

    return data

def dump_yaml_with_comments(data, filename):
    """Write YAML data to file with custom formatting and comments."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# ---------------------------------------------------------------------------\n")
        f.write("# Groups definition\n")
        f.write("# ---------------------------------------------------------------------------\n")
        f.write("groups:\n")
        for g in sorted(data["groups"].keys()):
            d = data["groups"][g]
            f.write(f"  {g}:\n")
            f.write(f"    parent: \"{d['parent']}\"\n")

        f.write("\n# -------------------------------------------------------------------------\n")
        f.write("# Functional Groups definition\n")
        f.write("# ---------------------------------------------------------------------------\n")
        f.write("functional_groups:\n")
        for fg in data.get("functional_groups") or []:
            for comment in fg.get("_comment", []):
                f.write(f"  # {comment}\n")
            f.write(f"  - name: \"{fg['name']}\"\n")
            f.write(f"    cluster_name: \"{fg['cluster_name']}\"\n")
            f.write(f"    group:\n")
            for g in sorted(set(fg["group"])):
                f.write(f"      - {g}\n")
            f.write("\n")

def main():
    """Initialize Ansible module for generating functional groups."""
    module_args = {
        "mapping_file_path": {"type": "str", "required": True},
        "functional_groups_file_path": {"type": "str", "required": True},
        "omnia_config_path": {"type": "str", "required": True},
        "classification_file_path": {"type": "str", "required": False, "default": None},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    mapping_file_path = module.params["mapping_file_path"]
    functional_groups_file_path = module.params["functional_groups_file_path"]
    omnia_config_path = module.params["omnia_config_path"]
    classification_file_path = module.params["classification_file_path"]

    try:
        if not os.path.exists(mapping_file_path):
            module.fail_json(msg=f"CSV file not found: {mapping_file_path}")

        # Load classification rules (data-driven) or fall back to hardcoded maps
        categories = None
        if classification_file_path:
            categories = load_classification(classification_file_path, module)

        kube_cluster_name, slurm_cluster_name = load_omnia_config(omnia_config_path, module)
        new_groups, new_func_groups = parse_csv(mapping_file_path, module, categories)

        # Always overwrite: build fresh YAML
        yaml_data = build_yaml(new_groups, new_func_groups, kube_cluster_name,
                               slurm_cluster_name, categories)
        dump_yaml_with_comments(yaml_data, functional_groups_file_path)

        module.exit_json(
            changed=True,
            msg=f"functional_groups_config.yml file overwritten: {functional_groups_file_path}",
            added_groups=list(new_groups.keys()),
            added_functional_groups=list(new_func_groups.keys())
        )

    except Exception as e:
        error_msg = f"Error while generating functional groups YAML: {str(e)}"
        module.fail_json(msg=error_msg)

if __name__ == "__main__":
    main()
