import os
import yaml
from ansible.module_utils.local_repo.common_functions import (
    load_yaml_file,
    get_repo_list,
)

def get_pem_files(repo_cert_path):
    """
	Retrieves a list of .pem files from a specified repository certificate path.

	Parameters:
		repo_cert_path (str): The path to the repository certificates.

	Returns:
		list: A list of .pem file names if the directory exists, otherwise None.
	"""
    if not os.path.isdir(repo_cert_path):
        return None  # Explicitly indicate missing directory
    return [f for f in os.listdir(repo_cert_path) if f.endswith(".pem")]

def validate_repo_certificates(repo_list, certs_path):
    """
	Validates the repository certificates based on the provided repository list and certificate path.

	Parameters:
		repo_list (list): A list of dictionaries containing repository information.
		certs_path (str): The path to the repository certificates.

	Returns:
		list: A list of strings describing certificate issues for each repository.
	"""

    cert_issues = []

    if not repo_list:
        return cert_issues

    for repo in repo_list:
        repo_name = repo.get("name", "unnamed_repo")
        repo_cert_path = os.path.join(certs_path, repo_name)

        cert_keys = ["sslcacert", "sslclientkey", "sslclientcert"]
        cert_values = {key: repo.get(key) for key in cert_keys}

        # # Skip if all cert values are None, No cert scenario
        if all(value is None for value in cert_values.values()):
            continue

        if not os.path.isdir(repo_cert_path):
            cert_issues.append(f"{repo_name} (certificate path not found)")
            continue

        all_files = os.listdir(repo_cert_path)
        pem_files = [f for f in all_files if f.endswith(".pem")]
        key_files = [f for f in all_files if f.endswith(".key")]
        crt_files = [f for f in all_files if f.endswith(".crt")]

        issues = []

        if len(pem_files) != 3:
            issues.append(f"{len(pem_files)} .pem files found: {pem_files}")
        if len(key_files) > 1:
            issues.append(f"{len(key_files)} .key files found: {key_files}")
        if len(crt_files) > 1:
            issues.append(f"{len(crt_files)} .crt files found: {crt_files}")

        if issues:
            cert_issues.append(f"{repo_name} ({'; '.join(issues)})")

    return cert_issues


def validate_certificates(local_repo_config_path, certs_path, repo_key="user_repo_url"):
    """
	Validates the repository certificates based on the provided repository list and certificate path.

	Parameters:
		local_repo_config_path (str): The path to the local repository configuration file.
		certs_path (str): The path to the repository certificates.
		repo_key (str): The key to access the repository list in the configuration file (default: "user_repo_url").

	Returns:
		dict: A dictionary containing the validation status and a list of issues if any.
	"""

    config_file = load_yaml_file(local_repo_config_path)
    repo_list = get_repo_list(config_file, repo_key)

    issues = validate_repo_certificates(repo_list, certs_path)

    if issues:
        return {"status": "error", "missing": issues}

    return {"status": "ok"}


