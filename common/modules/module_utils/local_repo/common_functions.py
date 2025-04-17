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

def decrypt_certificate(cert_path, vault_password_file):
    """
    Decrypts the given certificate file using Ansible Vault.

    Args:
        cert_path (str): The path to the certificate file.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        int: 1 if successful, 0 if failed.
    """
    if not os.path.exists(cert_path):
        return 0

    try:
        subprocess.run(
            ["ansible-vault", "decrypt", cert_path, "--vault-password-file", vault_password_file],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return 1
    except subprocess.CalledProcessError:
        return 0

def encrypt_certificate(cert_path, vault_password_file):
    """
    Encrypts the given certificate file using Ansible Vault.

    Args:
        cert_path (str): The path to the certificate file.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        int: 1 if successful, 0 if failed.
    """
    if not os.path.exists(cert_path):
        return 0

    try:
        subprocess.run(
            ["ansible-vault", "encrypt", cert_path, "--vault-password-file", vault_password_file],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return 1
    except subprocess.CalledProcessError:
        return 0
