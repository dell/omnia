"""Configuration file generators for wizard data.
Each generator function creates a specific YAML configuration file from wizard data.
"""

import copy
import csv
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Callable

from ..config.defaults import (
    get_build_stream_config_defaults,
    get_discovery_config_defaults,
    get_telemetry_config_defaults,
    get_telemetry_storage_config_defaults,
)


logger = logging.getLogger(__name__)

# Optional repo fields that should be omitted when empty
OPTIONAL_REPO_FIELDS = {'policy', 'caching', 'sslcacert', 'sslclientkey', 'sslclientcert'}

# RHEL repo keys for generate_local_repo_config
_RHEL_REPO_KEYS = (
    "rhel_os_url_x86_64", "rhel_os_url_aarch64",
    "omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64",
    "rhel_subscription_repo_config_x86_64", "rhel_subscription_repo_config_aarch64",
    "additional_repos_x86_64", "additional_repos_aarch64",
)

# PXE CSV header columns
_PXE_CSV_COLUMNS = (
    "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG",
    "PARENT_SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP",
    "BMC_MAC", "BMC_IP", "IB_NIC_NAME", "IB_IP",
)


def _yaml_escape(value: str) -> str:
    """Escape a string for safe YAML double-quoted output."""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def format_repo_entry(item: dict) -> str:
    """Format a repo entry as inline YAML, omitting empty optional fields."""
    parts = []
    for k, v in item.items():
        # Skip empty optional fields
        if k in OPTIONAL_REPO_FIELDS and (v is None or v == ''):
            continue
        # Format value
        if isinstance(v, bool):
            parts.append(f'{k}: {str(v).lower()}')
        elif isinstance(v, str) and v != '':
            parts.append(f'{k}: "{_yaml_escape(v)}"')
        elif v == '':
            parts.append(f'{k}: ""')
        else:
            parts.append(f'{k}: "{_yaml_escape(str(v))}"')
    return f"{{{', '.join(parts)}}}"


def has_meaningful_data(data: Any) -> bool:
    """Check if data has any non-empty, non-default values.

    Returns True if:
    - Non-empty list with at least one item
    - Non-empty string
    - Any number (including 0)
    - True boolean
    - Nested dict with meaningful data
    """
    if data is None:
        return False
    if isinstance(data, dict):
        for key, value in data.items():
            if has_meaningful_data(value):
                return True
        return False
    elif isinstance(data, list):
        for item in data:
            if has_meaningful_data(item):
                return True
        return False
    elif isinstance(data, bool):
        return data
    elif isinstance(data, (int, float)):
        return True  # Treat 0 as meaningful (port 0, timeout 0, etc.)
    elif isinstance(data, str):
        return len(data.strip()) > 0
    return False


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Recursively merge override into base.

    Values from override win. Existing keys in base that are not present in
    override are preserved.
    """
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _flatten_csm_metrics_powerscale_storage(config: Dict[str, Any]) -> None:
    """Flatten csm_metrics_powerscale_storage if the frontend sends a resources wrapper.

    The reference YAML and backend schema expect requests/limits directly under
    csm_metrics_powerscale_storage, while the frontend form uses a resources
    wrapper for UI consistency. This normalization merges the resources block
    into the top-level section and removes the wrapper.
    """
    section = config.get("csm_metrics_powerscale_storage")
    if not isinstance(section, dict) or "resources" not in section:
        return
    resources = section.pop("resources")
    if not isinstance(resources, dict):
        return
    for key, value in resources.items():
        if isinstance(value, dict) and isinstance(section.get(key), dict):
            section[key].update(value)
        else:
            section[key] = value


def generate_omnia_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate omnia_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    omnia_config = {}
    
    # Only include slurm_cluster if it has meaningful data
    slurm_clusters = wizard_data.get("slurm_cluster", [])
    slurm_meaningful = any(
        cluster.get("cluster_name") and len(str(cluster.get("cluster_name", "")).strip()) > 0
        for cluster in slurm_clusters if isinstance(cluster, dict)
    )
    if slurm_meaningful:
        omnia_config["slurm_cluster"] = slurm_clusters
    
    # Only include service_k8s_cluster if it has meaningful data
    k8s_clusters = wizard_data.get("service_k8s_cluster", [])
    k8s_meaningful = any(
        cluster.get("cluster_name") and len(str(cluster.get("cluster_name", "")).strip()) > 0 and
        cluster.get("deployment") is not None and cluster.get("deployment") != ""
        for cluster in k8s_clusters if isinstance(cluster, dict)
    )
    if k8s_meaningful:
        omnia_config["service_k8s_cluster"] = k8s_clusters

    if omnia_config:
        _write_config_file(input_dir / "omnia_config.yml", omnia_config, quote_all_strings=True)


def generate_network_spec(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate network_spec.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    networks = wizard_data.get("Networks", [])

    # Only generate if networks has meaningful data
    if has_meaningful_data(networks):
        # Filter out empty network entries
        filtered_networks = []
        for network in networks:
            if isinstance(network, dict) and has_meaningful_data(network):
                # IB network is optional; skip if no subnet is configured
                if network.get('ib_network'):
                    ib_subnet = str(network['ib_network'].get('subnet', '')).strip()
                    if not ib_subnet:
                        continue
                filtered_networks.append(network)

        if filtered_networks:
            _write_config_file(
                input_dir / "network_spec.yml",
                {"Networks": filtered_networks},
                quote_all_strings=True
            )
        else:
            logger.info("Skipped network_spec.yml (no meaningful network data)")
    else:
        logger.info("Skipped network_spec.yml (no meaningful data)")


def _convert_string_bools_to_bools(data: Any) -> Any:
    """Recursively convert string boolean values to actual boolean types."""
    if isinstance(data, dict):
        return {k: _convert_string_bools_to_bools(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_string_bools_to_bools(item) for item in data]
    elif isinstance(data, str):
        if data.lower() in ('true', 'yes', 'on'):
            return True
        elif data.lower() in ('false', 'no', 'off'):
            return False
        return data
    return data


def _clean_storage_entries(
    entries: list,
    required_key: str,
    array_fields: set,
    skip_fn: Callable[[str, dict], bool] = lambda k, e: False,
) -> list:
    """Clean and filter storage config entries.

    Args:
        entries: List of entry dicts to clean
        required_key: Key that must be present for entry to be included
        array_fields: Set of keys whose string values should be split on commas
        skip_fn: Optional function to skip certain fields based on key and entry

    Returns:
        List of cleaned entry dicts
    """
    result = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get(required_key):
            continue
        cleaned = {}
        for k, v in entry.items():
            if v is None or v == '' or v == [] or v == {}:
                continue
            if skip_fn(k, entry):
                continue
            if k in array_fields and isinstance(v, str):
                v = [x.strip() for x in v.split(',')]
            cleaned[k] = v
        result.append(cleaned)
    return result


def _write_config_file(
    path: Path,
    config: Dict[str, Any],
    quote_all_strings: bool = False,
    preserve_octal_mode: bool = False,
) -> None:
    """Write a config dict to a YAML file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            f.write(f"{key}:")
            if isinstance(value, dict) and not value:
                f.write(" {}\n")
            elif isinstance(value, (list, dict)):
                f.write("\n")
                _write_yaml_value(f, value, 1, quote_all_strings, preserve_octal_mode)
            else:
                f.write(" ")
                _write_yaml_value(f, value, 0, quote_all_strings, preserve_octal_mode)
    logger.info("Generated %s", path.name)


def _should_quote_string(value: str) -> bool:
    """Determine if a string value should be quoted based on content."""
    if value == "":
        return True
    # Quote YAML boolean-like strings
    if value.lower() in ('true', 'false', 'yes', 'no', 'on', 'off', 'null'):
        return True
    # Quote if contains special characters
    if any(char in value for char in ['/', '-', ':', '.', ' ', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '>', '!', '%', '@', '`']):
        return True
    # Quote if looks like a number but is a string
    if value.replace('.', '').replace('-', '').isdigit():
        return True
    # Quote storage sizes with units (Gi, Mi, Ki, Ti, G, M, K, T, GB, MB, KB, TB)
    if any(value.endswith(unit) for unit in ['Gi', 'Mi', 'Ki', 'Ti', 'G', 'M', 'K', 'T', 'GB', 'MB', 'KB', 'TB', 'm']):
        return True
    return False


def _write_yaml_value(f, value, indent, quote_all_strings=False, preserve_octal_mode=False):
    """Recursively write YAML value with proper indentation and quoting."""
    indent_str = "  " * indent
    if value is None:
        f.write(f'{indent_str}""\n')
    elif isinstance(value, bool):
        f.write(f"{indent_str}{str(value).lower()}\n")
    elif isinstance(value, int) or isinstance(value, float):
        f.write(f"{indent_str}{value}\n")
    elif isinstance(value, str):
        # Handle multi-line strings with block scalar
        if '\n' in value or value.startswith('|'):
            # Strip YAML block scalar indicator if user included it
            clean_value = value
            if clean_value.startswith('|'):
                clean_value = clean_value[1:]  # remove leading |
            clean_value = clean_value.strip('\n')  # remove leading/trailing newlines
            
            f.write(f"{indent_str}|\n")
            for line in clean_value.split('\n'):
                # Preserve relative indentation but add base indent
                stripped = line.rstrip()
                if stripped:
                    f.write(f"{indent_str}  {stripped}\n")
                else:
                    f.write("\n")  # empty line in block scalar
            return
        # Try to coerce numeric strings to numbers before quoting
        # NOTE: Intentional type coercion — numeric strings from the UI are written
        # as YAML integers/floats to match reference file format. If this causes
        # issues, set quote_all_strings=True for the affected config.
        # Skip coercion for:
        # 1. Octal mode values (preserve_octal_mode flag) - "0755" format
        # 2. Strings that are all digits but start with '0' - likely octal/permissions
        # 3. Single digit strings that should stay as strings (dump_freq, fsck_pass)
        should_preserve_string = (
            preserve_octal_mode or
            (value.startswith('0') and value.isdigit() and len(value) > 1) or
            (value.isdigit() and len(value) == 1)
        )
        if not quote_all_strings and not should_preserve_string:
            try:
                num = int(value)
                f.write(f"{indent_str}{num}\n")
                return
            except ValueError:
                try:
                    num = float(value)
                    f.write(f"{indent_str}{num}\n")
                    return
                except ValueError:
                    pass
        if quote_all_strings or _should_quote_string(value):
            # Use _yaml_escape for proper backslash and quote escaping
            escaped = _yaml_escape(value)
            f.write(f'{indent_str}"{escaped}"\n')
        else:
            f.write(f"{indent_str}{value}\n")
    elif isinstance(value, list):
        if not value:
            f.write(f"{indent_str}[]\n")
        else:
            for item in value:
                if isinstance(item, dict):
                    f.write(f"{indent_str}-")
                    first_key = True
                    for k, v in item.items():
                        if first_key:
                            f.write(f" {k}:")
                            first_key = False
                        else:
                            f.write(f"{indent_str}  {k}:")
                        if isinstance(v, (list, dict)):
                            f.write("\n")
                            _write_yaml_value(f, v, indent + 2, quote_all_strings, preserve_octal_mode)
                        else:
                            f.write(" ")
                            _write_yaml_value(f, v, 0, quote_all_strings, preserve_octal_mode)
                else:
                    f.write(f"{indent_str}- ")
                    _write_yaml_value(f, item, 0, quote_all_strings, preserve_octal_mode)
    elif isinstance(value, dict):
        if not value:
            f.write(f"{indent_str}{{}}\n")
        else:
            for k, v in value.items():
                f.write(f"{indent_str}{k}:")
                if isinstance(v, (list, dict)):
                    f.write("\n")
                    _write_yaml_value(f, v, indent + 1, quote_all_strings, preserve_octal_mode)
                else:
                    f.write(" ")
                    _write_yaml_value(f, v, 0, quote_all_strings, preserve_octal_mode)


def generate_gitlab_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate gitlab_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    gitlab_host = wizard_data.get("gitlab_host", "")
    if not has_meaningful_data(gitlab_host):
        logger.info("Skipped gitlab_config.yml (gitlab not enabled)")
        return
    
    gitlab_config = {
        "gitlab_host": gitlab_host,
        "gitlab_project_name": wizard_data.get("gitlab_project_name", ""),
        "gitlab_project_visibility": wizard_data.get("gitlab_project_visibility", "private"),
        "gitlab_default_branch": wizard_data.get("gitlab_default_branch", "main"),
        "gitlab_https_port": wizard_data.get("gitlab_https_port", 443),
        "gitlab_min_storage_gb": wizard_data.get("gitlab_min_storage_gb", 20),
        "gitlab_min_memory_gb": wizard_data.get("gitlab_min_memory_gb", 4),
        "gitlab_min_cpu_cores": wizard_data.get("gitlab_min_cpu_cores", 2),
        "gitlab_puma_workers": wizard_data.get("gitlab_puma_workers", 2),
        "gitlab_sidekiq_concurrency": wizard_data.get("gitlab_sidekiq_concurrency", 10),
    }

    _write_config_file(input_dir / "gitlab_config.yml", gitlab_config, quote_all_strings=True)


def generate_build_stream_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate build_stream_config.yml from wizard data.

    Always emitted; when build stream is not enabled, a disabled default
    configuration is written.
    """
    build_stream_config = copy.deepcopy(get_build_stream_config_defaults())
    user_data = {
        k: v
        for k, v in wizard_data.items()
        if k in build_stream_config and v is not None
    }
    _deep_merge(build_stream_config, user_data)
    _write_config_file(input_dir / "build_stream_config.yml", build_stream_config, quote_all_strings=True)


def generate_discovery_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate discovery_config.yml from wizard data.

    Always emitted; when BMC discovery is not enabled, a disabled default
    configuration is written.
    """
    discovery_config = copy.deepcopy(get_discovery_config_defaults())
    user_data = {
        k: v
        for k, v in wizard_data.items()
        if k in discovery_config and v is not None
    }
    _deep_merge(discovery_config, user_data)
    _write_config_file(input_dir / "discovery_config.yml", discovery_config, quote_all_strings=False)


def generate_high_availability_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate high_availability_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    # Only generate the HA config when Kubernetes is part of the selected cluster type
    k8s_clusters = wizard_data.get("service_k8s_cluster", [])
    k8s_selected = any(
        isinstance(cluster, dict)
        and cluster.get("cluster_name")
        and len(str(cluster.get("cluster_name", "")).strip()) > 0
        and cluster.get("deployment") is not None
        and cluster.get("deployment") != ""
        for cluster in k8s_clusters
    )
    if not k8s_selected:
        logger.info("Skipped high_availability_config.yml (no K8s cluster configured)")
        return

    # If HA is enabled, use the user-provided data; otherwise emit a disabled placeholder
    if wizard_data.get("enable_ha"):
        service_k8s_cluster_ha = wizard_data.get("service_k8s_cluster_ha", [])
    else:
        service_k8s_cluster_ha = [
            {
                "cluster_name": "",
                "enable_k8s_ha": False,
                "virtual_ip_address": "",
            }
        ]

    ha_config = {
        "service_k8s_cluster_ha": service_k8s_cluster_ha
    }

    _write_config_file(input_dir / "high_availability_config.yml", ha_config, quote_all_strings=False)


def _build_local_repo_config_for_os(data: Dict[str, Any], os_type: str) -> Dict[str, Any]:
    """Build local_repo_config content for a single OS (rhel or ubuntu).

    Args:
        data: OS-specific form data
        os_type: 'rhel' or 'ubuntu'

    Returns:
        Dictionary with local repo config entries
    """
    local_repo_config: Dict[str, Any] = {}
    os_cap = os_type.capitalize()

    show_user_registry = data.get("_ui_showUserRegistry", False)
    show_user_repos = data.get("_ui_showUserRepos", False)
    show_additional_repos = data.get("_ui_showAdditionalRepos", False)
    show_os_repos = data.get(f"_ui_show{os_cap}Repos", False)
    show_os_subscription = data.get(f"_ui_show{os_cap}Subscription", False)

    if show_user_registry and has_meaningful_data(data.get("user_registry")):
        local_repo_config["user_registry"] = data.get("user_registry")

    if show_user_repos:
        if has_meaningful_data(data.get("user_repo_url_x86_64")):
            local_repo_config["user_repo_url_x86_64"] = data.get("user_repo_url_x86_64")
        if has_meaningful_data(data.get("user_repo_url_aarch64")):
            local_repo_config["user_repo_url_aarch64"] = data.get("user_repo_url_aarch64")

    if show_additional_repos:
        if has_meaningful_data(data.get("additional_repos_x86_64")):
            local_repo_config["additional_repos_x86_64"] = data.get("additional_repos_x86_64")
        if has_meaningful_data(data.get("additional_repos_aarch64")):
            local_repo_config["additional_repos_aarch64"] = data.get("additional_repos_aarch64")

    if show_os_repos:
        os_repo_keys = (
            f"{os_type}_os_url_x86_64",
            f"{os_type}_os_url_aarch64",
        )
        for key in os_repo_keys:
            value = data.get(key)
            if has_meaningful_data(value):
                local_repo_config[key] = value

    # Omnia repos are on a separate tab with no enable toggle, so emit them
    # whenever they contain meaningful data.
    omnia_repo_keys = (
        f"omnia_repo_url_{os_type}_x86_64",
        f"omnia_repo_url_{os_type}_aarch64",
    )
    for key in omnia_repo_keys:
        value = data.get(key)
        if has_meaningful_data(value):
            local_repo_config[key] = value

    if show_os_subscription:
        subscription_keys = (
            f"{os_type}_subscription_repo_config_x86_64",
            f"{os_type}_subscription_repo_config_aarch64",
        )
        for key in subscription_keys:
            value = data.get(key)
            if has_meaningful_data(value):
                local_repo_config[key] = value

    return local_repo_config


def _write_local_repo_config(local_repo_config: Dict[str, Any], input_dir: Path) -> None:
    """Write local_repo_config.yml to disk.

    Args:
        local_repo_config: Dictionary containing local repo configuration
        input_dir: Directory where config files should be written
    """
    if not local_repo_config:
        logger.info("Skipped local_repo_config.yml (no meaningful data or sections not enabled)")
        return

    local_repo_config = _convert_string_bools_to_bools(local_repo_config)
    local_repo_config_path = input_dir / "local_repo_config.yml"
    local_repo_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_repo_config_path, 'w', encoding='utf-8') as f:
        for key, value in local_repo_config.items():
            f.write(f"{key}:\n")
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        entry_str = format_repo_entry(item)
                        f.write(f"  - {entry_str}\n")
                    else:
                        f.write(f"  - {item}\n")
            else:
                f.write(f"  {value}\n")
    logger.info("Generated local_repo_config.yml at %s", local_repo_config_path)


def generate_local_repo_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate local_repo_config.yml from wizard data.

    Supports both legacy wizard payloads and the new management payload
    that separates RHEL and Ubuntu configuration under top-level keys.

    Args:
        wizard_data: Dictionary containing wizard or management form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    # New management payload with per-OS sections
    if "rhel" in wizard_data or "ubuntu" in wizard_data:
        merged_config: Dict[str, Any] = {}
        for os_type in ("rhel", "ubuntu"):
            os_data = wizard_data.get(os_type, {})
            if not os_data:
                continue
            os_config = _build_local_repo_config_for_os(os_data, os_type)
            for key, value in os_config.items():
                if key in merged_config and isinstance(value, list) and isinstance(merged_config[key], list):
                    seen = {json.dumps(v, sort_keys=True) for v in merged_config[key]}
                    for item in value:
                        item_key = json.dumps(item, sort_keys=True)
                        if item_key not in seen:
                            merged_config[key].append(item)
                            seen.add(item_key)
                else:
                    merged_config[key] = value
        _write_local_repo_config(merged_config, input_dir)
        return

    # Legacy single-OS (RHEL) wizard payload
    local_repo_config = _build_local_repo_config_for_os(wizard_data, "rhel")
    if has_meaningful_data(wizard_data.get("rhel_os_url_x86_64")) and not local_repo_config:
        # Fallback: if no toggles are present, include legacy RHEL repo keys when meaningful
        for key in _RHEL_REPO_KEYS:
            value = wizard_data.get(key)
            if has_meaningful_data(value):
                local_repo_config[key] = value
    _write_local_repo_config(local_repo_config, input_dir)


def generate_telemetry_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate telemetry_config.yml from wizard data.

    Always emitted; when no telemetry source is enabled, a disabled default
    configuration is written.
    """
    telemetry_config = copy.deepcopy(get_telemetry_config_defaults())
    user_data = {
        k: v
        for k, v in wizard_data.items()
        if k in telemetry_config and isinstance(v, dict)
    }
    _deep_merge(telemetry_config, user_data)
    _write_config_file(input_dir / "telemetry_config.yml", telemetry_config, quote_all_strings=True)


def generate_telemetry_storage_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate telemetry_storage_config.yml from wizard data.

    Always emitted; when no telemetry source is enabled, a disabled default
    configuration is written.
    """
    telemetry_storage_config = copy.deepcopy(get_telemetry_storage_config_defaults())
    user_data = {
        k: v
        for k, v in wizard_data.items()
        if k in telemetry_storage_config and isinstance(v, dict)
    }
    _deep_merge(telemetry_storage_config, user_data)
    _flatten_csm_metrics_powerscale_storage(telemetry_storage_config)
    _write_config_file(input_dir / "telemetry_storage_config.yml", telemetry_storage_config, quote_all_strings=False)


def _write_user_registry_credential(credentials: Any, input_dir: Path) -> None:
    """Write user_registry_credential.yml to disk."""
    if not has_meaningful_data(credentials):
        logger.info("Skipped user_registry_credential.yml (no meaningful credential data)")
        return

    path = input_dir / "user_registry_credential.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("user_registry_credential:\n")
        for cred in credentials:
            name = _yaml_escape(str(cred.get("name", "")))
            username = _yaml_escape(str(cred.get("username", "")))
            password = _yaml_escape(str(cred.get("password", "")))
            f.write(f'  - {{name: "{name}", username: "{username}", password: "{password}"}}\n')
    logger.info("Generated user_registry_credential.yml at %s", path)


def generate_user_registry_credential(wizard_data, input_dir, write_yaml_fn):
    """Generate user_registry_credential.yml from wizard or management data."""
    if "rhel" in wizard_data or "ubuntu" in wizard_data:
        merged_credentials = []
        seen = set()
        for os_type in ("rhel", "ubuntu"):
            os_data = wizard_data.get(os_type, {})
            if os_data.get("_ui_showCredentials", False):
                credentials = os_data.get("user_registry_credential", [])
                if has_meaningful_data(credentials):
                    for cred in credentials:
                        key = json.dumps(cred, sort_keys=True)
                        if key not in seen:
                            merged_credentials.append(cred)
                            seen.add(key)
        _write_user_registry_credential(merged_credentials, input_dir)
        return

    if not wizard_data.get("_ui_showCredentials", False):
        logger.info("Skipped user_registry_credential.yml (credentials not enabled)")
        return

    _write_user_registry_credential(wizard_data.get("user_registry_credential", []), input_dir)
def generate_pxe_mapping_file(wizard_data: Dict[str, Any], input_dir: Path, ensure_directory_fn: Callable) -> None:
    """Generate pxe_mapping_file.csv from wizard data."""
    pxe_mapping_data = wizard_data.get("pxe_mapping_data")
    
    if pxe_mapping_data:
        pxe_mapping_path = input_dir / "pxe_mapping_file.csv"
        ensure_directory_fn(pxe_mapping_path.parent)
        
        # Write CSV header
        with open(pxe_mapping_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(_PXE_CSV_COLUMNS)

            # Write data rows
            for row in pxe_mapping_data:
                writer.writerow([row.get(col, "") for col in _PXE_CSV_COLUMNS])
        
        logger.info("Generated pxe_mapping_file.csv at %s", pxe_mapping_path)
    else:
        logger.warning("No PXE mapping data provided, skipping pxe_mapping_file.csv generation")


def generate_provision_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate provision_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    dns_enabled = wizard_data.get("dns_enabled", False)
    lease_time = wizard_data.get("default_lease_time", "")
    language = wizard_data.get("language", "")
    kernel_version = wizard_data.get("kernel_version_override", "")
    cloud_init = wizard_data.get("additional_cloud_init_config_file", "")
    pxe_mapping_data = wizard_data.get("pxe_mapping_data", [])

    if not (
        dns_enabled
        or has_meaningful_data(lease_time)
        or has_meaningful_data(kernel_version)
        or has_meaningful_data(cloud_init)
        or (language and language != "en_US.UTF-8")
        or has_meaningful_data(pxe_mapping_data)
    ):
        logger.info("Skipped provision_config.yml (no meaningful data)")
        return

    provision_config = {
        "pxe_mapping_file_path": "input/pxe_mapping_file.csv",
        "language": language or "en_US.UTF-8",
        "default_lease_time": lease_time or "86400",
        "dns_enabled": dns_enabled,
        "kernel_version_override": kernel_version,
        "additional_cloud_init_config_file": cloud_init,
    }

    _write_config_file(input_dir / "provision_config.yml", provision_config, quote_all_strings=True)


def generate_storage_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate storage_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    storage_config = {}

    # Mounts section
    mounts = wizard_data.get("mounts", [])
    if has_meaningful_data(mounts):
        filtered_mounts = _clean_storage_entries(
            mounts,
            "name",
            {'functional_group_prefix', 'groups', 'node_mount_point'}
        )
        if filtered_mounts:
            storage_config["mounts"] = filtered_mounts

    # Mount params section
    mount_params = wizard_data.get("mount_params", {})
    if has_meaningful_data(mount_params):
        storage_config["mount_params"] = mount_params

    # PowerVault section
    powervault = wizard_data.get("powervault_config", [])
    if has_meaningful_data(powervault):
        filtered_pv = _clean_storage_entries(
            powervault,
            "name",
            {'functional_group_prefix', 'node_mount_point', 'ip'}
        )
        if filtered_pv:
            storage_config["powervault_config"] = filtered_pv

    # Swap section
    swap = wizard_data.get("swap", [])
    if has_meaningful_data(swap):
        filtered_swap = _clean_storage_entries(
            swap,
            "filename",
            {'functional_group_prefix'},
            skip_fn=lambda k, e: k == 'maxsize' and e.get('size') != 'auto'
        )
        if filtered_swap:
            storage_config["swap"] = filtered_swap

    # S3 section
    s3 = wizard_data.get("s3_configurations", {})
    if has_meaningful_data(s3):
        storage_config["s3_configurations"] = s3

    if not storage_config:
        logger.info("Skipped storage_config.yml (no meaningful data)")
        return

    _write_config_file(input_dir / "storage_config.yml", storage_config, quote_all_strings=True, preserve_octal_mode=True)


def generate_additional_cloud_init(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate additional_cloud_init.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    cloud_init = {}

    # Common section
    common_data = copy.deepcopy(wizard_data.get("cloud_init_common", {}))
    if has_meaningful_data(common_data):
        # Transform runcmd from objects to strings for YAML output
        if "runcmd" in common_data and isinstance(common_data["runcmd"], list):
            common_data["runcmd"] = [item.get("command", "") if isinstance(item, dict) else item for item in common_data["runcmd"]]
        cloud_init["common"] = common_data
    else:
        cloud_init["common"] = {}

    # Groups section — transform array [{group_name, write_files, runcmd}] to {group_name: {write_files, runcmd}}
    groups_data = copy.deepcopy(wizard_data.get("cloud_init_groups", []))
    groups_dict = {}
    if isinstance(groups_data, list):
        for group in groups_data:
            if isinstance(group, dict) and group.get("group_name"):
                name = group["group_name"]
                entry = {}
                if has_meaningful_data(group.get("write_files")):
                    entry["write_files"] = group["write_files"]
                if has_meaningful_data(group.get("runcmd")):
                    # Transform runcmd from objects to strings for YAML output
                    runcmd_list = group["runcmd"]
                    if isinstance(runcmd_list, list):
                        entry["runcmd"] = [item.get("command", "") if isinstance(item, dict) else item for item in runcmd_list]
                    else:
                        entry["runcmd"] = runcmd_list
                if entry:
                    groups_dict[name] = entry

    if groups_dict:
        cloud_init["groups"] = groups_dict
    else:
        cloud_init["groups"] = {}

    # Only generate if there's any meaningful data
    if not has_meaningful_data(cloud_init.get("common")) and not has_meaningful_data(cloud_init.get("groups")):
        logger.info("Skipped additional_cloud_init.yml (no meaningful data)")
        return

    _write_config_file(input_dir / "additional_cloud_init.yml", cloud_init, quote_all_strings=False)


def generate_security_config(wizard_data: Dict[str, Any], input_dir: Path, write_yaml_fn: Callable) -> None:
    """Generate security_config.yml from wizard data.

    Args:
        wizard_data: Dictionary containing wizard form data
        input_dir: Directory where config files should be written
        write_yaml_fn: Callback for writing YAML (required by generator registry interface, unused)
    """
    security_config_data = wizard_data.get("security_config", {})

    # Only generate if there's meaningful data
    if not has_meaningful_data(security_config_data):
        logger.info("Skipped security_config.yml (no meaningful data)")
        return

    security_config = {
        "ldap_connection_type": security_config_data.get("ldap_connection_type", "TLS")
    }

    _write_config_file(input_dir / "security_config.yml", security_config, quote_all_strings=True)

