import os
import yaml
import subprocess

def load_yaml_file(path):
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
    with open(path, "r") as file:
        return yaml.safe_load(file)

def get_repo_list(config_file, repo_key):
    """
    Retrieve the list of repositories from config using a given key.

    Args:
        config_file (dict): The configuration file data.
        repo_key (str): The key to retrieve the repository list.

    Returns:
        list: The list of repositories.
    """
    return config_file.get(repo_key, [])

def is_file_exists(file_path):
    """
    Check if a file exists at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    return os.path.isfile(file_path)

def is_encrypted(file_path):
    with open(file_path, 'r') as f:
        first_line = f.readline()
    return "$ANSIBLE_VAULT" in first_line

def run_vault_command(command, file_path, vault_key):
    cmd = [
        "ansible-vault",
        command,
        file_path,
        "--vault-password-file", vault_key
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

