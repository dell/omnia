import requests
from ansible.module_utils.local_repo.common_functions import is_file_exists

def validate_user_registry(user_registry):
    """
    Validates a user registry by checking if each item is a dictionary and contains 'host' and 'cert_path' keys.
    
    Args:
        user_registry (list): A list of dictionaries representing user registry entries.
    
    Returns:
        tuple: A boolean indicating whether the user registry is valid, and a string describing any errors encountered.
    """
    for item in user_registry:
        if not isinstance(item, dict):
            return False, "Each item in user_registry must be a dictionary."
        if not item.get('host'):
            return False, f"Missing or empty 'host' in entry: {item}"
        if not item.get('cert_path'):
            return False, f"Missing 'cert_path' in entry: {item}"
    return True, ""

def check_reachability(user_registry, timeout):
    """
    Checks the reachability of hosts in the user registry.

    Args:
        user_registry (list): A list of dictionaries representing user registry entries.
        timeout (int): The maximum number of seconds to wait for a response.

    Returns:
        tuple: A tuple containing two lists: reachable hosts and unreachable hosts.
    """
    reachable, unreachable = [], []
    for item in user_registry:
        try:
            resp = requests.get(f"https://{item['host']}", timeout=timeout, verify=False)
            if resp.status_code == 200:
                reachable.append(item['host'])
            else:
                unreachable.append(item['host'])
        except Exception:
            unreachable.append(item['host'])
    return reachable, unreachable

def find_invalid_cert_paths(user_registry):
    """
    Finds and returns a list of invalid certificate paths in the given user registry.

    Args:
        user_registry (list): A list of dictionaries representing user registry entries.

    Returns:
        list: A list of invalid certificate paths.
    """
    return [
        item['cert_path'] for item in user_registry
        if item.get('cert_path') and not is_file_exists(item['cert_path'])
    ]

