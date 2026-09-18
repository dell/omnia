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

"""UFM telemetry component constants and command templates."""

UFM_SOURCE_NAME = "ufm"

UFM_SVC_NAME = "ufm-external"
UFM_VMSCRAPE_NAME = "ufm-infiniband-metrics"
# Kubernetes Secret object name, not a credential value.
UFM_SECRET_NAME = "ufm-telemetry-credentials"  # noqa: S105

UFM_EXPECTED_METRICS = [
    "infiniband_CBW",
    "PortXmitDataExtended",
    "PortRcvDataExtended",
    "PortXmitPktsExtended",
    "PortRcvPktsExtended",
    "LinkDownedCounterExtended",
]

CFG_KEY_UFM_METRICS_ENABLED = "telemetry_sources.ufm.metrics_enabled"
CFG_KEY_UFM_ENDPOINT = "ufm_configuration.ufm_endpoint"
CFG_KEY_UFM_PORT = "ufm_configuration.ufm_metrics_port"

UFM_DEFAULT_METRICS_PORT = "9001"
UFM_DEFAULT_METRICS_PATH = "/metrics"
UFM_UTC_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S UTC"

UFM_CMD_TEMPLATES = {
    "get_service_json": (
        "kubectl get svc {name} -n {namespace} -o json 2>/dev/null"
    ),
    "get_endpoints_json": (
        "kubectl get endpoints {name} -n {namespace} -o json 2>/dev/null"
    ),
    "get_vmscrape_json": (
        "kubectl get vmservicescrape {name} -n {namespace} "
        "-o json 2>/dev/null"
    ),
    "get_secret_json": (
        "kubectl get secret {name} -n {namespace} -o json 2>/dev/null"
    ),
}
