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

Designed for HPC clusters with 500-2000 nodes where serial Ansible
URI loops are prohibitively slow (50-80 min at 1000 nodes serial
vs ~4 min at 20 parallel threads).

Replicates all logic from read_node_idrac.yml including GPU fallback
detection via PCIe device enumeration.

Usage in playbook:
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


# ─── Main module ────────────────────────────────────────────────────────────

def run_module():
    """Ansible module entry point."""
    module_args = {
        "nodes": {"type": "list", "required": True, "elements": "str"},
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

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    nodes = module.params["nodes"]
    bmc_ip_map = module.params["bmc_ip_map"]
    bmc_username = module.params["bmc_username"]
    bmc_password = module.params["bmc_password"]
    max_parallel = module.params["max_parallel"]
    connect_timeout = module.params["connect_timeout"]
    defaults = module.params["defaults"]

    result = {
        "changed": False,
        "node_params": [],
        "gpu_params": {},
        "failed_nodes": [],
        "total_nodes": len(nodes),
        "discovered_count": 0,
    }

    if module.check_mode:
        module.exit_json(**result)

    if not nodes:
        module.exit_json(**result)

    # Validate that all nodes have BMC IPs
    missing_bmc = [n for n in nodes if n not in bmc_ip_map]
    if missing_bmc:
        module.warn(
            f"No BMC IP found for {len(missing_bmc)} node(s): "
            f"{', '.join(missing_bmc[:10])}{'...' if len(missing_bmc) > 10 else ''}"
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
                    module.warn(f"iDRAC discovery failed for {hostname}: {error}")
                else:
                    result["node_params"].append(node_params)
                    if gpus:
                        result["gpu_params"][hostname] = gpus
                    result["discovered_count"] += 1
            except Exception as exc:  # pylint: disable=broad-except
                result["failed_nodes"].append(hostname)
                module.warn(f"iDRAC discovery exception for {hostname}: {exc}")

    if result["failed_nodes"]:
        module.warn(
            f"iDRAC discovery failed for {len(result['failed_nodes'])} of "
            f"{len(nodes)} node(s)"
        )

    module.exit_json(**result)


def main():
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
