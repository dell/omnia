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

"""Immutable contracts for Orchestrator provision verification."""

PROVISION_REPORT = "provisioning_report.yml"
ORCHESTRATOR_INVENTORY = "orchestrator_inventory.yml"
FUNCTIONAL_GROUP_CONFIG = ".data/functional_groups_config.yml"
DEFAULT_MAPPING_FILE = "pxe_mapping_file.csv"
ORCHESTRATOR_CONFIG = "orchestrator_config.yml"

REQUIRED_MAPPING_COLUMNS: tuple[str, ...] = (
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
)

OPENCHAMI_API_PATHS: dict[str, str] = {
    "components": "/hsm/v2/State/Components",
    "ethernet": "/hsm/v2/Inventory/EthernetInterfaces",
    "smd_groups": "/hsm/v2/groups",
    "boot_configurations": "/boot-service/bootconfigurations",
    "boot_nodes": "/boot-service/nodes",
    "metadata_groups": "/metadata-service/groups",
    "instance_infos": "/metadata-service/instanceinfos",
}

COMMON_METADATA_GROUPS: frozenset[str] = frozenset({"ssh", "chrony"})
ADDITIONAL_METADATA_PREFIX = "additional_metadata_svc"
BOOT_SERVICE_SYNC_RETRIES = 25
BOOT_SERVICE_SYNC_DELAY_SECONDS = 15

PROVISION_COMMANDS: dict[str, str] = {
    # Generate a fresh token for every read. Retry authentication once because
    # TokenSmith may rotate credentials between token creation and the request.
    "api_get": (
        "sudo bash -lc '"
        "response=$(mktemp /tmp/omnia-openchami-api.XXXXXX) || exit 9; "
        "trap '\"'\"'rm -f -- \"$response\"'\"'\"' EXIT; "
        'attempt=1; while [ "$attempt" -le 2 ]; do '
        "token=$(gen_access_token 2>/dev/null) || exit 10; "
        'test -n "$token" || exit 10; '
        "code=$(curl -sS --connect-timeout 5 --max-time 30 "
        '-o "$response" -w "%%{http_code}" '
        '-H "Authorization: Bearer $token" "$1"); curl_rc=$?; '
        'test "$curl_rc" -eq 0 || exit 11; '
        'case "$code" in '
        '2??) cat "$response"; exit 0 ;; '
        "401|403) attempt=$((attempt + 1)); continue ;; "
        '*) cat "$response" >&2; exit 12 ;; '
        "esac; done; exit 13"
        "' -- %s"
    ),
}
