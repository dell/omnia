#!/usr/bin/python

import os
import json
import yaml

from ansible.module_utils.basic import AnsibleModule

def load_yaml_file(path, module):
    """
    Load a YAML file safely.

    Args:
        path (str): Path to the YAML file.
        module (AnsibleModule): The Ansible module instance, used for error reporting.

    Returns:
        dict: Parsed YAML content.

    Raises:
        Fails the module if the file cannot be read or parsed.
    """
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        module.fail_json(msg=f"Failed to read YAML file {path}: {e}")


def load_json_file(path, module):
    """
    Load a JSON file safely.

    Args:
        path (str): Path to the JSON file.
        module (AnsibleModule): The Ansible module instance, used for logging errors.

    Returns:
        dict or None: Parsed JSON content if successful, otherwise None.
    """
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        module.log(f"Failed to read JSON file {path}: {e}")
        return None


def collect_packages_from_json(sw_data, fg_name=None, slurm_defined=False, service_k8s_defined=False):
    """
    Collect RPM package names from a JSON-like dictionary of software data.

    Parameters
    ----------
    sw_data : dict
        The software JSON structure, containing sections such as "slurm_custom",
        "login_node", or a top-level "cluster".
    fg_name : str, optional
        The functional group name (e.g., "compute_x86_64"). If slurm_defined=True,
        this will be normalized (suffixes "_aarch64" and "_x86_64" are removed)
        and used to look up group-specific cluster entries.
    slurm_defined : bool, default=False
        If True:
          - Always collect packages from the top-level "slurm_custom/cluster".
          - Additionally, collect packages from the functional group cluster
            matching `fg_name`.
        If False:
          - Collect packages from all nested "cluster" sections.
          - Collect packages from a top-level "cluster" if present.

    Returns
    -------
    list of str
        A flat list of RPM package names extracted from the JSON structure.
    """

    packages = []
    if slurm_defined:
        fg_name = fg_name.replace("_aarch64", "").replace("_x86_64", "")

        # Always collect from top-level "slurm_custom" section
        if "slurm_custom" in sw_data and "cluster" in sw_data["slurm_custom"]:
            for entry in sw_data["slurm_custom"]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

        # Collect from matching functional group inside slurm_custom.json
        if fg_name in sw_data and "cluster" in sw_data[fg_name]:
            for entry in sw_data[fg_name]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])
    
    elif service_k8s_defined:
        fg_name = fg_name.replace("_aarch64", "").replace("_x86_64", "")

        # Always collect from top-level "service_k8s" section
        if "service_k8s" in sw_data and "cluster" in sw_data["service_k8s"]:
            for entry in sw_data["service_k8s"]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

        # Collect from matching functional group inside service_k8s
        if fg_name in sw_data and "cluster" in sw_data[fg_name]:
            for entry in sw_data[fg_name]["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

    else:
        # Case 1: nested sections like "slurm_custom", "login_node", etc.
        for section, section_data in sw_data.items():
            if isinstance(section_data, dict) and "cluster" in section_data:
                for entry in section_data["cluster"]:
                    if entry.get("type") == "rpm" and "package" in entry:
                        packages.append(entry["package"])

        # Case 2: "cluster" directly at the top level
        if "cluster" in sw_data and isinstance(sw_data["cluster"], list):
            for entry in sw_data["cluster"]:
                if entry.get("type") == "rpm" and "package" in entry:
                    packages.append(entry["package"])

    return packages


def process_functional_group(fg_name, base_name, arch, os_version, input_project_dir,
                             software_map, allowed_softwares, module):
    """
    Process a functional group and collect the list of required packages.

    This function scans the `config/{arch}/rhel/{os_version}` directory for JSON
    definitions corresponding to the given functional group, filters them based on
    the allowed software list, and extracts package names from those JSON files.

    Args:
        fg_name (str): Functional group name (e.g., "slurm_node_x86_64").
        base_name (str): Base image or role name (not directly used in this function).
        arch (str): Target architecture (e.g., "x86_64").
        os_version (str): OS version (e.g., "9.3").
        input_project_dir (str): Base project directory containing configuration files.
        software_map (dict): Mapping of functional groups to lists of software JSON files.
        allowed_softwares (list): List of software names allowed for this build.
        module (object): Ansible module (or compatible) used for logging.

    Returns:
        list: A deduplicated list of package names required by the functional group,
              preserving the original order of appearance.
    """
    group_path = os.path.join(input_project_dir, "config", arch, "rhel", os_version)
    if not os.path.isdir(group_path):
        module.log(f"Directory not found: {group_path}")
        return []

    json_files = software_map.get(fg_name, [])
    packages = []

    for json_file in json_files:
        # only include if its base name is in allowed_softwares
        sw_name = json_file.replace(".json", "")
        if sw_name not in allowed_softwares:
            continue

        sw_path = os.path.join(group_path, json_file)
        if not os.path.isfile(sw_path):
            module.log(f"File not found: {sw_path}")
            continue

        sw_data = load_json_file(sw_path, module)
        if not sw_data:
            continue

        # pylint: disable=line-too-long
        # Special handling for slurm_custom.json
        if json_file == "slurm_custom.json":
            packages.extend(collect_packages_from_json(sw_data, fg_name=fg_name, slurm_defined=True))
        elif json_file == "service_k8s.json":
            packages.extend(collect_packages_from_json(sw_data, fg_name=fg_name, service_k8s_defined=True))
        else:
            packages.extend(collect_packages_from_json(sw_data))

    # Deduplicate while preserving order
    seen = set()
    unique_packages = []
    for pkg in packages:
        if pkg not in seen:
            unique_packages.append(pkg)
            seen.add(pkg)

    return unique_packages


def run_module():
    """
    Run the Ansible module.

    This function:
    - Parses arguments for functional group and software configuration files.
    - Loads YAML and JSON configuration files.
    - Iterates over functional groups to determine required packages.
    - Produces a mapping (`compute_images_dict`) of groups to packages.
    - Exits cleanly with results or fails with an error.
    """

    module_args = dict(
        functional_groups_file=dict(type="str", required=True),
        software_config_file=dict(type="str", required=True),
        input_project_dir=dict(type="str", required=True),
    )

    result = dict(changed=False, compute_images_dict={})
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    functional_groups_file = module.params["functional_groups_file"]
    software_config_file = module.params["software_config_file"]
    input_project_dir = module.params["input_project_dir"]

    # Load configs
    functional_groups = load_yaml_file(functional_groups_file, module)
    software_config = load_json_file(software_config_file, module)

    os_version = software_config.get("cluster_os_version") if software_config else None
    if not os_version:
        module.fail_json(msg="cluster_os_version not found in software_config.json")

    # Build list of allowed softwares (from software_config.json)
    allowed_softwares = {sw["name"] for sw in software_config.get("softwares", [])}

    # pylint: disable=line-too-long
    # Functional group → json files mapping
    software_map = {
        "default_x86_64": ["nfs.json", "openldap.json"],
        "service_kube_node_x86_64": ["service_k8s.json", "nfs.json"],
        "service_kube_control_plane_first_x86_64": ["service_k8s.json", "nfs.json"],
        "service_kube_control_plane_x86_64": ["service_k8s.json", "nfs.json"],
        "slurm_control_node_x86_64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"],
        "slurm_node_x86_64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"],
        "login_node_x86_64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"],
        "login_compiler_node_x86_64": ["slurm_custom.json", "nfs.json", "openldap.json", "ucx.json", "openmpi.json","ldms.json"],
        "slurm_node_aarch64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"],
        "login_node_aarch64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"],
        "login_compiler_node_aarch64": ["slurm_custom.json", "nfs.json", "openldap.json","ldms.json"]
    }

    compute_images_dict = {}

    for fg in functional_groups.get("functional_groups", []):
        fg_name = fg.get("name") if isinstance(fg, dict) else str(fg)

        # Detect arch + base_name
        if fg_name.endswith("_x86_64"):
            base_name = fg_name.replace("_x86_64", "")
            arch = "x86_64"
        elif fg_name.endswith("_aarch64"):
            base_name = fg_name.replace("_aarch64", "")
            arch = "aarch64"
        else:
            base_name = fg_name
            arch = "x86_64"

        packages = process_functional_group(
            fg_name, base_name, arch, os_version, input_project_dir,
            software_map, allowed_softwares, module
        )

        compute_images_dict[fg_name] = {
            "functional_group": fg_name,
            "packages": packages
        }

    result["compute_images_dict"] = compute_images_dict
    module.exit_json(**result)


def main():
    """
    Main entry point of the module.

    This function calls the run_module function to execute the module's logic.
    """
    run_module()


if __name__ == "__main__":
    main()
