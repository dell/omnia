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

"""Node connectivity and cloud-init checks owned by the PXE lifecycle."""

from ..vars.pxeboot_vars import (
    PING_RETRIES,
    PING_RETRY_DELAY_SECONDS,
    SSH_RETRIES,
    SSH_RETRY_DELAY_SECONDS,
)
from ._provision_helpers import load_context
from ._pxeboot_helpers import (
    direct_cloud_init_probe,
    group_fields,
    hostname_ssh_probe,
    ping_probe,
    retry_nodes,
    runtime_exception,
    runtime_result,
    ssh_probe,
)


def check_node_ping(host):
    """Verify ICMP reachability for every mapped administrative address."""
    try:
        context = load_context(host)
        rows = context["rows"]
        outcomes = retry_nodes(
            rows,
            lambda row: ping_probe(host, row),
            PING_RETRIES,
            PING_RETRY_DELAY_SECONDS,
        )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "PXE node ICMP reachability",
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "Unreachable nodes: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("PXE node ICMP reachability", exc)


def check_node_ssh(host):
    """Verify passwordless root SSH from the execution OIM to every node."""
    try:
        context = load_context(host)
        rows = context["rows"]
        outcomes = retry_nodes(
            rows,
            lambda row: ssh_probe(host, row),
            SSH_RETRIES,
            SSH_RETRY_DELAY_SECONDS,
        )
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "OIM-to-node passwordless SSH",
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "SSH failed for: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("OIM-to-node passwordless SSH", exc)


def check_node_hostname_ssh(host):
    """Verify OIM name resolution and passwordless SSH by mapped hostname."""
    summary = "OIM-to-node hostname resolution and SSH"
    try:
        context = load_context(host)
        rows = context["rows"]
        outcomes = {}
        for row in rows:
            outcomes[row["HOSTNAME"]] = hostname_ssh_probe(host, row)
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            summary,
            [("Mapped nodes", len(rows)), *group_fields(rows, outcomes)],
            "Hostname resolution or SSH failed for: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_node_cloud_init(host):
    """Verify cloud-init directly on every node in the PXE mapping file."""
    try:
        context = load_context(host)
        rows = context["rows"]
        outcomes = {}
        for row in rows:
            outcomes[row["HOSTNAME"]] = direct_cloud_init_probe(host, row)
        failed = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failed,
            "Mapped-node cloud-init completion",
            [
                ("Mapping", context["mapping_path"]),
                ("Mapped nodes", len(rows)),
                ("Verification mode", "direct SSH probe"),
                *group_fields(rows, outcomes),
            ],
            "Cloud-init verification failed for: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception("Mapped-node cloud-init completion", exc)
