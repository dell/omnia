import os
from datetime import datetime
import yaml
from ansible.module_utils.basic import AnsibleModule

TELEMETRY_CONFIG_PATH_DEFAULT = "/opt/omnia/input/project_default/telemetry_config.yml"

def load_yaml(path):
    """
    Load YAML from a given file path.

    Args:
        path (str): The path to the YAML file.

    Returns:
        dict: The loaded YAML data.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding = "utf-8") as file:
        return yaml.safe_load(file)

def main():
    module_args = {
        "telemetry_config_path": {"type": "str", "required": False, "default": TELEMETRY_CONFIG_PATH_DEFAULT}
    }
    module = AnsibleModule(argument_spec=module_args)
    telemetry_config_path = module.params["telemetry_config_path"]
    telemetry_config_data = load_yaml(telemetry_config_path)

    telemetry_status_list = []

    if telemetry_config_data["idrac_telemetry_support"]:
        telemetry_status_list.append("idrac_telemetry")
    #if telemetry_config_data["visualization_support"]:
    #    telemetry_status_dict.append("visualization")

    module.exit_json(
            changed=False,
            telemetry_status_list=telemetry_status_list
    )


if __name__ == "__main__":
    main()
