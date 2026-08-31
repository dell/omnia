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
"""Container registry configuration and resolution helpers."""

import os
import socket
from urllib.parse import urlsplit, urlunsplit


PUBLIC_REGISTRY_URLS = {
    "docker.io": "https://registry-1.docker.io",
    "ghcr.io": "https://ghcr.io",
    "quay.io": "https://quay.io",
    "registry.k8s.io": "https://registry.k8s.io",
    "nvcr.io": "https://nvcr.io",
    "public.ecr.aws": "https://public.ecr.aws",
    "gcr.io": "https://gcr.io",
}


def is_public_registry(registry_name):
    """Return whether *registry_name* is supported without user configuration."""
    return registry_name in PUBLIC_REGISTRY_URLS


def build_registry_base_url(registry_config):
    """Build the upstream base URL from a validated lowercase registry config."""
    if not isinstance(registry_config, dict):
        raise TypeError("Registry configuration must be a mapping")

    base_url_value = registry_config.get("base_url", "")
    if not isinstance(base_url_value, str):
        raise ValueError("Registry base_url must be a string")
    base_url = base_url_value.rstrip("/")
    port = registry_config.get("port")
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid registry base_url: {base_url}")

    # Keep a port explicitly present in base_url. Otherwise add the configured port.
    if parsed.port is not None or port is None:
        return base_url

    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = f"{hostname}:{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path.rstrip("/"), "", ""))


def get_image_path_for_registry(package_name, registry_name):
    """Return the upstream image path after validating its catalog registry prefix."""
    prefix = f"{registry_name}/"
    if not package_name.startswith(prefix):
        raise ValueError(
            f"Image '{package_name}' must start with its catalog registry '{prefix}'"
        )
    image_path = package_name[len(prefix):]
    if not image_path:
        raise ValueError(f"Image path is empty for '{package_name}'")
    return image_path


def resolve_registry_contexts(registries, credential_data):
    """Resolve configured registries and their Ansible Vault credential records.

    The returned mapping is safe to pass to image tasks. Fixed keys are lowercase;
    user-provided values are preserved exactly.
    """
    contexts = {}
    registry_credentials = (credential_data or {}).get("registry_credentials") or {}
    if not isinstance(registry_credentials, dict):
        raise ValueError("registry_credentials must be a mapping")

    if registries is not None and not isinstance(registries, dict):
        raise ValueError("registries must be a mapping")

    for registry_name, registry_config in (registries or {}).items():
        if not isinstance(registry_config, dict):
            raise ValueError(f"Registry '{registry_name}' must be a mapping")
        auth = registry_config.get("auth") or {"type": "none"}
        if not isinstance(auth, dict):
            raise ValueError(f"Registry '{registry_name}' auth must be a mapping")
        auth_type = auth.get("type", "none")
        if auth_type not in ("none", "basic"):
            raise ValueError(
                f"Registry '{registry_name}' has unsupported auth type '{auth_type}'"
            )
        tls = registry_config.get("tls") or {}
        if not isinstance(tls, dict):
            raise ValueError(f"Registry '{registry_name}' tls must be a mapping")
        context = {
            "name": registry_name,
            "base_url": build_registry_base_url(registry_config),
            "auth_type": auth_type,
            "username": "",
            "password": "",
            "tls": tls,
        }

        if auth_type == "basic":
            credentials_config = auth.get("credentials") or {}
            vault_path = credentials_config.get("vault_path", "")
            credentials = registry_credentials.get(vault_path) or {}
            if not isinstance(credentials, dict):
                raise ValueError(
                    f"Credential record '{vault_path}' must be a mapping"
                )
            credential_registry = credentials.get("registry", "")
            if credential_registry and credential_registry != registry_name:
                raise ValueError(
                    f"Credential record '{vault_path}' is mapped to registry "
                    f"'{credential_registry}', not '{registry_name}'"
                )
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            if not username or not password:
                raise ValueError(
                    f"Basic authentication credentials are missing for registry '{registry_name}'"
                )
            context["username"] = username
            context["password"] = password
            context["vault_path"] = vault_path

        contexts[registry_name] = context

    return contexts


def validate_user_registry(registries):
    """Validate the lowercase configured-registry structure."""
    if registries is None:
        return True, ""
    if not isinstance(registries, dict):
        return False, "registries must be a mapping."

    for registry_name, registry_config in registries.items():
        if not isinstance(registry_config, dict):
            return False, f"Registry '{registry_name}' must be a mapping."
        try:
            build_registry_base_url(registry_config)
        except (TypeError, ValueError) as exc:
            return False, f"Registry '{registry_name}': {exc}"

        tls = registry_config.get("tls") or {}
        client_cert = tls.get("client_cert_path") or ""
        client_key = tls.get("client_key_path") or ""
        if bool(client_cert) != bool(client_key):
            return False, (
                f"Registry '{registry_name}' must configure client_cert_path and "
                "client_key_path together."
            )

    return True, ""


def _registry_host_port(registry_config):
    """Return a registry hostname and port for reachability checks."""
    parsed = urlsplit(registry_config.get("base_url", ""))
    return parsed.hostname, parsed.port or registry_config.get("port")


def tcp_ping(hostname, port, timeout=1):
    """Return whether a TCP connection can be established."""
    try:
        with socket.create_connection((hostname, int(port)), timeout=timeout):
            return True
    except (OSError, TypeError, ValueError):
        return False


def check_reachability(registries, timeout=1):
    """Return configured registry names split into reachable and unreachable lists."""
    reachable, unreachable = [], []
    for registry_name, registry_config in (registries or {}).items():
        hostname, port = _registry_host_port(registry_config)
        if hostname and port and tcp_ping(hostname, port, timeout):
            reachable.append(registry_name)
        else:
            unreachable.append(registry_name)
    return reachable, unreachable


def find_invalid_cert_paths(registries):
    """Return configured TLS certificate paths that are missing or incomplete."""
    invalid_entries = []
    for registry_name, registry_config in (registries or {}).items():
        tls = registry_config.get("tls") or {}
        ca_path = tls.get("ca_path") or ""
        client_cert = tls.get("client_cert_path") or ""
        client_key = tls.get("client_key_path") or ""

        if bool(client_cert) != bool(client_key):
            invalid_entries.append(
                f"{registry_name}: client_cert_path and client_key_path must be provided together."
            )
            continue

        for key, path in (
            ("ca_path", ca_path),
            ("client_cert_path", client_cert),
            ("client_key_path", client_key),
        ):
            if path and not os.path.isfile(path):
                invalid_entries.append(f"{registry_name}: {key} '{path}' does not exist.")

    return invalid_entries
