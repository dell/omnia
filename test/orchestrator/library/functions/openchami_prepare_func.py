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

"""OpenCHAMI postcondition helpers for the prepare lifecycle."""

import json
import re
from typing import Any

import yaml
from omnia_auto import run_on_host

from ..vars.prepare_vars import (
    HAPROXY_CERT_VOLUME,
    OPENCHAMI_ACTIVE_UNITS,
    OPENCHAMI_API_PATHS,
    OPENCHAMI_CONFIG_ARTIFACTS,
    OPENCHAMI_CONTAINERS,
    OPENCHAMI_DATA_VOLUMES,
    OPENCHAMI_INITIALIZATION_UNIT,
    OPENCHAMI_PACKAGES,
    POSTGRES_INIT_SCRIPT,
    PREPARE_COMMANDS,
)
from ._prepare_helpers import prepare_result, read_yaml_mapping


def _openchami_base_url(host) -> str:
    """Resolve the API base URL from the deployed ochami client config."""
    config = read_yaml_mapping(host, "/etc/ochami/config.yaml")
    default_name = config.get("default-cluster")
    clusters = config.get("clusters", [])
    if not isinstance(clusters, list):
        raise TypeError("ochami config clusters must be a list")
    for entry in clusters:
        if not isinstance(entry, dict):
            continue
        cluster = entry.get("cluster", {})
        if entry.get("name") == default_name and isinstance(cluster, dict):
            uri = str(cluster.get("uri", "")).rstrip("/")
            if re.fullmatch(r"https://[A-Za-z0-9.-]+:\d+", uri):
                return uri
    raise ValueError("ochami config has no valid default cluster URI")


def check_prepare_openchami_containers(host) -> dict[str, Any]:
    """Verify every long-running OpenCHAMI container is running."""
    states = []
    missing = []
    for container in OPENCHAMI_CONTAINERS:
        probe = run_on_host(host, PREPARE_COMMANDS["container_state"], container)
        state = probe.stdout.strip() if probe.rc == 0 else "missing"
        states.append((f"Container {container}", state))
        if state != "running":
            missing.append(container)
    return prepare_result(
        not missing,
        f"{len(OPENCHAMI_CONTAINERS) - len(missing)}/"
        f"{len(OPENCHAMI_CONTAINERS)} containers are running",
        states,
        "Containers not running: " + ", ".join(missing) if missing else "",
    )


def check_prepare_openchami_services(host) -> dict[str, Any]:
    """Verify active services and successful one-time SMD initialization."""
    fields = []
    failures = []
    for unit in OPENCHAMI_ACTIVE_UNITS:
        probe = run_on_host(host, PREPARE_COMMANDS["unit_active"], unit)
        state = probe.stdout.strip() if probe.rc == 0 else "inactive"
        fields.append((f"Unit {unit}", state))
        if state != "active":
            failures.append(f"{unit}={state}")

    initialization = run_on_host(
        host,
        PREPARE_COMMANDS["unit_result"],
        OPENCHAMI_INITIALIZATION_UNIT,
    )
    init_result = (
        initialization.stdout.strip() if initialization.rc == 0 else "unavailable"
    )
    fields.append((f"Unit {OPENCHAMI_INITIALIZATION_UNIT}", init_result))
    if init_result != "success":
        failures.append(f"{OPENCHAMI_INITIALIZATION_UNIT} result={init_result}")

    return prepare_result(
        not failures,
        "OpenCHAMI systemd runtime and initialization checked",
        fields,
        "; ".join(failures),
    )


def check_prepare_openchami_apis(host) -> dict[str, Any]:
    """Verify authenticated SMD, Boot Service and Metadata Service APIs."""
    try:
        base_url = _openchami_base_url(host)
    except (TypeError, ValueError) as exc:
        return prepare_result(False, "Unable to resolve OpenCHAMI API", [], str(exc))

    fields = [("API base URL", base_url)]
    urls = [f"{base_url}{path}" for _, path in OPENCHAMI_API_PATHS]
    probe = run_on_host(
        host,
        PREPARE_COMMANDS["api_probe_all"],
        *urls,
    )

    token_state = "unavailable"
    endpoint_results: dict[int, tuple[str, str]] = {}
    for line in probe.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 2 and parts[0] == "TOKEN":
            token_state = parts[1]
            continue
        if len(parts) != 4 or parts[0] != "PROBE":
            continue
        try:
            index = int(parts[1])
        except ValueError:
            continue
        if 0 <= index < len(OPENCHAMI_API_PATHS):
            endpoint_results[index] = (parts[2], parts[3])

    fields.append(("Access token", token_state.replace("_", " ")))
    if token_state in {"generation_failed", "refresh_failed", "unavailable"}:
        for service, _ in OPENCHAMI_API_PATHS:
            fields.append((service, "not checked"))
        reason = {
            "generation_failed": "TokenSmith access-token generation failed",
            "refresh_failed": "TokenSmith access-token refresh failed",
            "unavailable": "Access-token probe returned no valid status",
        }[token_state]
        return prepare_result(
            False,
            "OpenCHAMI API authentication could not be established",
            fields,
            reason,
        )

    failures = []
    for index, (service, _) in enumerate(OPENCHAMI_API_PATHS):
        result = endpoint_results.get(index)
        if result is None:
            state = "not checked"
            failure = f"{service}: probe result missing"
        else:
            outcome, detail = result
            if outcome == "reachable":
                state = f"reachable (HTTP {detail})"
                failure = ""
            elif outcome == "authentication":
                state = f"authentication failed (HTTP {detail})"
                failure = f"{service}: authentication failed after refresh"
            elif outcome == "transport":
                state = f"transport failure (curl rc {detail})"
                failure = f"{service}: transport failure"
            else:
                state = f"service failure (HTTP {detail})"
                failure = f"{service}: HTTP {detail}"
        fields.append((service, state))
        if failure:
            failures.append(failure)
    return prepare_result(
        not failures,
        "Authenticated OpenCHAMI endpoint probes completed",
        fields,
        "; ".join(failures),
    )


def check_prepare_openchami_storage(host) -> dict[str, Any]:
    """Verify persistent volumes and HAProxy certificate material."""
    fields = []
    failures = []
    for volume in OPENCHAMI_DATA_VOLUMES:
        exists = run_on_host(host, PREPARE_COMMANDS["volume_exists"], volume)
        state = "present" if exists.rc == 0 else "missing"
        fields.append((f"Volume {volume}", state))
        if exists.rc != 0:
            failures.append(volume)

    cert_volume = run_on_host(
        host, PREPARE_COMMANDS["volume_exists"], HAPROXY_CERT_VOLUME
    )
    pem_count = 0
    if cert_volume.rc == 0:
        mountpoint = run_on_host(
            host,
            PREPARE_COMMANDS["volume_mountpoint"],
            HAPROXY_CERT_VOLUME,
        )
        if mountpoint.rc == 0 and mountpoint.stdout.strip():
            count = run_on_host(
                host,
                PREPARE_COMMANDS["pem_count"],
                mountpoint.stdout.strip(),
            )
            if count.rc == 0 and count.stdout.strip().isdigit():
                pem_count = int(count.stdout.strip())
    fields.extend(
        [
            (
                "HAProxy certificate volume",
                "present" if cert_volume.rc == 0 else "missing",
            ),
            ("HAProxy PEM certificates", pem_count),
        ]
    )
    if cert_volume.rc != 0 or pem_count < 1:
        failures.append("haproxy-certs has no PEM certificate")

    return prepare_result(
        not failures,
        "OpenCHAMI persistent storage and TLS material checked",
        fields,
        "; ".join(failures),
    )


def check_prepare_openchami_artifacts(host) -> dict[str, Any]:
    """Verify packages, generated configuration and PostgreSQL init script."""
    fields = []
    failures = []
    for package in OPENCHAMI_PACKAGES:
        probe = run_on_host(host, PREPARE_COMMANDS["package_version"], package)
        version = probe.stdout.strip() if probe.rc == 0 else "missing"
        fields.append((f"Package {package}", version))
        if probe.rc != 0:
            failures.append(f"package {package}")

    for path, expected_mode, parser in OPENCHAMI_CONFIG_ARTIFACTS:
        artifact = host.file(path)
        state = "valid"
        if not artifact.is_file:
            state = "missing"
        elif artifact.user != "root" or artifact.group != "root":
            state = "invalid owner"
        elif artifact.mode != expected_mode:
            state = f"mode {oct(artifact.mode)}"
        elif not artifact.content_string.strip():
            state = "empty"
        else:
            try:
                if parser == "json":
                    json.loads(artifact.content_string)
                elif parser == "yaml":
                    yaml.safe_load(artifact.content_string)
            except (json.JSONDecodeError, yaml.YAMLError):
                state = f"invalid {parser}"
        fields.append((path, state))
        if state != "valid":
            failures.append(f"{path}: {state}")

    init_script = host.file(POSTGRES_INIT_SCRIPT)
    init_state = (
        "readable"
        if init_script.is_file and init_script.size > 0
        else "missing or empty"
    )
    fields.append((POSTGRES_INIT_SCRIPT, init_state))
    if init_state != "readable":
        failures.append(f"{POSTGRES_INIT_SCRIPT}: {init_state}")

    return prepare_result(
        not failures,
        "OpenCHAMI package and artifact contracts checked",
        fields,
        "; ".join(failures),
    )
