#!/usr/bin/python

"""
Ansible module: Generate cluster functional_groups.yaml based on a CSV mapping file.
Always overwrites the YAML file with new data.
"""

import os
import csv
from collections import OrderedDict
import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.input_validation.common_utils import config

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

def load_omnia_config(omnia_config_path, module):
    """Load omnia_config.yml and return (kube_name, slurm_name)."""
    if not os.path.exists(omnia_config_path):
        module.fail_json(msg=f"omnia_config.yml not found: {omnia_config_path}")

    try:
        with open(omnia_config_path) as f:
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


def parse_csv(filename, module):
    """Parse CSV file and extract groups and functional groups."""
    groups = {}
    functional_groups = {}
    kube_control_seen = False

    try:
        with open(filename, newline="") as f:
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
                if func_group in config.FUNCTIONAL_GROUP_LAYER_MAP:
                    functional_groups.setdefault(func_group, set()).add(group_name)

        return groups, functional_groups

    except Exception as e:
        error_msg = f"Error parsing CSV file: {str(e)}"
        module.fail_json(msg=error_msg)

def build_yaml(new_groups, new_func_groups, kube_cluster_name, slurm_cluster_name):
    """Build YAML structure with groups and functional groups."""
    data = OrderedDict({"groups": OrderedDict(), "functional_groups": []})

    # Add groups
    for grp, details in new_groups.items():
        data["groups"][grp] = details

    # Add functional groups
    for func_group, group_list in new_func_groups.items():
        layer = config.FUNCTIONAL_GROUP_LAYER_MAP[func_group]
        fg_lower = func_group.lower()
        # get appropriate cluster name
        cluster_name = (
            kube_cluster_name
            if "kube" in fg_lower
            else slurm_cluster_name or "slurm_cluster"
        )

        desc_key = next((k for k in DESCRIPTION_MAP if func_group.startswith(k)), func_group)
        description = DESCRIPTION_MAP.get(desc_key, func_group)

        new_entry = OrderedDict({
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
        data["functional_groups"].append(new_entry)

    return data

def dump_yaml_with_comments(data, filename):
    """Write YAML data to file with custom formatting and comments."""
    with open(filename, "w") as f:
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
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    mapping_file_path = module.params["mapping_file_path"]
    functional_groups_file_path = module.params["functional_groups_file_path"]
    omnia_config_path = module.params["omnia_config_path"]

    try:
        if not os.path.exists(mapping_file_path):
            module.fail_json(msg=f"CSV file not found: {mapping_file_path}")

        kube_cluster_name, slurm_cluster_name = load_omnia_config(omnia_config_path, module)
        new_groups, new_func_groups = parse_csv(mapping_file_path, module)

        # Always overwrite: build fresh YAML
        yaml_data = build_yaml(new_groups, new_func_groups, kube_cluster_name, slurm_cluster_name)
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
