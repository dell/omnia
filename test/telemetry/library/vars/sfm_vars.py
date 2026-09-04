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

"""SFM observability validation constants and command templates."""

# =============================================================================
# SFM TEST CONFIGURATION
# =============================================================================

SFM_CONFIG_KEYS = {
    "enabled": "configure_sfm",
    "api_ip": "sfm_api_ip",
    "api_port": "sfm_api_port",
    "ssh_ip": "sfm_ssh_ip",
    "ssh_port": "sfm_ssh_port",
    "force_export": "force_external_victoria_playbook",
}

SFM_CREDENTIAL_KEYS = {
    "api_username": "sfm_api_username",
    "api_password": "sfm_api_password",
    "ssh_username": "sfm_ssh_username",
    "ssh_password": "sfm_ssh_password",
}

SFM_ACTIONS = {
    "reused": "reused",
    "updated": "updated",
    "created": "created",
}

SFM_MAX_NETWORK_PORT = 65535
SFM_OIM_SSH_PORT_KEY = "oim_ssh_port"
SFM_INSTANCE_ID = 1
SFM_API_VERIFY_TLS = False
SFM_DEFAULT_API_PORT = 443
SFM_DEFAULT_SSH_PORT = 22
SFM_REQUIRED_ENDPOINT_SETTINGS = ("api_ip", "ssh_ip")
SFM_PORT_DEFAULTS = {
    "api_port": SFM_DEFAULT_API_PORT,
    "ssh_port": SFM_DEFAULT_SSH_PORT,
}

# =============================================================================
# OMNIA VICTORIAMETRICS RESOURCES
# =============================================================================

SFM_VMCLUSTER_LABEL_SELECTOR = "app.kubernetes.io/instance=victoria-cluster"
SFM_POD_RUNNING_PHASE = "Running"
SFM_REQUIRED_WORKLOADS = (
    {
        "component": "vminsert",
        "kind_candidates": (("deployment", "Deployment"),),
        "name": "vminsert-victoria-cluster",
        "pod_prefix": "vminsert-victoria-cluster-",
    },
    {
        "component": "vmstorage",
        "kind_candidates": (("statefulset", "StatefulSet"),),
        "name": "vmstorage-victoria-cluster",
        "pod_prefix": "vmstorage-victoria-cluster-",
    },
    {
        "component": "vmselect",
        "kind_candidates": (
            ("deployment", "Deployment"),
            ("statefulset", "StatefulSet"),
        ),
        "name": "vmselect-victoria-cluster",
        "pod_prefix": "vmselect-victoria-cluster-",
    },
)
SFM_REQUIRED_SERVICES = (
    {
        "component": "vminsert",
        "name": "vminsert-victoria-cluster",
        "type": "LoadBalancer",
        "ports": (8480,),
        "external_ip": True,
    },
    {
        "component": "vmstorage",
        "name": "vmstorage-victoria-cluster",
        "type": "ClusterIP",
        "ports": (8482, 8400, 8401),
        "external_ip": False,
    },
    {
        "component": "vmselect",
        "name": "vmselect-victoria-cluster",
        "type": "LoadBalancer",
        "ports": (8481,),
        "external_ip": True,
    },
)

# =============================================================================
# EXTERNAL VICTORIA EXPORT
# =============================================================================

SFM_EXTERNAL_VICTORIA_TAG = "external_victoria"
SFM_EXTERNAL_VICTORIA_SUBDIR = "external_victoria"
SFM_EXTERNAL_VICTORIA_DETAILS_FILE = (
    "external_victoria_connect_details.yml"
)
SFM_CA_CERTIFICATE_FILE = "ca.crt"
SFM_CA_CERTIFICATE_CONTENT_TYPE = "application/x-x509-ca-cert"

SFM_DETAILS_KEYS = {
    "vminsert_ip": (
        "victoria_metrics", "endpoints", "vminsert", "host",
    ),
    "vmselect_ip": (
        "victoria_metrics", "endpoints", "vmselect", "host",
    ),
    "remote_write_url": (
        "victoria_metrics", "notes", "sfm", "vminsert_write_url",
    ),
}
SFM_EXPORTED_ENDPOINT_FIELDS = ("vminsert_ip", "vmselect_ip")

# =============================================================================
# SFM PROMETHEUS AND FORCED-MENU SSH CONSOLE
# =============================================================================

SFM_NAMESPACE_TEMPLATE = "sfm-{instance_id}"
SFM_PROMETHEUS_POD_PREFIX = "sfm-prometheus-deployment-"
SFM_PROMETHEUS_CONTAINER = "sfm-prometheus-container"
SFM_REMOTE_WRITE_HOSTNAME = (
    "vminsert-victoria-cluster.telemetry.svc.cluster.local"
)
SFM_REMOTE_WRITE_PORT = 8480
SFM_DEBUG_MENU_OPTION = "6"
SFM_SECURE_SHELL_OPTION = "12"
SFM_SHELL_PROMPT_SUFFIXES = ("$ ", "# ", "$", "#")
SFM_ANSI_ESCAPE_PATTERN = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
SFM_SHELL_PROBE_OUTPUT = "omnia-sfm-shell-ready"
SFM_SSH_CONNECT_TIMEOUT_SECONDS = 20
SFM_SSH_AUTH_TIMEOUT_SECONDS = 30
SFM_SSH_BANNER_TIMEOUT_SECONDS = 30
SFM_SSH_MENU_TIMEOUT_SECONDS = 30
SFM_SSH_COMMAND_TIMEOUT_SECONDS = 45
SFM_SSH_READ_INTERVAL_SECONDS = 0.1
SFM_SSH_IDLE_SECONDS = 0.8
SFM_SSH_BUFFER_SIZE = 65535
SFM_SSH_CHANNEL_KIND = "direct-tcpip"
SFM_SSH_TERMINAL_WIDTH = 200
SFM_SSH_TERMINAL_HEIGHT = 1000
SFM_COMMAND_RC_MARKER = "__OMNIA_SFM_RC__"
SFM_NETWORK_TIMEOUT_SECONDS = 10

# =============================================================================
# SFM REST API
# =============================================================================

SFM_API_SCHEME = "https"
SFM_API_TIMEOUT_SECONDS = 30
SFM_API_RESPONSE_PREVIEW_LENGTH = 240
SFM_API_REDACTED_PREVIEW = "<redacted>"
SFM_API_AUTH_HEADER = "Authorization"
SFM_API_BEARER_TEMPLATE = "Bearer {token}"
SFM_API_MULTIPART_FIELD = ""
SFM_API_UNAUTHORIZED_STATUS = 401
SFM_ACCESS_TOKEN_KEYS = (
    "accessToken", "access_token", "token",
)

SFM_HTTP_METHODS = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "delete": "DELETE",
}

SFM_HTTP_SUCCESS = {
    "login": (200,),
    "read": (200,),
    "create": (200, 201),
    "update": (200, 201),
    "delete": (200, 202, 204),
}

SFM_API_PATHS = {
    "login": "/security/v1/auth/login",
    "remote_write": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite"
    ),
    "remote_write_list": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite"
        "?$expand=RemoteWrite&$source=config"
    ),
    "remote_write_item": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite"
        "('{remote_write_id}')"
    ),
    "certificate_import": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite/"
        "CertificateImport"
    ),
    "certificate_import_item": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite/"
        "CertificateImport('{import_id}')"
    ),
    "certificate_import_detail": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite/"
        "CertificateImport('{import_id}')?$source=config"
    ),
    "server_certificate": (
        "/redfish/v1/SFM/{instance_id}/Observability/RemoteWrite/"
        "CertificateImport('{import_id}')/ServerCertificate"
    ),
    "query_range": "/api/v1/{instance_id}/query_range",
}

SFM_API_RESPONSE_KEYS = {
    "remote_write_table": "RemoteWriteConfigTable",
    "remote_write_id": "RemoteWriteId",
    "import_id": "ImportId",
    "server_certificate_file": "ServerCertificateFileName",
    "status": "status",
    "data": "data",
    "result": "result",
    "values": "values",
    "metric": "metric",
}

SFM_API_REQUEST_FIELDS = {
    "username": "username",
    "password": "password",
    "target_name": "TargetName",
    "url": "Url",
    "state": "State",
    "message_version": "MessageVersion",
    "authorization_type": "AuthorizationType",
    "tls_verify": "TlsServerCertificateVerify",
    "oauth_config": "OAuth2Config",
    "certificate_import_id": "CertificateImportId",
}

SFM_REMOTE_WRITE_TARGET_NAME = "victoria"
SFM_REMOTE_WRITE_URL = (
    "https://vminsert-victoria-cluster.telemetry.svc.cluster.local:8480/"
    "insert/0/prometheus/api/v1/write"
)
SFM_REMOTE_WRITE_STATE = "Enable"
SFM_REMOTE_WRITE_MESSAGE_VERSION = "v1"
SFM_REMOTE_WRITE_AUTHORIZATION_TYPE = "None"
SFM_REMOTE_WRITE_TLS_VERIFY = "true"
SFM_REMOTE_WRITE_OAUTH_CONFIG = {
    "ClientId": "",
    "ClientSecret": "",
    "TokenUrl": "",
}

SFM_REMOTE_WRITE_FIELDS = tuple(
    SFM_API_REQUEST_FIELDS[field]
    for field in (
        "target_name",
        "url",
        "state",
        "message_version",
        "authorization_type",
        "tls_verify",
        "oauth_config",
        "certificate_import_id",
    )
)

# =============================================================================
# SFM REMOTE WRITE HEALTH
# =============================================================================

_SFM_HEALTH_SELECTOR = (
    'remote_name="victoria",url="'
    f'{SFM_REMOTE_WRITE_URL}'
    '"'
)
SFM_HEALTH_QUERIES = {
    "bytes_total": (
        "rate(prometheus_remote_storage_bytes_total{"
        f"{_SFM_HEALTH_SELECTOR}"
        "}[5m])*300"
    ),
    "samples_total": (
        "rate(prometheus_remote_storage_samples_total{"
        f"{_SFM_HEALTH_SELECTOR}"
        "}[5m])*300"
    ),
    "retried_samples": (
        "rate(prometheus_remote_storage_samples_retried_total{"
        f"{_SFM_HEALTH_SELECTOR}"
        "}[5m])*300"
    ),
    "failed_samples": (
        "rate(prometheus_remote_storage_samples_failed_total{"
        f"{_SFM_HEALTH_SELECTOR}"
        "}[5m])*300"
    ),
    "pending_samples": (
        "prometheus_remote_storage_samples_pending{"
        f"{_SFM_HEALTH_SELECTOR}"
        "}"
    ),
}
SFM_REQUIRED_HEALTH_QUERIES = (
    "bytes_total",
    "samples_total",
    "pending_samples",
)
SFM_QUERY_RANGE_WINDOW_SECONDS = 300
SFM_QUERY_RANGE_STEP_SECONDS = 60
SFM_HEALTH_POLL_ATTEMPTS = 6
SFM_HEALTH_POLL_INTERVAL_SECONDS = 10
SFM_MAX_FAILED_SAMPLES = 0
SFM_MAX_PENDING_GROWTH = 0
SFM_MAX_HEALTH_SAMPLE_AGE_SECONDS = 180
SFM_API_DELETE_POLL_ATTEMPTS = 5
SFM_API_DELETE_POLL_INTERVAL_SECONDS = 2

# =============================================================================
# SFM METRICS
# =============================================================================

SFM_EXPECTED_METRICS = (
    "transceiver_dom_temperature_value",
    "transceiver_dom_voltage_value",
    "transceiver_dom_wavelength_value",
)
SFM_METRIC_IDENTITY_LABELS = (
    "instance",
    "interface_name",
    "job",
    "switch_id",
    "type",
    "vendor",
)
SFM_TIMESTAMP_QUERY_TEMPLATE = "timestamp({selector})"
SFM_MAX_METRIC_AGE_SECONDS = 300
SFM_METRIC_RANGE_WINDOW_SECONDS = 900
SFM_METRIC_RANGE_STEP_SECONDS = 30
SFM_METRIC_QUERY_TIMEOUT_SECONDS = 15
SFM_VM_POLL_ATTEMPTS = 6
SFM_VM_POLL_INTERVAL_SECONDS = 10

# =============================================================================
# SFM COMMAND TEMPLATES
# =============================================================================

SFM_CMD_TEMPLATES = {
    "disable_echo": "stty -echo",
    "shell_probe": "printf '%s\\n' 'omnia-sfm-shell-ready'",
    "read_file_base64": "base64 -w0 {path} 2>/dev/null",
    "get_pods_json": "kubectl get pods -n {namespace} -o json",
    "read_pod_hosts": (
        "kubectl exec -n {namespace} {pod} -c {container} -- "
        "cat /etc/hosts"
    ),
    "write_pod_hosts": (
        "printf '%s' '{content_b64}' | base64 -d | "
        "kubectl exec -i -n {namespace} {pod} -c {container} -- "
        "sh -c 'cat > /etc/hosts'"
    ),
    "check_pod_network": (
        "kubectl exec -n {namespace} {pod} -c {container} -- sh -c '"
        "if command -v nc >/dev/null 2>&1; then "
        "nc -zvw {timeout} {hostname} {port}; "
        "elif command -v busybox >/dev/null 2>&1; then "
        "busybox nc -z -w {timeout} {hostname} {port}; "
        "else exit 127; fi'"
    ),
    "command_with_rc": (
        "{command}; printf '\\n{marker}%s\\n' \"$?\""
    ),
    "kubectl_get_workload_json": (
        "kubectl get {kind} {name} -n {namespace} -o json 2>/dev/null"
    ),
    "kubectl_get_endpoints_json": (
        "kubectl get endpoints {name} -n {namespace} -o json 2>/dev/null"
    ),
    "vm_query_range": (
        "curl -sk --max-time {timeout} 'https://{vmselect_ip}:{vmselect_port}"
        "/select/0/prometheus/api/v1/query_range?query={query}"
        "&start={start}&end={end}&step={step}'"
    ),
}
