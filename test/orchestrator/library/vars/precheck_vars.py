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

# ── OIM readiness thresholds ────────────────────────────────────────
OIM_MIN_CPU_CORES = 4
OIM_MIN_MEMORY_GB = 16
OIM_MIN_DISK_GB = 100

# ── OIM readiness commands ──────────────────────────────────────────
OIM_READINESS_COMMANDS: dict[str, str] = {
    "cpu_cores": "nproc 2>/dev/null",
    "memory_kb": "grep MemTotal /proc/meminfo | awk '{print $2}'",
    "disk_gb": "df -BG / | tail -1 | awk '{print $2}' | tr -d 'G'",
    "nic_operstate": "cat /sys/class/net/%s/operstate 2>/dev/null",
    "nic_ipv4": "ip -4 -o addr show %s scope global",
    "ssh_check": (
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
        "-o BatchMode=yes %s whoami 2>/dev/null"
    ),
    "os_release": "grep -E '^(ID=|VERSION_ID=)' /etc/os-release",
    "internet_ping": "ping -c 1 -W 5 -- %s",
}

INTERNET_CHECK_HOSTS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1", "208.67.222.222")
