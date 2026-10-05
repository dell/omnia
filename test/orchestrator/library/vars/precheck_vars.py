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

"""Immutable contracts for Orchestrator precheck verification."""

ENV_SYSTEM_HOSTNAME = "SYSTEM_HOSTNAME"
ENV_SYSTEM_DOMAIN_NAME = "SYSTEM_DOMAIN_NAME"
ENV_SYSTEM_ADMIN_IPV4 = "SYSTEM_ADMIN_NIC_IPV4"
ENV_OMNIA_DATA_PATH = "OMNIA_DATA_PATH"
ENV_IMAGE_BUILD_MANAGER_DATA_PATH = "IMAGE_BUILD_MANAGER_DATA_PATH"
ENV_REPO_MANAGER_DATA_PATH = "REPO_MANAGER_DATA_PATH"

REQUIRED_PROJECT_INPUTS: tuple[str, ...] = (
    "orchestrator_config.yml",
    "omnia_config.yml",
    "network_spec.yml",
)

PRECHECK_COMMANDS: dict[str, str] = {
    "hostname_short": "hostname -s 2>/dev/null",
    "hostname_domain": "hostname -d 2>/dev/null",
    "local_ipv4": "ip -o -4 address show scope global",
    "ping": "ping -c %s -W %s -- %s",
    "http_head": (
        "curl -k -sS -L -I --connect-timeout %s --max-time %s "
        "-o /dev/null -w '%%{http_code}' -- %s"
    ),
    "http_get": (
        "curl -k -sS -L --connect-timeout %s --max-time %s "
        "-o /dev/null -w '%%{http_code}' -- %s"
    ),
}

NFS_PING_COUNT = 2
NFS_PING_TIMEOUT_SECONDS = 3
HTTP_CONNECT_TIMEOUT_SECONDS = 5
HTTP_REQUEST_TIMEOUT_SECONDS = 20
