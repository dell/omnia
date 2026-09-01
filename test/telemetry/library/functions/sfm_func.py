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

"""SFM external Victoria integration and end-to-end verification helpers."""

import base64
import ipaddress
import json
import re
import time
from datetime import datetime, timezone
from functools import partial

import paramiko
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from omnia_auto import (
    connection_params,
    load_test_config,
    load_test_credentials,
    run_on_host,
    run_playbook,
)

from ..messages.sfm_msgs import SFM_DETAIL_MSGS, SFM_ERROR_MSGS
from ..vars.common_vars import (
    CMDS,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    TELEMETRY_NAMESPACE,
)
from ..vars.sfm_vars import (
    SFM_ACTIONS,
    SFM_ANSI_ESCAPE_PATTERN,
    SFM_CA_CERTIFICATE_FILE,
    SFM_CMD_TEMPLATES,
    SFM_COMMAND_RC_MARKER,
    SFM_CONFIG_KEYS,
    SFM_CREDENTIAL_KEYS,
    SFM_DEBUG_MENU_OPTION,
    SFM_DETAILS_KEYS,
    SFM_DEFAULT_API_PORT,
    SFM_DEFAULT_SSH_PORT,
    SFM_EXTERNAL_VICTORIA_DETAILS_FILE,
    SFM_EXTERNAL_VICTORIA_SUBDIR,
    SFM_EXTERNAL_VICTORIA_TAG,
    SFM_EXPORTED_ENDPOINT_FIELDS,
    SFM_INSTANCE_ID,
    SFM_MAX_NETWORK_PORT,
    SFM_NAMESPACE_TEMPLATE,
    SFM_NETWORK_TIMEOUT_SECONDS,
    SFM_OIM_SSH_PORT_KEY,
    SFM_POD_RUNNING_PHASE,
    SFM_PROMETHEUS_CONTAINER,
    SFM_PROMETHEUS_POD_PREFIX,
    SFM_REQUIRED_SERVICES,
    SFM_REQUIRED_WORKLOADS,
    SFM_REMOTE_WRITE_HOSTNAME,
    SFM_REMOTE_WRITE_PORT,
    SFM_REMOTE_WRITE_TARGET_NAME,
    SFM_REMOTE_WRITE_URL,
    SFM_SECURE_SHELL_OPTION,
    SFM_SHELL_PROMPT_SUFFIXES,
    SFM_SHELL_PROBE_OUTPUT,
    SFM_SSH_AUTH_TIMEOUT_SECONDS,
    SFM_SSH_BANNER_TIMEOUT_SECONDS,
    SFM_SSH_BUFFER_SIZE,
    SFM_SSH_CHANNEL_KIND,
    SFM_SSH_COMMAND_TIMEOUT_SECONDS,
    SFM_SSH_CONNECT_TIMEOUT_SECONDS,
    SFM_SSH_IDLE_SECONDS,
    SFM_SSH_MENU_TIMEOUT_SECONDS,
    SFM_SSH_READ_INTERVAL_SECONDS,
    SFM_SSH_TERMINAL_HEIGHT,
    SFM_SSH_TERMINAL_WIDTH,
    SFM_VMCLUSTER_LABEL_SELECTOR,
)
from .sfm_api_func import SfmApiError
from .sfm_api_func import configure_remote_write as _configure_remote_write
from .telemetry_func import get_output_path, run_on_kube_vip


class _SfmAutomationError(RuntimeError):
    """Internal error with a safe, user-facing description."""


def sfm_result(success, details="", error="", **extra):
    """Build the standard SFM result dictionary.

    Args:
        success: Whether the verification completed successfully.
        details: Human-readable structured result details.
        error: Safe failure description.
        **extra: Additional structured result fields.

    Returns:
        Standard result mapping with success, details, and error fields.
    """
    value = {
        "success": success,
        "details": details,
        "error": error,
    }
    value.update(extra)
    return value


def sfm_skip_result():
    """Return a standard result for a disabled opt-in SFM test.

    Returns:
        Successful result mapping marked as skipped.
    """
    return sfm_result(
        True,
        details=SFM_DETAIL_MSGS["disabled"],
        skipped=True,
    )


def _nested_value(data, key_path):
    """Return a nested mapping value or ``None`` when a key is absent."""
    value = data
    for key in key_path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _positive_int(value, field, maximum=None):
    """Return a bounded integer setting or raise a safe error."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["config_invalid"].format(field=field, value=value)
        )
    if value <= 0 or (maximum is not None and value > maximum):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["config_invalid"].format(field=field, value=value)
        )
    return value


def _boolean_setting(config, name, default):
    """Return one strictly boolean SFM setting."""
    field = SFM_CONFIG_KEYS[name]
    value = config.get(field, default)
    if not isinstance(value, bool):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["config_invalid"].format(
                field=field, value=value,
            )
        )
    return value


def _api_context(config):
    """Return validated non-secret SFM API settings."""
    return {
        "api_port": _positive_int(
            config.get(
                SFM_CONFIG_KEYS["api_port"], SFM_DEFAULT_API_PORT,
            ),
            SFM_CONFIG_KEYS["api_port"],
            SFM_MAX_NETWORK_PORT,
        ),
    }


def _ssh_context(config):
    """Return validated SFM and OIM SSH ports."""
    return {
        "ssh_port": _positive_int(
            config.get(
                SFM_CONFIG_KEYS["ssh_port"], SFM_DEFAULT_SSH_PORT,
            ),
            SFM_CONFIG_KEYS["ssh_port"],
            SFM_MAX_NETWORK_PORT,
        ),
        "oim_ssh_port": _positive_int(
            config.get(SFM_OIM_SSH_PORT_KEY),
            SFM_OIM_SSH_PORT_KEY,
            SFM_MAX_NETWORK_PORT,
        ),
    }


def _required_context_values(config, credentials, names):
    """Return required endpoint and credential values by logical name."""
    values = {}
    for name in names:
        is_config = name in SFM_CONFIG_KEYS
        fields = SFM_CONFIG_KEYS if is_config else SFM_CREDENTIAL_KEYS
        source = config if is_config else credentials
        field = fields[name]
        value = str(source.get(field, "")).strip()
        if not value:
            message_key = "config_missing" if is_config else "credential_missing"
            raise _SfmAutomationError(
                SFM_ERROR_MSGS[message_key].format(field=field)
            )
        values[name] = value
    return values


def _validate_context_ips(context):
    """Validate each endpoint IP present in an SFM context."""
    for name in ("api_ip", "ssh_ip"):
        if name not in context:
            continue
        try:
            ipaddress.ip_address(context[name])
        except ValueError as exc:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["config_invalid"].format(
                    field=SFM_CONFIG_KEYS[name], value=context[name],
                )
            ) from exc


def load_sfm_context(require_api=False, require_ssh=False):
    """Load validated SFM settings and encrypted credentials.

    Args:
        require_api: Include and require management API connection values.
        require_ssh: Include and require forced-menu SSH connection values.

    Returns:
        Context dict, or ``None`` when the opt-in integration is disabled.
    """
    config = load_test_config()
    if not _boolean_setting(config, "enabled", False):
        return None
    context = {
        "enabled": True,
        "force_export": _boolean_setting(config, "force_export", False),
        "instance_id": SFM_INSTANCE_ID,
    }
    required_names = []
    if require_api:
        context.update(_api_context(config))
        required_names.extend(("api_ip", "api_username", "api_password"))
    if require_ssh:
        context.update(_ssh_context(config))
        required_names.extend(("ssh_ip", "ssh_username", "ssh_password"))
    credentials = load_test_credentials() if required_names else {}
    context.update(_required_context_values(
        config, credentials, required_names,
    ))
    _validate_context_ips(context)
    return context


def _export_paths(host):
    """Return the fixed external Victoria details and CA paths."""
    export_dir = (
        f"{get_output_path(host)}/{SFM_EXTERNAL_VICTORIA_SUBDIR}"
    )
    return {
        "directory": export_dir,
        "details": f"{export_dir}/{SFM_EXTERNAL_VICTORIA_DETAILS_FILE}",
        "ca": f"{export_dir}/{SFM_CA_CERTIFICATE_FILE}",
    }


def _read_remote_text(host, path):
    """Read a target-host file through the centralized command template."""
    command = SFM_CMD_TEMPLATES["read_file_base64"].format(path=path)
    command_result = run_on_host(host, command)
    if command_result.rc != 0 or not command_result.stdout.strip():
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["export_read_failed"].format(path=path)
        )
    try:
        return base64.b64decode(command_result.stdout.strip()).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["export_read_failed"].format(path=path)
        ) from exc


def _read_victoria_export(host):
    """Read and validate the generated Victoria connection artifacts."""
    paths = _export_paths(host)
    try:
        details_text = _read_remote_text(host, paths["details"])
        ca_text = _read_remote_text(host, paths["ca"])
    except _SfmAutomationError as exc:
        raise _SfmAutomationError(str(exc)) from exc

    try:
        details = yaml.safe_load(details_text) or {}
    except yaml.YAMLError as exc:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["export_yaml_invalid"].format(error=exc)
        ) from exc

    values = {}
    for field, key_path in SFM_DETAILS_KEYS.items():
        values[field] = _nested_value(details, key_path)
        if not values[field]:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["export_value_missing"].format(field=field)
            )

    for endpoint_name in SFM_EXPORTED_ENDPOINT_FIELDS:
        try:
            ipaddress.ip_address(str(values[endpoint_name]))
        except ValueError as exc:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["export_ip_invalid"].format(
                    value=values[endpoint_name],
                )
            ) from exc

    if values["remote_write_url"] != SFM_REMOTE_WRITE_URL:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["export_url_mismatch"].format(
                url=values["remote_write_url"],
            )
        )
    ca_bytes = ca_text.encode("utf-8")
    try:
        certificate = x509.load_pem_x509_certificate(ca_bytes)
    except ValueError as exc:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["certificate_invalid"]
        ) from exc
    current_time = datetime.now(timezone.utc)
    if (
        certificate.not_valid_before_utc > current_time
        or certificate.not_valid_after_utc <= current_time
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["certificate_not_current"].format(
                not_before=certificate.not_valid_before_utc.isoformat(),
                not_after=certificate.not_valid_after_utc.isoformat(),
            )
        )
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()

    return {
        "paths": paths,
        "details": details,
        "ca_bytes": ca_bytes,
        "ca_fingerprint": fingerprint,
        "vminsert_ip": str(values["vminsert_ip"]),
        "vmselect_ip": str(values["vmselect_ip"]),
        "remote_write_url": str(values["remote_write_url"]),
    }


def verify_sfm_victoria_export(host):
    """Generate when needed, then validate Victoria details and ``ca.crt``.

    Args:
        host: Testinfra connection to the OIM host.

    Returns:
        Standard result with playbook action and exported endpoint addresses.
    """
    try:
        context = load_sfm_context()
        if context is None:
            return sfm_skip_result()

        playbook_ran = False
        try:
            export = _read_victoria_export(host)
        except _SfmAutomationError:
            export = None

        if export is None or context["force_export"]:
            playbook_result = run_playbook(
                playbook=PLAYBOOK_ENTRY_POINT,
                playbook_workdir=PLAYBOOK_WORKDIR,
                tag=SFM_EXTERNAL_VICTORIA_TAG,
            )
            playbook_ran = True
            if not playbook_result.get("success", False):
                raise _SfmAutomationError(
                    SFM_ERROR_MSGS["playbook_failed"].format(
                        error=playbook_result.get("error", ""),
                    )
                )
            export = _read_victoria_export(host)

        details = SFM_DETAIL_MSGS["export_ready"].format(
            details_path=export["paths"]["details"],
            ca_path=export["paths"]["ca"],
            vminsert_ip=export["vminsert_ip"],
            vmselect_ip=export["vmselect_ip"],
            remote_write_url=export["remote_write_url"],
            playbook_ran=playbook_ran,
        )
        return sfm_result(
            True,
            details=details,
            playbook_ran=playbook_ran,
            vminsert_ip=export["vminsert_ip"],
            vmselect_ip=export["vmselect_ip"],
        )
    except (OSError, ValueError, _SfmAutomationError) as exc:
        return sfm_result(False, error=str(exc))


def _read_kubernetes_json(host, command, resource):
    """Run one kubectl command and return a validated JSON mapping."""
    command_result = run_on_kube_vip(host, command)
    if command_result.rc != 0 or not command_result.stdout.strip():
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_resource_read_failed"].format(
                resource=resource,
            )
        )
    try:
        payload = json.loads(command_result.stdout)
    except json.JSONDecodeError as exc:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_json_invalid"].format(
                resource=resource, error=exc,
            )
        ) from exc
    if not isinstance(payload, dict):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    return payload


def _replica_count(value):
    """Return a non-negative Kubernetes replica count or ``None``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _pod_status(pod):
    """Return strict phase and container readiness for one pod mapping."""
    if not isinstance(pod, dict):
        return None
    metadata = pod.get("metadata")
    specification = pod.get("spec")
    status = pod.get("status")
    if not all(isinstance(value, dict) for value in (
        metadata, specification, status,
    )):
        return None
    if not metadata.get("name") or metadata.get("deletionTimestamp"):
        return None
    containers = specification.get("containers")
    container_statuses = status.get("containerStatuses")
    conditions = status.get("conditions")
    if not isinstance(containers, list) or not isinstance(
        container_statuses, list,
    ) or not isinstance(conditions, list):
        return None
    if (
        any(not isinstance(value, dict) for value in containers)
        or any(not isinstance(value, dict) for value in container_statuses)
        or any(not isinstance(value, dict) for value in conditions)
    ):
        return None
    container_names = {value.get("name") for value in containers}
    status_names = {value.get("name") for value in container_statuses}
    expected_containers = len(containers)
    ready_containers = sum(
        1 for value in container_statuses
        if isinstance(value, dict) and value.get("ready") is True
    )
    phase = status.get("phase", "")
    ready_condition = any(
        value.get("type") == "Ready" and value.get("status") == "True"
        for value in conditions
    )
    ready = (
        phase == SFM_POD_RUNNING_PHASE
        and ready_condition
        and expected_containers > 0
        and len(container_statuses) == expected_containers
        and container_names == status_names
        and ready_containers == expected_containers
    )
    return {
        "name": str(metadata.get("name", "")),
        "phase": str(phase),
        "containers": expected_containers,
        "container_names": sorted(container_names),
        "ready_containers": ready_containers,
        "ready": ready,
    }


def _workload_status(host, workload, pods):
    """Return strict replica and pod status for one required workload."""
    payload = None
    selected_kind = ""
    selected_api_kind = ""
    attempted_resources = []
    for resource_kind, api_kind in workload["kind_candidates"]:
        resource = f"{resource_kind}/{workload['name']}"
        attempted_resources.append(resource)
        command = SFM_CMD_TEMPLATES["kubectl_get_workload_json"].format(
            kind=resource_kind,
            name=workload["name"],
            namespace=TELEMETRY_NAMESPACE,
        )
        try:
            payload = _read_kubernetes_json(host, command, resource)
        except _SfmAutomationError:
            continue
        selected_kind = resource_kind
        selected_api_kind = api_kind
        break
    if payload is None:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_resource_read_failed"].format(
                resource=" or ".join(attempted_resources),
            )
        )
    resource = f"{selected_kind}/{workload['name']}"
    metadata = payload.get("metadata")
    specification = payload.get("spec")
    status = payload.get("status")
    if not all(isinstance(value, dict) for value in (
        metadata, specification, status,
    )):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    generation = _replica_count(metadata.get("generation"))
    observed_generation = _replica_count(status.get("observedGeneration"))
    desired = _replica_count(specification.get("replicas"))
    ready = _replica_count(status.get("readyReplicas", 0))
    if any(value is None for value in (
        generation, observed_generation, desired, ready,
    )):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    matching_pods = [
        pod for pod in pods
        if pod["name"].startswith(workload["pod_prefix"])
    ]
    ready_pods = sum(1 for pod in matching_pods if pod["ready"])
    rollout_ready = True
    if selected_kind == "deployment":
        updated = _replica_count(status.get("updatedReplicas", 0))
        available = _replica_count(status.get("availableReplicas", 0))
        rollout_ready = updated == desired and available == desired
    elif selected_kind == "statefulset":
        current = _replica_count(status.get("currentReplicas", 0))
        rollout_ready = (
            current == desired
            and bool(status.get("currentRevision"))
            and status.get("currentRevision") == status.get("updateRevision")
        )
    success = (
        metadata.get("name") == workload["name"]
        and payload.get("kind") == selected_api_kind
        and observed_generation >= generation
        and desired > 0
        and ready == desired
        and rollout_ready
        and len(matching_pods) == desired
        and ready_pods == desired
    )
    return {
        **workload,
        "kind": selected_kind,
        "success": success,
        "desired_replicas": desired,
        "ready_replicas": ready,
        "rollout_ready": rollout_ready,
        "generation": generation,
        "observed_generation": observed_generation,
        "pod_count": len(matching_pods),
        "ready_pods": ready_pods,
        "pods": matching_pods,
    }


def _victoria_cluster_pods(host):
    """Return strict pod status for the VictoriaMetrics VMCluster."""
    command = CMDS["kubectl_get_pods_json_by_label"].format(
        namespace=TELEMETRY_NAMESPACE,
        label_selector=SFM_VMCLUSTER_LABEL_SELECTOR,
    )
    payload = _read_kubernetes_json(
        host, command, SFM_VMCLUSTER_LABEL_SELECTOR,
    )
    items = payload.get("items")
    if not isinstance(items, list):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(
                resource=SFM_VMCLUSTER_LABEL_SELECTOR,
            )
        )
    pods = [_pod_status(item) for item in items]
    if any(pod is None for pod in pods):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(
                resource=SFM_VMCLUSTER_LABEL_SELECTOR,
            )
        )
    return pods


def verify_sfm_omnia_pods(host):
    """Export Victoria connection data and verify required Omnia workloads.

    Args:
        host: Testinfra connection to the OIM host.

    Returns:
        Standard result with export action and per-workload pod readiness.
    """
    try:
        if load_sfm_context() is None:
            return sfm_skip_result()
        export_result = verify_sfm_victoria_export(host)
        if not export_result["success"]:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["omnia_export_failed"].format(
                    error=export_result["error"],
                )
            )
        pods = _victoria_cluster_pods(host)
        workloads = [
            _workload_status(host, workload, pods)
            for workload in SFM_REQUIRED_WORKLOADS
        ]
        failed = [
            workload["component"] for workload in workloads
            if not workload["success"]
        ]
        detail_lines = [
            SFM_DETAIL_MSGS["omnia_workload_line"].format(
                status_icon="\u2713" if workload["success"] else "\u2717",
                **workload,
            )
            for workload in workloads
        ]
        details = SFM_DETAIL_MSGS["omnia_pods_ready"].format(
            namespace=TELEMETRY_NAMESPACE,
            playbook_ran=export_result["playbook_ran"],
            workloads="\n".join(detail_lines),
        )
        if failed:
            return sfm_result(
                False,
                details=details,
                error=SFM_ERROR_MSGS["omnia_workloads_unready"].format(
                    components=", ".join(failed),
                ),
                workloads=workloads,
            )
        return sfm_result(
            True,
            details=details,
            playbook_ran=export_result["playbook_ran"],
            workloads=workloads,
        )
    except (OSError, ValueError, _SfmAutomationError) as exc:
        return sfm_result(False, error=str(exc))


def _service_status(host, expected, expected_address=""):
    """Return service shape and ready endpoint status for one component."""
    resource = f"service/{expected['name']}"
    service_command = CMDS["kubectl_get_svc_json"].format(
        name=expected["name"], namespace=TELEMETRY_NAMESPACE,
    )
    service = _read_kubernetes_json(host, service_command, resource)
    specification = service.get("spec")
    status = service.get("status")
    metadata = service.get("metadata")
    if not all(isinstance(value, dict) for value in (
        metadata, specification, status,
    )):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    port_rows = specification.get("ports")
    if not isinstance(port_rows, list) or any(
        not isinstance(value, dict) for value in port_rows
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    if any(
        isinstance(value.get("port"), bool)
        or not isinstance(value.get("port"), int)
        for value in port_rows
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    ports = sorted({value["port"] for value in port_rows})
    load_balancer = status.get("loadBalancer", {})
    if not isinstance(load_balancer, dict):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    ingress = load_balancer.get("ingress", [])
    if not isinstance(ingress, list) or any(
        not isinstance(value, dict) for value in ingress
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    external_addresses = [
        str(value.get("ip") or value.get("hostname") or "")
        for value in ingress
    ]
    external_addresses = [value for value in external_addresses if value]

    endpoint_command = SFM_CMD_TEMPLATES["kubectl_get_endpoints_json"].format(
        name=expected["name"], namespace=TELEMETRY_NAMESPACE,
    )
    endpoints = _read_kubernetes_json(host, endpoint_command, resource)
    subsets = endpoints.get("subsets", [])
    if not isinstance(subsets, list) or any(
        not isinstance(value, dict) for value in subsets
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["k8s_shape_invalid"].format(resource=resource)
        )
    for subset in subsets:
        for field in ("addresses", "notReadyAddresses", "ports"):
            values = subset.get(field, [])
            if not isinstance(values, list) or any(
                not isinstance(value, dict) for value in values
            ):
                raise _SfmAutomationError(
                    SFM_ERROR_MSGS["k8s_shape_invalid"].format(
                        resource=resource,
                    )
                )
    ready_endpoints = sum(len(value.get("addresses", [])) for value in subsets)
    not_ready_endpoints = sum(
        len(value.get("notReadyAddresses", [])) for value in subsets
    )
    endpoint_ports = sorted({
        value.get("port")
        for subset in subsets
        for value in subset.get("ports", [])
        if isinstance(value.get("port"), int)
        and not isinstance(value.get("port"), bool)
    })
    expected_ports = set(expected["ports"])
    success = (
        metadata.get("name") == expected["name"]
        and specification.get("type") == expected["type"]
        and expected_ports == set(ports)
        and expected_ports == set(endpoint_ports)
        and (not expected["external_ip"] or bool(external_addresses))
        and (not expected_address or expected_address in external_addresses)
        and ready_endpoints > 0
        and not_ready_endpoints == 0
    )
    return {
        **expected,
        "success": success,
        "actual_type": str(specification.get("type", "")),
        "actual_ports": ports,
        "endpoint_ports": endpoint_ports,
        "external_addresses": external_addresses,
        "ready_endpoints": ready_endpoints,
        "not_ready_endpoints": not_ready_endpoints,
    }


def verify_sfm_omnia_services(host):
    """Verify exact Omnia services and ready endpoints required by SFM.

    Args:
        host: Testinfra connection to the OIM host.

    Returns:
        Standard result with per-service type, ports, and endpoint readiness.
    """
    try:
        if load_sfm_context() is None:
            return sfm_skip_result()
        export = _read_victoria_export(host)
        expected_addresses = {
            "vminsert": export["vminsert_ip"],
            "vmselect": export["vmselect_ip"],
        }
        services = [
            _service_status(
                host,
                expected,
                expected_addresses.get(expected["component"], ""),
            )
            for expected in SFM_REQUIRED_SERVICES
        ]
        failed = [
            service["component"] for service in services
            if not service["success"]
        ]
        detail_lines = [
            SFM_DETAIL_MSGS["omnia_service_line"].format(
                status_icon="\u2713" if service["success"] else "\u2717",
                component=service["component"],
                name=service["name"],
                service_type=service["actual_type"],
                ports=", ".join(
                    str(value) for value in service["actual_ports"]
                ),
                external=", ".join(service["external_addresses"])
                or SFM_DETAIL_MSGS["not_available"],
                ready_endpoints=service["ready_endpoints"],
                not_ready_endpoints=service["not_ready_endpoints"],
            )
            for service in services
        ]
        details = SFM_DETAIL_MSGS["omnia_services_ready"].format(
            namespace=TELEMETRY_NAMESPACE,
            services="\n".join(detail_lines),
        )
        if failed:
            return sfm_result(
                False,
                details=details,
                error=SFM_ERROR_MSGS["omnia_services_unready"].format(
                    components=", ".join(failed),
                ),
                services=services,
            )
        return sfm_result(True, details=details, services=services)
    except (OSError, ValueError, _SfmAutomationError) as exc:
        return sfm_result(False, error=str(exc))


def _ssh_client():
    """Build an SSH client that accepts only known host keys."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    return client


class _SfmSecureShell:
    """Paramiko session that navigates the SFM forced-menu SSH console."""

    def __init__(self, context):
        """Initialize an unopened secure-shell session from SFM context."""
        self.context = context
        self.jump_client = None
        self.client = None
        self.channel = None

    def __enter__(self):
        """Connect, enter the secure shell, and return this session."""
        try:
            self._connect()
            self._enter_secure_shell()
            return self
        except (OSError, EOFError, paramiko.SSHException, _SfmAutomationError):
            self.close()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        """Close all channels when leaving the context manager."""
        self.close()

    def close(self):
        """Close the SFM and optional OIM jump sessions."""
        if self.channel is not None:
            self.channel.close()
        if self.client is not None:
            self.client.close()
        if self.jump_client is not None:
            self.jump_client.close()

    def _connect(self):
        """Connect directly or through the configured OIM jump host."""
        connection = connection_params()
        sock = None
        if connection["mode"] == "ssh":
            self.jump_client = _ssh_client()
            self.jump_client.connect(
                hostname=connection["ip"],
                port=self.context["oim_ssh_port"],
                username=connection["user"],
                password=connection["auth_secret"],
                timeout=SFM_SSH_CONNECT_TIMEOUT_SECONDS,
                auth_timeout=SFM_SSH_AUTH_TIMEOUT_SECONDS,
                banner_timeout=SFM_SSH_BANNER_TIMEOUT_SECONDS,
                look_for_keys=not bool(connection["auth_secret"]),
                allow_agent=not bool(connection["auth_secret"]),
            )
            transport = self.jump_client.get_transport()
            if transport is None:
                raise _SfmAutomationError(SFM_ERROR_MSGS["ssh_jump_unavailable"])
            sock = transport.open_channel(
                SFM_SSH_CHANNEL_KIND,
                (self.context["ssh_ip"], self.context["ssh_port"]),
                (connection["ip"], 0),
            )

        self.client = _ssh_client()
        self.client.connect(
            hostname=self.context["ssh_ip"],
            port=self.context["ssh_port"],
            username=self.context["ssh_username"],
            password=self.context["ssh_password"],
            timeout=SFM_SSH_CONNECT_TIMEOUT_SECONDS,
            auth_timeout=SFM_SSH_AUTH_TIMEOUT_SECONDS,
            banner_timeout=SFM_SSH_BANNER_TIMEOUT_SECONDS,
            look_for_keys=False,
            allow_agent=False,
            sock=sock,
        )

    def _read_until(self, timeout, predicate=None, allow_idle=False):
        """Read channel output until a predicate, timeout, or menu idle."""
        end_time = time.monotonic() + timeout
        last_data_time = time.monotonic()
        chunks = []
        while time.monotonic() < end_time:
            if self.channel.recv_ready():
                chunks.append(
                    self.channel.recv(SFM_SSH_BUFFER_SIZE).decode(
                        "utf-8", errors="replace",
                    )
                )
                last_data_time = time.monotonic()
                output = "".join(chunks)
                if predicate is not None and predicate(output):
                    return output
                continue
            if (
                allow_idle
                and chunks
                and time.monotonic() - last_data_time >= SFM_SSH_IDLE_SECONDS
            ):
                break
            time.sleep(SFM_SSH_READ_INTERVAL_SECONDS)
        return "".join(chunks)

    def _send_line(self, value):
        """Send one complete UTF-8 line to the forced-menu channel."""
        self.channel.sendall(f"{value}\n".encode())

    @staticmethod
    def _has_shell_prompt(output):
        """Return whether normalized console output ends at a shell prompt."""
        without_ansi = re.sub(SFM_ANSI_ESCAPE_PATTERN, "", output)
        stripped = "".join(
            character for character in without_ansi
            if character in "\r\n\t" or ord(character) >= 32
        ).rstrip()
        return any(
            stripped.endswith(value.rstrip())
            for value in SFM_SHELL_PROMPT_SUFFIXES
        )

    def _verify_shell(self):
        """Prove menu navigation reached a command shell before mutations."""
        result = self.run(SFM_CMD_TEMPLATES["shell_probe"])
        if result["rc"] != 0 or SFM_SHELL_PROBE_OUTPUT not in result["stdout"]:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["ssh_shell_probe_failed"]
            )

    def _enter_secure_shell(self):
        """Navigate the appliance console and prove command-shell access."""
        self.channel = self.client.invoke_shell(
            width=SFM_SSH_TERMINAL_WIDTH,
            height=SFM_SSH_TERMINAL_HEIGHT,
        )
        first_output = self._read_until(
            SFM_SSH_MENU_TIMEOUT_SECONDS,
            predicate=self._has_shell_prompt,
            allow_idle=True,
        )
        if self._has_shell_prompt(first_output):
            self._verify_shell()
            self._disable_echo()
            return

        self._send_line(SFM_DEBUG_MENU_OPTION)
        debug_output = self._read_until(
            SFM_SSH_MENU_TIMEOUT_SECONDS,
            predicate=self._has_shell_prompt,
            allow_idle=True,
        )
        if self._has_shell_prompt(debug_output):
            self._verify_shell()
            self._disable_echo()
            return

        self._send_line(SFM_SECURE_SHELL_OPTION)
        shell_output = self._read_until(
            SFM_SSH_MENU_TIMEOUT_SECONDS,
            predicate=self._has_shell_prompt,
        )
        if not self._has_shell_prompt(shell_output):
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["ssh_menu_failed"].format(
                    error=shell_output.strip(),
                )
            )
        self._verify_shell()
        self._disable_echo()

    def _disable_echo(self):
        """Disable PTY echo so command output can be parsed deterministically."""
        self.run(SFM_CMD_TEMPLATES["disable_echo"])

    def run(self, command):
        """Run one command and parse the explicit exit-code marker."""
        wrapped = SFM_CMD_TEMPLATES["command_with_rc"].format(
            command=command,
            marker=SFM_COMMAND_RC_MARKER,
        )
        self._send_line(wrapped)
        marker_pattern = re.compile(
            rf"{re.escape(SFM_COMMAND_RC_MARKER)}\d+"
        )
        output = self._read_until(
            SFM_SSH_COMMAND_TIMEOUT_SECONDS,
            predicate=lambda value: (
                marker_pattern.search(value) is not None
                and self._has_shell_prompt(value)
            ),
        )
        match = re.search(
            rf"{re.escape(SFM_COMMAND_RC_MARKER)}(\d+)", output,
        )
        if match is None:
            raise _SfmAutomationError(SFM_ERROR_MSGS["ssh_rc_missing"])
        return {
            "rc": int(match.group(1)),
            "stdout": output[:match.start()].strip(),
        }


def _ready_sfm_prometheus_pod(shell, context):
    """Discover a running and ready SFM Prometheus pod dynamically."""
    namespace = SFM_NAMESPACE_TEMPLATE.format(
        instance_id=context["instance_id"],
    )
    command = SFM_CMD_TEMPLATES["get_pods_json"].format(namespace=namespace)
    command_result = shell.run(command)
    if command_result["rc"] != 0:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["ssh_command_failed"].format(
                error=command_result["stdout"],
            )
        )
    try:
        pod_data = json.loads(command_result["stdout"])
    except json.JSONDecodeError as exc:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["pods_json_invalid"].format(error=exc)
        ) from exc

    if not isinstance(pod_data, dict) or not isinstance(
        pod_data.get("items"), list,
    ):
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["pods_shape_invalid"]
        )
    ready_pods = []
    for item in pod_data["items"]:
        pod = _pod_status(item)
        if pod is None:
            raise _SfmAutomationError(SFM_ERROR_MSGS["pods_shape_invalid"])
        if not pod["name"].startswith(SFM_PROMETHEUS_POD_PREFIX):
            continue
        if (
            pod["ready"]
            and SFM_PROMETHEUS_CONTAINER in pod["container_names"]
        ):
            ready_pods.append(pod["name"])

    if not ready_pods:
        raise _SfmAutomationError(
            SFM_ERROR_MSGS["pod_missing"].format(namespace=namespace)
        )
    return {
        "namespace": namespace,
        "pod": min(ready_pods),
        "ready_count": len(ready_pods),
    }


def _normalized_hosts_content(content, hostname, address):
    """Replace every mapping for one hostname while preserving other lines."""
    kept_lines = []
    for line in content.splitlines():
        mapping, separator, comment = line.partition("#")
        fields = mapping.split()
        if fields and hostname in fields[1:]:
            fields = [fields[0], *(
                field for field in fields[1:] if field != hostname
            )]
            rebuilt = " ".join(fields) if len(fields) > 1 else ""
            if separator:
                rebuilt = f"{rebuilt}{' ' if rebuilt else ''}#{comment}"
            if rebuilt:
                kept_lines.append(rebuilt)
            continue
        kept_lines.append(line)
    kept_lines.append(f"{address} {hostname}")
    return "\n".join(kept_lines).rstrip() + "\n"


def _has_hosts_mapping(content, hostname, address):
    """Return whether exactly one correct mapping exists for a hostname."""
    matches = []
    for line in content.splitlines():
        fields = line.partition("#")[0].split()
        if fields and hostname in fields[1:]:
            matches.append(fields[0])
    return matches == [address]


def _ensure_sfm_hosts_mapping(context, export):
    """Ensure the current SFM Prometheus pod maps and reaches vminsert."""
    with _SfmSecureShell(context) as shell:
        pod = _ready_sfm_prometheus_pod(shell, context)
        read_command = SFM_CMD_TEMPLATES["read_pod_hosts"].format(
            namespace=pod["namespace"],
            pod=pod["pod"],
            container=SFM_PROMETHEUS_CONTAINER,
        )
        read_result = shell.run(read_command)
        if read_result["rc"] != 0:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["hosts_read_failed"].format(
                    pod=pod["pod"], error=read_result["stdout"],
                )
            )

        action = SFM_ACTIONS["reused"]
        if not _has_hosts_mapping(
            read_result["stdout"],
            SFM_REMOTE_WRITE_HOSTNAME,
            export["vminsert_ip"],
        ):
            action = SFM_ACTIONS["updated"]
            content = _normalized_hosts_content(
                read_result["stdout"],
                SFM_REMOTE_WRITE_HOSTNAME,
                export["vminsert_ip"],
            )
            write_command = SFM_CMD_TEMPLATES["write_pod_hosts"].format(
                content_b64=base64.b64encode(content.encode()).decode(),
                namespace=pod["namespace"],
                pod=pod["pod"],
                container=SFM_PROMETHEUS_CONTAINER,
            )
            write_result = shell.run(write_command)
            if write_result["rc"] != 0:
                raise _SfmAutomationError(
                    SFM_ERROR_MSGS["hosts_write_failed"].format(
                        pod=pod["pod"], error=write_result["stdout"],
                    )
                )
            verify_result = shell.run(read_command)
            if verify_result["rc"] != 0 or not _has_hosts_mapping(
                verify_result["stdout"],
                SFM_REMOTE_WRITE_HOSTNAME,
                export["vminsert_ip"],
            ):
                raise _SfmAutomationError(
                    SFM_ERROR_MSGS["hosts_verify_failed"]
                )

        network_command = SFM_CMD_TEMPLATES["check_pod_network"].format(
            namespace=pod["namespace"],
            pod=pod["pod"],
            container=SFM_PROMETHEUS_CONTAINER,
            timeout=SFM_NETWORK_TIMEOUT_SECONDS,
            hostname=SFM_REMOTE_WRITE_HOSTNAME,
            port=SFM_REMOTE_WRITE_PORT,
        )
        network_result = shell.run(network_command)
        if network_result["rc"] != 0:
            raise _SfmAutomationError(
                SFM_ERROR_MSGS["network_check_failed"].format(
                    pod=pod["pod"], error=network_result["stdout"],
                )
            )
    return {
        **pod,
        "action": action,
        "network": network_result["stdout"],
    }


def _prepare_remote_write_health(context, export):
    """Reapply ephemeral pod networking and convert failures for API rollback."""
    try:
        _ensure_sfm_hosts_mapping(context, export)
    except (
        OSError,
        EOFError,
        ValueError,
        paramiko.SSHException,
        _SfmAutomationError,
    ) as exc:
        raise SfmApiError(
            SFM_ERROR_MSGS["health_prerequisite_failed"].format(error=exc)
        ) from exc


def configure_sfm_switch(host):
    """Configure the complete SFM-side vminsert network prerequisite.

    Args:
        host: Testinfra connection to the OIM host.

    Returns:
        Standard result with Prometheus pod, hosts mapping, and network details.
    """
    try:
        context = load_sfm_context(require_ssh=True)
        if context is None:
            return sfm_skip_result()
        export = _read_victoria_export(host)
        pod = _ensure_sfm_hosts_mapping(context, export)
        details = SFM_DETAIL_MSGS["switch_ready"].format(
            namespace=pod["namespace"],
            pod=pod["pod"],
            container=SFM_PROMETHEUS_CONTAINER,
            ready_count=pod["ready_count"],
            vminsert_ip=export["vminsert_ip"],
            hostname=SFM_REMOTE_WRITE_HOSTNAME,
            action=pod["action"],
            port=SFM_REMOTE_WRITE_PORT,
        )
        return sfm_result(True, details=details, **pod)
    except (
        OSError,
        EOFError,
        ValueError,
        paramiko.SSHException,
        _SfmAutomationError,
    ) as exc:
        return sfm_result(False, error=str(exc))


def configure_sfm_observability(host):
    """Configure and health-check the complete SFM observability target.

    Args:
        host: Testinfra connection used to read Victoria export artifacts.

    Returns:
        Standard result with SFM IDs, action, readback, and target health.
    """
    try:
        context = load_sfm_context(require_api=True, require_ssh=True)
        if context is None:
            return sfm_skip_result()
        export = _read_victoria_export(host)
        pod = _ensure_sfm_hosts_mapping(context, export)
        prepare_health = partial(
            _prepare_remote_write_health, context, export,
        )
        api_result = _configure_remote_write(
            context,
            export["ca_bytes"],
            force_rotation=context["force_export"],
            prepare_health=prepare_health,
        )
        details = SFM_DETAIL_MSGS["observability_ready"].format(
            pod=pod["pod"],
            target=SFM_REMOTE_WRITE_TARGET_NAME,
            remote_write_id=api_result["remote_write_id"],
            import_id=api_result["import_id"],
            certificate=SFM_CA_CERTIFICATE_FILE,
            fingerprint=export["ca_fingerprint"],
            action=api_result["action"],
            warning=api_result["warning"],
            **api_result["health"],
        )
        return sfm_result(True, details=details, pod=pod, **api_result)
    except (
        OSError,
        EOFError,
        ValueError,
        paramiko.SSHException,
        SfmApiError,
        _SfmAutomationError,
    ) as exc:
        return sfm_result(False, error=str(exc))
