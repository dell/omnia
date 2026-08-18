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
#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module,line-too-long,too-many-locals
"""
Ansible module to bulk-discover hardware specs from iDRAC Redfish API
across multiple nodes in parallel.

Supports two discovery modes:

  Heterogeneous (per-node):  Each compute node is individually queried
      via its iDRAC.  Use the ``nodes`` parameter.

  Homogeneous (per-group):  For each hardware group one sample node is
      queried and the discovered specs are replicated to every node in
      that group.  Use the ``groups`` parameter.

Exactly one of ``nodes`` or ``groups`` must be provided.

Designed for HPC clusters with 500-2000 nodes where serial Ansible
URI loops are prohibitively slow (50-80 min at 1000 nodes serial
vs ~4 min at 20 parallel threads).

GPU fallback detection via PCIe device enumeration is included.

Usage in playbook (heterogeneous):
  bulk_discover_node_specs:
    nodes: "{{ cmpt_list }}"
    bmc_ip_map: "{{ bmc_ip_map }}"
    bmc_username: "{{ bmc_username }}"
    bmc_password: "{{ bmc_password }}"
    max_parallel: 20
    connect_timeout: 60
    defaults:
      real_memory: 864
      corespersocket: 72
      threadspercore: 1
  register: bulk_discovery

Usage in playbook (homogeneous group):
  bulk_discover_node_specs:
    groups: "{{ sample_idrac_groups }}"
    bmc_ip_map: "{{ bmc_ip_map }}"
    bmc_username: "{{ bmc_username }}"
    bmc_password: "{{ bmc_password }}"
    max_parallel: 20
    connect_timeout: 60
    defaults:
      real_memory: 864
      corespersocket: 72
      threadspercore: 1
      sockets: 2
  register: bulk_discovery
"""
import json
import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from ansible.module_utils.basic import AnsibleModule


# ─── Redfish API helpers ───────────────────────────────────────────────────

def _create_ssl_context():
    """Create an unverified SSL context for iDRAC self-signed certs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _redfish_get(bmc_ip, path, username, password, timeout):
    """Perform a Redfish GET request and return parsed JSON.

    Returns (success, json_data_or_error_string).
    """
    url = f"https://{bmc_ip}{path}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-Version": "4.0",
    }

    # Build basic auth header
    import base64
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers["Authorization"] = f"Basic {credentials}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    ctx = _create_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            return (True, data)
    except urllib.error.HTTPError as exc:
        return (False, f"HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        return (False, f"URL error: {exc.reason}")
    except Exception as exc:  # pylint: disable=broad-except
        return (False, str(exc))


# ─── GPU detection ─────────────────────────────────────────────────────────

def _detect_gpus_from_processors(proc_members):
    """Extract NVIDIA GPUs from Processor members (primary detection)."""
    gpus = []
    for member in proc_members:
        if member.get("ProcessorType") != "GPU":
            continue
        manufacturer = member.get("Manufacturer", "")
        if re.search(r"nvidia", manufacturer, re.IGNORECASE):
            gpus.append(member)
    return gpus


def _detect_gpus_from_pcie(bmc_ip, username, password, timeout):
    """Fallback GPU detection via PCIe device enumeration.

    Queries PCIeDevices collection, then individual devices for ClassCode
    and manufacturer matching.
    """
    gpus = []

    # Get PCIe device list
    ok, data = _redfish_get(
        bmc_ip,
        "/redfish/v1/Chassis/System.Embedded.1/PCIeDevices",
        username, password, timeout,
    )
    if not ok or "Members" not in data:
        return gpus

    device_urls = [
        m.get("@odata.id", "") for m in data.get("Members", [])
        if m.get("@odata.id")
    ]

    # Query each PCIe device for GPU identification
    for dev_url in device_urls:
        ok, dev_data = _redfish_get(bmc_ip, dev_url, username, password, timeout)
        if not ok:
            continue

        class_code = dev_data.get("ClassCode", "")
        vendor_id = dev_data.get("VendorId", "")
        manufacturer = dev_data.get("Manufacturer", "")
        name = dev_data.get("Name", "")

        # ClassCode 0x0300 = VGA controller, 0x0302 = 3D controller
        if class_code in ("0x0300", "0x0302") and vendor_id:
            gpus.append(dev_data)
        elif (re.search(r"nvidia", manufacturer, re.IGNORECASE)
              and re.search(r"GPU|RTX|TESLA|A100|H100|L40|GB", name, re.IGNORECASE)):
            gpus.append(dev_data)

    return gpus


# ─── Per-node discovery ────────────────────────────────────────────────────

def _discover_single_node(hostname, bmc_ip, username, password,
                          timeout, defaults):
    """Discover hardware specs for a single node via iDRAC Redfish.

    Returns (hostname, node_params_dict, gpu_list, error_string_or_None).
    """
    default_memory = defaults.get("real_memory", 864)
    default_cores = defaults.get("corespersocket", 72)
    default_threads = defaults.get("threadspercore", 1)

    # ── Step 1: Read Processors ──
    ok, proc_data = _redfish_get(
        bmc_ip,
        "/redfish/v1/Systems/System.Embedded.1/Processors?$expand=*($levels=1)",
        username, password, timeout,
    )

    if ok:
        members = proc_data.get("Members", [])
        cpus = [m for m in members if m.get("ProcessorType") == "CPU"]
        gpus = _detect_gpus_from_processors(members)
    else:
        cpus = []
        gpus = []

    # ── Step 2: GPU fallback via PCIe devices ──
    if not gpus:
        gpus = _detect_gpus_from_pcie(bmc_ip, username, password, timeout)

    # ── Step 3: Read System info for memory ──
    ok, sys_data = _redfish_get(
        bmc_ip,
        "/redfish/v1/Systems/System.Embedded.1",
        username, password, timeout,
    )

    if ok:
        total_gib = (sys_data
                     .get("MemorySummary", {})
                     .get("TotalSystemMemoryGiB", default_memory))
        total_mb = int(total_gib * 1024)
        real_memory = int(total_mb * 0.90)
    else:
        real_memory = default_memory

    # ── Step 4: Build node_params ──
    sockets = max(len(cpus), 1)
    if cpus:
        cores_per_socket = cpus[0].get("TotalEnabledCores", default_cores)
        total_threads = cpus[0].get("TotalThreads", default_threads)
        total_cores = cpus[0].get("TotalCores", 1)
        threads_per_core = total_threads // max(total_cores, 1)
    else:
        cores_per_socket = default_cores
        threads_per_core = default_threads

    node_params = {
        "NodeName": hostname,
        "Sockets": sockets,
        "CoresPerSocket": cores_per_socket,
        "ThreadsPerCore": threads_per_core,
        "RealMemory": real_memory,
    }

    if gpus:
        node_params["Gres"] = f"gpu:{len(gpus)}"

    return (hostname, node_params, gpus, None)


# ─── Per-group discovery (homogeneous) ────────────────────────────────────

def _discover_group(group_name, group_nodes, bmc_ip_map, username,
                    password, timeout, defaults):
    """Discover hardware specs for a homogeneous group via iDRAC Redfish.

    Tries each node in the group sequentially until one iDRAC responds,
    then replicates the discovered specs to all nodes in the group.

    Returns (group_name, node_params_list, gpu_dict, sample_node_or_None,
             failed_bool).
    """
    default_memory = defaults.get("real_memory", 864)
    default_cores = defaults.get("corespersocket", 72)
    default_threads = defaults.get("threadspercore", 1)
    default_sockets = defaults.get("sockets", 2)

    # Try each node until one responds
    sample_hostname = None
    sample_params = None
    sample_gpus = []

    for hostname in group_nodes:
        bmc_ip = bmc_ip_map.get(hostname)
        if not bmc_ip:
            continue
        _, params, gpus, error = _discover_single_node(
            hostname, bmc_ip, username, password, timeout, defaults,
        )
        if error is None:
            sample_hostname = hostname
            sample_params = params
            sample_gpus = gpus
            break

    # Replicate discovered (or default) specs to all nodes in group
    node_params_list = []
    gpu_dict = {}

    if sample_params:
        for hostname in group_nodes:
            entry = dict(sample_params)
            entry["NodeName"] = hostname
            node_params_list.append(entry)
            if sample_gpus:
                gpu_dict[hostname] = sample_gpus
    else:
        # All iDRACs in group failed — use defaults
        for hostname in group_nodes:
            node_params_list.append({
                "NodeName": hostname,
                "Sockets": default_sockets,
                "CoresPerSocket": default_cores,
                "ThreadsPerCore": default_threads,
                "RealMemory": default_memory,
            })

    return (group_name, node_params_list, gpu_dict, sample_hostname,
            sample_params is None)


# ─── Main module ────────────────────────────────────────────────────────────

def run_module():
    """Ansible module entry point."""
    module_args = {
        "nodes": {
            "type": "list", "required": False, "default": None,
            "elements": "str",
        },
        "groups": {
            "type": "dict", "required": False, "default": None,
        },
        "bmc_ip_map": {"type": "dict", "required": True},
        "bmc_username": {"type": "str", "required": True, "no_log": True},
        "bmc_password": {"type": "str", "required": True, "no_log": True},
        "max_parallel": {
            "type": "int", "required": False, "default": 20,
        },
        "connect_timeout": {
            "type": "int", "required": False, "default": 60,
        },
        "defaults": {
            "type": "dict", "required": False, "default": {},
        },
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[("nodes", "groups")],
        required_one_of=[("nodes", "groups")],
    )

    nodes = module.params["nodes"]
    groups = module.params["groups"]
    bmc_ip_map = module.params["bmc_ip_map"]
    bmc_username = module.params["bmc_username"]
    bmc_password = module.params["bmc_password"]
    max_parallel = module.params["max_parallel"]
    connect_timeout = module.params["connect_timeout"]
    defaults = module.params["defaults"]

    # Dispatch to per-node or per-group discovery
    if groups is not None:
        _run_group_discovery(
            module, groups, bmc_ip_map, bmc_username, bmc_password,
            max_parallel, connect_timeout, defaults,
        )
    else:
        _run_node_discovery(
            module, nodes or [], bmc_ip_map, bmc_username, bmc_password,
            max_parallel, connect_timeout, defaults,
        )


def _run_node_discovery(module, nodes, bmc_ip_map, bmc_username,
                        bmc_password, max_parallel, connect_timeout,
                        defaults):
    """Heterogeneous mode: discover every node individually in parallel."""
    result = {
        "changed": False,
        "node_params": [],
        "gpu_params": {},
        "failed_nodes": [],
        "total_nodes": len(nodes),
        "discovered_count": 0,
    }

    if module.check_mode or not nodes:
        module.exit_json(**result)

    # Validate that all nodes have BMC IPs
    missing_bmc = [n for n in nodes if n not in bmc_ip_map]
    if missing_bmc:
        module.warn(
            f"No BMC IP found for {len(missing_bmc)} node(s): "
            f"{', '.join(missing_bmc[:10])}"
            f"{'...' if len(missing_bmc) > 10 else ''}"
        )

    # Parallel iDRAC discovery
    workers = min(max_parallel, len(nodes))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for hostname in nodes:
            bmc_ip = bmc_ip_map.get(hostname)
            if not bmc_ip:
                result["failed_nodes"].append(hostname)
                continue
            future = pool.submit(
                _discover_single_node,
                hostname, bmc_ip, bmc_username, bmc_password,
                connect_timeout, defaults,
            )
            futures[future] = hostname

        for future in as_completed(futures):
            hostname = futures[future]
            try:
                _, node_params, gpus, error = future.result()
                if error:
                    result["failed_nodes"].append(hostname)
                    module.warn(
                        f"iDRAC discovery failed for {hostname}: {error}"
                    )
                else:
                    result["node_params"].append(node_params)
                    if gpus:
                        result["gpu_params"][hostname] = gpus
                    result["discovered_count"] += 1
            except Exception as exc:  # pylint: disable=broad-except
                result["failed_nodes"].append(hostname)
                module.warn(
                    f"iDRAC discovery exception for {hostname}: {exc}"
                )

    if result["failed_nodes"]:
        module.warn(
            f"iDRAC discovery failed for {len(result['failed_nodes'])} of "
            f"{len(nodes)} node(s)"
        )

    module.exit_json(**result)


def _run_group_discovery(module, groups, bmc_ip_map, bmc_username,
                         bmc_password, max_parallel, connect_timeout,
                         defaults):
    """Homogeneous mode: discover one sample per group in parallel."""
    all_nodes = [h for hosts in groups.values() for h in hosts]
    result = {
        "changed": False,
        "node_params": [],
        "gpu_params": {},
        "failed_nodes": [],
        "failed_groups": [],
        "total_nodes": len(all_nodes),
        "total_groups": len(groups),
        "discovered_count": 0,
        "group_sample_nodes": {},
    }

    if module.check_mode or not groups:
        module.exit_json(**result)

    # Parallel group discovery — one thread per group
    workers = min(max_parallel, len(groups))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for group_name, group_nodes in groups.items():
            future = pool.submit(
                _discover_group,
                group_name, group_nodes, bmc_ip_map,
                bmc_username, bmc_password, connect_timeout, defaults,
            )
            futures[future] = group_name

        for future in as_completed(futures):
            group_name = futures[future]
            try:
                (_, node_params_list, gpu_dict, sample_node,
                 failed) = future.result()
                result["node_params"].extend(node_params_list)
                result["gpu_params"].update(gpu_dict)
                if sample_node:
                    result["group_sample_nodes"][group_name] = sample_node
                if failed:
                    result["failed_groups"].append(group_name)
                    module.warn(
                        f"All iDRACs failed for group '{group_name}' "
                        f"({len(groups[group_name])} nodes) — "
                        f"using defaults"
                    )
                else:
                    result["discovered_count"] += len(
                        groups[group_name]
                    )
            except Exception as exc:  # pylint: disable=broad-except
                result["failed_groups"].append(group_name)
                module.warn(
                    f"Group discovery exception for '{group_name}': "
                    f"{exc}"
                )

    if result["failed_groups"]:
        module.warn(
            f"iDRAC group discovery failed for "
            f"{len(result['failed_groups'])} of "
            f"{len(groups)} group(s)"
        )

    module.exit_json(**result)


def main():
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
