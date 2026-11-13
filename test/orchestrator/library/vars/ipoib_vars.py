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

"""Immutable contracts for ER-ORCH-005 IPoIB input and post-boot checks."""

import os
import re
import tempfile

IB_NETWORK_KEY = "ib_network"
IB_MODE_DUAL_STACK = "dual-stack"
IB_MODE_IPV6_ONLY = "ipv6-only"
IB_MODE_IPV4_ONLY = "ipv4-only"
IPV6_MODES: frozenset[str] = frozenset({IB_MODE_DUAL_STACK, IB_MODE_IPV6_ONLY})
# Address families each ib_addr_mode assigns on the IB interface. Every
# post-boot check validates each family listed for the active mode.
IB_MODE_FAMILIES: dict[str, tuple[int, ...]] = {
    IB_MODE_IPV4_ONLY: (4,),
    IB_MODE_IPV6_ONLY: (6,),
    IB_MODE_DUAL_STACK: (6, 4),
}
SLURM_ENABLE_IPV6 = "EnableIPv6"

NETWORK_SPEC_FILE = "network_spec.yml"
ORCHESTRATOR_CONFIG_FILE = "orchestrator_config.yml"
MAPPING_PATH_KEY = "pxe_mapping_file_path"
LEGACY_IB_COLUMN = "IB_IP"
CANONICAL_MAPPING_HEADERS: tuple[str, ...] = (
    "FUNCTIONAL_GROUP_NAME",
    "GROUP_NAME",
    "SERVICE_TAG",
    "PARENT_SERVICE_TAG",
    "HOSTNAME",
    "ADMIN_MAC",
    "ADMIN_IP",
    "BMC_MAC",
    "BMC_IP",
    "IB_NIC_NAME",
    "IB_IPV4",
    "IB_IPV6",
)
IB_COLUMNS: tuple[str, ...] = ("IB_NIC_NAME", "IB_IPV4", "IB_IPV6")
MIN_IB_ROWS = 2
DEFAULT_IB_NIC_NAME = "InfiniBand.Slot.1-1"
SAFE_NIC_NAME = re.compile(r"^[A-Za-z0-9.-]{1,64}$")

# Every input case runs against a scratch clone of the active project input.
# The active project input is never edited.
SCRATCH_PROJECT_PREFIX = "omnia_fvt_ipoib_"
SCRATCH_PROJECT_PATTERN = re.compile(r"^omnia_fvt_ipoib_[0-9a-f]{8}$")
VALIDATE_TAG = "validate"
PROJECT_EXTRA_VAR = "project_name"
VALIDATE_TIMEOUT_SECONDS = 900
VALIDATION_RAN_MARKER = "Validation log:"
VALIDATION_ERROR_LABELS: tuple[str, ...] = (
    "network_spec",
    "orchestrator_config",
    "omnia_config",
    "storage_config",
)
VALIDATION_ERROR_LINE = re.compile(
    r'^\s*"msg":\s*(?P<message>"(?:[^"\\]|\\.)*")\s*,?\s*$'
)
EVIDENCE_SUBDIR = "ipoib_inputs"
REMOTE_WRITE_CHUNK = 32768
MAX_REPORTED_ERRORS = 5

# Mapping value specifications resolved against the populated clone.
ALL_IB_ROWS = "*"
COPY_FROM = "copy"  # ("copy", row, column)
EXPLODED_FROM = "exploded"  # ("exploded", row, column)
OUTSIDE_PREFIX = "outside"  # ("outside",)

EXPECT_REJECT = "reject"
EXPECT_ACCEPT = "accept"
SCHEMA_REJECTION = "is not valid under any of the given schemas"

# network:   ib_network overlay; None removes the key and {tokens} are derived
#            from the active ib_network IPv6 subnet.
# mapping:   (row, column, value-spec) applied to the populated Slurm compute
#            rows of the clone; row "*" selects every populated row.
# fragments: every fragment must appear in one error that the baseline run of
#            the unmodified clone did not report. {value} is the last value set.
IPOIB_INPUT_CASES: dict[str, dict[str, object]] = {
    "ipoib_input_ipv4_only_ignores_ipv6_subnet": {
        "expect": EXPECT_ACCEPT,
        "network": {"ib_addr_mode": IB_MODE_IPV4_ONLY},
        "mapping": ((ALL_IB_ROWS, "IB_IPV6", ""),),
    },
    "ipoib_input_mode_defaults_to_ipv4_only": {
        "expect": EXPECT_ACCEPT,
        "network": {
            "ib_addr_mode": None,
            "ipv6_subnet": None,
            "ipv6_netmask_bits": None,
        },
        "mapping": ((ALL_IB_ROWS, "IB_IPV6", ""),),
    },
    "ipoib_input_dual_stack_accepted": {
        "expect": EXPECT_ACCEPT,
        "network": {"ib_addr_mode": IB_MODE_DUAL_STACK},
    },
    "ipoib_input_empty_ib_columns_skipped": {
        "expect": EXPECT_ACCEPT,
        "mapping": tuple((1, column, "") for column in IB_COLUMNS),
    },
    "ipoib_input_ipv6_only_without_ipv4": {
        "expect": EXPECT_ACCEPT,
        "network": {"ib_addr_mode": IB_MODE_IPV6_ONLY},
        "mapping": ((ALL_IB_ROWS, "IB_IPV4", ""),),
    },
    "neg_ipoib_ipv6_subnet_malformed": {
        "expect": EXPECT_REJECT,
        "network": {"ipv6_subnet": "omnia-fvt-invalid-ipv6"},
        "fragments": (
            "ib_network.ipv6_subnet is not a valid IPv6 network address",
        ),
    },
    "neg_ipoib_ipv6_prefix_length_invalid": {
        "expect": EXPECT_REJECT,
        "network": {"ipv6_netmask_bits": "129"},
        "fragments": ("'ipv6_netmask_bits': '{value}'", SCHEMA_REJECTION),
    },
    "neg_ipoib_dual_stack_missing_ipv6_subnet": {
        "expect": EXPECT_REJECT,
        "network": {
            "ib_addr_mode": IB_MODE_DUAL_STACK,
            "ipv6_subnet": "",
            "ipv6_netmask_bits": "",
        },
        "fragments": ("ib_network", "ipv6_subnet"),
    },
    "neg_ipoib_addr_mode_unsupported": {
        "expect": EXPECT_REJECT,
        "network": {"ib_addr_mode": "omnia-fvt-unsupported"},
        "fragments": ("'ib_addr_mode': '{value}'", SCHEMA_REJECTION),
    },
    "neg_ipoib_gateway_input": {
        "expect": EXPECT_REJECT,
        "network": {"gateway": "{ipv6_host_1}"},
        "fragments": ("'gateway':", SCHEMA_REJECTION),
    },
    "neg_ipoib_static_route_input": {
        "expect": EXPECT_REJECT,
        "network": {"routes": ["{ipv6_cidr}"]},
        "fragments": ("'routes':", SCHEMA_REJECTION),
    },
    "neg_ipoib_default_route_input": {
        "expect": EXPECT_REJECT,
        "network": {"default_route": "{ipv6_host_1}"},
        "fragments": ("'default_route':", SCHEMA_REJECTION),
    },
    "neg_ipoib_pxe_ipv6_unparseable": {
        "expect": EXPECT_REJECT,
        "mapping": ((0, "IB_IPV6", "omnia-fvt-invalid-ipv6"),),
        "fragments": ("IB_IPV6 '{value}'", "is not a valid IPv6 address"),
    },
    "neg_ipoib_pxe_ipv4_unparseable": {
        "expect": EXPECT_REJECT,
        "mapping": ((0, "IB_IPV4", "omnia-fvt-invalid-ipv4"),),
        "fragments": ("IB_IPV4 '{value}'",),
    },
    "neg_ipoib_pxe_ipv4_in_ipv6_column": {
        "expect": EXPECT_REJECT,
        "mapping": ((0, "IB_IPV6", (COPY_FROM, 0, "IB_IPV4")),),
        "fragments": ("IB_IPV6 '{value}'", "is not a valid IPv6 address"),
    },
    "neg_ipoib_pxe_ipv6_duplicate": {
        "expect": EXPECT_REJECT,
        "mapping": ((1, "IB_IPV6", (COPY_FROM, 0, "IB_IPV6")),),
        "fragments": ("Duplicate IB_IPV6", "{value}"),
    },
    "neg_ipoib_pxe_ipv6_duplicate_expanded": {
        "expect": EXPECT_REJECT,
        "mapping": ((1, "IB_IPV6", (EXPLODED_FROM, 0, "IB_IPV6")),),
        "fragments": ("Duplicate IB_IPV6",),
    },
    "neg_ipoib_pxe_ipv6_without_nic_name": {
        "expect": EXPECT_REJECT,
        "mapping": ((0, "IB_NIC_NAME", ""), (0, "IB_IPV4", "")),
        "fragments": ("has IB_IPV6 set but IB_NIC_NAME is empty",),
    },
    "neg_ipoib_pxe_ipv6_outside_prefix": {
        "expect": EXPECT_REJECT,
        "mapping": ((0, "IB_IPV6", (OUTSIDE_PREFIX,)),),
        "fragments": ("IB_IPV6", "{value}"),
    },
    "neg_ipoib_pxe_dual_stack_missing_ipv6": {
        "expect": EXPECT_REJECT,
        "network": {"ib_addr_mode": IB_MODE_DUAL_STACK},
        "mapping": ((0, "IB_IPV6", ""),),
        "fragments": ("IB_IPV6",),
    },
    "neg_ipoib_pxe_dual_stack_missing_ipv4": {
        "expect": EXPECT_REJECT,
        "network": {"ib_addr_mode": IB_MODE_DUAL_STACK},
        "mapping": ((0, "IB_IPV4", ""),),
        "fragments": ("IB_IPV4",),
    },
}

NM_PROFILE_FIELDS: tuple[str, ...] = (
    "ipv4.method",
    "ipv4.addresses",
    "ipv4.gateway",
    "ipv6.method",
    "ipv6.addresses",
    "ipv6.gateway",
    "ipv6.ip6-privacy",
)
IPOIB_COMMANDS: dict[str, str] = {
    "path_absent": "test ! -e %s",
    "make_private_dir": "mkdir -m 0700 -- %s",
    "make_parent_dirs": "mkdir -p -- %s",
    "list_input_files": "find %s -maxdepth 1 -type f -printf '%%f\\n'",
    "copy_file": "cp -p -- %s %s",
    "write_base64_first": "printf '%%s' %s | base64 -d > %s",
    "write_base64_append": "printf '%%s' %s | base64 -d >> %s",
    # The validator rejects a PXE mapping that is group-writable or readable
    # by others, so every generated scratch input is owner-writable only.
    "restrict_file": "chmod 0640 -- %s",
    "remove_scratch": "rm -rf -- %s",
    # Node-side templates; values are validated and shlex-quoted before use.
    "ip_addresses": "ip -j address show",
    "nm_profile": "nmcli -g " + ",".join(NM_PROFILE_FIELDS) + " connection show %s",
    # Family-generic templates: the first %s is the family (4 or 6).
    "routes_on_dev": "ip -j -%s route show dev %s",
    "default_routes": "ip -j -%s route show default",
    "route_to": "ip -j -%s route get %s",
    "ping_from_iface": "ping -%s -c 1 -W %s -I %s %s",
    "ping": "ping -%s -c 1 -W %s %s",
    "slurm_show_config": "scontrol show config",
}
# NetworkManager methods configure-ib-network.sh sets for each ib_addr_mode.
# ipv4-only leaves IPv6 unmanaged (the profile keeps the NetworkManager
# default), so ipv6.method is not part of the ipv4-only contract; the absence
# of any global IPv6 on the IB interface is enforced by the address checks.
NM_EXPECTED_METHODS: dict[str, dict[str, str]] = {
    IB_MODE_DUAL_STACK: {"ipv4.method": "manual", "ipv6.method": "manual"},
    IB_MODE_IPV6_ONLY: {"ipv4.method": "disabled", "ipv6.method": "manual"},
    IB_MODE_IPV4_ONLY: {"ipv4.method": "manual"},
}
NM_PRIVACY_DISABLED: frozenset[str] = frozenset({"0", "disabled", "0 (disabled)"})
UNHEALTHY_IPV6_FLAGS: tuple[str, ...] = ("tentative", "dadfailed", "deprecated")
# Flags marking an address as DHCP/SLAAC-assigned rather than static.
DYNAMIC_ADDRESS_FLAGS: tuple[str, ...] = ("dynamic", "temporary", "mngtmpaddr")
SAFE_IFACE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
PING_TIMEOUT_SECONDS = 2
SLURM_UNRESPONSIVE_STATES: frozenset[str] = frozenset(
    {"down", "fail", "unknown", "future"}
)
SLURM_STATE_FLAG_SUFFIXES = "*~#!%$@^-"
SLURM_CONFIG_SOURCES_KEY = "config_sources"
SLURM_CONFIG_SOURCE = "slurm"

# ---------------------------------------------------------------------------
# Resilience, recovery, and PowerVault coexistence (TC-FVT-016/020/024/025/026)
# ---------------------------------------------------------------------------
# Node-side templates; every substituted value is validated and shlex-quoted.
IPOIB_RESILIENCE_COMMANDS: dict[str, str] = {
    "lsmod": "lsmod",
    "ofed": "ofed_info -s",
    "netdev_map": "ibdev2netdev",
    "ipv6_addr_dev": "ip -6 addr show dev %s",
    "ipv6_route_dev": "ip -6 route show dev %s",
    "use_tempaddr": "sysctl net.ipv6.conf.%s.use_tempaddr",
    "ipv6_addr_del": "ip -6 addr del %s/%s dev %s",
    "ipv6_addr_add": "ip -6 addr add %s/%s dev %s",
    "nm_device_reapply": "nmcli device reapply %s",
    "route_get": "ip -j route get %s",
    "routes_dev": "ip -j -%s route show dev %s",
    "ib_reprovision_present": "test -x /usr/local/bin/configure-ib-network.sh",
    "ib_reprovision": "bash /usr/local/bin/configure-ib-network.sh",
    "controller_services": "systemctl is-active slurmctld slurmdbd mariadb munge",
    "slurmctld_active": "systemctl is-active slurmctld",
    "slurmdbd_database": (
        "sacctmgr --noheader --parsable2 show cluster format=Cluster"
    ),
    "munge_roundtrip": "munge -n | unmunge",
    "slurm_conf": "cat /etc/slurm/slurm.conf",
    "slurm_node_line": "scontrol show node %s --oneliner",
    "hold_job": (
        "sbatch --parsable --nodes=1 --ntasks=1 --nodelist=%s "
        "--job-name=omnia-fvt-ib-hold --output=/dev/null --wrap='sleep %s'"
    ),
    "job_state": (
        "state=$(squeue --noheader --jobs=%s --format=%%T 2>/dev/null | head -1); "
        'if test -z "$state"; then state=$(sacct --noheader --parsable2 '
        "--jobs=%s --format=State | head -1); fi; printf '%%s' \"$state\""
    ),
    "cancel_job": "scancel %s",
    "iscsi_session_detail": "iscsiadm -m session -P 1",
    "findmnt_mountpoint": "findmnt -n -o TARGET,SOURCE,FSTYPE,OPTIONS --mountpoint %s",
    "findmnt_all": "findmnt -rn -o TARGET,SOURCE",
    "path_accessible": "test -r %s && test -x %s",
    "resolv_attributes": 'lsattr -d "$(readlink -f /etc/resolv.conf)"',
    "state_dir_rw": (
        "probe=%s/.omnia_fvt_ib_probe.$$; printf ok > \"$probe\" && "
        'test "$(cat "$probe")" = ok; rc=$?; rm -f -- "$probe"; exit $rc'
    ),
    "mpi_workspace": "install -d -m 0700 %s && printf %%s %s | base64 -d > %s",
    "mpi_workspace_cleanup": (
        "find %s -mindepth 1 -delete 2>/dev/null; rmdir %s 2>/dev/null || true"
    ),
}
IPOIB_KERNEL_MODULES: tuple[str, ...] = ("mlx5_ib", "ib_ipoib", "ib_umad", "ib_uverbs")
IPOIB_MIN_MTU = 2044
IPOIB_PING_ATTEMPTS = 3
IPOIB_RESTORE_TIMEOUT_SECONDS = 90
IPOIB_RESTORE_POLL_SECONDS = 5
IPOIB_REPROVISION_TIMEOUT_SECONDS = 300
IPOIB_HOLD_JOB_SECONDS = 3600
IPOIB_HOLD_JOB_START_TIMEOUT_SECONDS = 120
IPOIB_MIN_MULTI_REBOOT_NODES = 3
IPOIB_INTERRUPTED_JOB_STATES: frozenset[str] = frozenset(
    {"FAILED", "NODE_FAIL", "CANCELLED", "BOOT_FAIL", "PREEMPTED", "TIMEOUT",
     "OUT_OF_MEMORY", "REQUEUED"}
)
IPOIB_UNDISTURBED_JOB_STATES: frozenset[str] = frozenset({"RUNNING", "COMPLETED"})
IPOIB_HEALTHY_PEER_STATES: frozenset[str] = frozenset(
    {"idle", "allocated", "mixed", "completing"}
)
IPOIB_CONTROLLER_NFS_PATHS: tuple[str, ...] = ("/etc/slurm", "/etc/munge", "/var/log/slurm")
IPOIB_SLURMCTLD_STATE_DIR = "/var/spool/slurmctld"
IPOIB_MYSQL_DIR = "/var/lib/mysql"
# UCX transports that prove MPI traffic uses InfiniBand: if rc/ud are unusable
# UCX cannot wire up inter-node endpoints and the job fails.
IPOIB_MPI_UCX_TLS = "self,sm,rc,ud"
IPOIB_MPI_RESULT = re.compile(r"^(\d+)/(\d+)\|([A-Za-z0-9_.-]+)$")
IPOIB_OPENMPI_RECORD = re.compile(r"^(OPENMPI_EXECUTABLE|OPENMPI_COMPILER)\|(.+)$")
# Product health classifier, loaded from the source tree so verdicts come from
# the shipped ER-ORCH-005 decision matrix rather than a test reimplementation.
ADDRESS_VERIFIER_PATH: tuple[str, ...] = (
    "src", "orchestrator", "plugins", "module_utils",
    "orchestrator_validation", "renderers", "address_verifier.py",
)
HEALTH_HEALTHY = "HEALTHY"
HEALTH_DEGRADED_IPV6 = "DEGRADED_IPV6"
STAGE_ADDRESS_STATE = "address_state"
# TC-FVT-016: a recovery record must carry these fields.
RECOVERY_RECORD_FIELDS: tuple[str, ...] = ("retryable", "corrective_action")

# ---------------------------------------------------------------------------
# Slurm communication path verification (TC-FVT-023 extension)
# ---------------------------------------------------------------------------
IPOIB_COMM_PATH_COMMANDS: dict[str, str] = {
    "tcpdump_check": "which tcpdump",
    "tcpdump_start": (
        "rm -f %s %s; "
        "timeout %s tcpdump -nn -i any -w %s "
        "'ip and (tcp port 6817 or tcp port 6818 or tcp port 6819 "
        "or tcp portrange 60001-63000)' "
        ">/dev/null 2>&1 & "
        "timeout %s tcpdump -nn -i any -w %s "
        "'ip6 and (tcp port 6817 or tcp port 6818 or tcp port 6819 "
        "or tcp portrange 60001-63000)' "
        ">/dev/null 2>&1 & "
        "echo started"
    ),
    "tcpdump_read": "tcpdump -nn -r %s 2>/dev/null",
    "tcpdump_cleanup": "rm -f %s %s",
    "srun_2node": (
        "timeout 30 srun -N2 -w %s,%s --mem=10M "
        "bash -c 'hostname; sleep %s'"
    ),
}
IPOIB_COMM_CAPTURE_TIMEOUT = 25
IPOIB_COMM_JOB_SLEEP = 5
IPOIB_COMM_SETTLE_SECONDS = 3
IPOIB_COMM_V4_PCAP = os.path.join(tempfile.gettempdir(), "omnia_fvt_comm_v4.pcap")
IPOIB_COMM_V6_PCAP = os.path.join(tempfile.gettempdir(), "omnia_fvt_comm_v6.pcap")
# Slurm port classification
IPOIB_SLURM_PORT_SLURMCTLD = 6817
IPOIB_SLURM_PORT_SLURMD = 6818
IPOIB_SLURM_PORT_SLURMDBD = 6819
IPOIB_SLURM_SRUN_PORT_RANGE = (60001, 63000)

# ---------------------------------------------------------------------------
# Non-functional benchmarks (TC-NFT-001/002)
# ---------------------------------------------------------------------------
# Product modules exercised in-process from the source tree.
ALLOCATION_VALIDATOR_PATH: tuple[str, ...] = (
    "src", "orchestrator", "plugins", "module_utils",
    "orchestrator_validation", "validators", "ib_ipv6_allocation_validator.py",
)
NM_RENDERER_PATH: tuple[str, ...] = (
    "src", "orchestrator", "plugins", "module_utils",
    "orchestrator_validation", "renderers", "nm_renderer.py",
)
IPOIB_NFT_ITERATIONS = 5
IPOIB_NFT_INTERFACES_PER_NODE = 2
IPOIB_NFT_PREFIX = "fd00:1b::"
IPOIB_NFT_PREFIX_LENGTH = 64
IPOIB_NFT_VALIDATION_RECORDS = 500
IPOIB_NFT_VALIDATION_P95_MS_PER_RECORD = 100.0
IPOIB_NFT_RENDER_NODES = 500
IPOIB_NFT_RENDER_P95_S_PER_NODE = 30.0
